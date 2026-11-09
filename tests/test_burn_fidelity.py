import pytest
from src.core.exporter import to_ass, split_vertical_columns
from src.core.font_manager import extract_font_family, FONTS_DIR
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment, SubtitleStyle


def test_split_vertical_columns_kinsoku_shori():
    # 1. Closing punctuation and em dashes must never be orphaned into their own column
    line = "你和我卡在沙發兩端晃啊晃。"
    cols = split_vertical_columns(line, max_chars_per_col=12)
    assert len(cols) == 1
    assert "。" in cols[0]
    assert not any(c.startswith("。") or c.startswith("\\N。") for c in cols)

    # 1b. Em-dash ending must not break to orphan column
    line_dash = "本能在深處合作無間——"
    cols_dash = split_vertical_columns(line_dash, max_chars_per_col=9)
    assert len(cols_dash) == 1
    assert "—" in cols_dash[0]
    assert not any(c.startswith("—") for c in cols_dash[1:])

    # 2. Long text splitting respects kinsoku
    long_line = "這是一段非常非常長非常非常長的直排字幕測試內容，包含標點符號。"
    cols_long = split_vertical_columns(long_line, max_chars_per_col=12)
    assert len(cols_long) >= 2
    for c in cols_long:
        # No column should start with closing punctuation
        first_token = c.split("\\N")[0]
        assert first_token not in "，。！？；、,.!?;—"


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
    
    # libass 把 Fontsize 當作字型 Win 行高，故需乘上該字型的 (winAscent+winDescent)/unitsPerEm
    from src.core.font_manager import get_font_em_ratio
    ratio = get_font_em_ratio("Noto Sans CJK TC")
    style_line = [l for l in ass_content.splitlines() if l.startswith("Style: Default")][0]
    parts = style_line.split(",")
    fontsize = float(parts[2])
    assert abs(fontsize - round(36 * ratio, 2)) < 0.01

    outline = float(parts[16])
    assert round(outline, 1) == 2.5


def test_to_ass_vertical_layout_matches_css_vertical_rl():
    track = SubtitleTrack(
        source_file="test.mp4",
        segments=[SubtitleSegment(id=1, start=0.0, end=2.0, text="當世界只剩下一片漆黑。")]
    )
    style = SubtitleStyle(
        font_name="Noto Sans CJK TC", font_size=30, orientation="vertical",
        vertical_align="top", horizontal_align="right",
        padding_top=40, padding_right=50, padding_bottom=40, padding_left=40,
    )
    ass = to_ass(track, style=style, res_x=854, res_y=480)
    dialogues = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    # 每個字獨立定位，11 個字元 (含句號) 同一列
    assert len(dialogues) == 11
    import re as _re
    coords = [tuple(map(float, _re.search(r"\\pos\(([\d.]+),([\d.]+)\)", d).groups())) for d in dialogues]
    xs = {c[0] for c in coords}
    assert len(xs) == 1
    # 列中心 = 854 - 50 - 4(字幕框內距) - 0.75em
    assert abs(coords[0][0] - (854 - 50 - 4 - 30 * 0.75)) < 0.11
    # 第一字中心 = padding_top + 0.5em，每字前進 1em
    assert abs(coords[0][1] - (40 + 15)) < 0.11
    assert abs((coords[1][1] - coords[0][1]) - 30) < 0.11


def test_custom_font_family_matching_chenyuluoyan():
    chen_file = FONTS_DIR / "ChenYuluoyan-2.0-Thin.ttf"
    if chen_file.exists():
        info = extract_font_family(chen_file)
        # Family name must contain "Thin" to avoid generic fallback in libass
        assert "Thin" in info["family"] or info["family"] == "ChenYuluoyan 2.0 Thin"
