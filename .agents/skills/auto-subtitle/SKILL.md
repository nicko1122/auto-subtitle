---
name: auto-subtitle
description: >-
  Automated audio extraction, Whisper speech-to-text, Luna dual-verification lyrics alignment,
  local Edge LLM proofreading, CSS subtitle styling, and NVENC GPU video hardsub burn-in.
  Activate this skill when processing video/audio for subtitles, aligning lyrics, running batch
  subtitle automation, or configuring ASS/CSS hardcopy video burning.
---

# AutoSubtitle AI - Automation & Agent Skill Guide

This skill guides you on how to automate subtitle extraction, speech-to-text transcription, lyrics forced-alignment (Luna pipeline), local LLM proofreading, and GPU-accelerated video hardsub burn-in using the `auto-subtitle` CLI and FastAPI backend.

---

## 📌 Workflow Decision Matrix

Choose the appropriate command or pipeline based on input assets:

| Scenario / Goal | Recommended Command | Key Arguments |
| :--- | :--- | :--- |
| **Singing / Lyrics Alignment** (Media + `.txt` lyrics) | `python src/cli/main.py luna` (or `align`) | `<media> <lyrics.txt> --llm local/api -o <dir>` |
| **Speech / Talk / Video to Subtitles** (No script) | `python src/cli/main.py pipeline` | `<media> -d cuda -o <dir>` |
| **Audio Only Extraction** | `python src/cli/main.py extract` | `<video> -o <audio.wav> --sr 16000` |
| **Fix Typos / Homophones** (with Edge LLM) | `python src/cli/main.py proofread` | `<subtitles.srt> --gpu-layers -1` |
| **Burn Subtitles into Video (Hardsub)** | `python src/cli/main.py burn` | `<video> <subtitles.srt> --css "..."` |
| **Manage Fonts** (Install open-source / Win fonts) | `python src/cli/main.py fonts` | `list`, `install <id/path/url>`, `remove <filename>` |
| **AI Video Upscaling (Super-Resolution)** | `python src/cli/main.py upscale` | `<video> --scale 2 --model realesr-animevideov3` |
| **Launch Web Studio** | `python src/cli/main.py serve` | `--host 0.0.0.0 --port 8000` |

---

## 🛠️ CLI Command Reference

### 1. Luna Lyrics Pipeline (`luna` / `align`)
Runs the 5-step dual verification pipeline: Whisper acoustic feature extraction + `stable-ts` alignment + LLM Decision Brain audit + +0.16s readability padding:
```bash
python src/cli/main.py luna inputclip/test_video.mp4 inputclip/audio-org.txt \
    --llm local \
    --output-dir output_luna
```
**Output Deliverables in `--output-dir`**:
- `lyrics.srt`: Standard SRT subtitle track.
- `lyrics.vtt`: WebVTT format for web players.
- `lyrics.lrc`: Enhanced LRC format with millisecond timestamps for music players.
- `lyrics.ass`: Formatted ASS subtitles ready for FFmpeg burning.
- `cue_evidence.json`: Full acoustic evidence and confidence metrics per line.
- `review.csv`: Detailed report of anomalous lines and LLM arbitration decisions.
- `run_manifest.json`: SHA-256 integrity hashes of source media and outputs.

### 2. End-to-End Speech Pipeline (`pipeline`)
Automatic speech pipeline for talk shows, podcasts, and lectures:
```bash
python src/cli/main.py pipeline inputclip/test_video.mp4 \
    --device cuda \
    --prompt "繁體中文" \
    --max-chars 16 \
    --pause 0.45 \
    --output-dir output/
```

### 3. Edge LLM Proofreading (`proofread`)
Runs local `Qwen2.5-3B-Instruct GGUF` with GPU offload to fix speech recognition errors:
```bash
python src/cli/main.py proofread output/video.srt \
    --gpu-layers -1 \
    --batch-size 8 \
    --output output/video.proofread.srt
```

