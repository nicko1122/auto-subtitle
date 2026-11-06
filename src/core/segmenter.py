import re
from typing import List, Dict, Any, Optional
from ..schemas.subtitle import WordItem, SubtitleSegment, SubtitleTrack, SegmentationConfig


def is_cjk(text: str) -> bool:
    """判斷文字是否包含中日韓 (CJK) 字符"""
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', text))


def split_words_into_segments(
    words: List[WordItem],
    config: SegmentationConfig
) -> List[SubtitleSegment]:
    """
    依據「標點符號、靜音停頓、最大字數」規則，將逐字清單智慧切分成符合字幕觀影長度的 SubtitleSegment
    """
    if not words:
        return []

    segments: List[SubtitleSegment] = []
    current_words: List[WordItem] = []
    current_text = ""
    current_id = 1

    punctuation_set = set(config.punctuations)

    for i, w in enumerate(words):
        word_text = w.word
        current_words.append(w)
        current_text += word_text

        # 檢查下一個字
        has_next = (i + 1 < len(words))
        next_w = words[i + 1] if has_next else None

        # 條件 1: 停頓時間過長 (當前字結束 與 下一個字開始 的間隔超過 pause_threshold)
        is_pause = False
        if next_w is not None:
            gap = next_w.start - w.end
            if gap >= config.pause_threshold:
                is_pause = True

        # 條件 2: 包含標點符號
        has_punct = False
        if config.split_on_punctuation:
            if any(p in word_text for p in punctuation_set):
                has_punct = True

        # 條件 3: 超過最大字數限制
        # 計算字元數 (CJK 1 字計 1，英文字母計 1)
        stripped_len = len(current_text.strip())
        is_length_exceeded = (stripped_len >= config.max_chars)

        # 決定是否在此處斷句
        should_split = False
        if not has_next:
            should_split = True
        elif has_punct:
            should_split = True
        elif is_pause:
            should_split = True
        elif is_length_exceeded:
            should_split = True

        if should_split and current_words:
            # 清理文字，並確保起訖時間準確
            clean_text = current_text.strip()
            # 移除結尾的空格或可能的多餘換行
            if clean_text:
                seg = SubtitleSegment(
                    id=current_id,
                    start=current_words[0].start,
                    end=current_words[-1].end,
                    text=clean_text,
                    words=list(current_words)
                )
                segments.append(seg)
                current_id += 1
            current_words = []
            current_text = ""

    return segments


def build_subtitle_track(
    transcription_data: Dict[str, Any],
    config: Optional[SegmentationConfig] = None
) -> SubtitleTrack:
    """
    將 Whisper 辨識原始結果轉換為結構化的 SubtitleTrack 物件
    """
    if config is None:
        config = SegmentationConfig()

    raw_words = transcription_data.get("all_words", [])
    word_items = [WordItem(**w) if isinstance(w, dict) else w for w in raw_words]

    # 若沒有 word_timestamps，則退回直接使用 raw_segments
    if not word_items and "raw_segments" in transcription_data:
        segments = []
        for s in transcription_data["raw_segments"]:
            segments.append(
                SubtitleSegment(
                    id=s["id"],
                    start=s["start"],
                    end=s["end"],
                    text=s["text"],
                    words=[]
                )
            )
    else:
        segments = split_words_into_segments(word_items, config)

    return SubtitleTrack(
        version="1.0.0",
        source_file=transcription_data.get("source_file", ""),
        duration=transcription_data.get("duration", 0.0),
        language=transcription_data.get("language", "zh"),
        segments=segments
    )
