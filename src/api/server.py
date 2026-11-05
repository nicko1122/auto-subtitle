import os
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..schemas.subtitle import SubtitleTrack, SubtitleSegment, SubtitleStyle
from ..core.audio_extractor import extract_audio
from ..core.transcriber import transcribe_audio
from ..core.segmenter import build_subtitle_track
from ..core.aligner import align_script_to_audio
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態與媒體目錄
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/inputclip", StaticFiles(directory=str(INPUTCLIP_DIR)), name="inputclip")
app.mount("/presets", StaticFiles(directory=str(PRESETS_DIR)), name="presets")
app.mount("/fonts", StaticFiles(directory=str(FONTS_DIR)), name="fonts")


# ---------------- API Schemas ----------------
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


class ProofreadRequest(BaseModel):
    track: SubtitleTrack
    batch_size: int = 8


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
    model: str = "small"
    device: str = "cuda"
    prompt: str = "繁體中文"
    only_empty: bool = False
    auto_proofread: bool = False


# ---------------- API Endpoints ----------------
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return index_file.read_text(encoding="utf-8")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "Auto Subtitle Studio"}


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
        "url": f"{url_prefix}/{p.name}",
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


@app.get("/api/assets")
async def list_assets():
    """
    列出伺服器上已儲存的資產 (uploads/ 使用者資產 以及 inputclip/ 精選範例)
    自動排除暫存音軌 (*_extracted.wav) 與開發測試產物，並辨識成對的影片與字幕！
    """
    assets = []

    # 1. 掃描 uploads 目錄 (使用者上傳資產)
    if UPLOADS_DIR.exists():
        for p in sorted(UPLOADS_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True):
            if not p.is_file() or p.name.startswith("."):
                continue
            # 排除舊版遺留的提取音軌或暫存檔
            if p.name.endswith("_extracted.wav") or p.name.endswith(".temp_burn.ass"):
                continue
            assets.append(_inspect_asset_item(p, "uploads", "/uploads"))

    # 2. 掃描 inputclip 範例目錄 (僅保留乾淨的核心範例檔，過濾中間 json 與 vtt)
    ALLOWED_SAMPLES = {"test_video.mp4", "audio.aligned.srt", "audio-org.txt", "audio.srt"}
    if INPUTCLIP_DIR.exists():
        for p in sorted(INPUTCLIP_DIR.glob("*")):
            if p.is_file() and p.name in ALLOWED_SAMPLES:
                assets.append(_inspect_asset_item(p, "inputclip", "/inputclip"))

    # 3. 關聯配對同檔名之影片與字幕 (例如 director-film.mp4 配對 director-film.srt)
    for item in assets:
        if item["type"] == "video":
            stem = item["stem"]
            matched_sub = next(
                (a for a in assets if a["type"] == "subtitle" and (a["stem"] == stem or a["stem"].startswith(stem + "."))),
                None
            )
            item["paired_subtitle"] = matched_sub

    return {"assets": assets}


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
async def upload_asset(files: List[UploadFile] = File(...)):
    """
    支援單檔或多檔批量上傳 (影片、音訊、SRT字幕、文字檔或 TTF/OTF 字型檔)
    若包含 SRT / VTT 字幕，自動解析為帶有時間軸的 SubtitleTrack 回傳，實現直接載入！
    若包含 TXT 原稿，一併回傳原稿內容供有稿對齊直接使用！
    若包含 TTF / OTF / TTC / WOFF2 字型檔，自動安裝至專案 fonts/ 目錄並回傳字型家族資訊！
    """
    uploaded_items = []
    parsed_tracks = []
    videos = []
    scripts = []
    fonts = []

    for file in files:
        safe_name = Path(file.filename or "unnamed").name
        ext = Path(safe_name).suffix.lower()

        # 若為字型檔案 (.ttf / .otf / .ttc / .woff2)，直接安裝至 fonts/ 目錄
        if ext in ALLOWED_FONT_EXTS:
            font_dest = FONTS_DIR / safe_name
            with font_dest.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            font_info = install_font_from_file(str(font_dest), custom_filename=safe_name)
            fonts.append(font_info)
            uploaded_items.append({
                "name": safe_name,
                "folder": "fonts",
                "type": "font",
                "url": font_info["url"],
                "family": font_info["family"],
                "display_name": font_info["display_name"],
                "size_mb": font_info["size_mb"]
            })
            continue

        dest = UPLOADS_DIR / safe_name
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        item_info = _inspect_asset_item(dest, "uploads", "/uploads")
        f_type = item_info["type"]

        # 若為影片，解析解析度與時長
        if f_type == "video":
            w, h, d = get_video_info(str(dest))
            item_info["width"] = w
            item_info["height"] = h
            item_info["duration"] = d
            videos.append(item_info)

        # 若為 SRT / VTT / JSON 字幕，立即解析為 SubtitleTrack
        elif f_type == "subtitle":
            try:
                content = dest.read_text(encoding="utf-8")
                if dest.suffix.lower() == ".json":
                    track = SubtitleTrack(**json.loads(content))
                else:
                    track = parse_srt_content(content, source_file=safe_name)
                parsed_tracks.append({
                    "filename": safe_name,
                    "url": f"/uploads/{safe_name}",
                    "track": track.model_dump()
                })
            except Exception as e:
                logger.warning(f"解析上傳之字幕失敗 ({safe_name}): {e}")

        # 若為 TXT 原稿/歌詞
        elif f_type == "text":
            try:
                content = dest.read_text(encoding="utf-8")
                scripts.append({
                    "filename": safe_name,
                    "url": f"/uploads/{safe_name}",
                    "absolute_path": str(dest),
                    "content": content,
                    "line_count": item_info.get("line_count", 0)
                })
            except Exception as e:
                logger.warning(f"讀取上傳之原稿失敗 ({safe_name}): {e}")

        uploaded_items.append(item_info)

    return {
        "status": "success",
        "uploaded": uploaded_items,
        "videos": videos,
        "tracks": parsed_tracks,
        "scripts": scripts,
        "fonts": fonts
    }


