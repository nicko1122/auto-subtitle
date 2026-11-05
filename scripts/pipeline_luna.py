import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import time
import hashlib
import re
import csv
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pypinyin import lazy_pinyin

# Preload CUDA libraries
from src.core.env_utils import preload_cuda_libs, release_gpu_memory
preload_cuda_libs()

import stable_whisper
from src.core.transcriber import transcribe_audio
from src.core.proofreader import SubtitleProofreader, _extract_json_payload
from src.core.exporter import to_srt, save_file
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment, WordItem

HALLUCINATION_PATTERNS = [
    r"作[詞词曲]",
    r"詞曲",
    r"曲名字幕",
    r"李宗盛",
    r"独播剧场",
    r"Television Series",
    r"字幕志愿者",
    r"^(請|请)?(點贊|点赞|關注|关注|訂閱|订阅)",
    r"^(謝謝|谢谢)觀?看",
    r"^[啊啦喔哦嗯哼]+$",
]


def compute_sha256(filepath: str) -> str:
    """計算檔案的 SHA-256 雜湊值"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def clean_cjk(text: str) -> str:
    """去除標點與空格，僅保留文字用於對齊計算"""
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text)


def is_hallucination_text(text: str) -> bool:
    cleaned = text.strip()
    return any(bool(re.search(pat, cleaned, re.IGNORECASE)) for pat in HALLUCINATION_PATTERNS)


def cut_audio_segment(input_wav: str, start_sec: float, end_sec: float, output_wav: str) -> bool:
    """使用 FFmpeg 裁切局部音訊供局部重新對齊 (Section 8)"""
    dur = max(0.1, end_sec - start_sec)
    cmd = [
        "ffmpeg", "-y", "-ss", f"{start_sec:.3f}", "-t", f"{dur:.3f}",
        "-i", input_wav, "-ac", "1", "-ar", "16000", output_wav
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return res.returncode == 0


def to_lrc(track: SubtitleTrack) -> str:
    """匯出標準 LRC 動態歌詞格式 [mm:ss.xx]歌詞"""
    lines = []
    for seg in track.segments:
        mm = int(seg.start // 60)
        ss = seg.start % 60
        text_line = seg.text.replace("\n", " ")
        lines.append(f"[{mm:02d}:{ss:05.2f}]{text_line}")
    return "\n".join(lines) + "\n"


class LocalQwenReasoner:
    """
    純本地離線 Qwen2.5 決策引擎 (可完全替代雲端 Luna API)
    支援 7B (高精度) 或 3B (極速)，自動管理顯存/記憶體
    """
    def __init__(self, model_name: str = "qwen2.5-3b-instruct-q4_k_m.gguf"):
        from llama_cpp import Llama
        models_dir = Path(__file__).resolve().parent.parent / "models"
        model_path = models_dir / model_name
        if not model_path.exists():
            model_path = models_dir / "qwen2.5-3b-instruct-q4_k_m.gguf"
        
        self.model_path = str(model_path)
        self.model_name = model_path.name
        print(f"  [Local LLM] 正在載入本地模型: {self.model_name}...")
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=8192,
            n_threads=8,
            verbose=False
        )

    def decide(self, sys_prompt: str, user_prompt: str) -> str:
        resp = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        return resp["choices"][0]["message"]["content"]

    def close(self):
        if hasattr(self, "llm"):
            del self.llm
        release_gpu_memory()


class CloudLunaReasoner:
    """
    雲端 GPT-6 Luna API 決策引擎 (供對照測試使用)
    """
    def __init__(self):
        self.proofreader = SubtitleProofreader()
        self.model_name = self.proofreader.model_name

    def decide(self, sys_prompt: str, user_prompt: str) -> str:
        return self.proofreader._call_llm_api(sys_prompt, user_prompt)

    def close(self):
        self.proofreader.close()


class LunaPipeline:
    """
    依照《Whisper＋GPT-6 Luna 歌詞字幕 Pipeline》規範設計之完整處理引擎。
    支援純本地離線 (Local Qwen2.5) 或雲端 (GPT-6 Luna) 決策。
    """
    def __init__(
        self,
        audio_path: str,
        lyrics_path: str,
        output_dir: str = "output_luna_pipeline",
        llm_provider: str = "local",
        local_model_name: str = "qwen2.5-3b-instruct-q4_k_m.gguf"
    ):
        self.audio_path = str(Path(audio_path).resolve())
        self.lyrics_path = str(Path(lyrics_path).resolve())
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.llm_provider = llm_provider
        self.local_model_name = local_model_name

        self.manifest: Dict[str, Any] = {}
        self.raw_asr: Dict[str, Any] = {}
        self.asr_clean_segments: List[Dict[str, Any]] = []
        self.stable_ts_segments: List[Dict[str, Any]] = []
        self.org_lines: List[str] = []
        self.cue_evidence: List[Dict[str, Any]] = []
        self.corrections: List[Dict[str, Any]] = []
        self.reviews: List[Dict[str, Any]] = []
        self.final_track: Optional[SubtitleTrack] = None
        self.start_perf_time = time.time()

    def step_1_prepare_and_manifest(self) -> Dict[str, Any]:
        """【第 3 節】準備輸入與執行紀錄 (雜湊、元資料、讀取原歌詞)"""
        print("\n=== [步驟 1] 準備輸入與雜湊建檔 ===")
        if not os.path.exists(self.audio_path):
            raise FileNotFoundError(f"找不到音訊檔: {self.audio_path}")
        if not os.path.exists(self.lyrics_path):
            raise FileNotFoundError(f"找不到歌詞檔: {self.lyrics_path}")

        raw_lyrics_text = Path(self.lyrics_path).read_text(encoding="utf-8")
        cleaned_lines = []
        for line in raw_lyrics_text.splitlines():
            l = re.sub(r"\[.*?\]|\(.*?\)", "", line).strip()
            if l:
                cleaned_lines.append(l)

        self.org_lines = cleaned_lines
        print(f"  ✔ 成功讀取原歌詞: 共 {len(self.org_lines)} 行有效歌詞")

        audio_hash = compute_sha256(self.audio_path)
        lyrics_hash = compute_sha256(self.lyrics_path)

        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", self.audio_path]
        dur_str = subprocess.check_output(cmd).decode().strip()
        self.audio_duration = float(dur_str)
        print(f"  ✔ 音訊時長: {self.audio_duration:.2f} 秒 (SHA-256: {audio_hash[:12]}...)")

        self.manifest = {
            "run_id": f"run_{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "audio_file": Path(self.audio_path).name,
            "audio_sha256": audio_hash,
            "audio_duration": self.audio_duration,
            "lyrics_file": Path(self.lyrics_path).name,
            "lyrics_sha256": lyrics_hash,
            "lyrics_lines_count": len(self.org_lines),
            "whisper_model": "large-v3-turbo",
            "alignment_tool": "stable-ts 2.19.1",
            "llm_provider": self.llm_provider,
            "llm_model": self.local_model_name if self.llm_provider == "local" else "gpt-6-luna",
            "reading_extension_sec": 0.16,
            "anomaly_threshold_sec": 0.3
        }
        return self.manifest

    def step_2_whisper_full_asr(self) -> List[Dict[str, Any]]:
        """【第 4 節】Whisper 全曲辨識 (初稿分段 + 逐詞時間戳)"""
        print("\n=== [步驟 2] Whisper large-v3-turbo 全曲辨識 ===")
        prompt = "繁體中文歌曲。風雪裡的默契。牆上的時鐘，沒有感覺，真的好冷。"
        
        self.raw_asr = transcribe_audio(
            audio_path=self.audio_path,
            model_size="large-v3-turbo",
            device="cuda",
            vad_filter=False,
            condition_on_previous_text=False,
            hallucination_silence_threshold=None,
            word_timestamps=True,
            initial_prompt=prompt
        )

        raw_segs = self.raw_asr.get("raw_segments", [])
        print(f"  ✔ Whisper 完成辨識，取得 {len(raw_segs)} 段原生語音片段")

        asr_raw_path = self.output_dir / "asr_raw.json"
        with open(asr_raw_path, "w", encoding="utf-8") as f:
            json.dump(self.raw_asr, f, ensure_ascii=False, indent=2)

        clean_segs = []
        for s in raw_segs:
            txt = s.get("text", "").strip()
            if is_hallucination_text(txt):
                print(f"    [濾除幻覺] [{s['start']:.2f}s - {s['end']:.2f}s] {txt}")
                continue
            words = s.get("words", [])
            if words:
                w0 = dict(words[0])
                w0_txt = clean_cjk(w0["word"])
                max_lead = 0.30 * max(1, len(w0_txt))
                if (w0["end"] - w0["start"]) > max_lead:
                    w0["start"] = round(w0["end"] - max_lead, 3)
                words = [w0] + [dict(w) for w in words[1:]]
            
            clean_segs.append({
                "id": s["id"],
                "start": words[0]["start"] if words else s["start"],
                "end": words[-1]["end"] if words else s["end"],
                "text": txt,
                "words": words
            })

        self.asr_clean_segments = clean_segs
        print(f"  ✔ 人聲有效片段: {len(self.asr_clean_segments)} 段")
        return self.asr_clean_segments

    def step_3_and_4_alignment_and_evidence(self) -> List[Dict[str, Any]]:
        """
        【第 5 & 6 & 8 節】
        - 執行 stable-ts 原歌詞強制對齊
        - 比對雙軌時間 (ASR vs stable-ts)
        - 針對異常句子執行局部切音重跑對齊 (Section 8)
        """
        print("\n=== [步驟 3 & 4] stable-ts 強制對齊、雙軌比對與局部重跑 ===")
        lyrics_text = "\n".join(self.org_lines)

        st_model = stable_whisper.load_faster_whisper("large-v3-turbo", device="cuda", compute_type="float32")
        align_res = st_model.align(
            self.audio_path,
            lyrics_text,
            language="zh",
            original_split=True,
            token_step=160,
            regroup=False
        )

        align_segs = []
        for idx, s in enumerate(align_res.segments, 1):
            w_list = []
            for w in getattr(s, "words", []):
                w_list.append({
                    "word": w.word,
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "prob": round(getattr(w, "probability", 1.0), 3)
                })
            align_segs.append({
                "id": idx,
                "start": round(s.start, 3),
                "end": round(s.end, 3),
                "text": s.text.strip(),
                "words": w_list
            })

        self.stable_ts_segments = align_segs
        print(f"  ✔ 全曲強制對齊完成: 取得 {len(self.stable_ts_segments)} 句歌詞時間軸")

        # 雙軌比對與異常標記
        evidence_list = []
        temp_dir = self.output_dir / "temp_slices"
        temp_dir.mkdir(parents=True, exist_ok=True)

        realign_count = 0
        for line_idx, org_line in enumerate(self.org_lines, 1):
            st_seg = self.stable_ts_segments[line_idx - 1] if line_idx <= len(self.stable_ts_segments) else None
            t_align_start = st_seg["start"] if st_seg else 0.0
            t_align_end = st_seg["end"] if st_seg else 0.0

            # 尋找時間重疊度最高或最接近的 Whisper ASR segment
            matched_asr = None
            best_overlap = -1.0
            for s in self.asr_clean_segments:
                overlap = max(0.0, min(s["end"], t_align_end) - max(s["start"], t_align_start))
                if overlap > best_overlap:
                    best_overlap = overlap
                    matched_asr = s

            # 若無直接重疊，則取距離最近的段落
            if not matched_asr or best_overlap == 0.0:
                closest_dist = float("inf")
                for s in self.asr_clean_segments:
                    dist = abs(s["start"] - t_align_start)
                    if dist < closest_dist:
                        closest_dist = dist
                        matched_asr = s

            t_asr_start = matched_asr["start"] if matched_asr else t_align_start
            t_asr_end = matched_asr["end"] if matched_asr else t_align_end
            asr_text = matched_asr["text"] if matched_asr else ""

            # 檢測異常指標
            diff_start = abs(t_asr_start - t_align_start)
            diff_end = abs(t_asr_end - t_align_end)
            dur = t_align_end - t_align_start
            anomalies = []
            if diff_start > 0.3:
                anomalies.append(f"start_diff_gt_0.3s({diff_start:.2f}s)")
            if diff_end > 0.3:
                anomalies.append(f"end_diff_gt_0.3s({diff_end:.2f}s)")
            if dur < 0.35:
                anomalies.append("duration_too_short")
            elif dur > 6.5:
                anomalies.append("duration_too_long")

            candidates = {
                "cand_stable_ts": {
                    "candidate_id": "cand_stable_ts",
                    "source": "stable-ts full alignment",
                    "start": round(t_align_start, 3),
                    "end": round(t_align_end, 3)
                },
                "cand_asr": {
                    "candidate_id": "cand_asr",
                    "source": "whisper large-v3-turbo",
                    "start": round(t_asr_start, 3),
                    "end": round(t_asr_end, 3),
                    "text": asr_text
                }
            }

            # 【第 8 節】若有異常，執行局部切音重新對齊
            if anomalies:
                slice_st = max(0.0, min(t_align_start, t_asr_start) - 1.2)
                slice_et = min(self.audio_duration, max(t_align_end, t_asr_end) + 1.2)
                slice_wav = str(temp_dir / f"slice_line_{line_idx:02d}.wav")

                if cut_audio_segment(self.audio_path, slice_st, slice_et, slice_wav):
                    try:
                        slice_res = st_model.align(
                            slice_wav,
                            org_line,
                            language="zh",
                            original_split=True,
                            token_step=220,
                            regroup=False
                        )
                        if slice_res.segments:
                            loc_seg = slice_res.segments[0]
                            # 裁音偏移量由腳本換算為原曲絕對時間 (Section 8)
                            abs_loc_st = round(loc_seg.start + slice_st, 3)
                            abs_loc_et = round(loc_seg.end + slice_st, 3)
                            candidates["cand_local_retry"] = {
                                "candidate_id": "cand_local_retry",
                                "source": "stable-ts local slice retry",
                                "start": abs_loc_st,
                                "end": abs_loc_et
                            }
                            realign_count += 1
                    except Exception as e:
                        pass
                    finally:
                        if os.path.exists(slice_wav):
                            os.remove(slice_wav)

            evidence_item = {
                "line_id": line_idx,
                "org_line": org_line,
                "candidates": candidates,
                "diff_start": round(diff_start, 3),
                "diff_end": round(diff_end, 3),
                "anomalies": anomalies,
                "needs_review": bool(anomalies)
            }
            evidence_list.append(evidence_item)

        del st_model
        release_gpu_memory()

        if temp_dir.exists():
            try:
                temp_dir.rmdir()
            except OSError:
                pass

        self.cue_evidence = evidence_list
        abnormal_count = sum(1 for e in self.cue_evidence if e["anomalies"])
        print(f"  ✔ 雙軌證據比對完成: 共 {len(self.cue_evidence)} 句，檢測到 {abnormal_count} 句需審核")
        print(f"  ✔ 局部切音重跑完成: 共對 {realign_count} 句完成局部重新精煉候選")
        return self.cue_evidence

    def step_5_and_6_luna_decision(self) -> List[SubtitleSegment]:
        """【第 7 & 9 節】呼叫決策大腦 (Local Qwen2.5 / Luna) 審核異常句子並選定最佳時間邊界"""
        print(f"\n=== [步驟 5 & 6] 呼叫決策大腦 ({self.llm_provider}) 執行審核與對齊 ===")
        
        reasoner = (
            LocalQwenReasoner(self.local_model_name)
            if self.llm_provider == "local"
            else CloudLunaReasoner()
        )

        anomaly_lines = [ev for ev in self.cue_evidence if ev.get("needs_review")]
        print(f"  待審核異常句子數量: {len(anomaly_lines)} 句 (其餘 {len(self.cue_evidence) - len(anomaly_lines)} 句無異常直接採納)")

        decisions_map: Dict[int, Dict[str, Any]] = {}
        if anomaly_lines:
            audit_payload = []
            for ev in anomaly_lines:
                idx = ev["line_id"] - 1
                prev_line = self.cue_evidence[idx - 1] if idx > 0 else None
                next_line = self.cue_evidence[idx + 1] if idx + 1 < len(self.cue_evidence) else None
                
                prev_bound = f"上一句 (L{prev_line['line_id']}) 結束約: {prev_line['candidates']['cand_stable_ts']['end']:.2f}s" if prev_line else "開頭"
                next_bound = f"下一句 (L{next_line['line_id']}) 開始約: {next_line['candidates']['cand_stable_ts']['start']:.2f}s" if next_line else "曲尾"

                audit_payload.append({
                    "line_id": ev["line_id"],
                    "text": ev["org_line"],
                    "context": f"{prev_bound} | {next_bound}",
                    "candidates": ev["candidates"],
                    "anomalies": ev["anomalies"]
                })

            sys_prompt = """你是一位專業的繁體中文音樂與影視字幕對齊專家。
