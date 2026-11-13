from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import server
from src.core import css_renderer, font_manager
from src.schemas.subtitle import SubtitleStyle, SubtitleTrack


def test_disabled_outline_survives_api_and_css_render(tmp_path, monkeypatch):
    media=tmp_path/'video.mp4'
    media.touch()
    monkeypatch.setattr(server,'UPLOADS_DIR',tmp_path)
    styles=[]
    def burn(**kwargs):
        styles.append(kwargs['style'])
        return kwargs['output_path']
    monkeypatch.setattr(server,'burn_subtitles_to_video',burn)
    response=TestClient(server.app,base_url='http://localhost').post('/api/burn',json={
        'video_path':str(media),'track':{'source_file':'test'},'style':{'outline_enabled':False,'outline_width':2.5},
    })
    assert response.status_code == 200
    style=styles[0]
    assert style.outline_width == 2.5
    assert not style.outline_enabled
    html=css_renderer.build_subtitle_html(style, width=1920, height=1080)
    assert '-webkit-text-stroke: 0px transparent;' in html
    assert '0px transparent' in style.to_css()


@pytest.mark.parametrize('shadow',[0,1.2,2,4,10])
def test_css_roundtrips_do_not_change_shadow(shadow):
    style=SubtitleStyle(shadow_offset=shadow)
    for _ in range(5):
        style=SubtitleStyle.from_css(style.to_css())
        assert style.shadow_offset == shadow


@pytest.mark.parametrize('enabled',[True,False])
def test_css_roundtrips_preserve_effective_outline(enabled):
    style=SubtitleStyle(outline_enabled=enabled,outline_width=2.5)
    restored=SubtitleStyle.from_css(style.to_css())
    assert restored.outline_enabled is enabled
    assert restored.outline_width == (2.5 if enabled else 0)


@pytest.fixture
def font_directories(tmp_path,monkeypatch):
    fonts=tmp_path/'fonts';fonts.mkdir()
    temp=tmp_path/'temp';temp.mkdir()
    monkeypatch.setattr(server,'FONTS_DIR',fonts)
    monkeypatch.setattr(server,'TEMP_DIR',temp)
    monkeypatch.setattr(font_manager,'FONTS_DIR',fonts)
    return fonts,temp


@pytest.mark.parametrize('endpoint',['/api/fonts/upload','/api/upload'])
@pytest.mark.parametrize('content',[b'not a font',b'\x00\x01\x00\x00broken header'])
def test_invalid_font_upload_does_not_replace_existing(endpoint,content,font_directories):
    fonts,temp=font_directories
    original=fonts/'existing.ttf';original.write_bytes(b'previous font')
    response=TestClient(server.app,base_url='http://localhost').post(endpoint,files={'files':('existing.ttf',content,'application/octet-stream')})
    assert response.status_code == 400, response.text
    assert original.read_bytes() == b'previous font'
    assert list(fonts.iterdir()) == [original]
    assert not list(temp.iterdir())


def test_valid_font_upload_is_installed(font_directories):
    source=next(Path('/usr/share/fonts').rglob('*.ttf'),None)
    if source is None:
        pytest.skip('A real system font is required')
    fonts,temp=font_directories
    content=source.read_bytes()
    response=TestClient(server.app,base_url='http://localhost').post('/api/fonts/upload',files={'files':('valid.ttf',content,'font/ttf')})
    assert response.status_code == 200,response.text
    assert (fonts/'valid.ttf').read_bytes() == content
    assert not list(temp.iterdir())


def test_interrupted_font_install_keeps_existing(font_directories,tmp_path,monkeypatch):
    fonts,_=font_directories
    original=fonts/'existing.ttf';original.write_bytes(b'previous')
    source=tmp_path/'new.ttf';source.write_bytes(b'new')
    def fail_copy(src,dest):
        Path(dest).write_bytes(b'partial')
        raise OSError('copy failed')
    monkeypatch.setattr(font_manager.shutil,'copyfile',fail_copy)
    with pytest.raises(OSError,match='copy failed'):
        font_manager.install_font_from_file(str(source),custom_filename=original.name)
    assert original.read_bytes() == b'previous'
    assert list(fonts.iterdir()) == [original]
