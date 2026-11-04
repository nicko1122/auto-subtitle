#!/usr/bin/env bash
set -e

# ==============================================================================
# AutoSubtitle AI - One-click Setup & Model Download Script
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================================================"
echo "          AutoSubtitle AI - 一鍵環境安裝與地端模型下載"
echo "======================================================================"

# 1. 檢查 Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ 找不到 python3，請先安裝 Python 3.10 或以上版本！"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✔ 檢測到 Python 版本: $PY_VER"

# 2. 檢查 FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  警告: 系統找不到 ffmpeg，請先安裝 ffmpeg (例如: sudo apt-get install -y ffmpeg)"
else
    echo "✔ 檢測到 FFmpeg: $(ffmpeg -version | head -n1)"
fi

# 3. 建立並啟用虛擬環境
if [ ! -d ".venv" ]; then
    echo "📦 正在建立 Python 虛擬環境 (.venv)..."
    python3 -m venv .venv
fi

echo "🔌 啟用虛擬環境..."
source .venv/bin/activate

# 4. 升級 pip 並安裝套件
echo "📦 正在安裝相依套件 (requirements.txt)..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. 下載地端模型
echo "----------------------------------------------------------------------"
echo "📥 正在下載與準備地端模型..."

# (A) 下載本地 Edge LLM 模型 (Qwen2.5-3B-Instruct GGUF)
echo "   [1/3] 下載 Qwen2.5-3B-Instruct-GGUF (供同音錯字校對使用)..."
python3 src/core/download_model.py

# (B) 預載 Faster-Whisper Small 模型
echo "   [2/3] 預先快取 Faster-Whisper (small) 語音辨識模型..."
python3 -c "
from faster_whisper import WhisperModel
print('   正在快取 faster-whisper small 模型...')
try:
    WhisperModel('small', device='cpu', compute_type='int8')
    print('   ✔ Faster-Whisper small 模型快取完成')
except Exception as e:
    print('   ⚠️ Faster-Whisper 預載提醒:', e)
"

# (C) 預載開源繁中精選字型 (jf open 粉圓 2.0)
echo "   [3/3] 安裝預設繁體中文字幕字型 (jf open 粉圓 2.0)..."
python3 src/cli/main.py fonts install openhuninn || true

echo "======================================================================"
echo "🎉 安裝完成！"
echo ""
echo "🚀 啟動 Web 工作台："
echo "   source .venv/bin/activate"
echo "   python3 src/cli/main.py serve --host 0.0.0.0 --port 8000"
echo ""
echo "   本機存取: http://localhost:8000"
echo "======================================================================"
