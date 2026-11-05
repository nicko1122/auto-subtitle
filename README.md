# AutoSubtitle AI (智慧影音字幕工作台)

<p align="center">
  <b>結合聲學斷點分析、Faster-Whisper、GPT-6 Luna 雙軌歌詞對齊管線、地端/雲端 LLM 決策大腦、Web CSS 盒模型排版與 NVIDIA NVENC 硬字幕燒錄的一站式字幕系統。</b>
</p>

---

## 🌟 最新重大功能更新 (Latest Highlights)

### 1. 🌙 Whisper ＋ GPT-6 Luna 歌詞字幕對齊管線 (Luna Pipeline)
- **雙軌驗證架構 (Dual Verification)**：
  - **軌道 A**：Faster-Whisper (`large-v3-turbo` + CUDA) 全曲逐詞特徵提取與長句粗切。
  - **軌道 B**：原歌詞多行文字比對與 `stable-ts` 聲學強制對齊。
- **決策大腦 (Decision Brain)**：
  - 支援 **地端 Edge LLM (`Qwen2.5-3B-Instruct GGUF`)** 或 **雲端 API (OpenAI 相容 / GPT-6 Luna)**。
  - 智能掃描時長異常、單字密度過高或相似度偏低的異常句，進行單句精確仲裁，不擾動全局時間軸。
- **7 項標準交付產物 (Deliverables)**：
  - 一次性輸出：`lyrics.srt`、`lyrics.vtt`、`lyrics.lrc`（支援動態歌詞播放器）、`lyrics.ass`、`cue_evidence.json`（斷點聲學憑證）、`review.csv`（異常與校正報告）與 `run_manifest.json`（SHA-256 執行清單）。

### 2. 🎨 Web CSS 字幕樣式全面進化
- **透明度屬性（Opacity）**：
  - 支援 `0% ~ 100%`（`0.05 ~ 1.0`）平滑滑桿調節。
  - Web 影片預覽即時疊層透明效果。
  - 雙向解析 CSS `opacity: 0.8;` 或 `80%`。
  - **ASS 影音硬字幕同步**：自動換算 ASS 色彩 Alpha 通道（$$\text{Alpha} = \text{round}((1.0 - \text{opacity}) \times 255)$$），MP4 壓制時與 Web 預覽保持完全一致的透明度。
- **描邊外側生長（Outward Stroke）**：
  - 新增獨立描邊開關。
  - 引入 CSS `paint-order: stroke fill;`，描邊往外生長，絕不侵蝕內部筆畫字型。
- **字型安裝與管理中心**：
  - 一鍵安裝開源繁中字幕字型（粉圓體、文楷、芫荽體等）。
  - 支援本機 Windows 系統字型匯入與自訂網址 / 本機檔案上傳安裝，Web 預覽與 FFmpeg 壓片字型即時無縫生效。

### 3. 🛡️ 作業體驗防護（Semi-transparent Busy Modal）
- 長時間 AI 辨識／對齊任務執行時，自動顯示半透明整頁遮罩（`#busy-overlay`）搭配紫藍漸層旋轉動畫與實時碼錶，防止介面誤觸或重疊請求。

---

## ✨ 核心特色與工作流

### 1. 🎵 聲學斷點分析 ➔ 拍點快修 ➔ 鎖定時間軸填字（針對密集歌詞與歌唱語音）
- **階段 1：純聲學斷點掃描**：透過 Silero VAD ＋ 10ms 人聲高通 RMS 能量包絡波谷偵測，1 秒內標出全片發聲段落（`#1 ~ #N`），並自動計算預估字數與產生視覺化波形條。
- **階段 2：拍點快速校對**：
  - `🎧 聽頭` / `🎧 聽尾` / `▶ 整段` 試聽鈕（播放完畢自動暫停，省去手動按空白鍵的時間）。
  - `[` 設起點、`]` 設終點、`✂️ 游標處切開`（快捷鍵 `S`，自動吸附 `±0.18s` 最深換氣波谷）。
- **階段 3：鎖定時間軸填字**：
  - **手動模式**：直接打字（按下 `Enter` 自動跳下一段並試聽）、或貼上多行歌詞 1:1 填入。
  - **受控 Whisper 填空**：嚴格按校對好的起訖點切片辨識，按字數容量限制 Token 上限，**100% 不動時間軸、不跨句暴衝、不產生拖音幻覺**。

### 2. 🎯 有稿模式強制對齊 (Forced Alignment)
- 提供原稿/歌詞 `.txt`，透過 Needleman-Wunsch 動態規劃 ＋ Sakoe-Chiba 搜尋帶加速，以拼音相似度將原稿文字與語音強制對齊，100% 保留文字內容。

### 3. ✍️ 地端 Edge LLM 同音錯字校對 (Qwen2.5) / 雲端 API
- 內建 `Qwen2.5-3B-Instruct GGUF` 模型（GPU 全層加速），自動偵測並修正語音辨識常見的同音異字（如「開平洋 ➔ 太平洋」），亦支援透過 `.env` 設定雲端 OpenAI 相容模型。

### 4. 🎨 Web CSS 盒模型排版與 ASS 壓制引擎
- 支援標準 CSS 語法（`font-size`, `color`, `opacity`, `-webkit-text-stroke`, `paint-order`, `text-shadow`, `writing-mode: vertical-rl`, `padding`, `text-align`, `vertical-align`）。
- **直書長字幕自動多欄換行**：根據畫面高度自動由右至左折行（符合 CSS `vertical-rl` 規範）。
- **畫面直覺拖曳**：可直接在影片預覽區拖曳字幕位置，或使用 X / Y 滑桿平滑微調。

