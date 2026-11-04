# Auto Subtitle (自動上字幕服務)

一個基於本地 Whisper 語音辨識、自動音軌分離、智慧短句切分與 Timeline 時間軸標記的自動上字幕網站核心。

## 核心流程
1. **影片上傳** (Video Upload)
2. **音軌分離** (FFmpeg 提取 16kHz 單聲道 WAV)
3. **本地 Whisper 辨識** (faster-whisper 取得 word-level timestamps)
4. **智慧斷句與時間軸校準** (依標點、停頓、單行字數分塊)
5. **產生 Timeline 標記** (提供前端時間軸預填與編輯)

## 環境要求
- Ubuntu 24.04 (WSL2)
- Python 3.12+
- FFmpeg (已配置)
- NVIDIA GPU (選配，支援 CUDA 加速)
