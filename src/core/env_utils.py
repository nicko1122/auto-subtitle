import os
import sys
import gc
import ctypes
import logging

import torch

logger = logging.getLogger(__name__)

_cuda_preloaded = False


def preload_cuda_libs() -> None:
    """自動偵測並預載 pip 安裝的 nvidia cu12 函式庫 (如 cublas, cudnn)，避免動態連結找不到符號"""
    global _cuda_preloaded
    if _cuda_preloaded:
        return

    try:
        venv_base = sys.prefix
        site_packages = os.path.join(
            venv_base, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
        )
        nvidia_dir = os.path.join(site_packages, "nvidia")
        if os.path.isdir(nvidia_dir):
            for sub in sorted(os.listdir(nvidia_dir)):
                if sub == "cu13" or sub.startswith("cu13"):
                    continue  # CTranslate2 / faster-whisper specifically links against CUDA 12
                lib_dir = os.path.join(nvidia_dir, sub, "lib")
                if os.path.isdir(lib_dir):
                    curr_ld = os.environ.get("LD_LIBRARY_PATH", "")
                    if lib_dir not in curr_ld:
                        os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{curr_ld}" if curr_ld else lib_dir
                    for fname in sorted(os.listdir(lib_dir)):
                        if ".so" in fname:
                            fpath = os.path.join(lib_dir, fname)
                            try:
                                ctypes.CDLL(fpath, mode=ctypes.RTLD_GLOBAL)
                            except Exception:
                                pass
        _cuda_preloaded = True
    except Exception as e:
        logger.debug(f"預載 CUDA 函式庫略過: {e}")


def release_gpu_memory() -> None:
    """回收不再使用的物件與 PyTorch CUDA 快取，不初始化新的 CUDA context。"""
    gc.collect()
    try:
        torch.cuda.empty_cache()
    except RuntimeError as error:
        logger.warning(f"CUDA 快取回收失敗，請重啟工作台: {error}")
