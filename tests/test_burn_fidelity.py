import pytest
from src.core.exporter import to_ass, split_vertical_columns
from src.core.font_manager import extract_font_family, FONTS_DIR
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment, SubtitleStyle


def test_split_vertical_columns_kinsoku_shori():
    # 1. Columns strictly obey max_chars_per_col (never overflow avail_height)
    # "我想戳破這死寂的感覺。" (11 chars) with max_chars_per_col=9 -> Col 1 has 9 chars, Col 2 has "覺\N。"
    line = "我想戳破這死寂的感覺。"
    cols = split_vertical_columns(line, max_chars_per_col=9)
    assert cols == ["我\\N想\\N戳\\N破\\N這\\N死\\N寂\\N的\\N感", "覺\\N。"]

    # 1b. Kinsoku Oikomi (推入下一列): if the (max+1)-th char is a non-starter punctuation (e.g. 。 or ，),
    # pull the preceding character into the next column so the column neither overflows nor starts with punctuation.
    line_oikomi = "一二三四五六七八九。"
    cols_oikomi = split_vertical_columns(line_oikomi, max_chars_per_col=9)
    assert cols_oikomi == ["一\\N二\\N三\\N四\\N五\\N六\\N七\\N八", "九\\N。"]

    # 1c. Mid-column commas do NOT cause premature column breaks (matches CSS writing-mode: vertical-rl)
    line_comma = "沒交集，不理解，被命運推到邊緣。"
    cols_comma = split_vertical_columns(line_comma, max_chars_per_col=9)
    assert cols_comma == ["沒\\N交\\N集\\N，\\N不\\N理\\N解\\N，\\N被", "命\\N運\\N推\\N到\\N邊\\N緣\\N。"]

    # 2. Long text splitting respects both max_chars_per_col and kinsoku
    long_line = "這是一段非常非常長非常非常長的直排字幕測試內容，包含標點符號。"
    cols_long = split_vertical_columns(long_line, max_chars_per_col=12)
    assert len(cols_long) >= 2
    for c in cols_long:
        tokens = c.split("\\N")
        assert len(tokens) <= 12
        assert tokens[0] not in "，。！？；、,.!?;）】』」〉》"


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


def test_line_breaks_and_br_tag_support():
    from src.core.exporter import to_srt, to_vtt

    # 1. split_vertical_columns supports <br> and \n
    text_br = "第一行<br>第二行<br/>第三行"
    cols = split_vertical_columns(text_br, max_chars_per_col=10)
    assert cols == ["第\\N一\\N行", "第\\N二\\N行", "第\\N三\\N行"]

    text_nl = "第一行\n第二行"
    cols_nl = split_vertical_columns(text_nl, max_chars_per_col=10)
    assert cols_nl == ["第\\N一\\N行", "第\\N二\\N行"]

    # 2. to_ass horizontal supports <br>
    track = SubtitleTrack(
        source_file="test.mp4",
        segments=[SubtitleSegment(id=1, start=0.0, end=2.0, text="上半句<br>下半句")]
    )
    style = SubtitleStyle(orientation="horizontal")
    ass = to_ass(track, style=style)
    assert "上半句\\N下半句" in ass

    # 3. to_srt and to_vtt convert <br> to newline
    srt = to_srt(track)
    assert "上半句\n下半句" in srt

    vtt = to_vtt(track)
    assert "上半句\n下半句" in vtt


def test_vertical_mixed_cjk_and_english_rotation_and_wrapping():
    track = SubtitleTrack(
        source_file="test.mp4",
        segments=[SubtitleSegment(id=1, start=0.0, end=2.0, text="在沙子上寫下 I love you")]
    )
    style = SubtitleStyle(
        font_name="ChenYuluoyan 2.0 Thin", font_size=47, orientation="vertical",
        vertical_align="top", horizontal_align="right",
        padding_top=29, padding_right=154, padding_bottom=12, padding_left=21,
        letter_spacing=1.0,
    )
    ass = to_ass(track, style=style, res_x=854, res_y=480)
    dialogues = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    # CJK 6 chars ("在沙子上寫下") + rotated ASCII runs ("I love" on col 1, "you" on col 2)
    assert len(dialogues) == 8
    assert any("\\frz-90}I love" in d for d in dialogues)
    assert any("\\frz-90}you" in d for d in dialogues)


def test_horizontal_margin_clamp_prevents_text_squish():
    track = SubtitleTrack(
        source_file="test.mp4",
        segments=[SubtitleSegment(id=1, start=0.0, end=2.0, text="在沙子上寫下 I love you")]
    )
    style = SubtitleStyle(
        font_name="ChenYuluoyan 2.0 Thin", font_size=40, orientation="horizontal",
        padding_left=400, padding_right=400,
    )
    ass = to_ass(track, style=style, res_x=854, res_y=480)
    style_line = [l for l in ass.splitlines() if l.startswith("Style: Default")][0]
    parts = style_line.split(",")
    margin_l, margin_r = int(parts[19]), int(parts[20])
    # Must reserve at least 25% width (or 3*font_size) so text cannot get crushed into 1-char slivers
    assert 854 - margin_l - margin_r >= 213
