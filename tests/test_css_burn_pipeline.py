import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api import server
from src.core import css_renderer, video_burner
from src.schemas.subtitle import SubtitleSegment, SubtitleStyle, SubtitleTrack


def test_build_css_timeline_plan_handles_gaps_overlaps_and_dedup():
    track = SubtitleTrack(
        source_file="demo.mp4",
        duration=8.0,
        segments=[
            SubtitleSegment(id=1, start=1.0, end=3.0, text="重複句"),
            SubtitleSegment(id=2, start=2.0, end=4.0, text="第二句<br>換行"),
            SubtitleSegment(id=3, start=4.5, end=5.5, text="   "),
            SubtitleSegment(id=4, start=6.0, end=7.0, text="重複句"),
        ],
    )
    items, concat_entries = css_renderer.build_css_timeline_plan(track, video_duration=8.0)

    # 重複句 (seg 1 與 seg 4) 只應截圖一次；共 3 張不重複文字圖片
    assert len(items) == 3
    texts = [item["text"] for item in items]
    assert texts[0] == "重複句"
    assert texts[1] == "重複句\n第二句\n換行"
    assert texts[2] == "第二句\n換行"

    # 時間軸加總應精確等於 8.0s，且 seg 3 空白與前後間隔合併成 blank.png
    total = sum(dur for _, dur in concat_entries)
    assert abs(total - 8.0) < 1e-6
    assert concat_entries[0][0] == "blank.png"
    assert abs(concat_entries[0][1] - 1.0) < 1e-6
    assert concat_entries[1][0] == items[0]["file"]  # 1.0..2.0
    assert concat_entries[2][0] == items[1]["file"]  # 2.0..3.0 (overlap)
    assert concat_entries[3][0] == items[2]["file"]  # 3.0..4.0
    assert concat_entries[4][0] == "blank.png"       # 4.0..6.0 (merged blank)
    assert abs(concat_entries[4][1] - 2.0) < 1e-6
    assert concat_entries[5][0] == items[0]["file"]  # 6.0..7.0 (reused dedup)
    assert concat_entries[6][0] == "blank.png"       # 7.0..8.0

    ffconcat = css_renderer.build_ffconcat_content(concat_entries)
    assert ffconcat.startswith("ffconcat version 1.0\n")
    assert ffconcat.rstrip().endswith("file 'blank.png'")


def test_build_subtitle_html_matches_css_style_and_position():
    style = SubtitleStyle(
        font_name="ChenYuluoyan 2.0 Thin",
        font_size=36,
        primary_color="#FFCC00",
        outline_enabled=True,
        outline_width=2.5,
        outline_color="#112233",
        shadow_offset=2.0,
        opacity=0.85,
        letter_spacing=1.5,
        orientation="vertical",
        vertical_align="top",
        horizontal_align="right",
        padding_top=30,
        padding_right=40,
        pos_x=700,
        pos_y=120,
    )
    html = css_renderer.build_subtitle_html(style, width=864, height=480, font_face_uri="file:///D:/fonts/test.ttf")
    assert "url('file:///D:/fonts/test.ttf')" in html
    assert "writing-mode: vertical-rl;" in html
    assert "-webkit-text-stroke: 5.0px #112233; paint-order: stroke fill;" in html
    assert "opacity: 0.85;" in html
    assert "letter-spacing: 1.5px;" in html
    assert "left: 700px; top: 120px;" in html
    assert "transform: translate(-100%, 0%);" in html


def test_api_burn_css_only_and_async_start(tmp_path, monkeypatch):
    import time as _time
    media = tmp_path / "clip.mp4"
    media.touch()
    monkeypatch.setattr(server, "UPLOADS_DIR", tmp_path)
    calls = []

    def fake_burn(**kwargs):
        calls.append(kwargs)
        cb = kwargs.get("progress_callback")
        if cb:
            cb({"stage": "muxing", "percent": 90.0, "message": "mux"})
        return kwargs["output_path"]

    monkeypatch.setattr(server, "burn_subtitles_to_video", fake_burn)
    client = TestClient(server.app, base_url="http://localhost")

    r1 = client.post("/api/burn", json={"video_path": str(media), "track": {"source_file": "clip.mp4"}})
    assert r1.status_code == 200
    assert "render_mode" not in calls[-1]

    r2 = client.post("/api/burn/start", json={"video_path": str(media), "track": {"source_file": "clip.mp4"}})
    assert r2.status_code == 200
    task_id = r2.json()["task_id"]
    for _ in range(30):
        task = client.get(f"/api/burn/task/{task_id}").json()
        if task["stage"] in ("completed", "failed"):
            break
        _time.sleep(0.05)
    assert task["stage"] == "completed"
    assert task["result"]["status"] == "success"


def test_css_burn_cleans_temp_dir_on_failure(tmp_path, monkeypatch):
    media = tmp_path / "video.mp4"
    media.touch()
    created_dirs = []
    real_create = video_burner._create_css_work_dir

    def tracked_dir():
        d = real_create()
        created_dirs.append(d)
        return d

    monkeypatch.setattr(video_burner, "has_video_stream", lambda *_: True)
    monkeypatch.setattr(video_burner, "get_video_info", lambda *_: (640, 360, 2.0))
    monkeypatch.setattr(video_burner, "check_nvenc_support", lambda: False)
    monkeypatch.setattr(video_burner, "_create_css_work_dir", tracked_dir)

    def fake_render(*, work_dir, **kwargs):
        concat = work_dir / "subs.ffconcat"
        concat.write_text("ffconcat version 1.0\nfile 'blank.png'\nduration 2.0\nfile 'blank.png'\n", encoding="utf-8")
        return concat

    monkeypatch.setattr(video_burner, "render_css_subtitles_to_pngs", fake_render)
    monkeypatch.setattr(
        video_burner.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=1, stderr="simulated ffmpeg failure"),
    )

    track = SubtitleTrack(source_file="video.mp4", segments=[SubtitleSegment(id=1, start=0.2, end=1.2, text="測試")])
    with pytest.raises(RuntimeError, match="CSS Overlay"):
        video_burner.burn_subtitles_to_video(str(media), track, str(tmp_path / "out.mp4"))

    assert len(created_dirs) == 1
    assert not created_dirs[0].exists()


def test_end_to_end_css_burn_with_real_browser(tmp_path):
    if css_renderer.detect_headless_browser() is None:
        pytest.skip("無可用 Headless Chrome/Edge，跳過實機 CSS 渲染整合測試")

    sample_mp4 = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=#1f2937:s=640x360:d=2.0:r=24",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(sample_mp4),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )

    track = SubtitleTrack(
        source_file=str(sample_mp4),
        duration=2.0,
        segments=[
            SubtitleSegment(id=1, start=0.2, end=1.0, text="第一行<br>在沙子上寫下 I love you"),
            SubtitleSegment(id=2, start=1.3, end=1.8, text="直排與多行測試"),
        ],
    )
    style = SubtitleStyle(
        font_name="Noto Sans CJK TC",
        font_size=28,
        orientation="vertical",
        vertical_align="middle",
        horizontal_align="right",
        padding_right=24,
        outline_enabled=True,
        outline_width=2.0,
    )
    out_mp4 = tmp_path / "burned_css.mp4"
    result_path = video_burner.burn_subtitles_to_video(
        video_path=str(sample_mp4),
        subtitles_source=track,
        output_path=str(out_mp4),
        style=style,
        use_gpu=False,
    )
    assert Path(result_path).exists()
    assert Path(result_path).stat().st_size > 1024
