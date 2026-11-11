# AutoSubtitle AI (智慧影音字幕工作台)

<p align="center">
  <b>結合聲學斷點分析、原生 Whisper large-v3-turbo、GPT-6 Luna 雙軌歌詞對齊管線、地端/雲端 LLM 決策大腦、Web CSS 盒模型排版與 NVIDIA NVENC 硬字幕燒錄的一站式字幕系統。</b>
</p>

---

## 🌟 最新重大功能更新 (Latest Highlights)

### 1. 🌙 Whisper ＋ GPT-6 Luna 歌詞字幕對齊管線 (Luna Pipeline)
- **雙軌驗證架構 (Dual Verification)**：
  - **軌道 A**：原生 Whisper（預設 `large-v3-turbo`）＋ stable-ts 全曲辨識與逐詞時間提取。
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
- **1:1 Web-to-ASS 字型度量與排版保真**：
  - 自動讀取字型 `usWinAscent + usWinDescent` 計算 `em_ratio` 縮放倍率，並於壓制前自動修復損壞的 TrueType/OpenType 字型（補齊缺失表或異常字距），讓特定手寫/藝術字型與 Web CSS `font-size` 一致。
  - **多行字幕支援**：時間軸與編輯框支援 `<br>` / `<br/>` 標籤及 `Shift+Enter` 換行（單按 `Enter` 仍跳至下一段），同步轉換為 ASS `\N` 與多行 SRT/VTT。
  - **直排中英混排與避頭尾**：`vertical-rl` 直書自動偵測 ASCII / 英數區段套用真實 `hmtx`/`cmap` 字寬量測與 `\frz-90` 順時針旋轉、支援避頭尾推入法（Kinsoku Oikomi）折欄、水平安全邊距夾擠防溢出，且橫/直排切換時自動重置位置避免殘留偏移。
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
- **直書長字幕自動多欄換行與避頭尾**：根據畫面高度自動由右至左折行（符合 CSS `vertical-rl` 規範），套用中文避頭尾推入法與中英混排旋轉。
- **畫面直覺拖曳**：可直接在影片預覽區拖曳字幕位置，或使用 X / Y 滑桿平滑微調。

### 5. 🎧 純音訊字幕製作 & ⚡ NVIDIA NVENC 硬字幕壓制
- **純音訊模式（WAV / MP3 / M4A / FLAC / AAC / OGG）**：支援直接上傳或建立純音訊資產包，提供專屬音訊播放背景預覽、聲學斷點、Whisper/Luna 辨識對齊與匯出 `SRT` / `WebVTT` / `JSON`；純音訊模式不執行 MP4 燒錄與視訊放大。
- **NVIDIA NVENC GPU 硬字幕壓制**：支援以 NVIDIA NVENC 硬體加速將 ASS 樣式字幕無損音軌直接燒錄進 MP4 影片中。

### 6. ✨ AI 視訊超解析度放大 (Video Super-Resolution)
- **Compact 輕量視訊模型**：整合 `realesrgan-ncnn-vulkan`（`realesr-animevideov3`），兼具高速、低顯存與邊緣銳化保真度。
- **資產庫隨選放大與無痛繼承**：在資產庫可一鍵執行 2x / 4x 放大，自動衍生高畫質資產包，並同步繼承現有字幕與原稿（時間軸通用）；僅對視訊資產包開放（純音訊略過）。
- **執行預警、取消與清理**：開始前自動試算總影格數與預估耗時並顯示風險提醒；支援任務中途停止與自動清理暫存／未完成目錄。
- **GPU 任務鎖排程保護**：嚴格納入 `ModelTaskLock`，避免與 Whisper / LLM 並行造成顯存溢出。

---

## 🛠️ 環境需求

- **作業系統**：Linux / Ubuntu / Windows 11 + WSL2（附 `run_web.bat` Windows 一鍵啟動器）
- **Python**：3.10–3.12（目前 `av<14` 的相容範圍）
- **系統相依**：`ffmpeg`, `ffprobe`, `fontconfig`
- **GPU (可選但推薦)**：支援 CUDA 之 NVIDIA 顯卡（如 GTX 1070 Ti、RTX 3060 或更高等級）
  - **Pascal 架構（GTX 1070 Ti / `sm_61`）注意事項**：需安裝 NVIDIA 驅動 **550+** 與 PyTorch **cu126**（`torch==2.8.0+cu126`）；避免安裝已移除 `sm_61` 支援的 CUDA 13.x 套件。`transcriber.py` 內建 1ms CUDA 核心預檢，若不支援會自動安全降級至 CPU 或報錯提示。

---

## 🚀 快速安裝 (含地端模型一鍵下載)

