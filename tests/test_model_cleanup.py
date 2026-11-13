import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api import server
from src.core import acoustic_analyzer, env_utils, luna_pipeline, proofreader, transcriber
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment


@pytest.mark.parametrize('failure', ['call', 'serialization', 'conversion', None])
def test_whisper_unloads_on_success_or_failure(tmp_path, monkeypatch, failure):
    audio = tmp_path / 'audio.wav'
    audio.touch()
    error = RuntimeError('inference failed')
    result = Mock(language='zh')
    word = {'word':'hello','start':0,'end':1,'probability':2 if failure == 'conversion' else .9}
    result.to_dict.return_value = {'segments':[{'start':0,'end':1,'text':'hello','words':[word]}]}
    if failure == 'serialization':
        result.to_dict.side_effect = error
    model = SimpleNamespace(cpu=Mock(), device=SimpleNamespace(type='cpu'), transcribe=Mock(return_value=result))
    if failure == 'call':
        model.transcribe.side_effect = error
    monkeypatch.setattr(transcriber, 'load_whisper_model', lambda *a, **kw: model)
    monkeypatch.setattr(transcriber, 'get_media_duration', lambda *a: 1)
    if failure:
        with pytest.raises((RuntimeError, ValueError)) as caught:
            transcriber.transcribe_audio(str(audio))
        if failure != 'conversion':
            assert caught.value is error
        assert caught.value.__traceback__ is not None
    else:
        assert transcriber.transcribe_audio(str(audio))['raw_segments'][0]['text'] == 'hello'
    model.cpu.assert_called_once_with()


def test_cleanup_errors_do_not_replace_the_inference_error(tmp_path, monkeypatch):
    audio = tmp_path / 'audio.wav'
    audio.touch()
    error = RuntimeError('original inference failure')
    native = Mock()
    native.cpu.side_effect = RuntimeError('backend unload failed')
    model = SimpleNamespace(cpu=native.cpu, device=SimpleNamespace(type='cuda'), transcribe=Mock(side_effect=error))
    monkeypatch.setattr(transcriber, 'load_whisper_model', lambda *a, **kw: model)
    monkeypatch.setattr(env_utils.torch.cuda, 'empty_cache', Mock(side_effect=RuntimeError('CUDA cache failed')))
    with pytest.raises(RuntimeError) as caught:
        transcriber.transcribe_audio(str(audio))
    assert caught.value is error
    native.cpu.assert_called_once()


def test_failed_loader_does_not_keep_its_model_alive_during_retry(monkeypatch):
    references = []
    class Resource:
        pass

    def loader(name, device):
        if references:
            assert references[0]() is None, 'failed loader traceback retained the previous model'
            return 'loaded'
        resource = Resource()
        resource.cycle = resource
        references.append(weakref.ref(resource))
        raise RuntimeError('CUDA allocation failed')

    monkeypatch.setattr(transcriber.stable_whisper, 'load_model', loader)
    assert transcriber.load_whisper_model() == 'loaded'
    assert references[0]() is None


@pytest.mark.parametrize('failure', ['alignment', 'slice', 'partial_slice'])
def test_luna_unloads_model_and_removes_owned_slices(tmp_path, monkeypatch, failure):
    error = OSError('alignment or slice failed')
    segment = SimpleNamespace(start=0, end=8, text='歌詞', words=[])
    model = SimpleNamespace(cpu=Mock(), align=Mock(return_value=SimpleNamespace(segments=[segment])))
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
    model.cpu.assert_called_once_with()
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


def test_luna_run_releases_memory_after_failure(tmp_path, monkeypatch):
    pipeline = luna_pipeline.LunaPipeline('unused', '', output_dir=str(tmp_path), llm_audit=False)
    error = RuntimeError('inference failed')
    monkeypatch.setattr(pipeline, 'step_1_prepare_and_manifest', Mock(side_effect=error))
    cleanup = Mock()
    monkeypatch.setattr(luna_pipeline, 'release_gpu_memory', cleanup)
    with pytest.raises(RuntimeError) as caught:
        pipeline.run()
    assert caught.value is error
    cleanup.assert_called_once()
