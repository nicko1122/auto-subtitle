import os
import subprocess
import json
import logging
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Union

from ..schemas.subtitle import SubtitleTrack, SubtitleStyle
from .audio_extractor import get_media_duration
from .exporter import to_ass, save_file, parse_srt_content
from .font_manager import FONTS_DIR

logger = logging.getLogger(__name__)


def has_video_stream(media_path: str) -> bool:
    """檢查媒體檔案是否包含視訊軌 (純音訊檔案如 .wav/.mp3 會回傳 False)"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        str(media_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return "video" in res.stdout
    except Exception:
        return False


def get_video_info(video_path: str) -> Tuple[int, int, float]:
    """
    使用 ffprobe 取得影片的 (寬度, 高度, 總時長秒數)；若為純音訊則使用 1920x1080 與音訊時長
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(res.stdout)
        streams = data.get("streams") or []
        if not streams:
            return 1920, 1080, get_media_duration(str(video_path))
        stream = streams[0]
        width = int(stream["width"])
        height = int(stream["height"])
        duration = float(stream.get("duration") or get_media_duration(str(video_path)) or 0.0)
        return width, height, duration
    except Exception as e:
        logger.warning(f"ffprobe 解析影片長寬失敗 ({e})，使用預設值 1920x1080")
        return 1920, 1080, get_media_duration(str(video_path))


def check_nvenc_support() -> bool:
    """檢查目前 FFmpeg 是否支援 NVIDIA NVENC 硬體編碼器"""
    try:
        res = subprocess.run(
            ["ffmpeg", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


def burn_subtitles_to_video(
    video_path: str,
    subtitles_source: Union[str, SubtitleTrack],
    output_path: Optional[str] = None,
    style: Optional[SubtitleStyle] = None,
    use_gpu: bool = True
) -> str:
    """
    將字幕燒錄 (Hardcopy / Burn-in) 到影片中，支援自訂座標、九宮格對齊、字體、描邊與陰影

    :param video_path: 輸入來源影片路徑
    :param subtitles_source: 字幕來源 (可為 SubtitleTrack 物件、.json 檔案路徑、或 .srt 檔案路徑)
    :param output_path: 輸出的燒錄影片路徑 (預設為同目錄的 .hardsub.mp4)
    :param style: 字幕樣式配置 (包含 font_size, primary_color, alignment, pos_x, pos_y 等)
    :param use_gpu: 是否優先啟用 NVIDIA NVENC 硬體加速
    :return: 產出之燒錄影片絕對路徑
    """
    input_v = Path(video_path).resolve()
    if not input_v.exists():
        raise FileNotFoundError(f"找不到來源影片: {video_path}")

    if style is None:
        style = SubtitleStyle()

    # 1. 取得影片長寬解析度
    width, height, duration = get_video_info(str(input_v))
    logger.info(f"偵測到影片解析度: {width}x{height}")

    # 2. 準備 SubtitleTrack 物件
    track: Optional[SubtitleTrack] = None
    if isinstance(subtitles_source, SubtitleTrack):
        track = subtitles_source
    else:
        sub_p = Path(subtitles_source).resolve()
        if not sub_p.exists():
            raise FileNotFoundError(f"找不到字幕檔案: {subtitles_source}")
        if sub_p.suffix.lower() == ".json":
            data = json.loads(sub_p.read_text(encoding="utf-8"))
            track = SubtitleTrack(**data)
        elif sub_p.suffix.lower() in (".srt", ".vtt"):
            content = sub_p.read_text(encoding="utf-8")
            track = parse_srt_content(content, source_file=str(input_v))
            if duration > 0:
                track.duration = duration

    if track is None:
        raise ValueError("無法解析字幕資料源")

    # 3. 產生與影片解析度精確對應的 ASS 字幕檔
    ass_content = to_ass(track, style=style, res_x=width, res_y=height)
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as temp_ass:
        temp_ass_path = Path(temp_ass.name)
    save_file(ass_content, str(temp_ass_path))

    # 4. 決定輸出路徑
    if output_path is None:
        out_v = input_v.parent / f"{input_v.stem}.hardsub.mp4"
    else:
        out_v = Path(output_path).resolve()
    out_v.parent.mkdir(parents=True, exist_ok=True)

    # 5. 組裝 FFmpeg 指令
    # 在 FFmpeg -vf 中使用 ass 濾鏡，路徑中的特殊字元做轉義，並掛載專案 fonts/ 自訂字型目錄
    ass_escaped = str(temp_ass_path).replace("\\", "/").replace(":", "\\:")
    if FONTS_DIR.exists():
        fonts_escaped = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")
        vf_filter = f"ass='{ass_escaped}':fontsdir='{fonts_escaped}'"
    else:
        vf_filter = f"ass='{ass_escaped}'"

    gpu_available = use_gpu and check_nvenc_support()
    if gpu_available:
        logger.info("啟用 NVIDIA NVENC 硬體加速進行影片壓制...")
        encoder_args = [
            "-c:v", "h264_nvenc",
            "-preset", "p4",        # p4 是平衡速度與品質的標準預設
            "-cq", "22",           # 恆定品質
            "-b:v", "6M"
        ]
    else:
        logger.info("使用 CPU (libx264) 進行影片壓制...")
        encoder_args = [
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22"
        ]

    is_video = has_video_stream(str(input_v))
    if is_video:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_v),
            "-vf", vf_filter,
            *encoder_args,
            "-c:a", "copy",        # 音訊不重編碼，無損直通
            str(out_v)
        ]
    else:
        # 純音訊檔 (如 .wav / .mp3)：自動產生 1920x1080 黑底畫布並轉碼 AAC 音軌，壓製為歌詞影片 MP4
        canvas_dur = max(1.0, float(duration or 0.0))
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:r=24:d={canvas_dur:.3f}",
            "-i", str(input_v),
            "-vf", vf_filter,
            *encoder_args,
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(out_v)
        ]

    logger.info(f"開始執行壓制: {' '.join(cmd)}")
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    finally:
        # 確保無論壓制成功或失敗皆清理臨時的 .ass 檔案
        if temp_ass_path.exists():
            temp_ass_path.unlink()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg 影片字幕壓制失敗: {process.stderr}")

    return str(out_v)