### 4. GPU Hardsub Video Burning (`burn`)
Burns styled ASS subtitles directly into video frames with NVIDIA NVENC GPU acceleration:
```bash
# Using inline CSS string (Supports opacity, outward stroke, font, box-model padding, colors)
python src/cli/main.py burn inputclip/test_video.mp4 output/lyrics.srt \
    --css "font-family: 'Noto Sans CJK TC'; font-size: 36px; color: #FFD700; opacity: 0.85; -webkit-text-stroke: 3px #000; text-shadow: 2px 2px 3px #000; padding: 40px 40px 60px 40px;" \
    -o output/final_burned.mp4

# Or using an external CSS stylesheet:
python src/cli/main.py burn inputclip/test_video.mp4 output/lyrics.srt \
    --css-file styles/youtube_style.css \
    -o output/final_burned.mp4

# Or using explicit flags:
python src/cli/main.py burn inputclip/test_video.mp4 output/lyrics.srt \
    --font "jf-openhuninn-2.0" \
    --size 38 \
    --color "#FFFFFF" \
    --opacity 0.9 \
    --outline 3.0 \
    --outline-color "#000000" \
    --direction horizontal \
    --valign bottom \
    --halign center
```

### 5. Font Management (`fonts`)
```bash
# List all available, installed, and Windows system fonts
python src/cli/main.py fonts list

# Install popular open-source fonts by preset ID:
# Options: openhuninn (粉圓體), lxgw-wenkai (霞鶩文楷), iansui (芫荽體), win-msjhbd (微軟正黑粗體)
python src/cli/main.py fonts install openhuninn

# Install from URL or local file:
python src/cli/main.py fonts install https://example.com/font.ttf
python src/cli/main.py fonts install /path/to/custom_font.otf
```

### 6. AI Video Upscaling (`upscale`)
Uses Real-ESRGAN Compact lightweight video model (`realesr-animevideov3`) to upscale 2x or 4x:
```bash
# Upscale 2x with default Compact model
python src/cli/main.py upscale inputclip/test_video.mp4 --scale 2

# Upscale 4x with anime model
python src/cli/main.py upscale anime.mp4 --scale 4 --model realesrgan-x4plus-anime
```

---

## 🤖 Automation Recipes

### Recipe 1: Batch Process All Videos in a Directory (Bash)
```bash
#!/usr/bin/env bash
set -e
INPUT_DIR="./raw_videos"
OUTPUT_DIR="./dist_videos"
mkdir -p "$OUTPUT_DIR"

for video in "$INPUT_DIR"/*.mp4; do
  [ -f "$video" ] || continue
  filename=$(basename "$video")
  stem="${filename%.*}"
  lyrics="$INPUT_DIR/$stem.txt"
  
  echo "🚀 Processing: $filename"
  
  if [ -f "$lyrics" ]; then
    # Scripted lyrics pipeline
    python3 src/cli/main.py luna "$video" "$lyrics" --output-dir "$OUTPUT_DIR/$stem" --llm local
    sub_file="$OUTPUT_DIR/$stem/lyrics.srt"
  else
    # Unscripted speech pipeline
    python3 src/cli/main.py pipeline "$video" -d cuda --output-dir "$OUTPUT_DIR/$stem"
    sub_file="$OUTPUT_DIR/$stem/$stem.srt"
  fi
  
  # Burn hardsubs with branding style
  python3 src/cli/main.py burn "$video" "$sub_file" \
    --css "font-size: 34px; color: #FFFFFF; opacity: 0.9; -webkit-text-stroke: 2.5px #000; text-shadow: 2px 2px #000;" \
    -o "$OUTPUT_DIR/${stem}_subtitled.mp4"
    
  echo "✔ Finished: $stem"
done
```

