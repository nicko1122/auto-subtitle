import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from faster_whisper import WhisperModel

from ..schemas.subtitle import WordItem

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    device: str = "auto",
    compute_type: str = "default",
    language: Optional[str] = None,
    beam_size: int = 5,
    vad_filter: bool = True,
    word_timestamps: bool = True
) -> Dict[str, Any]:
    """
    使用 faster-whisper 對音訊進行辨識，並提取單字層級時間戳記 (Word-level timestamps)

    :param audio_path: 音訊檔案路徑 (建議 16kHz WAV)
    :param model_size: Whisper 模型大小 (tiny, base, small, medium, large-v3 等)
    :param device: 運算裝置 ("cuda", "cpu", "auto")
    :param compute_type: 精度 ("int8", "float16", "default" 等)
    :param language: 指定語言代碼 (如 "zh", "en")，若 None 則自動偵測
    :param beam_size: 搜尋光束大小，預設 5
    :param vad_filter: 是否啟用 Silero VAD 語音活動過濾 (跳過無聲片段)
    :param word_timestamps: 是否抽取逐字時間軸 (強烈建議 True)
    :return: 包含偵測語言、總時長與未切分原始 segment/words 的結構化資料
    """
    audio_p = Path(audio_path).resolve()
    if not audio_p.exists():
        raise FileNotFoundError(f"找不到音訊檔案: {audio_path}")

    # 如果 device 為 auto，可由 faster-whisper 自動決定，若 cuda 失敗會自動 fallback 或可手動處理
    logger.info(f"正在載入 Whisper 模型 [{model_size}], 裝置: {device}, 精度: {compute_type}...")
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as e:
        logger.warning(f"以 device={device} 載入失敗 ({e})，嘗試 fallback 至 CPU INT8 模式...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    logger.info(f"開始辨識音訊: {audio_p.name}...")
    segments_iter, info = model.transcribe(
        str(audio_p),
        beam_size=beam_size,
        language=language,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps
    )

    raw_segments: List[Dict[str, Any]] = []
    all_words: List[WordItem] = []

    for seg in segments_iter:
        seg_words: List[Dict[str, Any]] = []
        if seg.words:
            for w in seg.words:
                item = {
                    "word": w.word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "probability": round(w.probability, 3)
                }
                seg_words.append(item)
                all_words.append(WordItem(**item))

        raw_segments.append({
            "id": seg.id,
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": seg_words
        })

    return {
        "source_file": str(audio_p),
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration": round(info.duration, 3),
        "raw_segments": raw_segments,
        "all_words": [w.model_dump() for w in all_words]
    }
