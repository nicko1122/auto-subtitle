import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .env_utils import preload_cuda_libs, release_gpu_memory

logger = logging.getLogger(__name__)
WHISPER_MODEL = "large-v3-turbo"

preload_cuda_libs()

import stable_whisper
from .audio_extractor import get_media_duration
from ..schemas.subtitle import WordItem


def load_whisper_model(device="auto"):
    targets = ("cuda", "cpu") if device in ("auto", "cuda") else (device,)
    last_error = None
    for target in targets:
        try:
            model = stable_whisper.load_model(WHISPER_MODEL, device=target)
            logger.info(f"原生 Whisper: model={WHISPER_MODEL}, device={target}")
            return model
        except RuntimeError as error:
            last_error = error.with_traceback(None)
            logger.warning(f"原生 Whisper {WHISPER_MODEL}/{target} 載入失敗: {error}")
            release_gpu_memory()
    raise RuntimeError("無法載入原生 Whisper 模型") from last_error


def unload_whisper_model(model):
    try:
        model.cpu()
    except RuntimeError as error:
        logger.warning(f"原生 Whisper 卸載失敗，請重啟工作台: {error}")
    finally:
        release_gpu_memory()


def transcribe_audio(
    audio_path: str,
    device: str = "auto",
    language: Optional[str] = "zh",
    initial_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """所有辨識入口固定使用原生 Whisper large-v3-turbo 與逐詞時間戳。"""
    audio_p = Path(audio_path).resolve()
    if not audio_p.is_file():
        raise FileNotFoundError(f"找不到音訊檔案: {audio_path}")
    model = load_whisper_model(device)
    try:
        result = model.transcribe(
            str(audio_p), language=language, initial_prompt=initial_prompt,
            condition_on_previous_text=False, word_timestamps=True,
            regroup=False, suppress_silence=True,
            fp16=model.device.type == "cuda", verbose=False,
        )
        segments = [dict(segment, id=index) for index, segment in enumerate(result.to_dict()['segments'], 1)]
        words = [WordItem(**word).model_dump() for segment in segments for word in segment.get('words', [])]
        return {
            "source_file": str(audio_p), "language": result.language,
            "language_probability": None,
            "duration": get_media_duration(str(audio_p)),
            "raw_segments": segments, "all_words": words,
            "whisper_model": WHISPER_MODEL, "whisper_backend": "native",
            "device": str(model.device),
        }
    finally:
        unload_whisper_model(model)