### Recipe 2: Python Subtitle Generation Script
```python
from pathlib import Path
from src.core.luna_pipeline import run_luna_pipeline
from src.core.video_burner import burn_subtitles_to_video
from src.schemas.subtitle import SubtitleStyle

media_file = "inputclip/test_video.mp4"
lyrics_file = "inputclip/audio-org.txt"
out_dir = Path("output_automation")

# 1. Run Luna Dual-Verification Pipeline
track = run_luna_pipeline(
    audio_path=media_file,
    lyrics_source=lyrics_file,
    output_dir=str(out_dir),
    llm_provider="local"
)

# 2. Define Subtitle Style with Opacity & Outward Stroke
style = SubtitleStyle.from_css(
    "font-size: 36px; color: #FFD700; opacity: 0.85; -webkit-text-stroke: 3px #000;"
)

# 3. Burn Subtitles directly with NVENC GPU
burned_mp4 = burn_subtitles_to_video(
    video_path=media_file,
    subtitles_source=str(out_dir / "lyrics.srt"),
    output_path=str(out_dir / "burned_output.mp4"),
    style=style,
    use_gpu=True
)
print(f"Burned video created: {burned_mp4}")
```

### Recipe 3: REST API Integration (FastAPI)
The server runs on `http://localhost:8000`:
- **Transcribe / Unscripted**: `POST /api/ai/transcribe` with Form fields `media_path=...`, `auto_proofread=true`
- **Align / Luna Pipeline**: `POST /api/ai/align` with JSON `{"media_path": "...", "script_text": "...", "script_mode": "reference", "llm_provider": "local"}`
- **Parse CSS**: `POST /api/style/parse-css` with JSON `{"css": "font-size: 36px; opacity: 0.8;"}`
- **Burn Video**: `POST /api/burn` with JSON `{"video_path": "...", "subtitle_path": "...", "css": "..."}`

---

## 🎨 CSS Box Model & ASS Styling Mapping

When designing subtitle styles with `--css`:

| CSS Property | ASS Format Translation | Notes |
| :--- | :--- | :--- |
| `opacity: 0.85` | Inverted alpha hex `&H26FFFFFF&` | Alpha = `round((1 - opacity) * 255)`. 0=opaque, 255=transparent. |
| `-webkit-text-stroke: 4px #000` | `Outline: 2.0`, `OutlineColour: &H00000000&` | With `paint-order: stroke fill;`, stroke grows outward only. |
| `text-shadow: 2px 2px 3px #000` | `Shadow: 2.0`, `BackColour: &H80000000&` | Uses the larger absolute axis offset; equal-axis CSS round-trips without drift. |
| `writing-mode: vertical-rl` | Vertical column layout with `\N` breaks | Auto-wraps right-to-left when exceeding viewport height. |
| `text-align: center/left/right` | 九宮格 alignment mapping (1~9) | Bottom-center = 2, Top-center = 8, Middle-center = 5. |
| `padding: 50px 40px 60px 40px` | `MarginV`, `MarginL`, `MarginR` | Converted to ASS pixel margins relative to PlayRes resolution. |

---

## ⚠️ Important Implementation Notes

1. **GPU Acceleration**:
   - Whisper: All scripted, unscripted, and locked-timeline inference uses native Whisper `large-v3-turbo`. The model and backend are fixed; do not pass model or compute-type options.
   - Video Burn: Default `use_gpu=True` attempts FFmpeg `h264_nvenc`. Use CLI `--cpu` for `libx264` when NVENC is unavailable at runtime.
2. **Lyrics Multi-line Strings vs File Paths**:
   - `run_luna_pipeline` accepts either a file path (`.txt`) or a raw multiline lyrics string; the CLI takes a TXT path. Multi-line strings are parsed directly without file system path checks.
3. **No Overwriting of Source Subtitles**:
   - When generating `.srt` or `.vtt`, outputs are written to the target output directory or suffixed with `.generated.srt` if a file with the same name exists.
