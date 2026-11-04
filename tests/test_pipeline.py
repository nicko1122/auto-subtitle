from src.schemas.subtitle import WordItem, SubtitleSegment, SubtitleTrack, SegmentationConfig
from src.core.segmenter import split_words_into_segments, build_subtitle_track
from src.core.exporter import to_srt, to_vtt, to_json


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


def test_export_srt():
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


if __name__ == "__main__":
    test_segmentation_by_punctuation()
    test_segmentation_by_pause()
    test_segmentation_by_length()
    test_export_srt()
    print("All unit tests passed successfully!")
