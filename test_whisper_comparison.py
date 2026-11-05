import time
import json
from pathlib import Path
from src.core.transcriber import transcribe_audio
from src.core.env_utils import release_gpu_memory

audio_file = "inputclip/audio.wav"
if not Path(audio_file).exists():
    audio_file = "inputclip/test_video.mp4"

print(f"Testing on audio file: {audio_file}")

models_to_test = ["small", "large-v3-turbo"]
results = {}

for m in models_to_test:
    print(f"\n================ Running Whisper [{m}] ================")
    t0 = time.time()
    try:
        res = transcribe_audio(
            audio_path=audio_file,
            model_size=m,
            device="cuda",
            language="zh",
            word_timestamps=True,
            vad_filter=True
        )
        elapsed = time.time() - t0
        raw_segments = res["raw_segments"]
        all_words = res["all_words"]
        sample_texts = [s["text"] for s in raw_segments[:8]]
        
        results[m] = {
            "elapsed_s": round(elapsed, 2),
            "segments_count": len(raw_segments),
            "words_count": len(all_words),
            "sample_texts": sample_texts,
            "first_words": all_words[:10],
            "first_segments": raw_segments[:5]
        }
        print(f"[{m}] Finished in {elapsed:.2f}s, segments: {len(raw_segments)}, words: {len(all_words)}")
        for i, text in enumerate(sample_texts):
            print(f"  Seg {i+1}: {text}")
    except Exception as e:
        print(f"[{m}] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        release_gpu_memory()

with open("whisper_comparison_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nSaved comparison to whisper_comparison_result.json")
