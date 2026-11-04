import sys
import ctranslate2

print("Python version:", sys.version)
cuda_count = ctranslate2.get_cuda_device_count()
print("CTranslate2 CUDA devices:", cuda_count)
if cuda_count > 0:
    print("CUDA is supported and enabled!")
else:
    print("CTranslate2 currently detected 0 CUDA devices (runs in CPU int8 mode).")
