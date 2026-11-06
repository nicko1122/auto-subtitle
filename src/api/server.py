import os
import json
import logging
import shutil
import uuid
import ipaddress
import tempfile
from urllib.parse import quote

from . import asset_packages
from .model_tasks import model_task
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..schemas.subtitle import SubtitleTrack, SubtitleSegment, SubtitleStyle
from ..core.audio_extractor import extract_audio
from ..core.transcriber import WHISPER_MODEL, transcribe_audio
from ..core.segmenter import build_subtitle_track
from ..core.aligner import align_script_to_audio
from ..core.luna_pipeline import run_luna_pipeline, LunaPipeline
from ..core.proofreader import SubtitleProofreader
from ..core.acoustic_analyzer import (
    analyze_audio_breakpoints,
    snap_time_to_valley,
    transcribe_on_locked_timeline
)
from ..core.video_burner import burn_subtitles_to_video, get_video_info
from ..core.exporter import to_srt, to_vtt, to_json, save_file, parse_srt_content
from ..core.css_parser import parse_css_to_style_dict
from ..core.font_manager import (
    FONTS_DIR,
    ALLOWED_FONT_EXTS,
    get_font_catalog,
    install_font_from_file,
    install_font_from_url,
    install_preset_or_windows_font,
    delete_custom_font
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto-subtitle-api")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
INPUTCLIP_DIR = BASE_DIR / "inputclip"
PRESETS_DIR = BASE_DIR / "presets"
STATIC_DIR = BASE_DIR / "src" / "web" / "static"
TEMPLATES_DIR = BASE_DIR / "src" / "web" / "templates"

for d in (UPLOADS_DIR, OUTPUT_DIR, TEMP_DIR, STATIC_DIR, TEMPLATES_DIR, PRESETS_DIR, FONTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Auto Subtitle Web Studio", version="1.0.0")

@app.middleware("http")
async def disable_static_html_cache(request, call_next):
    host = request.url.hostname
    try:
        ipaddress.ip_address(host)
    except ValueError:
        allowed_hosts = os.environ.get("AUTOSUBTITLE_ALLOWED_HOSTS", "localhost").split(",")
        if host not in [h.strip() for h in allowed_hosts]:
            return JSONResponse(status_code=403, content={"detail": "請使用 localhost、伺服器 IP 或設定 AUTOSUBTITLE_ALLOWED_HOSTS"})
    origin = request.headers.get("origin")
    if (origin and origin.rstrip("/") != f"{request.url.scheme}://{request.url.netloc}") or request.headers.get("sec-fetch-site") == "cross-site":
        return JSONResponse(status_code=403, content={"detail": "不允許跨來源存取"})
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# 掛載靜態與媒體目錄
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/inputclip", StaticFiles(directory=str(INPUTCLIP_DIR)), name="inputclip")
app.mount("/presets", StaticFiles(directory=str(PRESETS_DIR)), name="presets")
app.mount("/fonts", StaticFiles(directory=str(FONTS_DIR)), name="fonts")


# ---------------- API Schemas ----------------
class PackageRequest(BaseModel):
    path: str


class MovePackageRequest(PackageRequest):
    destination: str


class SavePackageRequest(PackageRequest):
    track: Optional[SubtitleTrack] = None
    script_text: Optional[str] = None


class ParseCssRequest(BaseModel):
    css: str


class BurnVideoRequest(BaseModel):
    video_path: str
    track: Optional[SubtitleTrack] = None
    subtitle_path: Optional[str] = None
    style: Optional[SubtitleStyle] = None
    css: Optional[str] = None


class AlignRequest(BaseModel):
    media_path: str
    script_text: Optional[str] = None
    script_path: Optional[str] = None
    llm_provider: Literal["local", "api"] = "local"
    device: str = "cuda"
    prompt: Optional[str] = "繁體中文"
    auto_proofread: bool = True
    script_mode: Literal["reference", "transcript"] = "transcript"


class ProofreadRequest(BaseModel):
    track: SubtitleTrack
    batch_size: int = 8
    script_text: Optional[str] = None
    llm_provider: Literal["local", "api"] = "local"


class InstallFontRequest(BaseModel):
    preset_id: Optional[str] = None
    url: Optional[str] = None
    filename: Optional[str] = None


class BreakpointAnalyzeRequest(BaseModel):
    media_path: str
    mode: str = "balanced"  # "dense" | "balanced" | "slow"


class SnapSplitRequest(BaseModel):
    media_path: str
    time_sec: float


class TranscribeLockedRequest(BaseModel):
    media_path: str
    track: SubtitleTrack
    device: str = "cuda"
    prompt: str = "繁體中文"
    only_empty: bool = False
    auto_proofread: bool = False
    llm_provider: Literal["local", "api"] = "local"


# ---------------- API Endpoints ----------------
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return index_file.read_text(encoding="utf-8")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "Auto Subtitle Studio", "whisper": {"model": WHISPER_MODEL, "backend": "native"}}


def detect_file_type(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in (".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv"):
        return "video"
    elif ext in (".srt", ".vtt", ".json"):
        return "subtitle"
    elif ext in (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"):
        return "audio"
    elif ext in (".txt", ".lrc"):
        return "text"
    return "other"


def _inspect_asset_item(p: Path, folder: str, url_prefix: str) -> Dict[str, Any]:
    """解析單一資產檔案的中繼資料（包含字幕句數、原稿行數等）"""
    f_type = detect_file_type(p)
    size_mb = round(p.stat().st_size / (1024 * 1024), 2)
    item: Dict[str, Any] = {
        "name": p.name,
        "stem": p.stem,
        "folder": folder,
        "is_sample": (folder == "inputclip"),
        "url": f"{url_prefix}/{quote(p.name)}",
        "absolute_path": str(p),
        "size_mb": size_mb,
        "type": f_type,
        "modified_at": p.stat().st_mtime
    }

    if f_type == "subtitle":
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if p.suffix.lower() in (".srt", ".vtt"):
                item["segment_count"] = text.count("-->")
            elif p.suffix.lower() == ".json":
                data = json.loads(text)
                item["segment_count"] = len(data.get("segments", []))
        except Exception:
            item["segment_count"] = 0
    elif f_type == "text":
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            item["line_count"] = len(lines)
        except Exception:
            item["line_count"] = 0

    return item


def _describe_package(directory: Path):
    relative = directory.relative_to(UPLOADS_DIR).as_posix()
    media, subtitle, script = asset_packages.package_files(directory)
    prefix = "/uploads/" + quote(relative)
    def inspect(path):
        if path is None:
            return None
        item = _inspect_asset_item(path, "uploads", prefix)
        item["package_path"] = relative
        return item
    return {
        "path": relative, "name": directory.name,
        "media": inspect(media), "subtitle": inspect(subtitle), "script": inspect(script),
        "modified_at": max(p.stat().st_mtime for p in (media, subtitle, script) if p is not None),
    }


@app.get("/api/assets")
def list_assets():
    with asset_packages.mutation_lock:
        packages = []
        for path in asset_packages.list_packages(UPLOADS_DIR):
            try:
                packages.append(_describe_package(path))
            except ValueError as error:
                packages.append({"path": path.relative_to(UPLOADS_DIR).as_posix(), "name": path.name, "error": str(error)})
        assets = []
        for package in packages:
            if "error" in package:
                continue
            package["media"]["paired_subtitle"] = package["subtitle"]
            assets.extend(package[key] for key in ("media", "subtitle", "script") if package[key])
        # Keep loose files visible to existing API clients without moving user files on startup.
        for root, folder in ((UPLOADS_DIR, "uploads"), (INPUTCLIP_DIR, "inputclip")):
            for path in root.glob("*"):
                if path.is_file() and not path.is_symlink() and not path.name.startswith("."):
                    assets.append(_inspect_asset_item(path, folder, "/" + folder))
        return {"assets": assets, "packages": packages}


@app.post("/api/packages/open")
def open_package(req: PackageRequest):
    try:
        with asset_packages.mutation_lock:
            directory = asset_packages.resolve_package(UPLOADS_DIR, req.path)
            package = _describe_package(directory)
            media, subtitle, script = asset_packages.package_files(directory)
            track = parse_srt_content(subtitle.read_text(encoding="utf-8-sig"), subtitle.name) if subtitle else SubtitleTrack(source_file=media.stem + ".srt")
            return {"package": package, "track": track.model_dump(), "script_text": script.read_text(encoding="utf-8-sig") if script else ""}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/packages/save")
def save_package(req: SavePackageRequest):
    try:
        with asset_packages.mutation_lock:
            directory = asset_packages.resolve_package(UPLOADS_DIR, req.path)
            media, subtitle, script = asset_packages.package_files(directory)
            if req.track is not None:
                asset_packages.atomic_write(subtitle or directory / (media.stem + ".srt"), to_srt(req.track))
            if req.script_text is not None:
                asset_packages.atomic_write(script or directory / (media.stem + ".txt"), req.script_text)
            return {"status": "success", "package": _describe_package(directory)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/packages/move")
def move_package(req: MovePackageRequest):
    try:
        with asset_packages.mutation_lock:
            directory = asset_packages.move_package(UPLOADS_DIR, req.path, req.destination)
            return {"status": "success", "package": _describe_package(directory)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/packages")
def delete_package(path: str):
    try:
        with asset_packages.mutation_lock:
            directory = asset_packages.resolve_package(UPLOADS_DIR, path)
            asset_packages.package_files(directory)
            shutil.rmtree(directory)
            return {"status": "success"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/presets")
async def list_css_presets():
    """取得預設的 CSS 樣式集"""
    presets = []
    if PRESETS_DIR.exists():
        for p in PRESETS_DIR.glob("*.css"):
            content = p.read_text(encoding="utf-8")
            presets.append({
                "name": p.stem.replace("_", " ").title(),
                "filename": p.name,
                "url": f"/presets/{p.name}",
                "content": content
            })
    return {"presets": presets}


@app.post("/api/upload")
def upload_asset(files: List[UploadFile] = File(...), package_path: Optional[str] = Form(None)):
    media_files = []
    fonts = []
    for file in files:
        name = Path(file.filename or "unnamed").name
        if Path(name).suffix.lower() in ALLOWED_FONT_EXTS:
            fonts.append(file)
        else:
            media_files.append((file.filename or "unnamed", file.file))
    try:
        if package_path and media_files:
            with asset_packages.mutation_lock:
                directory = asset_packages.resolve_package(UPLOADS_DIR, package_path)
                suffixes = [Path(name).suffix.lower() for name, _ in media_files]
                if any(suffix not in asset_packages.SUBTITLE_EXTENSIONS | asset_packages.SCRIPT_EXTENSIONS for suffix in suffixes):
                    raise ValueError("補入資產包僅接受字幕或原稿；新增影片請建立新包")
                if sum(suffix in asset_packages.SUBTITLE_EXTENSIONS for suffix in suffixes) > 1 or sum(suffix in asset_packages.SCRIPT_EXTENSIONS for suffix in suffixes) > 1:
                    raise ValueError("一次補入一份工作字幕與一份原稿")
                directories = [asset_packages.import_files(UPLOADS_DIR, "", media_files, target=directory)]
        else:
            groups = asset_packages.group_uploads(media_files)
            directories = [asset_packages.import_files(UPLOADS_DIR, name, items) for name, items in groups.items()]
        installed_fonts = []
        for file in fonts:
            name = Path(file.filename).name
            installed_fonts.append(_install_uploaded_font(file, name))
        packages = [_describe_package(path) for path in directories]
        uploaded, videos, tracks, scripts = [], [], [], []
        for package in packages:
            media, subtitle, script = package["media"], package["subtitle"], package["script"]
            if media["type"] == "video":
                width, height, duration = get_video_info(media["absolute_path"])
                media.update(width=width, height=height, duration=duration)
            videos.append(media)
            uploaded.extend(item for item in (media, subtitle, script) if item)
            if subtitle:
                content = Path(subtitle["absolute_path"]).read_text(encoding="utf-8")
                tracks.append({"filename": subtitle["name"], "url": subtitle["url"], "track": parse_srt_content(content, subtitle["name"]).model_dump()})
            if script:
                scripts.append({**script, "content": Path(script["absolute_path"]).read_text(encoding="utf-8")})
        uploaded.extend({**font, "type": "font", "folder": "fonts"} for font in installed_fonts)
        return {
            "status": "success", "packages": packages, "uploaded": uploaded,
            "videos": videos, "tracks": tracks, "scripts": scripts, "fonts": installed_fonts,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/fonts")
async def list_fonts_endpoint():
    """取得已安裝字型、系統內建字型、可一鍵安裝開源字型包與本機 Windows 字型清單"""
    return get_font_catalog()


@app.post("/api/fonts/upload")
def upload_fonts_endpoint(files: List[UploadFile] = File(...)):
    """上傳 .ttf / .otf / .ttc / .woff2 字型檔案安裝至專案 fonts/ 目錄"""
    installed = []
    for file in files:
        safe_name = Path(file.filename or "unnamed.ttf").name
        ext = Path(safe_name).suffix.lower()
        if ext not in ALLOWED_FONT_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的字型格式 '{safe_name}'，請上傳 .ttf, .otf, .ttc 或 .woff2 檔案"
            )
        try:
            info = _install_uploaded_font(file, safe_name)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        installed.append(info)
    return {"status": "success", "installed": installed, "catalog": get_font_catalog()}


def _install_uploaded_font(file: UploadFile, name: str):
    with tempfile.TemporaryDirectory(dir=TEMP_DIR, prefix="font_upload_") as temporary:
        source = Path(temporary) / "font"
        with source.open("wb") as output:
            shutil.copyfileobj(file.file, output)
        return install_font_from_file(str(source), custom_filename=name)


@app.post("/api/fonts/install")
def install_font_endpoint(req: InstallFontRequest):
    """一鍵下載開源字型包、從自訂 URL 下載、或從本機 Windows 字型庫匯入字型"""
    try:
        if req.preset_id:
            info = install_preset_or_windows_font(req.preset_id)
        elif req.url:
            info = install_font_from_url(req.url, filename=req.filename)
        else:
            raise HTTPException(status_code=400, detail="請提供 preset_id 或字型下載 url")
        return {"status": "success", "font": info, "catalog": get_font_catalog()}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"安裝字型失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/fonts/{filename}")
async def delete_font_endpoint(filename: str):
    """移除專案 fonts/ 目錄下的自訂字型"""
    if delete_custom_font(filename):
        return {"status": "success", "deleted": Path(filename).name, "catalog": get_font_catalog()}
    raise HTTPException(status_code=404, detail=f"找不到自訂字型檔案: {filename}")


@app.delete("/api/assets/{filename}")
async def delete_asset(filename: str):
    """刪除 uploads/ 內的資產 (含路徑穿越防護)"""
    safe_name = Path(filename).name
    dest = UPLOADS_DIR / safe_name
    if dest.exists() and dest.is_file():
        dest.unlink()
        return {"status": "success", "deleted": safe_name}
    raise HTTPException(status_code=404, detail=f"找不到檔案: {safe_name}")


@app.post("/api/style/parse-css")
async def parse_css_endpoint(req: ParseCssRequest):
    """將 CSS 字串轉為 SubtitleStyle 物件"""
    try:
        style = SubtitleStyle.from_css(req.css)
        return {"status": "success", "style": style.model_dump(), "css": style.to_css()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _resolve_media_path(media_path: str) -> Path:
    """安全解析使用者傳入的媒體或原稿路徑"""
    p = Path(media_path)
    roots = [d.resolve() for d in (UPLOADS_DIR, INPUTCLIP_DIR, OUTPUT_DIR, TEMP_DIR)]
    for candidate in (p, BASE_DIR / media_path.lstrip("/"), UPLOADS_DIR / p.name, INPUTCLIP_DIR / p.name):
        resolved = candidate.resolve()
        if any(resolved.is_relative_to(d) for d in roots) and resolved.is_file():
            return resolved
    raise HTTPException(status_code=404, detail="找不到媒體或原稿檔案")


@app.post("/api/audio/breakpoints")
def analyze_breakpoints_endpoint(req: BreakpointAnalyzeRequest):
    """【階段一：音訊斷點分析】秒級掃描音訊能量與換氣斷點，建立 #1 ~ #N 時間軸骨架與波形資料"""
    p = _resolve_media_path(req.media_path)
    try:
        res = analyze_audio_breakpoints(str(p), mode=req.mode)
        return {
            "status": "success",
            "mode": res["mode"],
            "duration": res["duration"],
            "segment_count": res["segment_count"],
            "waveform_peaks": res["waveform_peaks"],
            "track": res["track"].model_dump()
        }
    except Exception as e:
        logger.error(f"音訊斷點分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audio/snap-split")
def snap_split_endpoint(req: SnapSplitRequest):
    """在播放游標附近尋找聲學能量最低谷，讓手動切句不會切在字音正中間"""
    p = _resolve_media_path(req.media_path)
    try:
        snapped = snap_time_to_valley(str(p), req.time_sec)
        return {"status": "success", "snapped_time": snapped}
    except Exception as e:
        return {"status": "success", "snapped_time": round(req.time_sec, 2)}


@app.post("/api/ai/transcribe-segments")
@model_task
def transcribe_locked_segments_endpoint(req: TranscribeLockedRequest):
    """【階段三：依鎖定時間軸填字】嚴格依照使用者已確認的每個 #index [start, end] 執行受控 Whisper 填字"""
    p = _resolve_media_path(req.media_path)
    try:
        report = {}
        updated_track = transcribe_on_locked_timeline(
            media_path=str(p),
            track=req.track,
            device=req.device,
            prompt=req.prompt,
            only_empty=req.only_empty,
            auto_proofread=req.auto_proofread,
            llm_provider=req.llm_provider,
            proofread_report=report,
        )
        return {"status": "success", "track": updated_track.model_dump(), "proofread_warning": report.get("warning"), "proofread_report": report or None}
    except Exception as e:
        logger.error(f"依鎖定時間軸辨識失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/transcribe")
@model_task
def transcribe_endpoint(
    media_path: str = Form(...),
    device: str = Form("cuda"),
    prompt: Optional[str] = Form("繁體中文"),
    auto_proofread: bool = Form(True),
    script_text: Optional[str] = Form(None),
    llm_provider: Literal["local", "api"] = Form("local"),
    script_mode: Literal["reference", "transcript"] = Form("transcript"),
):
    """【單一入口 AI 產生字幕】
    支援智慧雙分流：
    1. 若提供 script_text (原稿/歌詞)：啟動《Whisper＋Luna 歌詞字幕 Pipeline》，
       利用 stable-ts 強制對齊、雙軌時間比對、局部切音重跑與本地 Qwen2.5 / 雲端 Luna 決策審核，
       依選定模型執行原生 Whisper，輸出字幕及診斷檔案。
    2. 若未提供 script_text：以 Whisper 提取時間軸，並由 Qwen2.5 / 雲端 LLM 進行上下文盲校。
    """
    p = _resolve_media_path(media_path)
    job_id = uuid.uuid4().hex

    # 若為影片，提取 16kHz WAV 至 TEMP_DIR (避免污染 uploads 資產庫)
    is_video = p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    if is_video:
        wav_path = TEMP_DIR / f"{job_id}_extracted.wav"
        extract_res = extract_audio(str(p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(p)

    clean_script = (script_text or "").strip()

    try:
        if clean_script:
            # 【有稿模式：呼叫完整 Luna 強制對齊管線】
            logger.info(f"啟動完整 Luna 歌詞字幕對齊管線 (LLM Provider: {llm_provider})...")
            job_dir = OUTPUT_DIR / job_id
            job_dir.mkdir()
            script_file = job_dir / "script.txt"
            script_file.write_text(clean_script, encoding="utf-8")
            track = run_luna_pipeline(
                audio_path=audio_file,
                lyrics_source=str(script_file),
                output_dir=str(job_dir),
                llm_provider=llm_provider,
                device=device,
                prompt=prompt,
                llm_audit=auto_proofread,
                script_mode=script_mode,
            )
            manifest_path = job_dir / "run_manifest.json"
            audit_warning = json.loads(manifest_path.read_text(encoding="utf-8")).get("audit_warning") if manifest_path.exists() else None
            return {
                "status": "success",
                "track": track.model_dump(),
                "has_reference": True,
                "proofread_warning": audit_warning,
                "mode": "luna_pipeline"
            }
        else:
            # 【無稿模式：Whisper 全曲辨識 + 盲校】
            whisper_prompt = prompt or "繁體中文"
            raw_res = transcribe_audio(
                audio_path=audio_file,
                device=device,
                initial_prompt=whisper_prompt
            )
            track = build_subtitle_track(raw_res)

            proofread_warning = None
            proofread_report = None
            if auto_proofread and track.segments:
                try:
                    proofreader = SubtitleProofreader(n_gpu_layers=-1, provider=llm_provider)
                    try:
                        track = proofreader.proofread_track(
                            track,
                            batch_size=25
                        )
                        proofread_warning = proofreader.warning
                        proofread_report = proofreader.last_report
                    finally:
                        proofreader.close()
                except Exception as pe:
                    logger.warning(f"LLM API 校對跳過: {pe}")
                    proofread_warning = str(pe)

            return {
                "status": "success",
                "track": track.model_dump(),
                "has_reference": False,
                "proofread_warning": proofread_warning,
                "proofread_report": proofread_report,
                "mode": "whisper_asr"
            }
    except Exception as e:
        logger.error(f"產生字幕失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if is_video:
            wav_path.unlink(missing_ok=True)


@app.post("/api/ai/align")
@model_task
def align_endpoint(req: AlignRequest):
    """【有稿模式】利用完整 Luna Pipeline 進行原稿強制對齊與時間軸審核"""
    p = _resolve_media_path(req.media_path)
    job_id = uuid.uuid4().hex

    is_video = p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    if is_video:
        wav_path = TEMP_DIR / f"{job_id}_extracted.wav"
        extract_res = extract_audio(str(p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(p)

    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir()
    script_source = None
    if req.script_text:
        script_file = job_dir / "script.txt"
        script_file.write_text(req.script_text, encoding="utf-8")
        script_source = str(script_file)
    if not script_source and req.script_path:
        sp = _resolve_media_path(req.script_path)
        script_source = str(sp)

    if not script_source:
        raise HTTPException(status_code=400, detail="請提供原稿文字內容或原稿檔案路徑")

    try:
        track = run_luna_pipeline(
            audio_path=audio_file,
            lyrics_source=script_source,
            output_dir=str(job_dir),
            llm_provider=req.llm_provider or "local",
            device=req.device,
            prompt=req.prompt,
            llm_audit=req.auto_proofread,
            script_mode=req.script_mode,
        )
        manifest_path = job_dir / "run_manifest.json"
        warning = json.loads(manifest_path.read_text(encoding="utf-8")).get("audit_warning") if manifest_path.exists() else None
        return {"status": "success", "track": track.model_dump(), "mode": "luna_pipeline", "proofread_warning": warning}
    except Exception as e:
        logger.error(f"對齊失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if is_video:
            wav_path.unlink(missing_ok=True)


@app.post("/api/ai/proofread")
@model_task
def proofread_endpoint(req: ProofreadRequest):
    """【無稿/有稿模式】使用本地 Qwen2.5 進行錯別字校對"""
    proofreader = None
    clean_script = (req.script_text or "").strip()
    try:
        proofreader = SubtitleProofreader(n_gpu_layers=-1, provider=req.llm_provider)
        corrected_track = proofreader.proofread_track(
            req.track,
            batch_size=req.batch_size,
            reference_script=clean_script if clean_script else None
        )
        return {"status": "success", "track": corrected_track.model_dump(), "has_reference": bool(clean_script), "proofread_warning": proofreader.warning, "proofread_report": proofreader.last_report}
    except Exception as e:
        logger.error(f"校對失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if proofreader is not None:
            proofreader.close()


@app.post("/api/burn")
@model_task
def burn_endpoint(req: BurnVideoRequest):
    """【Hardcopy 壓制】將字幕硬燒錄進影片中"""
    v_path = _resolve_media_path(req.video_path)

    if req.css:
        style = SubtitleStyle.from_css(req.css)
    elif req.style:
        style = req.style
    else:
        style = SubtitleStyle()

    if req.track:
        sub_source = req.track
    elif req.subtitle_path:
        sub_source = str(_resolve_media_path(req.subtitle_path))
    else:
        raise HTTPException(status_code=400, detail="請提供字幕軌道 (track) 或字幕檔案路徑 (subtitle_path)")

    out_name = f"{v_path.stem}_burned_{uuid.uuid4().hex}.mp4"
    out_file = OUTPUT_DIR / out_name

    try:
        out_path = burn_subtitles_to_video(
            video_path=str(v_path),
            subtitles_source=sub_source,
            output_path=str(out_file),
            style=style,
            use_gpu=True
        )
        return {
            "status": "success",
            "filename": out_name,
            "url": f"/output/{out_name}",
            "absolute_path": out_path
        }
    except Exception as e:
        logger.error(f"壓制失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