### 5. ⚡ NVIDIA NVENC GPU 硬字幕壓制 (Hardsub)
- 支援以 NVIDIA NVENC 硬體加速將 ASS 樣式字幕無損音軌直接燒錄進 MP4 影片中。

---

## 🛠️ 環境需求

- **作業系統**：Linux / Ubuntu / WSL2 (Windows Subsystem for Linux)
- **Python**：3.10+
- **系統相依**：`ffmpeg`, `ffprobe`, `fontconfig`
- **GPU (可選但推薦)**：支援 CUDA 之 NVIDIA 顯卡（如 GTX 1070 Ti、RTX 3060 或更高等級）

---

## 🚀 快速安裝 (含地端模型一鍵下載)

執行專案內建的一鍵安裝腳本，會自動建立虛擬環境、安裝相依庫，並下載地端 Qwen2.5 GGUF 與 Faster-Whisper 模型：

```bash
# 1. 複製專案
git clone https://github.com/nicko1122/auto-subtitle.git
cd auto-subtitle

# 2. 執行一鍵安裝與模型下載腳本
chmod +x install.sh
./install.sh
```

### ⚙️ 設定檔 (.env，可選)
若欲啟用雲端 LLM API（如 OpenAI / GPT-4o / GPT-6 Luna）：
```bash
cp .env.example .env
```
在 `.env` 中設定：
```env
LLM_PROVIDER=api
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

---

## 💻 使用方式

### 1. 啟動 Web Studio 視覺化工作台

```bash
source .venv/bin/activate
python3 src/cli/main.py serve --host 0.0.0.0 --port 8000
```
- 本機造訪：`http://localhost:8000`
- 搭配 Tailscale 遠端存取：`http://<Your-Tailscale-IP>:8000`

---

### 2. CLI 指令工具箱

```bash
# 查看所有可用指令
python3 src/cli/main.py --help

# 1. 🌙 執行 Whisper ＋ GPT-6 Luna 雙軌對齊管線
python3 src/cli/main.py luna inputclip/test_video.mp4 inputclip/audio-org.txt \
    --output-dir output_luna \
    --llm-provider auto

# 2. 音軌抽離 (16kHz Mono WAV)
python3 src/cli/main.py extract inputclip/test_video.mp4

# 3. 有稿強制時間軸對齊 (原稿 TXT + 影音)
python3 src/cli/main.py align inputclip/test_video.mp4 inputclip/audio-org.txt

# 4. 地端 Qwen2.5 錯別字校對
python3 src/cli/main.py proofread inputclip/audio.srt

# 5. 影片硬字幕燒錄 (支援 CSS 樣式與透明度)
python3 src/cli/main.py burn inputclip/test_video.mp4 inputclip/audio.aligned.srt \
    --css "font-size: 36px; color: #FFD700; opacity: 0.85; -webkit-text-stroke: 3px #000;"

# 6. 字型庫管理 (列出、安裝開源字型、匯入本機字型)
python3 src/cli/main.py fonts list
python3 src/cli/main.py fonts install openhuninn
```

---

## 🧪 執行單元測試

專案包含音訊聲學斷點、DTW 對齊、CSS 樣式解析、透明度與直排換欄的完整測試集：

```bash
source .venv/bin/activate
PYTHONPATH=. python3 tests/test_pipeline.py
PYTHONPATH=. python3 tests/test_api_endpoints.py
```

---

## 📂 專案結構

```text
auto-subtitle/
├── src/
│   ├── api/             # FastAPI 後端服務 (資產庫、AI 路由、樣式解析、字型管理 API)
│   ├── cli/             # Typer CLI 命令列介面
│   ├── core/            # 核心邏輯
│   │   ├── acoustic_analyzer.py  # 聲學斷點分析、能量波谷吸附、受控 Whisper
│   │   ├── aligner.py            # Needleman-Wunsch + Sakoe-Chiba DTW 強制對齊
│   │   ├── audio_extractor.py    # FFmpeg 抽音
│   │   ├── css_parser.py         # CSS 解析 (支援 opacity, paint-order, stroke)
│   │   ├── env_utils.py          # .env 與環境變數載入工具
│   │   ├── exporter.py           # SRT / VTT / JSON / ASS (含 Alpha 透明度計算) 匯出
│   │   ├── font_manager.py       # 字型安裝與管理中心
│   │   ├── luna_pipeline.py      # Whisper ＋ GPT-6 Luna 雙軌驗證管線核心
│   │   ├── proofreader.py        # llama-cpp-python Qwen2.5 與雲端 API 校對引擎
│   │   ├── transcriber.py        # Faster-Whisper 語音辨識
│   │   └── video_burner.py       # NVENC / libx264 影音壓制燒錄
│   ├── schemas/         # Pydantic 資料模型 (SubtitleTrack, SubtitleStyle 等)
│   └── web/             # 前端工作台 (Tailwind CSS, Vanilla JS, HTML 模板)
│       ├── static/app.js         # 前端應用邏輯 (含雙向 CSS、即時預覽、Modal)
│       └── templates/index.html  # 4-Tab 整合式工作台 UI
├── scripts/             # 輔助與管線腳本
├── install.sh           # 一鍵環境安裝與地端模型下載腳本
├── requirements.txt     # Python 相依清單
└── tests/               # 測試腳本
```

---

## 📄 License
MIT License
