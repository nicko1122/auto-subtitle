import shutil
import subprocess
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Tuple, Optional, Union, List, Callable, Dict, Any

from ..schemas.subtitle import SubtitleTrack, SubtitleStyle
from .audio_extractor import get_media_duration
from .css_renderer import render_css_subtitles_to_pngs
from .exporter import parse_srt_content

logger = logging.getLogger(__name__)


def _probe_audio_codec(media_path: Path) -> Optional[str]:
    """回傳來源影片第一條音軌的編碼名稱 (無音軌回傳 None)。"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "csv=p=0",
        str(media_path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        codec = res.stdout.strip().splitlines()[0].strip().lower() if res.stdout.strip() else ""
        return codec or None
    except Exception:
        return None


def _mux_audio_args(input_v: Path, out_v: Path) -> List[str]:
    """依來源音軌編碼與輸出容器副檔名決定 copy 或轉碼，避免 .webm/Opus 封裝進 .mp4 時失敗。"""
    codec = _probe_audio_codec(input_v)
    if not codec:
        return ["-an"]

    ext = out_v.suffix.lower()
    mp4_copy_ok = {"aac", "mp3", "ac3", "eac3", "alac", "mp2"}
    webm_copy_ok = {"opus", "vorbis"}

    if ext in (".mp4", ".m4v", ".mov"):
        if codec in mp4_copy_ok:
            return ["-c:a", "copy"]
        return ["-c:a", "aac", "-b:a", "320k"]
    if ext == ".webm":
        if codec in webm_copy_ok:
            return ["-c:a", "copy"]
        return ["-c:a", "libopus", "-b:a", "192k"]
    return ["-c:a", "copy"]


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


def _run_ffmpeg_with_progress(
    cmd: List[str],
    duration: float,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    register_process: Optional[Callable[[Any], None]] = None,
) -> Tuple[int, str]:
    """執行 FFmpeg，並在提供進度/取消回呼時解析 -progress pipe:1 即時回報編碼進度。"""
    if progress_callback is None and cancel_check is None and register_process is None:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc.returncode, getattr(proc, "stderr", "") or ""

    prog_cmd = cmd[:-1] + ["-progress", "pipe:1", "-nostats", cmd[-1]]
    proc = subprocess.Popen(
        prog_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    if register_process:
        register_process(proc)

    try:
        if proc.stdout is not None:
            for raw_line in proc.stdout:
                if cancel_check and cancel_check():
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
                    raise InterruptedError("硬字幕燒錄已手動中止")

                line = raw_line.strip()
                if line.startswith("out_time_us=") and progress_callback and duration > 0:
                    try:
                        us = int(line.split("=", 1)[1])
                        ratio = min(1.0, max(0.0, (us / 1_000_000.0) / duration))
                        pct = round(35.0 + ratio * 65.0, 1)
                        progress_callback({
                            "stage": "encoding",
                            "percent": pct,
                            "message": f"正在合成硬字幕影片 ({pct:.0f}%)...",
                        })
                    except Exception:
                        pass

        rc = proc.wait()
        stderr_text = proc.stderr.read() if proc.stderr is not None else ""
        return rc, stderr_text
    finally:
        if register_process:
            register_process(None)


def _burn_with_css(
    input_v: Path,
    out_v: Path,
    track: SubtitleTrack,
    style: SubtitleStyle,
    width: int,
    height: int,
    duration: float,
    encoder_args: List[str],
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    register_process: Optional[Callable[[Any], None]] = None,
) -> None:
    """使用 Headless 瀏覽器 CSS 截透明 PNG + FFmpeg ffconcat overlay 的 100% 所見即所得燒錄管線。"""
    work_dir = _create_css_work_dir()
    try:
        if progress_callback:
            progress_callback({
                "stage": "rendering_css",
                "percent": 5.0,
                "message": "正在啟動瀏覽器渲染 CSS 字幕圖層...",
            })

        def _on_png(done: int, total: int):
            if progress_callback and total > 0:
                pct = round(5.0 + (done / total) * 30.0, 1)
                progress_callback({
                    "stage": "rendering_css",
                    "current_frame": done,
                    "total_frames": total,
                    "percent": pct,
                    "message": f"正在渲染 CSS 字幕圖層 ({done}/{total})...",
                })

        concat_path = render_css_subtitles_to_pngs(
            track=track,
            style=style,
            width=width,
            height=height,
            video_duration=duration,
            work_dir=work_dir,
            progress_callback=_on_png if progress_callback else None,
            cancel_check=cancel_check,
        )
        audio_args = _mux_audio_args(input_v, out_v)
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
            *audio_args,
            str(out_v),
        ]
        if progress_callback:
            progress_callback({
                "stage": "encoding",
                "percent": 35.0,
                "message": "正在進行影片硬字幕合成編碼...",
            })
        logger.info(f"開始執行 CSS PNG Overlay 壓制: {' '.join(cmd)}")
        rc, stderr_text = _run_ffmpeg_with_progress(
            cmd,
            duration=duration,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
            register_process=register_process,
        )
        if rc != 0:
            raise RuntimeError(f"FFmpeg CSS Overlay 影片壓制失敗: {stderr_text}")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def burn_subtitles_to_video(
    video_path: str,
    subtitles_source: Union[str, SubtitleTrack],
    output_path: Optional[str] = None,
    style: Optional[SubtitleStyle] = None,
    use_gpu: bool = True,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    register_process: Optional[Callable[[Any], None]] = None,
) -> str:
    """
    將字幕以 Headless 瀏覽器 CSS 透明圖層 100% 所見即所得燒錄 (Hardcopy / Burn-in) 至影片中。

    :param video_path: 輸入來源影片路徑
    :param subtitles_source: 字幕來源 (可為 SubtitleTrack 物件、.json 檔案路徑、或 .srt/.vtt 檔案路徑)
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

    if not has_video_stream(str(input_v)):
        raise ValueError("純音訊檔案 (.wav / .mp3 等) 不支援硬字幕影片壓制，請改為匯出 SRT / VTT 字幕檔")

    width, height, duration = get_video_info(str(input_v))
    logger.info(f"偵測到影片解析度: {width}x{height} (CSS 渲染燒錄模式)")

    track = _load_subtitle_track(subtitles_source, input_v, duration)

    if output_path is None:
        out_v = input_v.parent / f"{input_v.stem}.hardsub.mp4"
    else:
        out_v = Path(output_path).resolve()
    out_v.parent.mkdir(parents=True, exist_ok=True)

    encoder_args = _get_encoder_args(use_gpu)
    _burn_with_css(
        input_v,
        out_v,
        track,
        style,
        width,
        height,
        duration,
        encoder_args,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
        register_process=register_process,
    )

    return str(out_v)
