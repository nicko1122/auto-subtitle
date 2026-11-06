from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.api import server
from src.cli import main as cli
from src.core import acoustic_analyzer, luna_pipeline, transcriber
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment


@pytest.mark.parametrize('command',['transcribe','pipeline'])
def test_unscripted_cli_has_no_model_or_precision_selector(tmp_path,monkeypatch,command):
    media=tmp_path/'audio.wav';media.touch()
    asr=Mock(return_value={'source_file':str(media),'duration':1,'language':'zh','raw_segments':[],'all_words':[]})
    monkeypatch.setattr(cli,'transcribe_audio',asr)
    arguments=[command,str(media),'-o',str(tmp_path/('raw.json' if command=='transcribe' else 'result'))]
    result=CliRunner().invoke(cli.app,arguments)
    assert result.exit_code==0,result.output
    assert 'model_size' not in asr.call_args.kwargs
    assert 'compute_type' not in asr.call_args.kwargs
    for options in [['--model','small'],['-m','large-v3'],['--compute-type','int8']]:
        assert CliRunner().invoke(cli.app,arguments+options).exit_code==2


@pytest.mark.parametrize('endpoint',['/api/ai/transcribe','/api/ai/align'])
@pytest.mark.parametrize('audit',[True,False])
@pytest.mark.parametrize('script_mode',[None,'reference'])
def test_scripted_api_cannot_select_another_model(tmp_path,monkeypatch,endpoint,audit,script_mode):
    for name in ['UPLOADS_DIR','OUTPUT_DIR','TEMP_DIR']:
        directory=tmp_path/name;directory.mkdir();monkeypatch.setattr(server,name,directory)
    media=server.UPLOADS_DIR/'audio.wav';media.touch()
    pipeline=Mock(return_value=SubtitleTrack(source_file='test'))
    monkeypatch.setattr(server,'run_luna_pipeline',pipeline)
    payload={'media_path':str(media),'script_text':'原詞','model':'small','device':'cpu','prompt':'訪談','auto_proofread':audit}
    if script_mode:payload['script_mode']=script_mode
    response=TestClient(server.app,base_url='http://localhost').post(endpoint,**({'data':payload} if endpoint.endswith('transcribe') else {'json':payload}))
    assert response.status_code==200,response.text
    assert 'whisper_model' not in pipeline.call_args.kwargs
    assert pipeline.call_args.kwargs['device']=='cpu'
    assert pipeline.call_args.kwargs['prompt']=='訪談'
    assert pipeline.call_args.kwargs['llm_audit'] is audit
    assert pipeline.call_args.kwargs['script_mode']==(script_mode or 'transcript')


@pytest.mark.parametrize('endpoint',['/api/ai/transcribe','/api/ai/transcribe-segments'])
def test_unscripted_and_locked_apis_ignore_stale_model_choices(tmp_path,monkeypatch,endpoint):
    media=tmp_path/'audio.wav';media.touch()
    monkeypatch.setattr(server,'UPLOADS_DIR',tmp_path)
    function=Mock(return_value={'source_file':'test','all_words':[]} if endpoint.endswith('transcribe') else SubtitleTrack(source_file='test'))
    monkeypatch.setattr(server,'transcribe_audio' if endpoint.endswith('transcribe') else 'transcribe_on_locked_timeline',function)
    payload={'media_path':str(media),'model':'/tmp/untrusted.pt','auto_proofread':False}
    if endpoint.endswith('segments'):payload['track']={'source_file':'test'}
    response=TestClient(server.app,base_url='http://localhost').post(endpoint,**({'data':payload} if endpoint.endswith('transcribe') else {'json':payload}))
    assert response.status_code==200,response.text
    assert 'model_size' not in function.call_args.kwargs


@pytest.mark.parametrize('audit',[True,False])
@pytest.mark.parametrize('script_mode',[None,'reference'])
def test_cli_align_has_fixed_model(tmp_path,monkeypatch,audit,script_mode):
    media,script=tmp_path/'audio.wav',tmp_path/'lyrics.txt'
    media.touch();script.write_text('歌詞')
    pipeline=Mock(return_value=SubtitleTrack(source_file='test'))
    monkeypatch.setattr(cli,'run_luna_pipeline',pipeline)
    arguments=['luna',str(media),str(script),'-d','cpu','--prompt','訪談','-o',str(tmp_path/'output')]
    if script_mode:arguments+=['--script-mode',script_mode]
    arguments+=['--audit' if audit else '--no-audit']
    result=CliRunner().invoke(cli.app,arguments)
    assert result.exit_code==0,result.output
    assert 'whisper_model' not in pipeline.call_args.kwargs
    assert pipeline.call_args.kwargs['llm_audit'] is audit
    assert CliRunner().invoke(cli.app,arguments+['-m','small']).exit_code==2


