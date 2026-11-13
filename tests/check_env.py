import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from src.core.css_renderer import detect_headless_browser

print("Python version:", sys.version)
print("PyTorch:", torch.__version__, "| CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA device:", torch.cuda.get_device_name(0))
print("FFmpeg:", shutil.which("ffmpeg") or "NOT FOUND")
print("CSS Headless Browser:", detect_headless_browser() or "NOT FOUND")
