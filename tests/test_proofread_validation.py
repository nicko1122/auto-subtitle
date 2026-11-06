import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.api import server
from src.core.proofreader import SubtitleProofreader
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment


def engine(reply):
    value = SubtitleProofreader.__new__(SubtitleProofreader)
    value.provider, value.model_name, value.llm = 'local', 'mock', None
    value._call_llm_api = Mock(side_effect=reply) if isinstance(reply, Exception) else Mock(return_value=reply)
    return value


def track():
    return SubtitleTrack(source_file='test', segments=[SubtitleSegment(id=i,start=i,end=i+1,text=f'原句{i}',expected_chars=5) for i in (1,2)])


@pytest.mark.parametrize('items', [
    [{'id':1.9,'text':'錯誤'}], [{'id':True,'text':'錯誤'}], [{'id':'1','text':'錯誤'}],
    [{'id':1,'text':{'bad':'object'}}], [{'id':99,'text':'錯誤'}],
    [{'id':1,'text':'甲'},{'id':1,'text':'乙'}], [{'id':1,'text':''}],
])
def test_invalid_responses_do_not_change_subtitles(items):
    reader = engine(json.dumps({'results':items}))
    original = track()
    result = reader.proofread_track(original)
    assert result == original
    assert reader.warning
    assert not reader.last_report['complete']


@pytest.mark.parametrize('reply',[ValueError('context window exceeded'),'invalid JSON','{"results":[]}'])
def test_failed_batch_retains_original_and_reports_why(reply):
    reader = engine(reply)
    assert reader.proofread_track(track()) == track()
    assert reader.warning
    assert reader.last_report['batches'][0]['missing_ids'] == [1,2]


def test_partial_reply_and_successful_next_batch_keep_times():
    reader = engine('')
    reader._call_llm_api.side_effect = [ValueError('context limit'),'{"results":[{"id":2,"text":"正字"}]}']
    result = reader.proofread_track(track(),batch_size=1)
    assert [s.text for s in result.segments] == ['原句1','正字']
    assert [(s.id,s.start,s.end,s.expected_chars) for s in result.segments] == [(s.id,s.start,s.end,s.expected_chars) for s in track().segments]
    assert reader.last_report['batches'][0]['missing_ids'] == [1]
    assert reader.last_report['batches'][1]['accepted_ids'] == [2]
    assert reader.warning
    reader._call_llm_api.side_effect = None
    reader._call_llm_api.return_value = '{"results":[{"id":1,"text":"甲"},{"id":2,"text":"乙"}]}'
    reader.proofread_track(track())
    assert reader.warning is None
    assert reader.last_report['complete']


@pytest.mark.parametrize('endpoint',['/api/ai/proofread','/api/ai/transcribe'])
def test_api_exposes_failed_proofreading(tmp_path,monkeypatch,endpoint):
    reader = engine(ValueError('context window exceeded'))
    monkeypatch.setattr(server,'SubtitleProofreader',lambda **kw:reader)
    media = tmp_path/'test.wav'
    media.touch()
    monkeypatch.setattr(server,'UPLOADS_DIR',tmp_path)
    monkeypatch.setattr(server,'transcribe_audio',lambda **kw:{'source_file':str(media),'raw_segments':[s.model_dump() for s in track().segments]})
    options = {'json':{'track':track().model_dump()}} if endpoint.endswith('proofread') else {'data':{'media_path':str(media),'auto_proofread':'true'}}
    response = TestClient(server.app,base_url='http://localhost').post(endpoint,**options)
    assert response.status_code == 200, response.text
    assert 'context window exceeded' in response.json()['proofread_warning']
    assert not response.json()['proofread_report']['complete']
