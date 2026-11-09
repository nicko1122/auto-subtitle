import pytest
from src.core.exporter import to_ass, split_vertical_columns
from src.core.font_manager import extract_font_family, FONTS_DIR
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment, SubtitleStyle


def test_split_vertical_columns_kinsoku_shori():
    # 1. Closing punctuation must never be orphaned into its own column
    line = "你和我卡在沙發兩端晃啊晃。"
    cols = split_vertical_columns(line, max_chars_per_col=12)
    assert len(cols) == 1
    assert "。" in cols[0]
    assert not any(c.startswith("。") or c.startswith("\\N。") for c in cols)

    # 2. Long text splitting respects kinsoku
    long_line = "這是一段非常非常長非常非常長的直排字幕測試內容，包含標點符號。"
    cols_long = split_vertical_columns(long_line, max_chars_per_col=12)
    assert len(cols_long) >= 2
    for c in cols_long:
        # No column should start with closing punctuation
        first_token = c.split("\\N")[0]
        assert first_token not in "，。！？；、,.!?;"


def test_to_ass_font_size_and_metrics_fidelity():
    track = SubtitleTrack(
        source_file="test.mp4",
        segments=[SubtitleSegment(id=1, start=0.0, end=2.0, text="測試字幕大小")]
    )
    # Style specifies CSS font_size 36
    style = SubtitleStyle(
        font_name="Noto Sans CJK TC",
        font_size=36,
        outline_enabled=True,
        outline_width=2.5,
        shadow_offset=2.0
    )
    ass_content = to_ass(track, style=style, res_x=1920, res_y=1080)
    
    # In ASS, 36 CSS px should convert to 48 points (36 * 96 / 72)
    style_line = [l for l in ass_content.splitlines() if l.startswith("Style: Default")][0]
    parts = style_line.split(",")
    fontsize = int(parts[2])
    assert fontsize == 48

    outline = float(parts[16])
    assert round(outline, 1) == round(2.5 * 96.0 / 72.0, 1)


def test_custom_font_family_matching_chenyuluoyan():
    chen_file = FONTS_DIR / "ChenYuluoyan-2.0-Thin.ttf"
    if chen_file.exists():
        info = extract_font_family(chen_file)
        # Family name must contain "Thin" to avoid generic fallback in libass
        assert "Thin" in info["family"] or info["family"] == "ChenYuluoyan 2.0 Thin"
