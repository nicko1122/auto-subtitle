import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional


def check_ffmpeg() -> bool:
    """檢查系統是否安裝了 ffmpeg"""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_media_duration(file_path: str) -> float:
    """使用 ffprobe 取得影音時長 (秒)"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def extract_audio(
    video_path: str,
    output_path: Optional[str] = None,
    sample_rate: int = 16000
) -> Dict[str, Any]:
    """
    從影片抽取音訊並轉成 Whisper 最佳化格式 (16kHz, 16-bit, Mono WAV)

    :param video_path: 來源影片路徑
    :param output_path: 輸出的 WAV 檔案路徑 (若未提供則自動建立同名 .wav)
    :param sample_rate: 取樣率，預設 16000 Hz
    :return: 包含音訊檔案路徑與時長等中繼資訊的字典
    """
    input_p = Path(video_path).resolve()
    if not input_p.exists():
        raise FileNotFoundError(f"找不到來源影片檔案: {video_path}")

    if output_path is None:
        out_p = input_p.with_suffix(".wav")
    else:
        out_p = Path(output_path).resolve()

    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",               # 覆蓋已存在的檔案
        "-i", str(input_p), # 輸入檔案
        "-vn",              # 去除視訊軌
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", str(sample_rate),# 取樣率 16000
        "-ac", "1",         # 單聲道
        str(out_p)
    ]

    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg 音訊提取失敗: {process.stderr}")

    duration = get_media_duration(str(out_p))

    return {
        "audio_path": str(out_p),
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": 1
    }
