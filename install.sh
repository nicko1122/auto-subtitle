#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# AutoSubtitle AI - One-click Setup & Model Download Script
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================================================"
echo "          AutoSubtitle AI - 一鍵環境安裝與地端模型下載"
echo "======================================================================"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &> /dev/null; then
    echo "找不到 $PYTHON，請指定 PYTHON=/path/to/python3.12"
    exit 1
fi
"$PYTHON" -c 'import sys; assert (3, 10) <= sys.version_info[:2] <= (3, 12), "目前 av<14 需要 Python 3.10–3.12；請指定 PYTHON=/path/to/python3.12"'

# 2. 檢查 FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "找不到 ffmpeg，請先安裝 FFmpeg。"
    exit 1
else
    echo "✔ 檢測到 FFmpeg: $(ffmpeg -version | head -n1)"
fi

# 3. 建立並啟用虛擬環境
if [ ! -d ".venv" ]; then
    echo "📦 正在建立 Python 虛擬環境 (.venv)..."
    "$PYTHON" -m venv .venv
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

# (B) 預載兩種後端的預設 Whisper 模型
echo "   [2/3] 預先快取原生與 Faster-Whisper 預設模型..."
python3 -c "
from faster_whisper import WhisperModel
from src.core.transcriber import DEFAULT_WHISPER_MODEL, load_native_whisper_model, unload_native_whisper_model
print('   正在快取原生 Whisper', DEFAULT_WHISPER_MODEL)
model = load_native_whisper_model(DEFAULT_WHISPER_MODEL, device='cpu')
unload_native_whisper_model(model)
del model
print('   正在快取 Faster-Whisper', DEFAULT_WHISPER_MODEL)
WhisperModel(DEFAULT_WHISPER_MODEL, device='cpu', compute_type='int8')
print('   ✔ 預設 Whisper 模型快取完成')
"

# (C) 預載開源繁中精選字型 (jf open 粉圓 2.0)
echo "   [3/3] 安裝預設繁體中文字幕字型 (jf open 粉圓 2.0)..."
python3 src/cli/main.py fonts install openhuninn

echo "======================================================================"
echo "🎉 安裝完成！"
echo ""
echo "🚀 啟動 Web 工作台："
echo "   source .venv/bin/activate"
echo "   python3 src/cli/main.py serve --host 127.0.0.1 --port 8000"
echo ""
echo "   本機存取: http://localhost:8000"
echo "======================================================================"
