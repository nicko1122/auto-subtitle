import os
import sys
import gc
import ctypes
import logging

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
    """主動觸發 Python 垃圾回收以釋放 CTranslate2 / llama.cpp 佔用的顯存 (VRAM)"""
    gc.collect()
