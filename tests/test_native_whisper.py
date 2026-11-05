from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.api import server
from src.cli import main as cli
from src.core import luna_pipeline, transcriber
from src.schemas.subtitle import SubtitleTrack


@pytest.mark.parametrize('endpoint', ['/api/ai/transcribe', '/api/ai/align'])
@pytest.mark.parametrize('model', [None, 'small'])
@pytest.mark.parametrize('audit', [True, False])
def test_scripted_api_forwards_selected_model_device_and_prompt(tmp_path, monkeypatch, endpoint, model, audit):
    for name in ('UPLOADS_DIR', 'OUTPUT_DIR', 'TEMP_DIR'):
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.setattr(server, name, directory)
    media = server.UPLOADS_DIR / 'audio.wav'
    media.touch()
    pipeline = Mock(return_value=SubtitleTrack(source_file='test', segments=[]))
    monkeypatch.setattr(server, 'run_luna_pipeline', pipeline)
    payload = {'media_path': str(media), 'script_text': '訪談逐字稿', 'device': 'cpu', 'prompt': '訪談', 'auto_proofread': audit}
    if model is not None:
        payload['model'] = model
    options = {'data': payload} if endpoint.endswith('transcribe') else {'json': payload}
    response = TestClient(server.app, base_url='http://localhost').post(endpoint, **options)
    assert response.status_code == 200, response.text
    assert pipeline.call_args.kwargs['whisper_model'] == (model or 'large-v3-turbo')
    assert pipeline.call_args.kwargs['device'] == 'cpu'
    assert pipeline.call_args.kwargs['prompt'] == '訪談'
    assert pipeline.call_args.kwargs['llm_audit'] is audit


@pytest.mark.parametrize('model', [None, 'small'])
@pytest.mark.parametrize('audit', [True, False])
def test_cli_align_forwards_model_selection(tmp_path, monkeypatch, model, audit):
    media, script = tmp_path / 'audio.wav', tmp_path / 'lyrics.txt'
    media.touch()
    script.write_text('歌詞')
    pipeline = Mock(return_value=SubtitleTrack(source_file='test', segments=[]))
    monkeypatch.setattr(cli, 'run_luna_pipeline', pipeline)
    arguments = ['luna', str(media), str(script), '-d', 'cpu', '--prompt', '訪談', '-o', str(tmp_path / 'output')]
    if model:
        arguments.extend(['-m', model])
    arguments.append('--audit' if audit else '--no-audit')
    result = CliRunner().invoke(cli.app, arguments)
    assert result.exit_code == 0, result.output
    assert pipeline.call_args.kwargs['whisper_model'] == (model or 'large-v3-turbo')
    assert pipeline.call_args.kwargs['device'] == 'cpu'
    assert pipeline.call_args.kwargs['prompt'] == '訪談'
    assert pipeline.call_args.kwargs['llm_audit'] is audit


def test_luna_uses_selected_native_model_for_both_phases(tmp_path, monkeypatch):
    asr = Mock(return_value={'raw_segments': [{'id': 1, 'start': 0, 'end': 1, 'text': '歌詞', 'words': []}]})
    model = SimpleNamespace(cpu=Mock(), align=Mock(return_value=SimpleNamespace(segments=[SimpleNamespace(start=0, end=1, text='歌詞', words=[])])))
    loader = Mock(return_value=model)
    monkeypatch.setattr(luna_pipeline, 'transcribe_native_audio', asr)
    monkeypatch.setattr(luna_pipeline, 'load_native_whisper_model', loader)
    pipeline = luna_pipeline.LunaPipeline('unused', '歌詞', output_dir=str(tmp_path), whisper_model='small', device='cpu', prompt='訪談')
    pipeline.org_lines = ['歌詞']
    pipeline.audio_duration = 1
    pipeline.step_2_whisper_full_asr()
    pipeline.step_3_and_4_alignment_and_evidence()
    assert asr.call_args.kwargs['model_size'] == 'small'
    assert asr.call_args.kwargs['device'] == 'cpu'
    assert asr.call_args.kwargs['initial_prompt'] == '訪談'
    loader.assert_called_once_with('small', 'cpu')
    model.cpu.assert_called_once_with()


@pytest.mark.parametrize('failure', [None, 'transcribe', 'conversion'])
@pytest.mark.parametrize('device', ['cpu', 'cuda'])
def test_native_asr_unloads_on_success_or_failure(tmp_path, monkeypatch, failure, device):
    audio = tmp_path / 'audio.wav'
    audio.touch()
    words = [{'word': '測試', 'start': 0, 'end': 1, 'probability': 2 if failure == 'conversion' else .9}]
    result = transcriber.stable_whisper.WhisperResult({'language': 'zh', 'segments': [{'start': 0, 'end': 1, 'text': '測試', 'words': words}]})
    model = SimpleNamespace(device=SimpleNamespace(type=device), cpu=Mock(), transcribe=Mock(return_value=result))
    if failure == 'transcribe':
        model.transcribe.side_effect = RuntimeError('native inference failed')
    loader = Mock(return_value=model)
    monkeypatch.setattr(transcriber, 'load_native_whisper_model', loader)
    monkeypatch.setattr(transcriber, 'get_media_duration', lambda path: 2)
    if failure:
        with pytest.raises((RuntimeError, ValueError)) as caught:
            transcriber.transcribe_native_audio(str(audio), 'small', device, '訪談')
        assert caught.value.__traceback__ is not None
    else:
        data = transcriber.transcribe_native_audio(str(audio), 'small', device, '訪談')
        assert data['duration'] == 2
        assert data['whisper_backend'] == 'native'
        assert data['whisper_model'] == 'small'
        assert data['raw_segments'][0]['id'] == 1
        assert data['all_words'][0]['probability'] == .9
    assert model.transcribe.call_args.kwargs['fp16'] is (device == 'cuda')
    assert model.transcribe.call_args.kwargs['suppress_silence'] is True
    model.cpu.assert_called_once_with()


def test_native_loader_rejects_checkpoint_paths(tmp_path, monkeypatch):
    checkpoint = tmp_path / 'untrusted.pt'
    checkpoint.touch()
    loader = Mock()
    monkeypatch.setattr(transcriber.stable_whisper, 'load_model', loader)
    with pytest.raises(ValueError, match='不支援'):
        transcriber.load_native_whisper_model(str(checkpoint))
    loader.assert_not_called()


def test_luna_preserves_native_sung_word_onsets(tmp_path, monkeypatch):
    word = {'word': '真的', 'start': 183.82, 'end': 185.18, 'probability': .9}
    monkeypatch.setattr(luna_pipeline, 'transcribe_native_audio', lambda **kwargs: {'raw_segments': [{'id': 1, 'start': word['start'], 'end': word['end'], 'text': '真的', 'words': [word]}]})
    pipeline = luna_pipeline.LunaPipeline('unused', '真的', output_dir=str(tmp_path))
    segment = pipeline.step_2_whisper_full_asr()[0]
    assert segment['start'] == 183.82
    assert segment['words'][0] == word
