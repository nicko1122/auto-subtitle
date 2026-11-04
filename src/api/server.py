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
from ..core.video_burner import burn_subtitles_to_video, get_video_info
from ..core.exporter import to_srt, to_vtt, to_json, save_file
from ..core.css_parser import parse_css_to_style_dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto-subtitle-api")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
INPUTCLIP_DIR = BASE_DIR / "inputclip"
PRESETS_DIR = BASE_DIR / "presets"
STATIC_DIR = BASE_DIR / "src" / "web" / "static"
TEMPLATES_DIR = BASE_DIR / "src" / "web" / "templates"

for d in (UPLOADS_DIR, OUTPUT_DIR, STATIC_DIR, TEMPLATES_DIR, PRESETS_DIR):
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


@app.get("/api/samples")
async def list_sample_assets():
    """取得現有測試素材清單 (包含 inputclip 內的檔案)"""
    samples = []
    if INPUTCLIP_DIR.exists():
        for p in INPUTCLIP_DIR.glob("*"):
            if p.is_file() and p.suffix.lower() in (".mp4", ".mov", ".wav", ".srt", ".vtt", ".txt", ".json"):
                samples.append({
                    "name": p.name,
                    "path": f"/inputclip/{p.name}",
                    "absolute_path": str(p),
                    "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
                    "type": p.suffix.lower().lstrip(".")
                })
    return {"samples": samples}


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
async def upload_asset(file: UploadFile = File(...)):
    """上傳檔案 (影片、音訊、字幕或文字檔)"""
    dest = UPLOADS_DIR / file.filename
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 若為影片，解析其時長與長寬
    info = {"width": 1920, "height": 1080, "duration": 0.0}
    if dest.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
        w, h, d = get_video_info(str(dest))
        info = {"width": w, "height": h, "duration": d}

    return {
        "status": "success",
        "filename": file.filename,
        "url": f"/uploads/{file.filename}",
        "absolute_path": str(dest),
        "info": info
    }


@app.post("/api/style/parse-css")
async def parse_css_endpoint(req: ParseCssRequest):
    """將 CSS 字串轉為 SubtitleStyle 物件"""
    try:
        style = SubtitleStyle.from_css(req.css)
        return {"status": "success", "style": style.model_dump(), "css": style.to_css()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ai/transcribe")
async def transcribe_endpoint(
    media_path: str = Form(...),
    model: str = Form("base"),
    device: str = Form("cuda"),
    prompt: Optional[str] = Form("繁體中文")
):
    """【步驟 1】AI 語音辨識與自動斷句生成 SubtitleTrack"""
    p = Path(media_path)
    if not p.exists():
        # 嘗試相對或 inputclip
        if (BASE_DIR / media_path.lstrip("/")).exists():
            p = BASE_DIR / media_path.lstrip("/")
        elif (INPUTCLIP_DIR / p.name).exists():
            p = INPUTCLIP_DIR / p.name
        elif (UPLOADS_DIR / p.name).exists():
            p = UPLOADS_DIR / p.name
        else:
            raise HTTPException(status_code=404, detail=f"找不到媒體檔案: {media_path}")

    # 若為影片，先提取 16kHz WAV
    is_video = p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    if is_video:
        wav_path = UPLOADS_DIR / f"{p.stem}_extracted.wav"
        extract_res = extract_audio(str(p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(p)

    # 執行 faster-whisper 辨識
    try:
        raw_res = transcribe_audio(
            audio_path=audio_file,
            model_size=model,
            device=device,
            vad_filter=True,
            initial_prompt=prompt
        )
        track = build_subtitle_track(raw_res)
        return {"status": "success", "track": track.model_dump()}
    except Exception as e:
        logger.error(f"辨識失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/align")
async def align_endpoint(req: AlignRequest):
    """【有稿模式】利用原稿強制動態對齊"""
    p = Path(req.media_path)
    if not p.exists():
        if (INPUTCLIP_DIR / p.name).exists():
            p = INPUTCLIP_DIR / p.name
        elif (UPLOADS_DIR / p.name).exists():
            p = UPLOADS_DIR / p.name
        else:
            raise HTTPException(status_code=404, detail=f"找不到媒體檔案: {req.media_path}")

    # 音軌
    is_video = p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]
    if is_video:
        wav_path = UPLOADS_DIR / f"{p.stem}_extracted.wav"
        extract_res = extract_audio(str(p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(p)

    # 原稿
    script_source = req.script_text
    if not script_source and req.script_path:
        sp = Path(req.script_path)
        if not sp.exists():
            if (INPUTCLIP_DIR / sp.name).exists():
                sp = INPUTCLIP_DIR / sp.name
            elif (UPLOADS_DIR / sp.name).exists():
                sp = UPLOADS_DIR / sp.name
        if sp.exists():
            script_source = str(sp)

    if not script_source:
        raise HTTPException(status_code=400, detail="請提供原稿文字內容或原稿檔案路徑")

    try:
        # 先以 small 模型辨識 Word-level 時間戳記
        trans_res = transcribe_audio(
            audio_path=audio_file,
            model_size="small",
            device="cuda",
            vad_filter=False,  # 歌曲對齊通常關閉 VAD
            word_timestamps=True,
            initial_prompt="繁體中文"
        )
        track = align_script_to_audio(script_source, trans_res)
        return {"status": "success", "track": track.model_dump()}
    except Exception as e:
        logger.error(f"對齊失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/proofread")
async def proofread_endpoint(req: ProofreadRequest):
    """【無稿模式】使用本地 Qwen2.5 進行錯別字校對"""
    try:
        proofreader = SubtitleProofreader(n_gpu_layers=-1)
        corrected_track = proofreader.proofread_track(req.track, batch_size=req.batch_size)
        return {"status": "success", "track": corrected_track.model_dump()}
    except Exception as e:
        logger.error(f"校對失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/burn")
async def burn_endpoint(req: BurnVideoRequest):
    """【Hardcopy 壓制】將字幕硬燒錄進影片中"""
    v_path = Path(req.video_path)
    if not v_path.exists():
        if (INPUTCLIP_DIR / v_path.name).exists():
            v_path = INPUTCLIP_DIR / v_path.name
        elif (UPLOADS_DIR / v_path.name).exists():
            v_path = UPLOADS_DIR / v_path.name
        else:
            raise HTTPException(status_code=404, detail=f"找不到來源影片: {req.video_path}")

    # 樣式決定 (若提供 CSS，優先解析 CSS)
    if req.css:
        style = SubtitleStyle.from_css(req.css)
    elif req.style:
        style = req.style
    else:
        style = SubtitleStyle()

    # 字幕來源決定
    if req.track:
        sub_source = req.track
    elif req.subtitle_path:
        sub_source = req.subtitle_path
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