執行專案內建的一鍵安裝腳本，會自動建立虛擬環境、安裝相依庫，並下載地端 Qwen2.5 GGUF 與固定的原生 Whisper large-v3-turbo 模型：

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

單一 API 服務行程一次執行一個辨識、對齊、校對或燒錄任務；忙碌時回覆 HTTP 409 與 `Retry-After`，可在目前任務完成後重試。此鎖不涵蓋另外啟動的 CLI 或多個服務行程。

LLM 回覆會驗證編號與文字型別；失敗、漏答或重複編號保留該段原文，API 的 `proofread_warning`／`proofread_report` 回報未完成項目。有詞時間審核的失敗記錄於執行 manifest 與 `decision_batches.json`。

每次 Web 任務使用獨立輸出目錄／檔名；CLI `luna` 預設建立獨立資料夾，明確指定 `-o` 時沿用該目錄。除七項標準交付檔，另保留 `corrections.json` 與 `validation.json` 診斷檔。

### ⚙️ 設定檔 (.env，可選)
若欲啟用雲端 LLM API（支援 Gemini、OpenAI 相容端點、Anthropic，且系統支援熱重載無需重啟服務）：
```bash
cp .env.example .env
```
在 `.env` 中設定（預設 `LLM_PROVIDER=auto`，依序偵測可用的 API Key）：
```env
LLM_PROVIDER=auto

# Google Gemini (推薦)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# OpenAI / 相容端點 (DeepSeek, OpenRouter, Ollama 等)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
```

---

## 💻 使用方式

### 本機資產包

每個 `uploads/訪談/` 資料夾管理一支影片或純音訊檔（支援 `MP4/MKV/MOV/AVI/WEBM` 及 `WAV/MP3/M4A/FLAC/AAC/OGG`），以及選填的 `訪談.txt` 原詞與 `訪談.srt` 工作字幕。可匯入整個資料夾，或一起選取媒體、原詞和字幕建立資產包；直接在 `uploads/` 放入整理好的資料夾後，重新整理也能讀取。

開啟資產包會同時載入三者。編輯文字、時間軸或原詞後自動儲存，也可按頂端「儲存字幕」或 Ctrl+S；SRT 不存在時會建立，已存在時更新同一份檔案。純音訊資產包會於預覽區自動切換為音訊播放介面，產出完字幕後可直接匯出 `SRT` / `WebVTT` / `JSON`（隱藏燒錄與 AI 放大操作）。切換資產包前會先完成儲存，儲存失敗則保留目前工作區。包內不建立編輯紀錄 JSON。

AI 結果套用前會核對工作區與內容，過期回覆不會覆寫新編輯。全文編輯以 `[#序號]` 保留每段的多行文字及空字幕；字幕框內支援 `<br>` / `<br/>` 或 `Shift+Enter` 換行，貼上每行一段的純文字時，段數須與時間軸一致。無效的字幕匯入會被拒絕，字型經暫存驗證成功後才替換。

頂端「儲存字幕」旁提供 `🗑️ 刪除資產` 按鈕（亦可於資產庫管理頁面操作），刪除前會先釋放 `<video>`/`<audio>` 檔案鎖定並清除 Windows NTFS 唯讀屬性後移除整包；亦可重新命名或相對於 `uploads/` 移動。重複匯入同名包會建立另一個資料夾，不覆蓋既有包。未來多語字幕可沿用 `訪談_EN.srt` 命名，目前優先編輯與媒體同名的 SRT。

### 1. 啟動 Web Studio 視覺化工作台

**方法 A：Windows 一鍵獨立背景啟動（推薦）**
雙擊專案根目錄的 [`run_web.bat`](run_web.bat)，將以獨立背景程序透過 WSL2 啟動服務（關閉命令提示字元視窗亦不中斷）。

**方法 B：Linux / WSL2 終端手動啟動**
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

所有辨識與對齊入口固定使用**原生 Whisper `large-v3-turbo`**：有詞、無詞、鎖定時間軸填字、CLI 與 API 均採同一載入器。介面不提供模型選單，CLI 不再接受 `--model`／`-m`／`--compute-type`，API 不再提供 `model` 欄位。CUDA 無法使用時只切換到 CPU，模型與後端維持相同。健康檢查與辨識紀錄會回報固定模型及後端。

固定模型由 `WHISPER_MODEL` 定義；安裝腳本只預載這個原生模型。Faster-Whisper 套件只用於 Silero VAD 聲學斷點分析，不再執行語音辨識。舊 `scripts/pipeline_luna.py` 現在轉呼叫正式 `luna` CLI，需提供影音與 TXT 路徑；重複實驗流程 `scripts/test_pipeline_inputclip.py` 已移除。關鍵字命中的疑似幻覺會保留並標記待複核。

