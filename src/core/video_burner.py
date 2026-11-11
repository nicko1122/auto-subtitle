import os
import shutil
import subprocess
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Tuple, Optional, Union, Literal, List

from ..schemas.subtitle import SubtitleTrack, SubtitleStyle
from .audio_extractor import get_media_duration
from .css_renderer import render_css_subtitles_to_pngs
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


def _get_encoder_args(use_gpu: bool) -> List[str]:
    """依硬體支援挑選 NVENC 或 libx264 編碼參數。"""
    if use_gpu and check_nvenc_support():
        logger.info("啟用 NVIDIA NVENC 硬體加速進行影片壓制...")
        return [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-cq", "22",
            "-b:v", "6M",
        ]
    logger.info("使用 CPU (libx264) 進行影片壓制...")
    return [
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
    ]


def _load_subtitle_track(
    subtitles_source: Union[str, SubtitleTrack],
    video_path: Path,
    duration: float,
) -> SubtitleTrack:
    """從 SubtitleTrack、.json、.srt 或 .vtt 載入字幕軌道。"""
    if isinstance(subtitles_source, SubtitleTrack):
        return subtitles_source

    sub_p = Path(subtitles_source).resolve()
    if not sub_p.exists():
        raise FileNotFoundError(f"找不到字幕檔案: {subtitles_source}")
    suffix = sub_p.suffix.lower()
    if suffix == ".json":
        data = json.loads(sub_p.read_text(encoding="utf-8"))
        return SubtitleTrack(**data)
    if suffix in (".srt", ".vtt"):
        content = sub_p.read_text(encoding="utf-8")
        track = parse_srt_content(content, source_file=str(video_path))
        if duration > 0:
            track.duration = duration
        return track
    raise ValueError("無法解析字幕資料源")


def _create_css_work_dir() -> Path:
    """建立跨 WSL/Windows 瀏覽器可高效存取的隔離暫存目錄。"""
    project_temp = Path(__file__).resolve().parents[2] / "temp"
    if str(project_temp).startswith("/mnt/"):
        base = project_temp
    elif Path("/mnt/c/Windows/Temp").exists():
        base = Path("/mnt/c/Windows/Temp")
    else:
        return Path(tempfile.mkdtemp(prefix="autosub_css_"))
    base.mkdir(parents=True, exist_ok=True)
    job_dir = base / f"autosub_css_{uuid.uuid4().hex}"
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def _burn_with_ass(
    input_v: Path,
    out_v: Path,
    track: SubtitleTrack,
    style: SubtitleStyle,
    width: int,
    height: int,
    encoder_args: List[str],
) -> None:
    """傳統 ASS/libass 硬字幕燒錄管線。"""
    ass_content = to_ass(track, style=style, res_x=width, res_y=height)
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as temp_ass:
        temp_ass_path = Path(temp_ass.name)
    save_file(ass_content, str(temp_ass_path))

    ass_escaped = str(temp_ass_path).replace("\\", "/").replace(":", "\\:")
    if FONTS_DIR.exists():
        fonts_escaped = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")
        vf_filter = f"ass='{ass_escaped}':fontsdir='{fonts_escaped}'"
    else:
        vf_filter = f"ass='{ass_escaped}'"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_v),
        "-vf", vf_filter,
        *encoder_args,
        "-c:a", "copy",
        str(out_v),
    ]
    logger.info(f"開始執行 ASS 壓制: {' '.join(cmd)}")
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    finally:
        if temp_ass_path.exists():
            temp_ass_path.unlink()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg 影片字幕壓制失敗: {process.stderr}")


def _burn_with_css(
    input_v: Path,
    out_v: Path,
    track: SubtitleTrack,
    style: SubtitleStyle,
    width: int,
    height: int,
    duration: float,
    encoder_args: List[str],
) -> None:
    """使用 Headless 瀏覽器 CSS 截透明 PNG + FFmpeg ffconcat overlay 的 100% 所見即所得燒錄管線。"""
    work_dir = _create_css_work_dir()
    try:
        concat_path = render_css_subtitles_to_pngs(
            track=track,
            style=style,
            width=width,
            height=height,
            video_duration=duration,
            work_dir=work_dir,
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_v),
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
            "-filter_complex", "[0:v][1:v]overlay=0:0:eof_action=pass[v]",
            "-map", "[v]",
            "-map", "0:a?",
            *encoder_args,
            "-c:a", "copy",
            str(out_v),
        ]
        logger.info(f"開始執行 CSS PNG Overlay 壓制: {' '.join(cmd)}")
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg CSS Overlay 影片壓制失敗: {process.stderr}")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def burn_subtitles_to_video(
    video_path: str,
    subtitles_source: Union[str, SubtitleTrack],
    output_path: Optional[str] = None,
    style: Optional[SubtitleStyle] = None,
    use_gpu: bool = True,
    render_mode: Literal["css", "ass"] = "ass",
) -> str:
    """
    將字幕燒錄 (Hardcopy / Burn-in) 到影片中，支援 CSS 瀏覽器透明圖層 (css) 與傳統 libass (ass) 雙引擎

    :param video_path: 輸入來源影片路徑
    :param subtitles_source: 字幕來源 (可為 SubtitleTrack 物件、.json 檔案路徑、或 .srt/.vtt 檔案路徑)
    :param output_path: 輸出的燒錄影片路徑 (預設為同目錄的 .hardsub.mp4)
    :param style: 字幕樣式配置 (包含 font_size, primary_color, alignment, pos_x, pos_y 等)
    :param use_gpu: 是否優先啟用 NVIDIA NVENC 硬體加速
    :param render_mode: 渲染引擎，"css" (瀏覽器 CSS 截圖疊加) 或 "ass" (傳統 libass 濾鏡)
    :return: 產出之燒錄影片絕對路徑
    """
    input_v = Path(video_path).resolve()
    if not input_v.exists():
        raise FileNotFoundError(f"找不到來源影片: {video_path}")

    if style is None:
        style = SubtitleStyle()

    if not has_video_stream(str(input_v)):
        raise ValueError("純音訊檔案 (.wav / .mp3 等) 不支援硬字幕影片壓制，請改為匯出 SRT / VTT 字幕檔")

    width, height, duration = get_video_info(str(input_v))
    logger.info(f"偵測到影片解析度: {width}x{height} (render_mode={render_mode})")

    track = _load_subtitle_track(subtitles_source, input_v, duration)

    if output_path is None:
        out_v = input_v.parent / f"{input_v.stem}.hardsub.mp4"
    else:
        out_v = Path(output_path).resolve()
    out_v.parent.mkdir(parents=True, exist_ok=True)

    encoder_args = _get_encoder_args(use_gpu)
    if render_mode == "css":
        _burn_with_css(input_v, out_v, track, style, width, height, duration, encoder_args)
    elif render_mode == "ass":
        _burn_with_ass(input_v, out_v, track, style, width, height, encoder_args)
    else:
        raise ValueError(f"不支援的 render_mode: {render_mode}")

    return str(out_v)
