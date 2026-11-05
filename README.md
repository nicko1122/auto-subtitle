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

### 3. 🛡️ 作業體驗防護（Semi-transparent Busy Modal & 60FPS Sync）
- 長時間 AI 辨識／對齊任務執行時，自動顯示半透明整頁遮罩（`#busy-overlay`）搭配紫藍漸層旋轉動畫與實時碼錶，防止介面誤觸或重疊請求。
- 採用 `requestAnimationFrame` 60FPS 毫秒級即時比對，歌詞唱完的一瞬間立刻乾淨消失，無任何拖泥帶水的殘影。

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
- **Python**：3.10–3.12（目前 `av<14` 的相容範圍）
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

可用 `PYTHON=/path/to/python3.12 ./install.sh` 指定直譯器。安裝失敗會停止，不會顯示完成。

Web 校對依「本地 / 雲端」選單執行；本地模式不讀取雲端金鑰。API 拒絕跨來源瀏覽器請求，檔案路徑限於 `uploads/`、`inputclip/`、`output/`、`temp/`。自訂服務網域需以 `AUTOSUBTITLE_ALLOWED_HOSTS=your.domain,localhost` 指定。

每次 Web 任務使用獨立輸出目錄／檔名；CLI `luna` 預設建立獨立資料夾，明確指定 `-o` 時沿用該目錄。除七項標準交付檔，另保留 `corrections.json` 與 `validation.json` 診斷檔。

### ⚙️ 設定檔 (.env，可選)
若欲啟用雲端 LLM API（如 OpenAI / GPT-4o / GPT-6 Luna）：
```bash
cp .env.example .env
```
在 `.env` 中設定：
```env
LLM_PROVIDER=openai
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

### 2. 📖 CLI 指令與完整參數手冊 (Command Reference)

CLI 適合批次自動化、伺服器排程與無頭（Headless）作業。輸入 `python3 src/cli/main.py --help` 可查看總覽。

#### 🔹 (1) `luna` / `align`：有稿歌詞雙軌對齊管線
結合 Whisper 聲學逐詞特徵與原歌詞文字，經決策大腦裁決產出 7 項標準交付檔：
```bash
python3 src/cli/main.py luna <媒體檔案> <原稿.txt> [OPTIONS]
```
| 參數名稱 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `media_path` | (必填) | - | 來源影音檔案路徑 (MP4, MKV, WAV 等) |
| `script_path` | (必填) | - | 原歌詞或字幕文字檔案路徑 (.txt) |
| `--llm` | - | `local` | 決策大腦模式：`local` (地端 Qwen GGUF) 或 `api` (雲端 OpenAI 相容) |
| `-o`, `--output-dir` | `-o` | 來源檔同目錄中的獨立資料夾 | 輸出交付產物之目錄 |

#### 🔹 (2) `pipeline`：無稿全自動上字幕流水線
針對演講、訪談或 Podcast，一鍵完成抽音、Whisper 辨識、智慧斷句並匯出字幕：
```bash
python3 src/cli/main.py pipeline <媒體檔案> [OPTIONS]
```
| 參數名稱 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `media_path` | (必填) | - | 來源影音檔案路徑 |
| `-m`, `--model` | `-m` | `base` | Faster-Whisper 模型大小 (`tiny`, `base`, `small`, `medium`, `large-v3-turbo`) |
| `-d`, `--device` | `-d` | `auto` | 運算裝置 (`auto`, `cuda`, `cpu`) |
| `-l`, `--lang` | `-l` | 自動辨識 | 指定語言代碼 (如 `zh`, `en`, `ja`) |
| `--prompt` | - | `繁體中文` | 引導詞 (預設引導模型產出正體中文) |
| `-c`, `--max-chars`| `-c` | `16` | 單行字幕最大字數 (中文建議 12~18) |
| `-p`, `--pause` | `-p` | `0.45` | 視為句子斷點的語音停頓時間 (秒) |
| `-o`, `--output-dir`| `-o` | 來源同目錄 | 輸出目錄 |

#### 🔹 (3) `burn`：影音硬字幕燒錄壓制 (Hardsub)
以 GPU (NVENC) 或 CPU 將 ASS/SRT 字幕永久燒錄進 MP4 影片中：
```bash
python3 src/cli/main.py burn <影片路徑> <字幕路徑> [OPTIONS]
```
| 參數名稱 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `video_path` | (必填) | - | 來源影片路徑 (.mp4, .mov, .mkv 等) |
| `subtitle_path`| (必填) | - | 字幕路徑 (.srt, .vtt, .json) |
| `--css` | - | `None` | **標準 CSS 樣式字串** (支援 opacity, stroke, shadow, padding 等) |
| `--css-file` | - | `None` | 外掛 `.css` 樣式檔案路徑 |
| `--font` | - | `Noto Sans CJK TC` | 字型名稱 (支援所有已安裝開源字型) |
| `-s`, `--size` | `-s` | `32` | 字級大小 (像素) |
| `--color` | - | `#FFFFFF` | 字體顏色 (Hex) |
| `--opacity` | - | `1.0` | **字體整體不透明度** (`0.0 ~ 1.0`) |
| `--outline` | - | `2.5` | 外擴描邊粗細 (像素，0 為無描邊) |
| `--outline-color`| - | `#000000` | 描邊顏色 (Hex) |
| `--shadow` | - | `1.2` | 陰影偏移量 (像素) |
| `-d`, `--direction`| `-d` | `horizontal` | 排版方向：`horizontal` (橫式) 或 `vertical` (直式) |
| `--valign` | - | `bottom` | 垂直對齊：`top` (靠頂), `middle` (居中), `bottom` (靠底) |
| `--halign` | - | `center` | 水平對齊：`left` (靠左), `center` (居中), `right` (靠右) |
| `--padding` | - | `None` | CSS 邊距簡寫 (如 `"50 40"` 或 `"50 40 60 40"`) |
| `--x`, `--y` | - | `None` | 精確絕對座標定位 (覆蓋九宮格排版) |
| `--cpu` | - | `False` | 強制使用 CPU libx264 (預設自動啟用 NVIDIA NVENC) |
| `-o`, `--output`| `-o` | `<影片名>.hardsub.mp4` | 輸出影片路徑 |

