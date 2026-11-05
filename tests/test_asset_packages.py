import io
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import asset_packages, server

SRT = '1\n00:00:00,123 --> 00:00:01,456\n原始字幕\n第二行\n'


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in ('UPLOADS_DIR', 'OUTPUT_DIR', 'TEMP_DIR', 'INPUTCLIP_DIR'):
        path = tmp_path / name
        path.mkdir()
        monkeypatch.setattr(server, name, path)
    monkeypatch.setattr(server, 'get_video_info', lambda *args: (320, 180, 2))
    return TestClient(server.app, base_url='http://localhost')


def upload(client, prefix='', stem='影片'):
    result = client.post('/api/upload', files=[
        ('files', (prefix + stem + '.Mp4', b'video', 'video/mp4')),
        ('files', (prefix + stem + '.Srt', SRT.encode(), 'text/plain')),
        ('files', (prefix + '原詞.txt', '原詞內容'.encode(), 'text/plain')),
    ])
    assert result.status_code == 200, result.text
    return result.json()['packages'][0]


def test_import_bundle_open_and_save_one_srt(client):
    package = upload(client, '訪談資產包/')
    directory = server.UPLOADS_DIR / package['path']
    assert package['name'] == '訪談資產包'
    opened = client.post('/api/packages/open', json={'path': package['path']}).json()
    assert opened['script_text'] == '原詞內容'
    assert opened['track']['segments'][0]['text'] == '原始字幕\n第二行'
    assert opened['track']['segments'][0]['start'] == .123
    opened['track']['segments'][0]['text'] = '繼續編輯'
    saved = client.post('/api/packages/save', json={'path': package['path'], 'track': opened['track'], 'script_text': '更新原詞'})
    assert saved.status_code == 200
    reopened = client.post('/api/packages/open', json={'path': package['path']}).json()
    assert reopened['track']['segments'][0]['text'] == '繼續編輯'
    assert reopened['script_text'] == '更新原詞'
    assert reopened['track']['segments'][0]['start'] == .123
    assert sorted(p.suffix.lower() for p in directory.iterdir()) == ['.mp4', '.srt', '.txt']


def test_missing_companions_are_empty_and_created_on_save(client):
    response = client.post('/api/upload', files={'files': ('空白.mp4', b'video', 'video/mp4')})
    package = response.json()['packages'][0]
    opened = client.post('/api/packages/open', json={'path': package['path']}).json()
    assert opened['track']['segments'] == []
    assert opened['script_text'] == ''
    assert [p.suffix for p in (server.UPLOADS_DIR / package['path']).iterdir()] == ['.mp4']
    opened['track']['segments'] = [{'id': 1, 'start': 0, 'end': 1, 'text': '新字幕'}]
    result = client.post('/api/packages/save', json={'path': package['path'], 'track': opened['track']})
    assert result.status_code == 200
    assert (server.UPLOADS_DIR / package['path'] / '空白.srt').exists()
    assert not (server.UPLOADS_DIR / package['path'] / '空白.txt').exists()


def test_clearing_subtitles_is_persisted(client):
    package = upload(client)
    assert client.post('/api/packages/save', json={'path': package['path'], 'track': {'source_file': 'test', 'segments': []}}).status_code == 200
    assert client.post('/api/packages/open', json={'path': package['path']}).json()['track']['segments'] == []


def test_same_names_in_different_packages_never_cross_pair(client):
    first = upload(client, '甲/')
    second = upload(client, '乙/')
    packages = client.get('/api/assets').json()['packages']
    assert len(packages) == 2
    for package in packages:
        assert package['path'] in (first['path'], second['path'])
        for field in ('media', 'subtitle', 'script'):
            assert Path(package[field]['absolute_path']).parent.name == package['name']
        assert package['media']['paired_subtitle']['package_path'] == package['path']


def test_reimport_does_not_overwrite_existing_bundle(client):
    first = upload(client)
    second = upload(client)
    assert first['path'] != second['path']
    assert (server.UPLOADS_DIR / first['path'] / '影片.Mp4').read_bytes() == b'video'


def test_attach_companions_reuses_existing_filenames(client):
    package = upload(client)
    response = client.post('/api/upload', data={'package_path': package['path']}, files=[
        ('files', ('新版.srt', SRT.replace('原始字幕', '新版字幕').encode(), 'text/plain')),
        ('files', ('別名.txt', '新原稿'.encode(), 'text/plain')),
    ])
    assert response.status_code == 200, response.text
    directory = server.UPLOADS_DIR / package['path']
    assert len(list(directory.iterdir())) == 3
    assert '新版字幕' in (directory / package['subtitle']['name']).read_text()
    assert (directory / package['script']['name']).read_text() == '新原稿'


def test_import_multiple_flat_bundles_matches_by_stem(client):
    response = client.post('/api/upload', files=[
        ('files', ('A.mp4', b'a', 'video/mp4')), ('files', ('B.mp4', b'b', 'video/mp4')),
        ('files', ('A.srt', SRT.replace('原始字幕', 'A字幕').encode(), 'text/plain')),
        ('files', ('B.srt', SRT.replace('原始字幕', 'B字幕').encode(), 'text/plain')),
    ])
    assert response.status_code == 200, response.text
    assert {p['name'] for p in response.json()['packages']} == {'A', 'B'}
    for name in ('A', 'B'):
        assert name + '字幕' in (server.UPLOADS_DIR / name / (name + '.srt')).read_text()


def test_ambiguous_import_is_rejected_before_creating_packages(client):
    response = client.post('/api/upload', files=[
        ('files', ('A.mp4', b'a', 'video/mp4')), ('files', ('B.mp4', b'b', 'video/mp4')),
        ('files', ('不明原詞.txt', b'text', 'text/plain')),
    ])
    assert response.status_code == 400
    assert list(server.UPLOADS_DIR.iterdir()) == []


