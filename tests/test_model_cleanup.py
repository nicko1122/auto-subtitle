import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from faster_whisper import audio

from src.api import server
from src.core import acoustic_analyzer, env_utils, luna_pipeline, proofreader, transcriber
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment


@pytest.mark.parametrize('failure', ['call', 'iteration', 'conversion', None])
def test_whisper_unloads_on_success_or_failure(tmp_path, monkeypatch, failure):
    audio = tmp_path / 'audio.wav'
    audio.touch()
    error = RuntimeError('inference failed')
    native = Mock()
    segment = SimpleNamespace(id=1, start=0, end=1, text='hello', words=[])
    info = SimpleNamespace(duration=1, language='en', language_probability=1)
    if failure == 'conversion':
        segment.words = [SimpleNamespace(word='hello', start=0, end=1, probability=2)]

    def segments():
        yield segment
        if failure == 'iteration':
            raise error

    model = SimpleNamespace(model=native, transcribe=Mock(return_value=(segments(), info)))
    if failure == 'call':
        model.transcribe.side_effect = error
    monkeypatch.setattr(transcriber, 'load_whisper_model', lambda *a, **kw: model)
    if failure:
        with pytest.raises((RuntimeError, ValueError)) as caught:
            transcriber.transcribe_audio(str(audio))
        if failure != 'conversion':
            assert caught.value is error
        # The exception is still alive here; unloading must not depend on its traceback being freed.
        assert caught.value.__traceback__ is not None
    else:
        assert transcriber.transcribe_audio(str(audio))['raw_segments'][0]['text'] == 'hello'
    native.unload_model.assert_called_once_with()


def test_cleanup_errors_do_not_replace_the_inference_error(tmp_path, monkeypatch):
    audio = tmp_path / 'audio.wav'
    audio.touch()
    error = RuntimeError('original inference failure')
    native = Mock()
    native.unload_model.side_effect = RuntimeError('backend unload failed')
    model = SimpleNamespace(model=native, transcribe=Mock(side_effect=error))
    monkeypatch.setattr(transcriber, 'load_whisper_model', lambda *a, **kw: model)
    monkeypatch.setattr(env_utils.torch.cuda, 'empty_cache', Mock(side_effect=RuntimeError('CUDA cache failed')))
    with pytest.raises(RuntimeError) as caught:
        transcriber.transcribe_audio(str(audio))
    assert caught.value is error
    native.unload_model.assert_called_once()


def test_failed_loader_does_not_keep_its_model_alive_during_retry():
    references = []
    class Resource:
        pass

    def loader(name, device, compute_type):
        if references:
            assert references[0]() is None, 'failed loader traceback retained the previous model'
            return 'loaded'
        resource = Resource()
        resource.cycle = resource
        references.append(weakref.ref(resource))
        raise RuntimeError('CUDA allocation failed')

    assert transcriber.load_whisper_model('base', loader=loader) == 'loaded'
    assert references[0]() is None


@pytest.mark.parametrize('failure', ['call', 'iteration'])
def test_locked_timeline_unloads_after_failure(tmp_path, monkeypatch, failure):
    path = tmp_path / 'audio.wav'
    path.touch()
    monkeypatch.setattr(audio, 'decode_audio', lambda *a, **kw: np.zeros(16000, dtype=np.float32))
    native = Mock()
    error = RuntimeError('locked inference failed')
    def segments():
        raise error
        yield
    model = SimpleNamespace(model=native, transcribe=Mock(return_value=(segments(), None)))
    if failure == 'call':
        model.transcribe.side_effect = error
    monkeypatch.setattr(acoustic_analyzer, 'load_whisper_model', lambda *a, **kw: model)
    track = SubtitleTrack(source_file='audio', segments=[SubtitleSegment(id=1, start=0, end=1, text='')])
    with pytest.raises(RuntimeError) as caught:
        acoustic_analyzer.transcribe_on_locked_timeline(str(path), track)
    assert caught.value is error
    native.unload_model.assert_called_once()


