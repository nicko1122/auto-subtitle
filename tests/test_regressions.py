import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api import server
from src.core import font_manager, transcriber, luna_pipeline, video_burner
from src.core.exporter import parse_srt_content, to_srt, to_vtt
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in ('UPLOADS_DIR', 'OUTPUT_DIR', 'TEMP_DIR', 'INPUTCLIP_DIR'):
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.setattr(server, name, directory)
    return TestClient(server.app, base_url='http://localhost')


@pytest.fixture
def track():
    return SubtitleTrack(source_file='probe', duration=1, segments=[SubtitleSegment(id=1, start=0, end=1, text='測試')])


@pytest.mark.parametrize('headers', [
    {'Origin': 'https://evil.example'}, {'Origin': 'null'}, {'Sec-Fetch-Site': 'cross-site'}, {'Host': 'evil.example'},
])
def test_browser_access_boundaries(client, headers):
    assert client.get('/api/assets', headers=headers).status_code == 403


def test_same_origin_and_configured_domain(client, monkeypatch):
    assert client.get('/api/health', headers={'Origin': 'http://localhost'}).status_code == 200
    monkeypatch.setenv('AUTOSUBTITLE_ALLOWED_HOSTS', 'studio.example,localhost')
    assert client.get('/api/health', headers={'Host': 'studio.example', 'Origin': 'http://studio.example'}).status_code == 200


def test_paths_cannot_escape_asset_directories(client, tmp_path):
    secret = tmp_path / 'private.txt'
    secret.write_text('private')
    (server.UPLOADS_DIR / 'escape.txt').symlink_to(secret)
    for path in (str(secret), str(server.UPLOADS_DIR / 'escape.txt'), '../private.txt'):
        with pytest.raises(HTTPException):
            server._resolve_media_path(path)
    asset = server.UPLOADS_DIR / 'valid.txt'
    asset.write_text('lyrics')
    assert server._resolve_media_path('/uploads/valid.txt') == asset


def test_upload_rejects_active_html(client):
    response = client.post('/api/upload', files={'files': ('evil.html', b'<script>alert(1)</script>', 'text/html')})
    assert response.status_code == 400
    assert not (server.UPLOADS_DIR / 'evil.html').exists()


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'ftp://example.com/font.ttf', 'https://user:pass@example.com/font.ttf'])
def test_font_urls_reject_non_public_schemes(tmp_path, url):
    with pytest.raises(ValueError):
        font_manager._download_font(url, tmp_path / 'font.ttf')


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '100.64.0.1', '::1', '::ffff:127.0.0.1'])
def test_font_urls_reject_private_addresses(tmp_path, monkeypatch, address):
    monkeypatch.setattr(font_manager.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', (address, 80))])
    connection = Mock(side_effect=AssertionError('must not connect'))
    monkeypatch.setattr(font_manager.socket, 'create_connection', connection)
    with pytest.raises(ValueError):
        font_manager._download_font('http://fonts.example/font.ttf', tmp_path / 'font.ttf')
    connection.assert_not_called()


def test_font_redirects_are_checked_and_dns_is_pinned(tmp_path, monkeypatch):
    def resolve(host, *a, **kw):
        return [(2, 1, 6, '', ('93.184.216.34' if host == 'fonts.example' else '127.0.0.1', 80))]
    monkeypatch.setattr(font_manager.socket, 'getaddrinfo', resolve)
    connect = Mock()
    monkeypatch.setattr(font_manager.socket, 'create_connection', connect)
    response = Mock(status=302)
    response.getheader.return_value = 'http://internal.example/font.ttf'
    connection = Mock()
    connection.getresponse.return_value = response
    monkeypatch.setattr(font_manager.http.client, 'HTTPConnection', Mock(return_value=connection))
    with pytest.raises(ValueError):
        font_manager._download_font('http://fonts.example/font.ttf', tmp_path / 'font.ttf')
    connect.assert_called_once_with(('93.184.216.34', 80), timeout=60)
    connection.close.assert_called_once()


def test_font_download_rejects_non_fonts_without_replacing_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(font_manager, 'FONTS_DIR', tmp_path)
    target = tmp_path / 'font.ttf'
    target.write_bytes(b'existing')
    monkeypatch.setattr(font_manager.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('93.184.216.34', 80))])
    monkeypatch.setattr(font_manager.socket, 'create_connection', Mock())
    connection = Mock()
    connection.getresponse.return_value = SimpleNamespace(status=200, read=io.BytesIO(b'not a font').read)
    monkeypatch.setattr(font_manager.http.client, 'HTTPConnection', Mock(return_value=connection))
    with pytest.raises(ValueError, match='字型'):
        font_manager.install_font_from_url('http://fonts.example/font.ttf')
    assert target.read_bytes() == b'existing'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['font.ttf']


