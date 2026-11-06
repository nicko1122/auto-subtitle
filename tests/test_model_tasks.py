from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api import server


def test_model_tasks_share_a_lock_without_blocking_other_apis(tmp_path, monkeypatch):
    media = tmp_path/'audio.wav'
    media.touch()
    monkeypatch.setattr(server,'UPLOADS_DIR',tmp_path)
    entered, release = Event(), Event()
    def transcribe(**kwargs):
        entered.set()
        assert release.wait(10)
        return {'source_file':'audio.wav','all_words':[]}
    monkeypatch.setattr(server,'transcribe_audio',transcribe)
    llm = Mock(side_effect=AssertionError('Busy request must not allocate an LLM'))
    monkeypatch.setattr(server,'SubtitleProofreader',llm)
    client = TestClient(server.app,base_url='http://localhost')
    with ThreadPoolExecutor(1) as pool:
        running = pool.submit(client.post,'/api/ai/transcribe',data={'media_path':str(media),'auto_proofread':False})
        try:
            assert entered.wait(10)
            for endpoint,options in [
                ('/api/ai/transcribe',{'data':{'media_path':str(media)}}),
                ('/api/ai/align',{'json':{'media_path':str(media),'script_text':'原詞'}}),
                ('/api/ai/transcribe-segments',{'json':{'media_path':str(media),'track':{'source_file':'test'}}}),
                ('/api/ai/proofread',{'json':{'track':{'source_file':'test'}}}),
                ('/api/burn',{'json':{'video_path':str(media)}}),
            ]:
                busy = client.post(endpoint,**options)
                assert busy.status_code == 409, busy.text
                assert busy.headers['retry-after'] == '5'
            assert client.get('/api/health').status_code == 200
            llm.assert_not_called()
        finally:
            release.set()
        assert running.result(timeout=10).status_code == 200
    assert client.post('/api/ai/transcribe',data={'media_path':str(media),'auto_proofread':False}).status_code == 200


def test_model_task_failure_releases_lock(tmp_path,monkeypatch):
    media=tmp_path/'audio.wav'
    media.touch()
    monkeypatch.setattr(server,'UPLOADS_DIR',tmp_path)
    transcribe=Mock(side_effect=[RuntimeError('inference failed'),{'source_file':'test','all_words':[]}])
    monkeypatch.setattr(server,'transcribe_audio',transcribe)
    client=TestClient(server.app,base_url='http://localhost')
    request={'media_path':str(media),'auto_proofread':False}
    assert client.post('/api/ai/transcribe',data=request).status_code == 500
    assert client.post('/api/ai/transcribe',data=request).status_code == 200