@pytest.mark.parametrize('failure', ['alignment', 'slice', 'partial_slice'])
def test_luna_unloads_model_and_removes_owned_slices(tmp_path, monkeypatch, failure):
    native = Mock()
    error = OSError('alignment or slice failed')
    segment = SimpleNamespace(start=0, end=8, text='歌詞', words=[])
    model = SimpleNamespace(model=native, align=Mock(return_value=SimpleNamespace(segments=[segment])))
    if failure == 'alignment':
        model.align.side_effect = error
    monkeypatch.setattr(luna_pipeline, 'load_whisper_model', lambda *a, **kw: model)
    slices = []
    def cut(source, start, end, output):
        path = Path(output)
        path.write_bytes(b'partial slice')
        slices.append(path)
        if failure == 'slice':
            raise error
        return False
    monkeypatch.setattr(luna_pipeline, 'cut_audio_segment', cut)
    pipeline = luna_pipeline.LunaPipeline('unused', '歌詞', output_dir=str(tmp_path))
    pipeline.org_lines = ['歌詞']
    pipeline.audio_duration = 10
    if failure == 'partial_slice':
        pipeline.step_3_and_4_alignment_and_evidence()
    else:
        with pytest.raises(OSError) as caught:
            pipeline.step_3_and_4_alignment_and_evidence()
        assert caught.value is error
    native.unload_model.assert_called_once()
    assert all(not path.exists() for path in slices)
    assert list(tmp_path.iterdir()) == []


def test_qwen_close_releases_ownership_even_if_backend_close_fails(monkeypatch):
    engine = object.__new__(proofreader.SubtitleProofreader)
    engine.llm = Mock()
    model = engine.llm
    error = RuntimeError('close failed')
    model.close.side_effect = error
    release = Mock()
    monkeypatch.setattr(proofreader, 'release_gpu_memory', release)
    with pytest.raises(RuntimeError) as caught:
        engine.close()
    assert caught.value is error
    assert engine.llm is None
    release.assert_called_once()
    engine.close()
    model.close.assert_called_once()


def test_api_closes_qwen_after_proofreading_failure(monkeypatch):
    engine = Mock()
    engine.proofread_track.side_effect = RuntimeError('proofreading failed')
    monkeypatch.setattr(server, 'SubtitleProofreader', Mock(return_value=engine))
    response = TestClient(server.app, base_url='http://localhost').post('/api/ai/proofread', json={
        'llm_provider': 'local', 'track': {'source_file': 'test', 'segments': [{'id': 1, 'start': 0, 'end': 1, 'text': 'test'}]},
    })
    assert response.status_code == 500
    assert response.json()['detail'] == 'proofreading failed'
    engine.close.assert_called_once()


def test_luna_prepares_audit_before_allocating_qwen(tmp_path, monkeypatch):
    factory = Mock(side_effect=AssertionError('must not allocate a model before input preparation'))
    monkeypatch.setattr(luna_pipeline, 'LocalQwenReasoner', factory)
    pipeline = luna_pipeline.LunaPipeline('unused', '歌詞', output_dir=str(tmp_path))
    pipeline.cue_evidence = [
        {'line_id': 1, 'org_line': '歌詞', 'candidates': {}, 'needs_review': True},
        {'line_id': 2, 'org_line': '歌詞', 'candidates': {}},
    ]
    with pytest.raises(KeyError):
        pipeline.step_5_and_6_luna_decision()
    factory.assert_not_called()


def test_luna_closes_qwen_after_reasoning_failure(tmp_path, monkeypatch):
    engine = Mock()
    engine.decide.side_effect = RuntimeError('reasoning failed')
    monkeypatch.setattr(luna_pipeline, 'LocalQwenReasoner', Mock(return_value=engine))
    pipeline = luna_pipeline.LunaPipeline('unused', '歌詞', output_dir=str(tmp_path))
    pipeline.audio_duration = 2
    pipeline.cue_evidence = [{'line_id': 1, 'org_line': '歌詞', 'candidates': {'cand_stable_ts': {'start': 0, 'end': 1}}, 'needs_review': True, 'anomalies': ['test']}]
    assert pipeline.step_5_and_6_luna_decision()[0].text == '歌詞'
    engine.close.assert_called_once()
