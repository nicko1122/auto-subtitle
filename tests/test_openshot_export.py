from pathlib import Path

from src.core.exporter import parse_srt_content, to_openshot
from src.schemas.subtitle import SubtitleSegment, SubtitleTrack


def test_to_openshot_matches_consecutive_no_blank_line_format():
    track = SubtitleTrack(
        source_file="claw.mp4",
        segments=[
            SubtitleSegment(id=1, start=7.879, end=8.160, text="爪痕"),
            SubtitleSegment(id=2, start=18.359, end=21.500, text="像貓躲在你的懷裡"),
            SubtitleSegment(id=3, start=24.000, end=27.140, text="   "),
            SubtitleSegment(id=4, start=30.320, end=33.570, text="第一行<br>第二行"),
        ],
    )
    rendered = to_openshot(track)
    assert rendered == (
        "00:00:07,879 --> 00:00:08,160\n"
        "爪痕\n"
        "00:00:18,359 --> 00:00:21,500\n"
        "像貓躲在你的懷裡\n"
        "00:00:30,320 --> 00:00:33,570\n"
        "第一行\n"
        "第二行\n"
    )
    reparsed = parse_srt_content(rendered)
    assert len(reparsed.segments) == 3
    assert [s.text for s in reparsed.segments] == ["爪痕", "像貓躲在你的懷裡", "第一行\n第二行"]


def test_openshot_export_button_present_in_web_ui():
    root = Path(__file__).resolve().parents[1]
    html = (root / "src/web/templates/index.html").read_text(encoding="utf-8")
    js = (root / "src/web/static/app.js").read_text(encoding="utf-8")
    assert 'id="btn-export-openshot"' in html
    assert "btnExportOpenshot" in js
    assert "_openshot.txt" in js