#### 🔹 (4) `proofread`：地端 LLM 逐字稿校對
調用本地 Qwen2.5-3B 模型全速修正語音辨識的同音異字：
```bash
python3 src/cli/main.py proofread <字幕檔.srt/.json> [OPTIONS]
```
| 參數名稱 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `input_file` | (必填) | - | 來源字幕檔案 (.srt, .json 或影音檔) |
| `-b`, `--batch-size` | `-b` | `8` | 每次批次送入 LLM 校對的字幕句數 |
| `--gpu-layers` | - | `-1` | GPU 卸載層數 (`-1` 為全層放入 VRAM 加速) |
| `-o`, `--output`| `-o` | `<檔名>.proofread.srt` | 輸出校對後字幕檔路徑 |

#### 🔹 (5) `fonts`：字型庫安裝與管理
```bash
# 查看所有可用、已安裝與本機 Windows 字型清單
python3 src/cli/main.py fonts list

# 一鍵安裝開源繁中字幕字型包 (openhuninn, lxgw-wenkai, iansui, win-msjhbd)
python3 src/cli/main.py fonts install openhuninn

# 從 URL 或本機 .ttf/.otf 安裝字型
python3 src/cli/main.py fonts install https://example.com/CustomFont.ttf
python3 src/cli/main.py fonts install /path/to/MyFont.otf

# 移除自訂字型
python3 src/cli/main.py fonts remove jf-openhuninn-2.0.ttf
```

#### 🔹 (6) 其它單元模組工具
- **抽音**：`python3 src/cli/main.py extract <影片> -o <音訊.wav> --sr 16000`
- **獨立辨識**：`python3 src/cli/main.py transcribe <音訊.wav> -m large-v3-turbo -d cuda`
- **獨立斷句**：`python3 src/cli/main.py segment <raw.json> -c 16 -p 0.45`
- **格式轉換**：`python3 src/cli/main.py export <track.json> -f srt -o <out.srt>`

---

## 🤖 自動化批次處理與 Agent 整合指南

