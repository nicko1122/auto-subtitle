import sys
import json
import time
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.core.env_utils import preload_cuda_libs, release_gpu_memory
preload_cuda_libs()

from llama_cpp import Llama

# 測試用標準影音辨識語料（涵蓋同音錯字、口語誤聽、成語/專有名詞、歌詞常見錯別字）
# 每一題都有原始 Whisper 辨識錯字，以及標準答案
TEST_CASES = [
    {
        "id": 1,
        "input": "牆上的時鐘它，滴答滴答。你和我卡在開發兩端晃啊晃。",
        "ground_truth": "牆上的時鐘它，滴答滴答。你和我卡在沙發兩端晃啊晃。",
        "targets": ["沙發"]
    },
    {
        "id": 2,
        "input": "像是隔著開平洋，想不想啊。我想出破這死計的感覺。",
        "ground_truth": "像是隔著太平洋，想不想啊。我想戳破這死寂的感覺。",
        "targets": ["太平洋", "戳破", "死寂"]
    },
    {
        "id": 3,
        "input": "你的腦袋裝什麼，我沒高冬。我的世界在下雪，愛也節冰。",
        "ground_truth": "你的腦袋裝什麼，我沒搞懂。我的世界在下雪，愛也結冰。",
        "targets": ["沒搞懂", "結冰"]
    },
    {
        "id": 4,
        "input": "大樓請，退路斷，命賢一線！那一秒對上眼，心照不宣。",
        "ground_truth": "大樓傾，退路斷，命懸一線！那一秒對上眼，心照不宣。",
        "targets": ["大樓傾", "命懸一線"]
    },
    {
        "id": 5,
        "input": "真的好冷，靈魂快要被凍節。寂寞在慢延，心裡在破碎片。",
        "ground_truth": "真的好冷，靈魂快要被凍結。寂寞在漫延，心裡在破碎。",
        "targets": ["凍結", "漫延", "破碎"]
    },
    {
        "id": 6,
        "input": "我們穿過水泥重林發著瘋。你扯衣角，我引著風。",
        "ground_truth": "我們穿過水泥叢林發著瘋。你扯衣角，我迎著風。",
        "targets": ["水泥叢林", "迎著風"]
    },
    {
        "id": 7,
        "input": "轉過街角，路燈還量著。去偷一秒，微弱的溫月。",
        "ground_truth": "轉過街角，路燈還亮著。去偷一秒，微弱的溫熱。",
        "targets": ["亮著", "溫熱"]
    },
    {
        "id": 8,
        "input": "在公私的會議室裡，大家的意件相左，各執幾見。",
        "ground_truth": "在公司的會議室裡，大家的意見相左，各執己見。",
        "targets": ["公司", "意見", "各執己見"]
    }
]

SYSTEM_PROMPT = """你是一位繁體中文字幕校對專家。
任務：修正由語音辨識（ASR）產生的字幕句子中的錯別字（特別是中文同音字與口語誤聽）。
規則：
1. 嚴格保持與輸入相同的 id，不要增減或合併 id。
2. 將同音錯字（如「開平洋」改為「太平洋」、「沒高冬」改為「沒搞懂」）修復為上下文通順的繁體中文用字。
3. 輸出純 JSON 格式，格式範例：
{"results": [{"id": 1, "text": "校對後的完整句子"}]}
"""

