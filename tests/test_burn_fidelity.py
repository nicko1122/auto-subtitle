import pytest
from src.core.css_renderer import build_subtitle_html
from src.core.exporter import split_vertical_columns
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


def test_css_renderer_font_size_and_metrics_fidelity():
    style = SubtitleStyle(
        font_name="Noto Sans CJK TC",
        font_size=36,
        outline_enabled=True,
        outline_width=2.5,
        shadow_offset=2.0
    )
    html = build_subtitle_html(style, width=1920, height=1080)
    assert "font-size: 36px;" in html
    assert "-webkit-text-stroke: 5.0px #000000; paint-order: stroke fill;" in html


def test_css_renderer_vertical_layout():
    style = SubtitleStyle(
        font_name="Noto Sans CJK TC", font_size=30, orientation="vertical",
        vertical_align="top", horizontal_align="right",
        padding_top=40, padding_right=50, padding_bottom=40, padding_left=40,
    )
    html = build_subtitle_html(style, width=854, height=480)
    assert "writing-mode: vertical-rl;" in html
    assert "padding: 40px 50px 40px 40px;" in html


def test_custom_font_family_matching_chenyuluoyan():
    chen_file = FONTS_DIR / "ChenYuluoyan-2.0-Thin.ttf"
    if chen_file.exists():
        info = extract_font_family(chen_file)
        # Family name must contain "Thin" to avoid generic fallback in libass
        assert "Thin" in info["family"] or info["family"] == "ChenYuluoyan 2.0 Thin"


def test_line_breaks_and_br_tag_support():
    from src.core.exporter import to_srt, to_vtt, to_openshot

    # 1. split_vertical_columns supports <br> and \n
    text_br = "第一行<br>第二行<br/>第三行"
    cols = split_vertical_columns(text_br, max_chars_per_col=10)
    assert cols == ["第\\N一\\N行", "第\\N二\\N行", "第\\N三\\N行"]

    text_nl = "第一行\n第二行"
    cols_nl = split_vertical_columns(text_nl, max_chars_per_col=10)
    assert cols_nl == ["第\\N一\\N行", "第\\N二\\N行"]

    # 2. to_srt, to_vtt, to_openshot convert <br> to newline
    track = SubtitleTrack(
        source_file="test.mp4",
        segments=[SubtitleSegment(id=1, start=0.0, end=2.0, text="上半句<br>下半句")]
    )
    srt = to_srt(track)
    assert "上半句\n下半句" in srt

    vtt = to_vtt(track)
    assert "上半句\n下半句" in vtt

    openshot = to_openshot(track)
    assert "上半句\n下半句" in openshot
