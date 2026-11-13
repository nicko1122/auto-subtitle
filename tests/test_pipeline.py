from src.schemas.subtitle import WordItem, SubtitleSegment, SubtitleTrack, SegmentationConfig, SubtitleStyle
from src.core.segmenter import split_words_into_segments, build_subtitle_track
from src.core.exporter import to_srt, to_vtt, to_json, parse_srt_content, split_vertical_columns
from src.core.font_manager import get_font_catalog
from src.core.acoustic_analyzer import analyze_audio_breakpoints, snap_time_to_valley


def test_segmentation_by_punctuation():
    words = [
        WordItem(word="大家", start=0.0, end=0.4),
        WordItem(word="好，", start=0.4, end=0.8),
        WordItem(word="歡迎", start=0.9, end=1.3),
        WordItem(word="收看。", start=1.3, end=1.8),
    ]
    cfg = SegmentationConfig(max_chars=16, pause_threshold=0.5, split_on_punctuation=True)
    segments = split_words_into_segments(words, cfg)
    
    assert len(segments) == 2
    assert segments[0].text == "大家好，"
    assert segments[0].start == 0.0
    assert segments[0].end == 0.8
    assert segments[1].text == "歡迎收看。"
    assert segments[1].start == 0.9
    assert segments[1].end == 1.8


def test_segmentation_by_pause():
    words = [
        WordItem(word="第一句", start=0.0, end=0.5),
        # 停頓 1.5 秒 (0.5 -> 2.0)
        WordItem(word="第二句", start=2.0, end=2.5),
    ]
    cfg = SegmentationConfig(max_chars=16, pause_threshold=0.5, split_on_punctuation=True)
    segments = split_words_into_segments(words, cfg)

    assert len(segments) == 2
    assert segments[0].text == "第一句"
    assert segments[1].text == "第二句"


def test_segmentation_by_length():
    # 超過 10 個字自動切斷
    words = [WordItem(word=f"字{i}", start=float(i), end=float(i)+0.5) for i in range(15)]
    cfg = SegmentationConfig(max_chars=10, pause_threshold=1.0)
    segments = split_words_into_segments(words, cfg)

    assert len(segments) >= 2


def test_export_and_parse_srt():
    track = SubtitleTrack(
        source_file="test.mp4",
        duration=3.0,
        language="zh",
        segments=[
            SubtitleSegment(id=1, start=0.5, end=2.1, text="測試字幕")
        ]
    )
    srt_out = to_srt(track)
    assert "1\n00:00:00,500 --> 00:00:02,100\n測試字幕" in srt_out

    parsed = parse_srt_content("\ufeff" + srt_out)
    assert len(parsed.segments) == 1
    assert parsed.segments[0].text == "測試字幕"
    assert abs(parsed.segments[0].start - 0.5) < 0.01


def test_css_and_vertical_wrapping():
    css = """
    font-size: 40px;
    color: #FFD700;
    -webkit-text-stroke: 3px #1F1F1F;
    writing-mode: vertical-rl;
    text-align: right;
    vertical-align: top;
    padding: 60px 50px;
    """
    style = SubtitleStyle.from_css(css)
    assert style.font_size == 40
    assert style.primary_color == "#FFD700"
    assert style.outline_color == "#1F1F1F"
    assert style.orientation == "vertical"
    assert style.padding_top == 60
    assert style.padding_right == 50

    cols = split_vertical_columns("這是一段非常長的直式字幕，應該在標點處自動換成第二列顯示", max_chars_per_col=12)
    assert len(cols) >= 2


def test_font_catalog():
    catalog = get_font_catalog()
    assert "installed" in catalog
    assert "presets" in catalog
    assert len(catalog["installed"]) >= 3
    assert len(catalog["presets"]) >= 5


def test_acoustic_breakpoint_analyzer():
    from pathlib import Path
    sample_video = Path(__file__).resolve().parent.parent / "inputclip" / "test_video.mp4"
    if sample_video.exists():
        res = analyze_audio_breakpoints(str(sample_video), mode="dense")
        assert res["segment_count"] >= 1
        assert len(res["waveform_peaks"]) == 360
        for seg in res["track"].segments:
            assert seg.end > seg.start
            assert seg.expected_chars is not None and seg.expected_chars >= 2
        snapped = snap_time_to_valley(str(sample_video), 13.8)
        assert abs(snapped - 13.8) <= 0.25


if __name__ == "__main__":
    test_segmentation_by_punctuation()
    test_segmentation_by_pause()
    test_segmentation_by_length()
    test_export_and_parse_srt()
    test_css_and_vertical_wrapping()
    test_font_catalog()
    test_acoustic_breakpoint_analyzer()
    print("All unit tests passed successfully!")