def evaluate_model(model_path: str, model_name: str):
    p = Path(model_path)
    if not p.exists():
        print(f"[{model_name}] 檔案不存在: {model_path}")
        return None

    print(f"\n=======================================================")
    print(f"評測模型: {model_name} ({p.name})")
    print(f"檔案大小: {round(p.stat().st_size / (1024*1024), 1)} MB")
    print(f"=======================================================")

    t0 = time.time()
    try:
        llm = Llama(
            model_path=str(p),
            n_gpu_layers=-1, # GPU 全層加速
            n_ctx=2048,
            verbose=False
        )
    except Exception as e:
        print(f"模型載入失敗: {e}")
        return None
    load_time = round(time.time() - t0, 2)
    print(f"✔ GPU 載入耗時: {load_time}s")

    # 組裝批次輸入
    input_lines = [f"[{item['id']}] {item['input']}" for item in TEST_CASES]
    user_prompt = "請校對以下字幕片段，修正其中的錯別字：\n" + "\n".join(input_lines)

    t1 = time.time()
    try:
        # Gemma 與 Gemini Nano 原生 chat template 不支援 system role，需合併進 user prompt
        is_gemma_family = ("gemma" in model_path.lower() or "gemini" in model_path.lower())
        if is_gemma_family:
            combined_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
            messages = [{"role": "user", "content": combined_prompt}]
        else:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

        res = llm.create_chat_completion(
            messages=messages,
            response_format={"type": "json_object"} if "qwen" in model_path.lower() else None,
            temperature=0.1,
            max_tokens=2048
        )
        infer_time = round(time.time() - t1, 2)
        raw_output = res["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"推理失敗: {e}")
        llm.close()
        release_gpu_memory()
        return None

    # 解析 JSON (加入容錯提取 markdown 與正則匹配)
    parsed_results = {}
    clean_text = re.sub(r"^```(?:json)?\s*", "", raw_output.strip())
    clean_text = re.sub(r"\s*```$", "", clean_text).strip()

    try:
        data = json.loads(clean_text)
        items = data.get("results") or data.get("subtitles") or data
        if isinstance(items, list):
            for it in items:
                i_id = it.get("id") or it.get("index")
                i_txt = it.get("text") or it.get("corrected_text")
                if i_id and i_txt:
                    parsed_results[int(i_id)] = str(i_txt).strip()
    except Exception:
        # 備援正則提取
        regex_matches = re.findall(r'\{\s*"id"\s*:\s*(\d+)\s*,\s*"text"\s*:\s*"([^"]+)"\s*\}', clean_text)
        for i_id, i_txt in regex_matches:
            parsed_results[int(i_id)] = i_txt.strip()

    # 釋放 GPU 顯存
    del llm
    release_gpu_memory()

    # 計算各題目評測分數
    total_targets = 0
    hit_targets = 0
    full_sentence_matches = 0
    details = []

    for item in TEST_CASES:
        item_id = item["id"]
        corrected = parsed_results.get(item_id, "")
        targets = item["targets"]
        total_targets += len(targets)

        target_hits = [t for t in targets if t in corrected]
        hit_targets += len(target_hits)

        is_full_match = (corrected == item["ground_truth"])
        if is_full_match:
            full_sentence_matches += 1

        details.append({
            "id": item_id,
            "raw_in": item["input"],
            "corrected": corrected,
            "truth": item["ground_truth"],
            "targets": targets,
            "hit_targets": target_hits,
            "all_hit": len(target_hits) == len(targets)
        })

    target_acc = round((hit_targets / max(1, total_targets)) * 100, 1)
    sentence_acc = round((full_sentence_matches / len(TEST_CASES)) * 100, 1)
    tokens_sec = round(res["usage"]["completion_tokens"] / max(0.01, infer_time), 1)

    print(f"📊 推理耗時: {infer_time}s ({tokens_sec} tokens/s)")
    print(f"🎯 關鍵錯字修復率 (Target Recall): {hit_targets}/{total_targets} ({target_acc}%)")
    print(f"🏆 全句完美修復率 (Exact Match): {full_sentence_matches}/{len(TEST_CASES)} ({sentence_acc}%)")

    # 列印對照樣本
    for d in details[:3]:
        status = "✔" if d["all_hit"] else "❌"
        print(f"  {status} [#{d['id']}] 輸入: {d['raw_in']}")
        print(f"     輸出: {d['corrected']}")
        print(f"     標準: {d['truth']}")

    return {
        "model_name": model_name,
        "load_time": load_time,
        "infer_time": infer_time,
        "tokens_sec": tokens_sec,
        "target_acc": target_acc,
        "sentence_acc": sentence_acc,
        "hit_targets": hit_targets,
        "total_targets": total_targets,
        "details": details
    }

if __name__ == "__main__":
    benchmark_models = [
        ("models/qwen2.5-3b-instruct-q4_k_m.gguf", "Qwen2.5-3B-Instruct (目前預設)"),
        ("models/gemma-2-2b-it-Q4_K_M.gguf", "Gemma-2-2B-IT (Google)"),
        ("models/Phi-3.5-mini-instruct-Q4_K_M.gguf", "Phi-3.5-Mini (Microsoft)"),
        ("models/Llama-3.2-3B-Instruct-Q4_K_M.gguf", "Llama-3.2-3B-Instruct (Meta)"),
        ("models/Gemini-Nano-Gemmafied.Q4_K_M.gguf", "Gemini-Nano (Google)")
    ]

    summary = []
    for path, name in benchmark_models:
        if Path(path).exists():
            res = evaluate_model(path, name)
            if res:
                summary.append(res)
        else:
            print(f"跳過未下載完成之模型: {name}")

    print("\n" + "="*70)
    print("                總評測對比排行榜 (Benchmark Summary)")
    print("="*70)
    print(f"{'模型名稱':<32} | {'錯字修復率':<10} | {'完美句子率':<10} | {'速度(T/s)':<10}")
    print("-" * 70)
    for s in summary:
        print(f"{s['model_name']:<32} | {s['target_acc']:>8}% | {s['sentence_acc']:>8}% | {s['tokens_sec']:>8}")
    print("="*70)