@app.get("/api/fonts")
async def list_fonts_endpoint():
    """取得已安裝字型、系統內建字型、可一鍵安裝開源字型包與本機 Windows 字型清單"""
    return get_font_catalog()


@app.post("/api/fonts/upload")
async def upload_fonts_endpoint(files: List[UploadFile] = File(...)):
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
        dest = FONTS_DIR / safe_name
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        info = install_font_from_file(str(dest), custom_filename=safe_name)
        installed.append(info)
    return {"status": "success", "installed": installed, "catalog": get_font_catalog()}


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
    if p.exists() and p.is_file():
        return p
    rel = BASE_DIR / media_path.lstrip("/")
    if rel.exists() and rel.is_file():
        return rel
    if (UPLOADS_DIR / p.name).exists():
        return UPLOADS_DIR / p.name
    if (INPUTCLIP_DIR / p.name).exists():
        return INPUTCLIP_DIR / p.name
    raise HTTPException(status_code=404, detail=f"找不到檔案: {media_path}")


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
def transcribe_locked_segments_endpoint(req: TranscribeLockedRequest):
    """【階段三：依鎖定時間軸填字】嚴格依照使用者已確認的每個 #index [start, end] 執行受控 Whisper 填字"""
    p = _resolve_media_path(req.media_path)
    try:
        updated_track = transcribe_on_locked_timeline(
            media_path=str(p),
            track=req.track,
            model_size=req.model,
            device=req.device,
            prompt=req.prompt,
            only_empty=req.only_empty,
            auto_proofread=req.auto_proofread
        )
        return {"status": "success", "track": updated_track.model_dump()}
    except Exception as e:
        logger.error(f"依鎖定時間軸辨識失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/transcribe")
def transcribe_endpoint(
    media_path: str = Form(...),
    model: str = Form("large-v3-turbo"),
    device: str = Form("cuda"),
    prompt: Optional[str] = Form("繁體中文"),
    auto_proofread: bool = Form(False)
):
    """【無稿模式】AI 語音辨識與自動斷句生成 SubtitleTrack（可選一併執行 Qwen2.5 錯字校對）"""
    p = _resolve_media_path(media_path)

    # 若為影片，提取 16kHz WAV 至 TEMP_DIR (避免污染 uploads 資產庫)
    is_video = p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    if is_video:
        wav_path = TEMP_DIR / f"{p.stem}_extracted.wav"
        extract_res = extract_audio(str(p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(p)

    try:
        raw_res = transcribe_audio(
            audio_path=audio_file,
            model_size=model,
            device=device,
            vad_filter=True,
            initial_prompt=prompt
        )
        track = build_subtitle_track(raw_res)

        if auto_proofread and track.segments:
            proofreader = SubtitleProofreader(n_gpu_layers=-1)
            try:
                track = proofreader.proofread_track(track, batch_size=8)
            finally:
                proofreader.close()

        return {"status": "success", "track": track.model_dump()}
    except Exception as e:
        logger.error(f"辨識失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/align")
def align_endpoint(req: AlignRequest):
    """【有稿模式】利用原稿強制動態對齊"""
    p = _resolve_media_path(req.media_path)

    is_video = p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    if is_video:
        wav_path = TEMP_DIR / f"{p.stem}_extracted.wav"
        extract_res = extract_audio(str(p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(p)

    script_source = req.script_text
    if not script_source and req.script_path:
        sp = _resolve_media_path(req.script_path)
        script_source = str(sp)

    if not script_source:
        raise HTTPException(status_code=400, detail="請提供原稿文字內容或原稿檔案路徑")

    try:
        trans_res = transcribe_audio(
            audio_path=audio_file,
            model_size="large-v3-turbo",
            device="cuda",
            vad_filter=False,
            word_timestamps=True,
            initial_prompt="繁體中文"
        )
        track = align_script_to_audio(script_source, trans_res)
        return {"status": "success", "track": track.model_dump()}
    except Exception as e:
        logger.error(f"對齊失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/proofread")
def proofread_endpoint(req: ProofreadRequest):
    """【無稿模式】使用本地 Qwen2.5 進行錯別字校對"""
    proofreader = None
    try:
        proofreader = SubtitleProofreader(n_gpu_layers=-1)
        corrected_track = proofreader.proofread_track(req.track, batch_size=req.batch_size)
        return {"status": "success", "track": corrected_track.model_dump()}
    except Exception as e:
        logger.error(f"校對失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if proofreader is not None:
            proofreader.close()


@app.post("/api/burn")
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

    out_name = f"{v_path.stem}_burned_{os.getpid()}.mp4"
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