def test_api_local_selection_is_forwarded(client, monkeypatch, track):
    media = server.UPLOADS_DIR / 'audio.wav'
    media.touch()
    monkeypatch.setattr(server, 'transcribe_audio', lambda *a, **kw: {'source_file': str(media), 'duration': 1, 'raw_segments': [track.segments[0].model_dump()]})
    factory = Mock()
    factory.return_value.proofread_track.return_value = track
    monkeypatch.setattr(server, 'SubtitleProofreader', factory)
    response = client.post('/api/ai/transcribe', data={'media_path': str(media), 'llm_provider': 'local'})
    assert response.status_code == 200
    factory.assert_called_once_with(n_gpu_layers=-1, provider='local')
    factory.reset_mock()
    response = client.post('/api/ai/proofread', json={'track': track.model_dump(), 'llm_provider': 'api'})
    assert response.status_code == 200
    factory.assert_called_once_with(n_gpu_layers=-1, provider='api')


def test_burn_outputs_do_not_overwrite_previous_results(client, monkeypatch, track):
    media = server.UPLOADS_DIR / 'video.mp4'
    media.touch()
    def burn(**kwargs):
        Path(kwargs['output_path']).write_text(kwargs['subtitles_source'].segments[0].text)
        return kwargs['output_path']
    monkeypatch.setattr(server, 'burn_subtitles_to_video', burn)
    payload = {'video_path': str(media), 'track': track.model_dump()}
    first = client.post('/api/burn', json=payload).json()
    payload['track']['segments'][0]['text'] = 'second'
    second = client.post('/api/burn', json=payload).json()
    assert first['url'] != second['url']
    assert Path(first['absolute_path']).read_text() == '測試'


def test_luna_jobs_isolate_outputs_and_treat_script_text_literally(client, monkeypatch, track, tmp_path):
    media = server.UPLOADS_DIR / 'audio.wav'
    media.touch()
    private = tmp_path / 'private.txt'
    private.write_text('must not read')
    directories = []
    def run(**kwargs):
        directory = Path(kwargs['output_dir'])
        directories.append(directory)
        assert Path(kwargs['lyrics_source']).read_text() == str(private)
        (directory / 'lyrics.srt').write_text(str(len(directories)))
        return track
    monkeypatch.setattr(server, 'run_luna_pipeline', run)
    for endpoint in ('/api/ai/transcribe', '/api/ai/align'):
        payload = {'media_path': str(media), 'script_text': str(private)}
        response = client.post(endpoint, **({'data': payload} if endpoint.endswith('transcribe') else {'json': payload}))
        assert response.status_code == 200
    assert len(set(directories)) == 2
    assert (directories[0] / 'lyrics.srt').read_text() == '1'


def test_whisper_retries_cpu_when_cuda_is_unavailable():
    cpu_model = object()
    def load(name, device, compute_type):
        if device == 'cuda':
            raise RuntimeError('CUDA unavailable')
        assert compute_type == 'int8'
        return cpu_model
    assert transcriber.load_whisper_model('base', loader=load) is cpu_model


def test_luna_uses_the_same_cpu_fallback(tmp_path, monkeypatch):
    model = Mock()
    model.align.return_value = SimpleNamespace(segments=[SimpleNamespace(start=0, end=1, words=[], text='歌詞')])
    def load(name, device):
        if device == 'cuda':
            raise RuntimeError('out of memory')
        return model
    monkeypatch.setattr(transcriber.stable_whisper, 'load_model', load)
    pipeline = luna_pipeline.LunaPipeline('unused', '歌詞', output_dir=str(tmp_path))
    pipeline.org_lines = ['歌詞']
    pipeline.audio_duration = 1
    pipeline.asr_clean_segments = [{'start': 0, 'end': 1, 'text': '歌詞'}]
    assert len(pipeline.step_3_and_4_alignment_and_evidence()) == 1
    model.align.assert_called_once()


