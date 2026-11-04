from src.schemas.subtitle import WordItem, SubtitleSegment, SubtitleTrack, SegmentationConfig, SubtitleStyle
from src.core.segmenter import split_words_into_segments, build_subtitle_track
from src.core.exporter import to_srt, to_vtt, to_json, to_ass, parse_srt_content, split_vertical_columns
from src.core.aligner import align_script_to_audio


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


def test_css_and_vertical_ass_wrapping():
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
    assert style.ass_alignment == 9

    cols = split_vertical_columns("這是一段非常長的直式字幕，應該在標點處自動換成第二列顯示", max_chars_per_col=12)
    assert len(cols) >= 2

    track = SubtitleTrack(
        source_file="v.mp4",
        duration=5.0,
        segments=[SubtitleSegment(id=1, start=0.0, end=4.0, text="這是一段非常長的直式字幕，應該在標點處自動換成第二列顯示")]
    )
    ass_text = to_ass(track, style=style, res_x=1080, res_y=720)
    assert ass_text.count("Dialogue:") >= 2


def test_aligner_with_band_search():
    script = "牆上的時鐘\n滴答滴答"
    trans_data = {
        "source_file": "a.wav",
        "duration": 4.0,
        "language": "zh",
        "all_words": [
            {"word": "強上", "start": 0.2, "end": 0.8, "probability": 0.9},
            {"word": "的時鐘", "start": 0.8, "end": 1.5, "probability": 0.9},
            {"word": "滴答滴答", "start": 2.0, "end": 3.2, "probability": 0.9},
        ]
    }
    aligned = align_script_to_audio(script, trans_data)
    assert len(aligned.segments) == 2
    assert aligned.segments[0].text == "牆上的時鐘"
    assert aligned.segments[0].start == 0.2
    assert aligned.segments[1].text == "滴答滴答"
    assert aligned.segments[1].start >= 1.5


if __name__ == "__main__":
    test_segmentation_by_punctuation()
    test_segmentation_by_pause()
    test_segmentation_by_length()
    test_export_and_parse_srt()
    test_css_and_vertical_ass_wrapping()
    test_aligner_with_band_search()
    print("All unit tests passed successfully!")
