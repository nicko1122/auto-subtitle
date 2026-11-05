import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .env_utils import preload_cuda_libs, release_gpu_memory

logger = logging.getLogger(__name__)

preload_cuda_libs()

from faster_whisper import WhisperModel
from ..schemas.subtitle import WordItem


def transcribe_audio(
    audio_path: str,
    model_size: str = "large-v3-turbo",
    device: str = "auto",
    compute_type: str = "default",
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    beam_size: int = 5,
    vad_filter: bool = False,
    condition_on_previous_text: bool = False,
    hallucination_silence_threshold: Optional[float] = 2.0,
    word_timestamps: bool = True
) -> Dict[str, Any]:
    """
    使用 faster-whisper 對音訊進行辨識，並提取單字層級時間戳記 (Word-level timestamps)
    """
    audio_p = Path(audio_path).resolve()
    if not audio_p.exists():
        raise FileNotFoundError(f"找不到音訊檔案: {audio_path}")

    # 再次確保函式庫符號已載入
    preload_cuda_libs()

    logger.info(f"正在載入 Whisper 模型 [{model_size}], 裝置: {device}, 精度: {compute_type}...")
    
    # 智慧嘗試策略: 先嘗試指定的 device/compute_type，若失敗依序降級嘗試 float32、CPU int8
    model = None
    try_configs = []
    
    if device in ("cuda", "auto"):
        # Pascal GPU (GTX 1070 等) 通常不支援原生高效 fp16，float32 更穩定
        if compute_type == "default":
            try_configs.append({"device": "cuda", "compute_type": "float32"})
            try_configs.append({"device": "cuda", "compute_type": "int8_float32"})
        else:
            try_configs.append({"device": "cuda", "compute_type": compute_type})
    
    # 最後備援方案: CPU int8
    try_configs.append({"device": "cpu", "compute_type": "int8"})

    for cfg in try_configs:
        try:
            model = WhisperModel(model_size, device=cfg["device"], compute_type=cfg["compute_type"])
            logger.info(f"成功以 device={cfg['device']}, compute_type={cfg['compute_type']} 載入模型")
            break
        except Exception as e:
            logger.warning(f"以 {cfg} 載入失敗 ({e})，嘗試下一個備援配置...")

    if model is None:
        raise RuntimeError("無法以任何配置載入 Whisper 模型！")

    logger.info(f"開始辨識音訊: {audio_p.name} (vad_filter={vad_filter}, condition_on_prev={condition_on_previous_text})...")
    segments_iter, info = model.transcribe(
        str(audio_p),
        beam_size=beam_size,
        language=language,
        initial_prompt=initial_prompt,
        vad_filter=vad_filter,
        condition_on_previous_text=condition_on_previous_text,
        hallucination_silence_threshold=hallucination_silence_threshold,
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

    duration = round(info.duration, 3)
    lang = info.language
    lang_prob = round(info.language_probability, 3)

    # 明確釋放 Whisper 模型與顯存
    del model
    release_gpu_memory()

    return {
        "source_file": str(audio_p),
        "language": lang,
        "language_probability": lang_prob,
        "duration": duration,
        "raw_segments": raw_segments,
        "all_words": [w.model_dump() for w in all_words]
    }