中文原詞先經繁簡正規化與整串拼音比對，映射回 Whisper 逐詞時間；詞內字元共用完整詞時間窗。映射有效時作為主時間，缺少有效映射才保留強制對齊候選並標記待確認。LLM 每批審核最多 4 句，`decision_batches.json` 保存證據、回覆及漏答編號；未提供的句號或候選不會套用。原稿文字與 0.16 秒閱讀延長規則保留。

取消介面的「AI 決策與錯字校對」、API 傳入 `auto_proofread=false`，或有詞 CLI 使用 `--no-audit`，即可保留 Whisper 映射與待複核標記，不載入 LLM 或套用其時間建議。

| 參數名稱 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `media_path` | (必填) | - | 來源影音檔案路徑 (MP4, MKV, WAV 等) |
| `script_path` | (必填) | - | 原歌詞或字幕文字檔案路徑 (.txt) |
| `--llm` | - | `local` | 決策大腦模式：`local` (地端 Qwen GGUF) 或 `api` (雲端 OpenAI 相容) |
| `-o`, `--output-dir` | `-o` | 來源檔同目錄中的獨立資料夾 | 輸出交付產物之目錄 |
| `-d`, `--device` | `-d` | `auto` | `auto`、`cuda` 或 `cpu` |
| `--prompt` | — | `繁體中文` | 辨識引導詞 |
| `--audit` / `--no-audit` | — | `--audit` | 是否執行 LLM 時間候選審核 |

#### 🔹 (2) `pipeline`：無稿全自動上字幕流水線
針對演講、訪談或 Podcast，一鍵完成抽音、Whisper 辨識、智慧斷句並匯出字幕：
```bash
python3 src/cli/main.py pipeline <媒體檔案> [OPTIONS]
```
| 參數名稱 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `media_path` | (必填) | - | 來源影音檔案路徑 |
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

#### 🔹 (4) `upscale`：AI 視訊超解析度放大 (Super-Resolution)
使用 Real-ESRGAN Compact 輕量視訊模型將影片超解析放大 (2x / 4x)：
```bash
# 放大 2x (使用 Compact 輕量視訊模型，預設)
python3 src/cli/main.py upscale <來源影片.mp4> --scale 2

# 指定輸出路徑與動漫特化模型放大 4x
python3 src/cli/main.py upscale anime.mp4 -o anime_4k.mp4 --scale 4 --model realesrgan-x4plus-anime
```
| 參數名稱 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `video_path` | (必填) | - | 來源影片檔案路徑 (MP4, MOV, MKV 等) |
| `-s`, `--scale` | `-s` | `2` | 放大倍率 (`2` 或 `4`) |
| `-m`, `--model` | `-m` | `realesr-animevideov3` | 模型 (`realesr-animevideov3`, `realesrgan-x4plus-anime`, `realesrgan-x4plus`) |
| `--no-gpu` | - | `False` | 強制停用 NVENC 硬體加速編碼 |
| `-o`, `--output`| `-o` | `<影片名>_<scale>x.mp4` | 輸出高解析度影片路徑 |

#### 🔹 (5) `proofread`：地端 LLM 逐字稿校對
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

#### 🔹 (6) `fonts`：字型庫安裝與管理
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

#### 🔹 (7) 其它單元模組工具
- **抽音**：`python3 src/cli/main.py extract <影片> -o <音訊.wav> --sr 16000`
- **獨立辨識**：`python3 src/cli/main.py transcribe <音訊.wav> -d cuda`
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
    python3 src/cli/main.py luna "$video" "$lyrics" -o "$OUTPUT_DIR/$stem" --llm local
    sub_file="$OUTPUT_DIR/$stem/lyrics.srt"
  else
    # 無稿口播影片：走全自動辨識 + 智慧斷句流水線
    python3 src/cli/main.py pipeline "$video" -d cuda -o "$OUTPUT_DIR/$stem"
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
網頁預設使用「歌詞參考」：依 Whisper 辨識順序反覆引用原詞，副歌不必逐次寫出；未能對上原詞的聲音辨識文字會保留並標記待複核。「完整逐句稿」則依原稿順序，每行輸出一次。