def test_luna_uses_the_shared_native_transcriber_and_loader(tmp_path,monkeypatch):
    asr=Mock(return_value={'raw_segments':[{'id':1,'start':0,'end':1,'text':'歌詞','words':[]}]})
    model=SimpleNamespace(cpu=Mock(),align=Mock(return_value=SimpleNamespace(segments=[SimpleNamespace(start=0,end=1,text='歌詞',words=[])])))
    loader=Mock(return_value=model)
    monkeypatch.setattr(luna_pipeline,'transcribe_audio',asr)
    monkeypatch.setattr(luna_pipeline,'load_whisper_model',loader)
    pipeline=luna_pipeline.LunaPipeline('unused','歌詞',output_dir=str(tmp_path),device='cpu',prompt='訪談')
    pipeline.org_lines=['歌詞'];pipeline.audio_duration=1
    pipeline.step_2_whisper_full_asr();pipeline.step_3_and_4_alignment_and_evidence()
    assert 'model_size' not in asr.call_args.kwargs
    assert asr.call_args.kwargs['device']=='cpu'
    loader.assert_called_once_with('cpu')
    model.cpu.assert_called_once_with()


@pytest.mark.parametrize('failure',[None,'transcribe','conversion'])
@pytest.mark.parametrize('device',['cpu','cuda'])
def test_native_asr_unloads_on_success_or_failure(tmp_path,monkeypatch,failure,device):
    audio=tmp_path/'audio.wav';audio.touch()
    words=[{'word':'測試','start':0,'end':1,'probability':2 if failure=='conversion' else .9}]
    result=transcriber.stable_whisper.WhisperResult({'language':'zh','segments':[{'start':0,'end':1,'text':'測試','words':words}]})
    model=SimpleNamespace(device=SimpleNamespace(type=device),cpu=Mock(),transcribe=Mock(return_value=result))
    if failure=='transcribe':model.transcribe.side_effect=RuntimeError('native inference failed')
    monkeypatch.setattr(transcriber,'load_whisper_model',Mock(return_value=model))
    monkeypatch.setattr(transcriber,'get_media_duration',lambda path:2)
    if failure:
        with pytest.raises((RuntimeError,ValueError)):
            transcriber.transcribe_audio(str(audio),device=device,initial_prompt='訪談')
    else:
        data=transcriber.transcribe_audio(str(audio),device=device,initial_prompt='訪談')
        assert data['whisper_backend']=='native'
        assert data['whisper_model']=='large-v3-turbo'
        assert data['raw_segments'][0]['id']==1
        assert data['all_words'][0]['probability']==.9
    assert model.transcribe.call_args.kwargs['fp16'] is (device=='cuda')
    assert model.transcribe.call_args.kwargs['suppress_silence'] is True
    model.cpu.assert_called_once_with()


def test_loader_always_uses_native_turbo_and_has_no_model_parameter(monkeypatch):
    loader=Mock(return_value=object())
    monkeypatch.setattr(transcriber.stable_whisper,'load_model',loader)
    transcriber.load_whisper_model(device='cpu')
    loader.assert_called_once_with('large-v3-turbo',device='cpu')
    for kwargs in [{'model_size':'small'},{'model_size':'/tmp/untrusted.pt'}]:
        with pytest.raises(TypeError):transcriber.load_whisper_model(**kwargs)
    assert loader.call_count==1


def test_locked_native_slices_keep_timestamps_and_use_native_token_limit(tmp_path,monkeypatch):
    import numpy as np
    media=tmp_path/'audio.wav';media.touch()
    monkeypatch.setattr(acoustic_analyzer,'load_audio',lambda *a,**kw:np.zeros(160000,dtype=np.float32))
    model=SimpleNamespace(device=SimpleNamespace(type='cuda'),cpu=Mock(),transcribe=Mock(return_value=SimpleNamespace(segments=[SimpleNamespace(text='固定模型')])) )
    monkeypatch.setattr(acoustic_analyzer,'load_whisper_model',Mock(return_value=model))
    track=SubtitleTrack(source_file='test',segments=[SubtitleSegment(id=1,start=1,end=3,text=''),SubtitleSegment(id=2,start=4,end=5,text='手動保留')])
    result=acoustic_analyzer.transcribe_on_locked_timeline(str(media),track,only_empty=True)
    assert [(s.start,s.end) for s in result.segments]==[(1,3),(4,5)]
    assert [s.text for s in result.segments]==['固定模型','手動保留']
    assert model.transcribe.call_count==1
    assert 'sample_len' in model.transcribe.call_args.kwargs
    assert 'max_new_tokens' not in model.transcribe.call_args.kwargs
    model.cpu.assert_called_once()


def test_model_choice_is_absent_from_ui_and_openapi():
    client=TestClient(server.app,base_url='http://localhost')
    assert client.get('/api/health').json()['whisper']=={'model':'large-v3-turbo','backend':'native'}
    html=client.get('/').text
    assert 'select-whisper-model' not in html
    assert 'Large-v3-turbo · 原生' in html
    schemas=client.get('/openapi.json').json()['components']['schemas']
    for name in ['AlignRequest','TranscribeLockedRequest']:
        assert 'model' not in schemas[name]['properties']
    form=next(value for key,value in schemas.items() if key.startswith('Body_transcribe_endpoint'))
    assert 'model' not in form['properties']


def test_luna_preserves_native_sung_word_onsets(tmp_path,monkeypatch):
    word={'word':'真的','start':183.82,'end':185.18,'probability':.9}
    monkeypatch.setattr(luna_pipeline,'transcribe_audio',lambda **kw:{'raw_segments':[{'id':1,'start':word['start'],'end':word['end'],'text':'真的','words':[word]}]})
    pipeline=luna_pipeline.LunaPipeline('unused','真的',output_dir=str(tmp_path))
    segment=pipeline.step_2_whisper_full_asr()[0]
    assert segment['start']==183.82
    assert segment['words'][0]==word