AutoSubtitle AI 的所有後端核心與 CLI 均具備純函式化、非互動式的無頭（Headless）設計，非常適合與 **Shell 腳本、排程任務、或是 AI Agent (如 Antigravity, LangChain, n8n, Dify)** 串接自動化。

### 1. 批次處理腳本 (Batch Processing Script)
將以下腳本儲存為 `batch_process.sh`，即可一鍵處理資料夾內所有影片並輸出含自訂品牌的壓制短影音：

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
  
  echo "🎬 正在自動化處理: $filename ..."
  
  if [ -f "$lyrics" ]; then
    # 有歌詞原稿：走 Luna 雙軌對齊管線
    python3 src/cli/main.py luna "$video" "$lyrics" -o "$OUTPUT_DIR/$stem" --llm auto
    sub_file="$OUTPUT_DIR/$stem/lyrics.srt"
  else
    # 無稿口播影片：走全自動辨識 + 智慧斷句流水線
    python3 src/cli/main.py pipeline "$video" -m large-v3-turbo -d cuda -o "$OUTPUT_DIR/$stem"
    # 地端 LLM 同音錯字校對
    python3 src/cli/main.py proofread "$OUTPUT_DIR/$stem/$stem.srt" -o "$OUTPUT_DIR/$stem/$stem.proofread.srt"
    sub_file="$OUTPUT_DIR/$stem/$stem.proofread.srt"
  fi
  
  # 套用統一 CSS 樣式與透明度，以 NVENC GPU 燒錄壓制
  python3 src/cli/main.py burn "$video" "$sub_file" \
    --css "font-size: 34px; color: #FFD700; opacity: 0.9; -webkit-text-stroke: 2.5px #000; text-shadow: 2px 2px #000;" \
    -o "$OUTPUT_DIR/${stem}_final.mp4"
    
  echo "✔ $stem 處理並壓制完成！"
done
```

### 2. Python 程式化 SDK 調用
在自有 Python 程式或自動化工作流中直接調用核心模組：

```python
from pathlib import Path
from src.core.luna_pipeline import run_luna_pipeline
from src.core.video_burner import burn_subtitles_to_video
from src.schemas.subtitle import SubtitleStyle

# 1. 執行雙軌對齊
track = run_luna_pipeline(
    audio_path="inputclip/test_video.mp4",
    lyrics_source="inputclip/audio-org.txt",
    output_dir="output_run",
    llm_provider="auto"
)

# 2. 宣告樣式 (支援標準 CSS 字串)
style = SubtitleStyle.from_css(
    "font-size: 36px; color: #FFFFFF; opacity: 0.85; -webkit-text-stroke: 3px #000;"
)

# 3. 壓制燒錄出片
out_mp4 = burn_subtitles_to_video(
    video_path="inputclip/test_video.mp4",
    subtitles_source="output_run/lyrics.srt",
    output_path="output_run/burned.mp4",
    style=style,
    use_gpu=True
)
print("輸出完成:", out_mp4)
```

### 3. REST API Webhook 自動化 (FastAPI)
啟動 `serve` 服務後，外部系統可透過 HTTP REST 呼叫進行無人值守排程：
- 完整的 Swagger 互動式文件：造訪 `http://localhost:8000/docs`
- 常用 API 端點：
  - `POST /api/ai/transcribe`：無稿辨識（接收媒體路徑與模型參數）
  - `POST /api/ai/align`：Luna 歌詞雙軌對齊（接收媒體與歌詞文字）
  - `POST /api/style/parse-css`：CSS 樣式雙向解析
  - `POST /api/burn`：背景壓制燒錄硬字幕

### 4. 🧠 Antigravity Workspace Skill 整合
本專案已在倉庫內建標準 Antigravity Agent Skill：
- 路徑：[`.agents/skills/auto-subtitle/SKILL.md`](file:///D:/projects/auto-subtitle/.agents/skills/auto-subtitle/SKILL.md)（與 `skills/auto-subtitle/SKILL.md`）
- **功能**：任何使用 Antigravity / Gemini 的 AI 代理人皆可自動加載此技能，理解專案架構並自主執行音訊抽離、雙軌對齊、樣式調校與硬字幕燒錄作業。

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
├── .agents/skills/auto-subtitle/ # Antigravity 專用 Agent Skill 定義檔
│   └── SKILL.md
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
