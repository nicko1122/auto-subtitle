import os
import sys
import time
import shutil
import subprocess
import json
import logging
import tempfile
import threading
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, Callable

from .video_burner import check_nvenc_support

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TOOLS_DIR = BASE_DIR / "tools" / "realesrgan"
MODELS_DIR = TOOLS_DIR / "models"


def find_upscaler_binary() -> Optional[Path]:
    """
    尋找可執行的 realesrgan-ncnn-vulkan 程式。
    優先順序：
    1. WSL 環境下若有 realesrgan-ncnn-vulkan.exe (可直接調用 Windows GPU 驅動)
    2. 本地 tools/realesrgan/ 下的 Linux 執行檔
    3. 系統 PATH 中的 realesrgan-ncnn-vulkan
    """
    is_wsl = "microsoft" in os.uname().release.lower() if hasattr(os, "uname") else False
    win_exe = TOOLS_DIR / "realesrgan-ncnn-vulkan.exe"
    linux_bin = TOOLS_DIR / "realesrgan-ncnn-vulkan-linux"
    standard_bin = TOOLS_DIR / "realesrgan-ncnn-vulkan"

    if (is_wsl or sys.platform == "win32") and win_exe.exists():
        return win_exe

    if linux_bin.exists() and os.access(str(linux_bin), os.X_OK):
        return linux_bin

    if standard_bin.exists() and os.access(str(standard_bin), os.X_OK):
        return standard_bin

    system_which = shutil.which("realesrgan-ncnn-vulkan")
    if system_which:
        return Path(system_which)

    return None


def ensure_upscaler_installed() -> Optional[Path]:
    """若未安裝，則自動從 GitHub 下載預編譯 Real-ESRGAN binary 與 Compact 模型"""
    binary = find_upscaler_binary()
    if binary:
        return binary

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    is_wsl = "microsoft" in os.uname().release.lower() if hasattr(os, "uname") else False
    is_win = sys.platform == "win32" or is_wsl

    zip_name = "realesrgan-ncnn-vulkan-20220424-windows.zip" if is_win else "realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
    url = f"https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/{zip_name}"

    logger.info(f"正在下載 Real-ESRGAN 放大引擎與 Compact 模型 ({zip_name})...")
    import urllib.request
    import zipfile

    tmp_zip = TOOLS_DIR / zip_name
    urllib.request.urlretrieve(url, str(tmp_zip))

    with zipfile.ZipFile(str(tmp_zip), "r") as zip_ref:
        zip_ref.extractall(str(TOOLS_DIR))
    tmp_zip.unlink(missing_ok=True)

    for f in TOOLS_DIR.glob("*"):
        if not f.is_dir() and not f.name.endswith(".zip") and not f.name.endswith(".dll"):
            try:
                os.chmod(str(f), 0o755)
            except Exception:
                pass

    return find_upscaler_binary()


def get_video_stream_info(video_path: str) -> Dict[str, Any]:
    """
    使用 ffprobe 獲取影片的寬度、高度、FPS、總時長與音軌資訊
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration,r_frame_rate,nb_frames",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        duration = float(stream.get("duration", 0.0))

        fps_str = stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)

        nb_frames = int(stream.get("nb_frames", 0))
        if nb_frames <= 0 and duration > 0 and fps > 0:
            nb_frames = int(round(duration * fps))

        return {
            "width": width,
            "height": height,
            "fps": fps,
            "duration": duration,
            "nb_frames": nb_frames
        }
    except Exception as e:
        logger.warning(f"ffprobe 解析失敗 ({e})，使用預設值")
        return {"width": 1920, "height": 1080, "fps": 30.0, "duration": 0.0, "nb_frames": 0}


def check_audio_stream(video_path: str) -> bool:
    """檢查影片是否包含音訊軌"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(res.stdout)
        return len(data.get("streams", [])) > 0
    except Exception:
        return False