CLI、Python 與 API 為保留既有行為，預設 `script_mode="transcript"`；歌詞參考請指定 `reference`（CLI：`--script-mode reference`）。參考模式的 `lyric_occurrences.json` 記錄每次引用來源及逐詞時間，`validation.json` 檢查辨識內容是否完整覆蓋；這不代表聽寫文字已人工校對。

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
    llm_provider="local"
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
  - `POST /api/ai/transcribe-segments`：分段語音辨識
  - `POST /api/ai/align`：Luna 歌詞雙軌對齊（接收媒體與歌詞文字）
  - `POST /api/ai/proofread`：LLM 字幕校對
  - `POST /api/audio/breakpoints` / `POST /api/audio/snap-split`：聲學斷點與能量波谷吸附切分
  - `POST /api/style/parse-css`：CSS 樣式雙向解析
  - `POST /api/burn`：背景壓制燒錄硬字幕（視訊限定）
  - `DELETE /api/packages` / `DELETE /api/assets/{filename}`：刪除資產包或單一資產
  - `POST /api/upscale/estimate` / `POST /api/upscale/start` / `POST /api/upscale/task/{task_id}/cancel`：AI 超解析度試算、執行與取消

### 4. 🧠 Antigravity Workspace Skill 整合
本專案已在倉庫內建標準 Antigravity Agent Skill：
- 路徑：[`.agents/skills/auto-subtitle/SKILL.md`](file:///D:/projects/auto-subtitle/.agents/skills/auto-subtitle/SKILL.md)（與 `skills/auto-subtitle/SKILL.md`）
- **功能**：任何使用 Antigravity / Gemini 的 AI 代理人皆可自動加載此技能，理解專案架構並自主執行音訊抽離、雙軌對齊、樣式調校與硬字幕燒錄作業。

---

## 🧪 執行單元測試

專案包含 Python 後端（聲學斷點、DTW 對齊、CSS 解析、Web-to-ASS 度量/中英直排與破損字型修復、純音訊流程、AI 放大等）與 Node.js 前端完整性測試集：

```bash
source .venv/bin/activate
.venv/bin/pytest
node tests/editor_integrity.cjs
node tests/frontend_security.cjs
node tests/package_workflow.cjs
```

---

## 📂 專案結構

```text
auto-subtitle/
├── .agents/skills/auto-subtitle/ # Antigravity 專用 Agent Skill 定義檔
│   └── SKILL.md
├── src/
│   ├── api/                      # FastAPI 後端服務
│   │   ├── asset_packages.py     # 本機資產包管理與清理
│   │   ├── model_tasks.py        # GPU 模型任務互斥鎖 (ModelTaskLock)
│   │   └── server.py             # API 路由與靜態檔案服務
│   ├── cli/                      # Typer CLI 命令列介面
│   ├── core/                     # 核心邏輯
│   │   ├── acoustic_analyzer.py  # 聲學斷點分析、能量波谷吸附、受控 Whisper
│   │   ├── aligner.py            # Needleman-Wunsch + Sakoe-Chiba DTW 強制對齊
│   │   ├── audio_extractor.py    # FFmpeg 抽音
│   │   ├── css_parser.py         # CSS 解析 (支援 opacity, paint-order, stroke)
│   │   ├── env_utils.py          # .env 與環境變數熱重載工具
│   │   ├── exporter.py           # SRT / VTT / JSON / ASS (含 em_ratio、旋轉、避頭尾)
│   │   ├── font_manager.py       # 字型安裝、管理與破損字型自動修復
│   │   ├── luna_pipeline.py      # Whisper ＋ Luna 雙軌驗證管線核心
│   │   ├── lyric_reference.py    # 歌詞參考載入與切分工具
│   │   ├── proofreader.py        # llama-cpp-python Qwen2.5 與雲端 API 校對引擎
│   │   ├── segmenter.py          # 字幕斷句與分段工具
│   │   ├── transcriber.py        # 原生 Whisper large-v3-turbo 辨識與 CUDA 預檢
│   │   ├── video_burner.py       # NVENC / libx264 影音壓制燒錄
│   │   └── video_upscaler.py     # Real-ESRGAN AI 視訊超解析度放大
│   ├── schemas/                  # Pydantic 資料模型 (SubtitleTrack, SubtitleStyle 等)
│   └── web/                      # 前端工作台 (Tailwind CSS, Vanilla JS, HTML 模板)
│       ├── static/app.js         # 前端應用邏輯 (含雙向 CSS、純音訊/多行編輯、Modal)
│       └── templates/index.html  # 4-Tab 整合式工作台 UI
├── scripts/                      # 輔助與管線腳本
├── install.sh                    # 一鍵環境安裝與地端模型下載腳本
├── run_web.bat                   # Windows 一鍵獨立背景啟動腳本 (透過 WSL2)
├── requirements.txt              # Python 相依清單
└── tests/                        # pytest 與 Node.js (.cjs) 整合測試集
```

---

## 📄 License
MIT License
