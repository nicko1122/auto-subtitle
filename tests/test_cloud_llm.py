import json
from unittest.mock import Mock

import pytest

from src.core import proofreader
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment


def test_cloud_proofreading_preserves_timeline(monkeypatch):
    monkeypatch.setattr(proofreader, 'load_env_config', lambda: {
        'LLM_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key', 'OPENAI_MODEL': 'test-model',
    })
    engine = proofreader.SubtitleProofreader(provider='api')
    call = Mock(return_value=json.dumps({'results': [{'id': 7, 'text': '像是隔著太平洋'}]}))
    monkeypatch.setattr(engine, '_call_llm_api', call)
    track = SubtitleTrack(source_file='test', segments=[SubtitleSegment(id=7, start=1, end=3, text='像是隔著開平洋')])
    corrected = engine.proofread_track(track, reference_script='像是隔著太平洋')
    assert corrected.segments[0].text == '像是隔著太平洋'
    assert (corrected.segments[0].id, corrected.segments[0].start, corrected.segments[0].end) == (7, 1, 3)
    assert '像是隔著太平洋' in call.call_args.args[1]


def test_local_does_not_read_cloud_configuration(monkeypatch):
    import llama_cpp
    cloud_config = Mock(side_effect=AssertionError('local mode must not read keys'))
    monkeypatch.setattr(proofreader, 'load_env_config', cloud_config)
    llm = Mock()
    llm.create_chat_completion.return_value = {'choices': [{'message': {'content': '{"results":[{"id":1,"text":"本地校對"}]}'}}]}
    monkeypatch.setattr(llama_cpp, 'Llama', Mock(return_value=llm))
    engine = proofreader.SubtitleProofreader(provider='local')
    track = SubtitleTrack(source_file='test', segments=[SubtitleSegment(id=1, start=0, end=1, text='原稿')])
    try:
        assert engine.proofread_track(track).segments[0].text == '本地校對'
        cloud_config.assert_not_called()
        llm.create_chat_completion.assert_called_once()
    finally:
        engine.close()
    llm.close.assert_called_once()


def test_missing_cloud_key_fails_only_when_cloud_is_selected(monkeypatch):
    monkeypatch.setattr(proofreader, 'load_env_config', lambda: {})
    with pytest.raises(RuntimeError, match='API Key'):
        proofreader.SubtitleProofreader(provider='api')
