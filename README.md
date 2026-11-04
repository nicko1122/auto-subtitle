# AutoSubtitle AI (自動上字幕與影音工作台)

一個結合本地端 **Faster-Whisper (CUDA)**、**動態規劃原稿強制對齊 (Forced Alignment)**、**Qwen2.5 Edge LLM 錯字校對**、**Web CSS 盒模型排版**與 **NVIDIA NVENC 硬字幕燒錄**的全功能字幕自動化系統。

---

## ✨ 核心功能

1. **三種字幕產生流程**：
   - **現成字幕直載**：支援拖入 `Video + SRT/VTT`，免重跑 AI 直接預覽、改字與壓制。
   - **無稿模式 (Unscripted AI)**：FFmpeg 提取 16kHz 單聲道音軌 ➔ Faster-Whisper 逐字時間戳辨識 ➔ 智慧標點/停頓斷句 ➔ 本地 Qwen2.5-3B-Instruct (GGUF) 自動修正同音錯字。
   - **有稿模式 (Forced Alignment)**：提供歌詞或逐字稿 `.txt`，透過拼音相似度與 Needleman-Wunsch 動態規劃演算法（含 Sakoe-Chiba 搜尋帶加速），100% 保留原稿文字並精準對齊時間軸。
2. **Web CSS 盒模型與直/橫式排版引擎**：
   - 支援標準 CSS 屬性（`font-size`, `color`, `-webkit-text-stroke`, `text-shadow`, `writing-mode: vertical-rl`, `padding`, `text-align`, `vertical-align`）。
   - 橫式與直式字幕（自動多列右至左換列）在 Web 預覽與 FFmpeg ASS 硬字幕壓制保持一致。
3. **視覺化 Web Studio 工作台**：
   - 左右 50/50 對稱全屏設計，左側為原生比例等比錨定播放器，右側提供「資產與工作流、字幕編輯器、CSS 樣式與位置、GPU 壓制與匯出」四大工作頁籤。

---

## 🚀 快速開始

### 1. 啟動視覺化 Web Studio 工作台
```bash
.venv/bin/python3 src/cli/main.py serve --host 0.0.0.0 --port 8000
```
啟動後開啟瀏覽器造訪 **`http://localhost:8000`**。

### 2. CLI 指令工具箱

```bash
# 一鍵無稿辨識全流程 (Video -> WAV -> Whisper -> SRT/VTT/JSON)
.venv/bin/python3 src/cli/main.py pipeline inputclip/test_video.mp4 -m small

# 有稿模式：原稿/歌詞強制時間軸對齊
.venv/bin/python3 src/cli/main.py align inputclip/audio.wav inputclip/audio-org.txt --no-vad

# 無稿校對：使用本地 Qwen2.5 修正 SRT 或 JSON 內的同音錯字
.venv/bin/python3 src/cli/main.py proofread inputclip/audio.srt

# 硬字幕壓制 (支援 CSS 樣式檔或行內 CSS + NVENC 硬體加速)
.venv/bin/python3 src/cli/main.py burn inputclip/test_video.mp4 inputclip/audio.aligned.srt --css-file presets/tiktok_vertical.css
```

---

## 🧪 執行單元測試
```bash
.venv/bin/python3 tests/test_pipeline.py
```