def test_luna_repairs_missing_timestamps_and_exports_all_formats(tmp_path):
    pipeline = luna_pipeline.LunaPipeline('unused', 'a\nb\nc', output_dir=str(tmp_path))
    pipeline.audio_duration = 1
    pipeline.org_lines = ['a', 'b', 'c']
    pipeline.cue_evidence = [{'line_id': i, 'org_line': text, 'candidates': {'cand_stable_ts': {'start': 0, 'end': 0}}, 'anomalies': []} for i, text in enumerate(pipeline.org_lines, 1)]
    segments = pipeline.step_5_and_6_luna_decision()
    result = pipeline.step_7_display_rules_and_export(segments)
    assert all(0 <= s.start < s.end <= 1 for s in result.segments)
    assert all(a.end <= b.start for a, b in zip(result.segments, result.segments[1:]))
    assert all(r['status'] == 'needs_review' for r in pipeline.reviews)
    for filename in ('lyrics.srt', 'lyrics.vtt', 'lyrics.ass', 'lyrics.lrc', 'cue_evidence.json', 'review.csv', 'run_manifest.json'):
        assert (tmp_path / filename).is_file()


def test_luna_validation_rejects_invalid_times_and_wrong_text(tmp_path):
    pipeline = luna_pipeline.LunaPipeline('unused', 'original', output_dir=str(tmp_path))
    pipeline.audio_duration = 1
    pipeline.org_lines = ['original']
    pipeline.step_7_display_rules_and_export([SubtitleSegment(id=1, start=1, end=1, text='changed')])
    report = json.loads((tmp_path / 'validation.json').read_text())
    assert report['inverted_timestamps'] == 1
    assert not report['lyrics_text_100_percent_match']
    assert not report['validation_passed']


@pytest.mark.parametrize('content', [
    'WEBVTT\n\n00:01.000 --> 00:02.000\nhello\nworld\n',
    'WEBVTT\n\nidentifier\n00:00:01.000 --> 00:02.000 align:start position:10%\nhello\nworld\n',
    '1\n00:00:01,000 --> 00:00:02,000\nhello\nworld\n',
])
def test_srt_and_vtt_parse_and_roundtrip(content):
    result = parse_srt_content(content)
    assert len(result.segments) == 1
    assert (result.segments[0].start, result.segments[0].end, result.segments[0].text) == (1, 2, 'hello\nworld')
    for exporter in (to_srt, to_vtt):
        assert parse_srt_content(exporter(result)).segments == result.segments


def test_vtt_ignores_note_timestamps():
    content = 'WEBVTT\n\nNOTE comment\n00:01.000 --> 00:02.000\nignored\n\n00:02.000 --> 00:03.000\nvisible\n'
    assert [s.text for s in parse_srt_content(content).segments] == ['visible']


def test_tight_srt_without_blank_lines():
    content = '1\n00:00:01,000 --> 00:00:02,000\nfirst\n2\n00:00:02,000 --> 00:00:03,000\nsecond'
    assert [s.text for s in parse_srt_content(content).segments] == ['first', 'second']


def test_concurrent_burns_use_separate_temporary_subtitles(tmp_path, monkeypatch, track):
    media = tmp_path / 'video.mp4'
    media.touch()
    monkeypatch.setattr(video_burner, 'get_video_info', lambda *a: (320, 180, 1))
    monkeypatch.setattr(video_burner, 'check_nvenc_support', lambda: False)
    barrier = Barrier(2)
    paths = []
    def run(command, **kwargs):
        path = Path(re.search(r"ass='([^']+)'", command[command.index('-vf') + 1])[1])
        paths.append(path)
        barrier.wait(timeout=5)
        assert path.exists()
        assert '測試' in path.read_text()
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(video_burner.subprocess, 'run', run)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda i: video_burner.burn_subtitles_to_video(str(media), track, str(tmp_path / f'{i}.mp4')), range(2)))
    assert results[0] != results[1]
    assert len(set(paths)) == 2
    assert all(not p.exists() for p in paths)


def test_font_api_rejects_local_file_urls(client, tmp_path, monkeypatch):
    monkeypatch.setattr(font_manager, 'FONTS_DIR', tmp_path)
    response = client.post('/api/fonts/install', json={'url': (tmp_path / 'private').as_uri(), 'filename': 'font.ttf'})
    assert response.status_code == 400
    assert not (tmp_path / 'font.ttf').exists()


def test_frontend_names_are_not_html():
    import shutil
    import subprocess
    if not shutil.which('node'):
        pytest.skip('Node.js is required for the frontend security test')
    subprocess.run(['node', 'tests/frontend_security.cjs'], check=True, cwd=Path(__file__).resolve().parents[1])