def clean_stale_upscale_temp_dirs(max_age_seconds: int = 1800):
    """
    清理過期或未完成殘留的 upscale_* 暫存目錄（預設清理 30 分鐘前殘留檔案）
    """
    temp_root = BASE_DIR / "temp"
    if not temp_root.exists():
        return
    now = time.time()
    for item in temp_root.glob("upscale_*"):
        if item.is_dir():
            try:
                mtime = item.stat().st_mtime
                if now - mtime > max_age_seconds:
                    logger.info(f"自動清理過期殘留暫存目錄: {item}")
                    shutil.rmtree(item, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理過期目錄失敗 {item}: {e}")


def estimate_upscale_time(width: int, height: int, total_frames: int, model_name: str, scale: int = 2) -> Dict[str, Any]:
    """
    估算超解析度放大耗時與提供警語
    基準依據：GTX 1070 Ti 實測數據 (1080p: Compact ~1.8s/幀, x4plus ~22s/幀)
    """
    pixel_count = max(1, width * height)
    ratio_to_1080p = pixel_count / (1920 * 1080)

    if "animevideov3" in model_name:
        base_sec = 1.8 if scale == 2 else 3.5
    elif "anime" in model_name:
        base_sec = 7.0 if scale == 2 else 14.0
    else:  # realesrgan-x4plus 重型寫實照片模型
        base_sec = 22.0 if scale == 2 else 26.0

    sec_per_frame = max(0.05, base_sec * ratio_to_1080p)
    total_sec = int(total_frames * sec_per_frame)

    if total_sec < 60:
        est_text = f"約 {total_sec} 秒"
    elif total_sec < 3600:
        est_text = f"約 {round(total_sec / 60, 1)} 分鐘"
    else:
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60
        est_text = f"約 {hours} 小時 {mins} 分鐘"

    is_heavy = False
    warning = None

    if "x4plus" in model_name and "anime" not in model_name and total_frames > 200:
        is_heavy = True
        warning = f"⚠️ 警告：選取的【{model_name}】為 23 層極重型靜態照片模型，在此影片（{total_frames} 幀）預估需耗時 {est_text}！強烈建議切換為【Compact 輕量視訊模型】，速度可提升 10~15 倍。"
    elif total_sec > 7200:  # 超過 2 小時
        is_heavy = True
        warning = f"⚠️ 提醒：影片總長度較長（{total_frames} 幀），預估需耗時 {est_text}。運算期間請勿關閉服務行程。"

    return {
        "width": width,
        "height": height,
        "total_frames": total_frames,
        "sec_per_frame": round(sec_per_frame, 2),
        "estimated_seconds": total_sec,
        "estimated_text": est_text,
        "is_heavy_warning": is_heavy,
        "warning_message": warning
    }


def upscale_video(
    input_path: str,
    output_path: Optional[str] = None,
    scale: int = 2,
    model_name: str = "realesr-animevideov3",
    use_gpu: bool = True,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    register_process: Optional[Callable[[subprocess.Popen], None]] = None,
    on_temp_dir_created: Optional[Callable[[Path], None]] = None,
) -> str:
    """
    使用 Real-ESRGAN (Compact 輕量模型) 進行影片畫質超解析放大 (2x / 4x)
    內建即時影格進度監聽、自動暫存清理與中途取消中斷機制。
    """
    input_file = Path(input_path).resolve()
    if not input_file.exists():
        raise FileNotFoundError(f"找不到來源影片: {input_path}")

    upscaler_bin = find_upscaler_binary() or ensure_upscaler_installed()
    if not upscaler_bin:
        raise RuntimeError(
            "未找到 realesrgan-ncnn-vulkan 執行檔。請確認 tools/realesrgan 已備妥。"
        )

    # 1. 取得視訊參數
    info = get_video_stream_info(str(input_file))
    fps = info["fps"]
    total_frames = info["nb_frames"]
    has_audio = check_audio_stream(str(input_file))

    # 2. 決定輸出路徑
    if output_path is None:
        out_file = input_file.parent / f"{input_file.stem}_{scale}x.mp4"
    else:
        out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 3. 建立臨時工作目錄
    temp_dir = Path(tempfile.mkdtemp(prefix="upscale_", dir=str(BASE_DIR / "temp" if (BASE_DIR / "temp").exists() else None)))
    if on_temp_dir_created:
        try:
            on_temp_dir_created(temp_dir)
        except Exception:
            pass
    frames_in = temp_dir / "in"
    frames_out = temp_dir / "out"
    frames_in.mkdir(parents=True, exist_ok=True)
    frames_out.mkdir(parents=True, exist_ok=True)
    audio_path = temp_dir / "audio.aac"

    logger.info(f"建立 AI 放大暫存目錄: {temp_dir}")

    try:
        if cancel_check and cancel_check():
            raise InterruptedError("任務已由使用者中止")

        # (A) 提取音軌 (若有)
        if has_audio:
            logger.info("提取來源影片音軌...")
            audio_cmd = [
                "ffmpeg", "-y",
                "-i", str(input_file),
                "-vn", "-c:a", "copy",
                str(audio_path)
            ]
            res = subprocess.run(audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", str(input_file),
                    "-vn", "-c:a", "aac", "-b:a", "320k",
                    str(audio_path)
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if cancel_check and cancel_check():
            raise InterruptedError("任務已由使用者中止")

        # (B) 分解影格為高品質 JPEG
        if progress_callback:
            progress_callback({
                "stage": "extracting",
                "current_frame": 0,
                "total_frames": total_frames,
                "percent": 0.0,
                "message": f"正在分解影格中 ({total_frames} 幀 @ {fps:.1f} fps)..."
            })

        logger.info(f"分解影片影格中 ({fps} fps)...")
        extract_cmd = [
            "ffmpeg", "-y",
            "-i", str(input_file),
            "-q:v", "2",
            str(frames_in / "frame_%08d.jpg")
        ]
        p_ext = subprocess.Popen(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if register_process:
            register_process(p_ext)
        p_ext.wait()

        if cancel_check and cancel_check():
            raise InterruptedError("任務已由使用者中止")

        actual_extracted = len(os.listdir(str(frames_in)))
        if actual_extracted > 0:
            total_frames = actual_extracted

        # (C) 執行 Real-ESRGAN 超解析放大
        logger.info(f"執行 AI 超解析放大 ({model_name}, {scale}x)...")
        is_exe = upscaler_bin.name.lower().endswith(".exe")

        if is_exe:
            w_in = subprocess.check_output(["wslpath", "-w", str(frames_in)], text=True).strip()
            w_out = subprocess.check_output(["wslpath", "-w", str(frames_out)], text=True).strip()
            w_models = subprocess.check_output(["wslpath", "-w", str(MODELS_DIR)], text=True).strip()
            upscale_cmd = [
                str(upscaler_bin),
                "-i", w_in,
                "-o", w_out,
                "-s", str(scale),
                "-m", w_models,
                "-n", model_name,
                "-f", "jpg"
            ]
        else:
            upscale_cmd = [
                str(upscaler_bin),
                "-i", str(frames_in),
                "-o", str(frames_out),
                "-s", str(scale),
                "-m", str(MODELS_DIR),
                "-n", model_name,
                "-f", "jpg"
            ]

        proc = subprocess.Popen(upscale_cmd, cwd=str(TOOLS_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if register_process:
            register_process(proc)

        start_t = time.time()
        while proc.poll() is None:
            if cancel_check and cancel_check():
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise InterruptedError("任務已由使用者中止")

            try:
                done = len(os.listdir(str(frames_out)))
            except Exception:
                done = 0

            elapsed = time.time() - start_t
            pct = min(99.0, round((done / total_frames) * 100, 1)) if total_frames > 0 else 0.0

            if done > 3 and elapsed > 2:
                sec_per_f = elapsed / done
                rem_sec = int((total_frames - done) * sec_per_f)
                if rem_sec < 60:
                    rem_txt = f"{rem_sec} 秒"
                elif rem_sec < 3600:
                    rem_txt = f"{round(rem_sec / 60, 1)} 分鐘"
                else:
                    rem_txt = f"{rem_sec // 3600} 小時 {(rem_sec % 3600) // 60} 分鐘"
            else:
                rem_sec = 0
                rem_txt = "估算中..."

            if progress_callback:
                progress_callback({
                    "stage": "upscaling",
                    "current_frame": done,
                    "total_frames": total_frames,
                    "percent": pct,
                    "elapsed_seconds": int(elapsed),
                    "eta_seconds": rem_sec,
                    "eta_text": rem_txt,
                    "message": f"正在放大影格: {done} / {total_frames} ({pct}%) · 預估剩餘: {rem_txt}"
                })

            time.sleep(1.0)

        if proc.returncode != 0:
            if cancel_check and cancel_check():
                raise InterruptedError("任務已由使用者中止")
            raise RuntimeError(f"Real-ESRGAN 放大行程異常結束 (returncode={proc.returncode})")

        if cancel_check and cancel_check():
            raise InterruptedError("任務已由使用者中止")

        # (D) 重新合成為高畫質視訊
        if progress_callback:
            progress_callback({
                "stage": "encoding",
                "current_frame": total_frames,
                "total_frames": total_frames,
                "percent": 99.0,
                "message": "已完成所有影格放大，正在進行最終視訊壓制封裝..."
            })

        logger.info("重新編碼高解析度視訊...")
        gpu_available = use_gpu and check_nvenc_support()
        if gpu_available:
            encoder_args = [
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "20",
                "-b:v", "12M"
            ]
        else:
            encoder_args = [
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18"
            ]

        assemble_cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(frames_out / "frame_%08d.jpg")
        ]
        if has_audio and audio_path.exists():
            assemble_cmd.extend(["-i", str(audio_path), "-c:a", "copy"])

        assemble_cmd.extend([
            *encoder_args,
            "-pix_fmt", "yuv420p",
            str(out_file)
        ])

        p_ass = subprocess.Popen(assemble_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if register_process:
            register_process(p_ass)
        p_ass.wait()

        if p_ass.returncode != 0:
            raise RuntimeError(f"FFmpeg 視訊封裝失敗 (returncode={p_ass.returncode})")

    finally:
        # 自動清理暫存影格目錄
        logger.info(f"自動清理臨時放大目錄: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)

    return str(out_file)


# ---------------- 非同步任務管理器 (支援即時進度與中途停止) ----------------
class UpscaleTask:
    def __init__(self, task_id: str, target_name: str, total_frames: int):
        self.task_id = task_id
        self.target_name = target_name
        self.total_frames = total_frames
        self.current_frame = 0
        self.percent = 0.0
        self.stage = "preparing"
        self.message = "正在初始化工作區..."
        self.start_time = time.time()
        self.elapsed_seconds = 0
        self.eta_seconds = 0
        self.eta_text = "計算中..."
        self.cancel_requested = False
        self.current_process: Optional[subprocess.Popen] = None
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.temp_dir: Optional[Path] = None

    def cancel(self):
        self.cancel_requested = True
        self.stage = "cancelled"
        self.message = "使用者已手動中止任務"
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                time.sleep(0.3)
                if self.current_process.poll() is None:
                    self.current_process.kill()
            except Exception:
                pass
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def to_dict(self) -> Dict[str, Any]:
        now = time.time()
        elapsed = int(now - self.start_time) if self.stage in ("extracting", "upscaling", "encoding") else self.elapsed_seconds
        return {
            "task_id": self.task_id,
            "target_name": self.target_name,
            "stage": self.stage,
            "current_frame": self.current_frame,
            "total_frames": self.total_frames,
            "percent": self.percent,
            "message": self.message,
            "elapsed_seconds": elapsed,
            "eta_seconds": self.eta_seconds,
            "eta_text": self.eta_text,
            "cancel_requested": self.cancel_requested,
            "error": self.error,
            "result": self.result
        }


class UpscaleTaskManager:
    def __init__(self):
        self.tasks: Dict[str, UpscaleTask] = {}
        self.lock = threading.Lock()

    def create_task(self, task_id: str, target_name: str, total_frames: int) -> UpscaleTask:
        with self.lock:
            task = UpscaleTask(task_id, target_name, total_frames)
            self.tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Optional[UpscaleTask]:
        with self.lock:
            return self.tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                task.cancel()
                return True
            return False


upscale_manager = UpscaleTaskManager()