def test_bundle_rename_move_and_delete(client):
    package = upload(client, '原包/')
    for destination in ('新包', '客戶/新包'):
        response = client.post('/api/packages/move', json={'path': package['path'], 'destination': destination})
        assert response.status_code == 200, response.text
        package = response.json()['package']
        assert package['path'] == destination
        assert client.post('/api/packages/open', json={'path': destination}).status_code == 200
    other = upload(client, '保留/')
    assert client.delete('/api/packages', params={'path': package['path']}).status_code == 200
    assert not (server.UPLOADS_DIR / package['path']).exists()
    assert (server.UPLOADS_DIR / other['path']).is_dir()


def test_move_collision_and_move_into_self_preserve_sources(client):
    first = upload(client, '甲/')
    second = upload(client, '乙/')
    for destination, expected in ((second['path'], 409), (first['path'] + '/子包', 400)):
        response = client.post('/api/packages/move', json={'path': first['path'], 'destination': destination})
        assert response.status_code == expected
    assert (server.UPLOADS_DIR / first['path']).is_dir()
    assert (server.UPLOADS_DIR / second['path']).is_dir()


@pytest.mark.parametrize('path', ['.', '..', '../outside', '/tmp', 'a/../../outside', 'a\\b', '.hidden'])
def test_paths_cannot_escape_package_root(client, path):
    for endpoint in ('open', 'save'):
        assert client.post('/api/packages/' + endpoint, json={'path': path}).status_code == 400
    assert client.delete('/api/packages', params={'path': path}).status_code == 400


def test_symlink_bundle_is_not_followed(client, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'private.mp4').write_bytes(b'private')
    (server.UPLOADS_DIR / 'escape').symlink_to(outside, target_is_directory=True)
    assert client.post('/api/packages/open', json={'path': 'escape'}).status_code == 400
    assert client.delete('/api/packages', params={'path': 'escape'}).status_code == 400
    assert (outside / 'private.mp4').exists()


def test_mixed_case_existing_files_and_language_subtitles_are_preserved(client):
    directory = server.UPLOADS_DIR / '既有包'
    directory.mkdir()
    (directory / '訪談.Mp4').write_bytes(b'video')
    (directory / '訪談.Srt').write_text(SRT)
    (directory / '訪談_EN.srt').write_text(SRT.replace('原始字幕', 'English'))
    package = client.post('/api/packages/open', json={'path': '既有包'}).json()
    assert package['package']['subtitle']['name'] == '訪談.Srt'
    assert client.post('/api/packages/save', json={'path': '既有包', 'track': package['track']}).status_code == 200
    assert len(list(directory.glob('*'))) == 3
    assert 'English' in (directory / '訪談_EN.srt').read_text()


def test_special_characters_in_urls_are_escaped(client):
    package = upload(client, '訪談 #1/', '影片 #1')
    assert '%23' in package['media']['url']
    assert ' ' not in package['media']['url']
    assert '%E8' in package['media']['url']


def test_atomic_save_keeps_previous_srt_if_publish_fails(client, monkeypatch):
    package = upload(client)
    path = Path(package['subtitle']['absolute_path'])
    original = path.read_text()
    def fail_replace(*args):
        raise OSError('disk failure')
    monkeypatch.setattr(Path, 'replace', fail_replace)
    with pytest.raises(OSError):
        asset_packages.atomic_write(path, 'new subtitle')
    assert path.read_text() == original
    assert len(list(path.parent.iterdir())) == 3


def test_concurrent_imports_do_not_overwrite_each_other(client):
    def create(index):
        return asset_packages.import_files(server.UPLOADS_DIR, '訪談', [('訪談.mp4', io.BytesIO(str(index).encode()))])
    with ThreadPoolExecutor(2) as pool:
        paths = list(pool.map(create, (1, 2)))
    assert paths[0] != paths[1]
    assert {(p / '訪談.mp4').read_bytes() for p in paths} == {b'1', b'2'}


def test_invalid_bundle_does_not_hide_valid_packages(client):
    upload(client, '正常/')
    invalid = server.UPLOADS_DIR / '兩支影片'
    invalid.mkdir()
    (invalid / 'a.mp4').touch()
    (invalid / 'b.mp4').touch()
    response = client.get('/api/assets')
    assert response.status_code == 200
    packages = response.json()['packages']
    assert any(p.get('media') for p in packages)
    assert any(p.get('error') for p in packages)


def test_frontend_package_workflow():
    if not shutil.which('node'):
        pytest.skip('Node.js is required for the frontend workflow test')
    subprocess.run(['node', 'tests/package_workflow.cjs'], check=True, cwd=Path(__file__).resolve().parents[1])


def test_folder_import_ignores_unrelated_and_hidden_files(client):
    response = client.post('/api/upload', files=[
        ('files', ('訪談/影片.mp4', b'video', 'video/mp4')),
        ('files', ('訪談/.DS_Store', b'ignore', 'application/octet-stream')),
        ('files', ('訪談/縮圖.jpg', b'ignore', 'image/jpeg')),
    ])
    assert response.status_code == 200, response.text
    directory = server.UPLOADS_DIR / response.json()['packages'][0]['path']
    assert [p.name for p in directory.iterdir()] == ['影片.mp4']


def test_cannot_nest_a_package_inside_another_package(client):
    first = upload(client, '甲/')
    second = upload(client, '乙/')
    response = client.post('/api/packages/move', json={'path': first['path'], 'destination': second['path'] + '/甲'})
    assert response.status_code == 400
    assert (server.UPLOADS_DIR / first['path']).exists()