任務：針對被標記有時間軸異常（例如辨識與強制對齊存在時間差或時長異常）的歌詞句子，根據所提供的候選時間戳與前後句時間邊界，為每個異常句子選擇最合適的開始 (start) 與結束 (end) 候選識別碼，並說明簡短理由。

規則：
1. 只能從該句提供的 candidates 中選擇候選邊界，嚴禁憑空編造秒數。
2. 保持時間軸單調遞增，不能早於上一句結束時間，不能晚於下一句開始時間。
3. 如果各候選差異小或原始對齊已合理，action 填 "keep"。
4. 若選擇特定候選，action 填 "choose_candidate"，並指定 start_candidate_id 與 end_candidate_id (例如 "cand_local_retry", "cand_stable_ts", "cand_asr")。
5. 必須以純 JSON 格式輸出：
{
  "decisions": [
    {
      "line_id": 14,
      "action": "choose_candidate",
      "start_candidate_id": "cand_local_retry",
      "end_candidate_id": "cand_stable_ts",
      "reason": "局部重跑補回開頭起音，且句尾與原對齊一致"
    }
  ]
}"""

            user_input = json.dumps(audit_payload, ensure_ascii=False, indent=2)

            t0 = time.time()
            print(f"  ⏳ 正在執行審核決策推理中...")
            raw_res = reasoner.decide(sys_prompt, user_input)
            print(f"  ✔ 推理決策完成，耗時 {time.time() - t0:.2f} 秒")

            try:
                data = _extract_json_payload(raw_res)
                items = data.get("decisions") or (data if isinstance(data, list) else [])
                for it in items:
                    lid = it.get("line_id")
                    if lid:
                        decisions_map[int(lid)] = it
            except Exception as e:
                print(f"  ⚠️ JSON 解析警告: {e}，將使用安全候選邊界")

        reasoner.close()

        # 彙整最終時間軸與記錄 corrections
        final_segments: List[SubtitleSegment] = []
        corrections: List[Dict[str, Any]] = []
        reviews: List[Dict[str, Any]] = []

        last_end = 0.0
        for ev in self.cue_evidence:
            lid = ev["line_id"]
            org_line = ev["org_line"]
            cands = ev["candidates"]
            def_st = cands["cand_stable_ts"]["start"]
            def_et = cands["cand_stable_ts"]["end"]

            chosen_st = def_st
            chosen_et = def_et
            st_source = "cand_stable_ts"
            et_source = "cand_stable_ts"
            decision_action = "keep"
            decision_reason = "雙軌時間吻合，自動採納 stable-ts"

            if lid in decisions_map:
                dec = decisions_map[lid]
                act = dec.get("action", "keep")
                decision_reason = dec.get("reason", "LLM審核決定")
                if act == "choose_candidate":
                    decision_action = "choose_candidate"
                    s_id = dec.get("start_candidate_id")
                    e_id = dec.get("end_candidate_id")
                    if s_id in cands:
                        chosen_st = cands[s_id]["start"]
                        st_source = s_id
                    if e_id in cands:
                        chosen_et = cands[e_id]["end"]
                        et_source = e_id

            # 確保單調遞增與邊界合法性
            if chosen_st < last_end:
                chosen_st = last_end
            if chosen_et <= chosen_st:
                chosen_et = min(self.audio_duration, chosen_st + max(1.2, def_et - def_st))
            if chosen_et > self.audio_duration:
                chosen_et = self.audio_duration

            # 記錄是否有變更
            is_modified = (abs(chosen_st - def_st) > 0.05 or abs(chosen_et - def_et) > 0.05)
            if is_modified or decision_action == "choose_candidate":
                corrections.append({
                    "line_id": lid,
                    "text": org_line,
                    "original_start": def_st,
                    "original_end": def_et,
                    "final_start": round(chosen_st, 3),
                    "final_end": round(chosen_et, 3),
                    "start_candidate_id": st_source,
                    "end_candidate_id": et_source,
                    "reason": decision_reason
                })

            status = "needs_review" if (ev["anomalies"] and not is_modified and decision_action == "keep") else "passed"
            reviews.append({
                "line_id": lid,
                "text": org_line,
                "start": round(chosen_st, 3),
                "end": round(chosen_et, 3),
                "anomalies": ";".join(ev["anomalies"]),
                "status": status,
                "reason": decision_reason
            })

            ev["selected_start"] = round(chosen_st, 3)
            ev["selected_end"] = round(chosen_et, 3)
            ev["selected_start_source"] = st_source
            ev["selected_end_source"] = et_source

            final_segments.append(
                SubtitleSegment(
                    id=lid,
                    start=round(chosen_st, 3),
                    end=round(chosen_et, 3),
                    text=org_line,
                    words=[]
                )
            )
            last_end = chosen_et

        self.corrections = corrections
        self.reviews = reviews
        print(f"  ✔ 決策審核完成: 共採納 {len(corrections)} 項邊界調整修正")
        return final_segments

    def step_7_display_rules_and_export(self, segments: List[SubtitleSegment]) -> SubtitleTrack:
        """【第 10 & 11 節】套用 +0.16s 閱讀延長規則，排版並輸出 7 項標準交付檔案"""
        print("\n=== [步驟 7] 套用字幕顯示規則 (+0.16s 延長) 與輸出 7 項檔案 ===")
        processed_segments: List[SubtitleSegment] = []

        for i, seg in enumerate(segments):
            st = seg.start
            et = seg.end

            # 文件第 10 節：每句結束延長 0.16 秒，且不超過下一句開始或音訊總長
            et_extended = et + 0.16
            if i + 1 < len(segments):
                next_st = segments[i + 1].start
                if et_extended > next_st:
                    et_extended = next_st
            if et_extended > self.audio_duration:
                et_extended = self.audio_duration

            text = seg.text
            if len(text) > 18:
                m = re.search(r"([，,；;])", text)
                if m and 4 <= m.start() <= len(text) - 4:
                    pos = m.end()
                    text = text[:pos] + "\n" + text[pos:].strip()

            processed_segments.append(
                SubtitleSegment(
                    id=seg.id,
                    start=round(st, 3),
                    end=round(et_extended, 3),
                    text=text,
                    words=[]
                )
            )

        self.final_track = SubtitleTrack(
            source_file=self.audio_path,
            duration=self.audio_duration,
            language="zh",
            segments=processed_segments
        )

        # 1. lyrics.srt
        srt_content = to_srt(self.final_track)
        save_file(srt_content, str(self.output_dir / "lyrics.srt"))

        # 2. lyrics.lrc
        lrc_content = to_lrc(self.final_track)
        save_file(lrc_content, str(self.output_dir / "lyrics.lrc"))

        # 3. cue_evidence.json
        with open(self.output_dir / "cue_evidence.json", "w", encoding="utf-8") as f:
            json.dump(self.cue_evidence, f, ensure_ascii=False, indent=2)

        # 4. corrections.json
        with open(self.output_dir / "corrections.json", "w", encoding="utf-8") as f:
            json.dump(self.corrections, f, ensure_ascii=False, indent=2)

        # 5. review.csv
        with open(self.output_dir / "review.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["line_id", "text", "start", "end", "anomalies", "status", "reason"])
            for r in self.reviews:
                writer.writerow([r["line_id"], r["text"], r["start"], r["end"], r["anomalies"], r["status"], r["reason"]])

        # 6. validation.json
        overlaps = 0
        exceeds = 0
        for idx_k, s in enumerate(processed_segments):
            if s.end > self.audio_duration:
                exceeds += 1
            if idx_k > 0 and s.start < processed_segments[idx_k - 1].end:
                overlaps += 1

        val_report = {
            "total_lyric_lines": len(self.org_lines),
            "output_subtitle_count": len(processed_segments),
            "lyrics_text_100_percent_match": (len(self.org_lines) == len(processed_segments)),
            "negative_timestamps": sum(1 for s in processed_segments if s.start < 0),
            "inverted_timestamps": sum(1 for s in processed_segments if s.start >= s.end),
            "overlaps": overlaps,
            "exceeds_audio_duration": exceeds,
            "validation_passed": (overlaps == 0 and exceeds == 0 and len(self.org_lines) == len(processed_segments))
        }
        with open(self.output_dir / "validation.json", "w", encoding="utf-8") as f:
            json.dump(val_report, f, ensure_ascii=False, indent=2)

        # 7. run_manifest.json
        self.manifest["execution_duration_sec"] = round(time.time() - self.start_perf_time, 2)
        with open(self.output_dir / "run_manifest.json", "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)

        print(f"  ✔ 成功產生 7 項標準交付成果於目錄: {self.output_dir}")
        for fname in ["lyrics.srt", "lyrics.lrc", "cue_evidence.json", "corrections.json", "review.csv", "validation.json", "run_manifest.json"]:
            print(f"    - {fname}")
        return self.final_track

    def step_8_benchmark_with_reference(self, reference_srt_path: str):
        """【第 12 節】以已確認的參考 SRT 進行無作弊獨立驗收比對"""
        print(f"\n=== [步驟 8] 獨立驗收基準比對 (對照 {Path(reference_srt_path).name}) ===")
        from src.core.exporter import parse_srt_content
        ref_text = Path(reference_srt_path).read_text(encoding="utf-8")
        ref_track = parse_srt_content(ref_text)
        ref_segs = ref_track.segments

        gen_segs = self.final_track.segments
        print(f"  參考句數: {len(ref_segs)} | 生成句數: {len(gen_segs)}")

        start_diffs = []
        end_diffs = []
        within_02 = 0
        within_03 = 0

        compare_count = min(len(ref_segs), len(gen_segs))
        for i in range(compare_count):
            r = ref_segs[i]
            g = gen_segs[i]
            d_st = abs(g.start - r.start)
            d_et = abs(g.end - r.end)
            start_diffs.append(d_st)
            end_diffs.append(d_et)
            if d_st <= 0.2 and d_et <= 0.2:
                within_02 += 1
            if d_st <= 0.3 and d_et <= 0.3:
                within_03 += 1

        import numpy as np
        mae_st = float(np.mean(start_diffs))
        median_st = float(np.median(start_diffs))
        max_st = float(np.max(start_diffs))

        mae_et = float(np.mean(end_diffs))
        median_et = float(np.median(end_diffs))
        max_et = float(np.max(end_diffs))

        print(f"\n  📊 開始時間誤差 (Start Time):")
        print(f"    - 平均絕對誤差 (MAE): {mae_st:.3f} 秒")
        print(f"    - 中位數誤差 (Median): {median_st:.3f} 秒")
        print(f"    - 最大誤差 (Max):     {max_st:.3f} 秒")
        print(f"\n  📊 結束時間誤差 (End Time):")
        print(f"    - 平均絕對誤差 (MAE): {mae_et:.3f} 秒")
        print(f"    - 中位數誤差 (Median): {median_et:.3f} 秒")
        print(f"    - 最大誤差 (Max):     {max_et:.3f} 秒")
        print(f"\n  🎯 誤差在 0.2 秒內比例: {within_02}/{compare_count} ({within_02/compare_count*100:.1f}%)")
        print(f"  🎯 誤差在 0.3 秒內比例: {within_03}/{compare_count} ({within_03/compare_count*100:.1f}%)")


def main():
    wav_file = "inputclip/audio.wav"
    org_file = "inputclip/audio-org.txt"
    ref_file = "inputclip/audio.srt"
    out_dir = "output_luna_pipeline"

    # 100% 純本地離線測試 (Local Qwen2.5 3B + Whisper + stable-ts)
    pipeline = LunaPipeline(
        audio_path=wav_file,
        lyrics_path=org_file,
        output_dir=out_dir,
        llm_provider="local",
        local_model_name="qwen2.5-3b-instruct-q4_k_m.gguf"
    )

    pipeline.step_1_prepare_and_manifest()
    pipeline.step_2_whisper_full_asr()
    pipeline.step_3_and_4_alignment_and_evidence()
    final_segs = pipeline.step_5_and_6_luna_decision()
    pipeline.step_7_display_rules_and_export(final_segs)
    pipeline.step_8_benchmark_with_reference(ref_file)


if __name__ == "__main__":
    main()
