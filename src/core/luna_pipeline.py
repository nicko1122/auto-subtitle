import os
import sys
import json
import time
import hashlib
import re
import csv
import subprocess
import uuid
import tempfile
import difflib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from pypinyin import lazy_pinyin
from opencc import OpenCC

from .env_utils import preload_cuda_libs, release_gpu_memory
preload_cuda_libs()

import stable_whisper
from .transcriber import DEFAULT_WHISPER_MODEL, transcribe_native_audio, load_native_whisper_model, unload_native_whisper_model
from .proofreader import SubtitleProofreader, _extract_json_payload
from .lyric_reference import build_lyric_occurrences
from .exporter import to_srt, to_vtt, to_ass, save_file, parse_srt_content
from ..schemas.subtitle import SubtitleTrack, SubtitleSegment, WordItem

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


def compute_sha256_file(filepath: str) -> str:
    """計算檔案的 SHA-256 雜湊值"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def compute_sha256_text(text: str) -> str:
    """計算字串文字的 SHA-256 雜湊值"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_cjk(text: str) -> str:
    """去除標點與空格，僅保留文字用於對齊計算"""
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text)


def map_lyrics_to_asr_words(lines, segments):
    """原版中文／拼音配對；每個字符沿用所屬 ASR 詞的完整時間窗。"""
    converter = OpenCC("t2s")
    def normalize(text):
        return [char for char in converter.convert(text) if "\u4e00" <= char <= "\u9fff"]

    reference, owners, spoken, words = [], [], [], []
    lengths = []
    for index, line in enumerate(lines):
        chars = normalize(line)
        lengths.append(len(chars))
        reference.extend(chars)
        owners.extend([index] * len(chars))
    for segment in segments:
        for word in segment.get("words", []):
            chars = normalize(word["word"])
            spoken.extend(chars)
            words.extend([word] * len(chars))
    ref_pinyin, spoken_pinyin = lazy_pinyin("".join(reference)), lazy_pinyin("".join(spoken))
    n, m = len(reference), len(spoken)
    previous = [j * .8 for j in range(m + 1)]
    back = [bytearray(m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        back[i][0] = 1
    for j in range(1, m + 1):
        back[0][j] = 2

    def cost(i, j):
        if reference[i] == spoken[j]:
            return 0.0
        if ref_pinyin[i] == spoken_pinyin[j]:
            return .2
        return .65 if difflib.SequenceMatcher(None, ref_pinyin[i], spoken_pinyin[j]).ratio() >= .65 else 1.15

    for i in range(1, n + 1):
        current = [i * .8] + [0.0] * m
        for j in range(1, m + 1):
            options = (previous[j - 1] + cost(i - 1, j - 1), previous[j] + .8, current[j - 1] + .8)
            action = min(range(3), key=options.__getitem__)
            current[j], back[i][j] = options[action], action
        previous = current
    matched = [[] for _ in lines]
    i, j = n, m
    while i or j:
        action = back[i][j]
        if i and j and action == 0:
            if cost(i - 1, j - 1) <= .65:
                matched[owners[i - 1]].append(j - 1)
            i, j = i - 1, j - 1
        elif i and (action == 1 or not j):
            i -= 1
        else:
            j -= 1
    result = []
    for indices, length in zip(matched, lengths):
        anchors = []
        for index in sorted(indices):
            if not anchors or words[index] is not anchors[-1]:
                anchors.append(words[index])
        result.append({"words": anchors, "matched_characters": len(indices), "original_characters": length})
    return result


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
    純本地離線 Qwen2.5 決策引擎 (完全替代雲端 Luna API)
    自動檢測並優先使用 models/ 內的 Qwen2.5 GGUF 模型
    """
    def __init__(self, model_name: str = "qwen2.5-3b-instruct-q4_k_m.gguf"):
        models_dir = Path(__file__).resolve().parent.parent.parent / "models"
        model_path = models_dir / model_name
        if not model_path.exists():
            model_path = models_dir / "qwen2.5-3b-instruct-q4_k_m.gguf"
        if not model_path.exists():
            model_path = models_dir / "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
        self.proofreader = SubtitleProofreader(
            model_path=str(model_path),
            provider="local", n_ctx=8192,
        )
        self.model_name = self.proofreader.model_name

    def decide(self, sys_prompt: str, user_prompt: str) -> str:
        return self.proofreader._call_llm_api(sys_prompt, user_prompt)

    def close(self):
        self.proofreader.close()


class CloudLunaReasoner:
    """
    雲端 GPT-6 Luna / LLM API 決策引擎 (依據 .env 金鑰)
    """
    def __init__(self):
        self.proofreader = SubtitleProofreader(provider="api")
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
        lyrics_source: str,  # 可以是檔案路徑，或純文字歌詞內容
        output_dir: Optional[str] = None,
        llm_provider: str = "local",  # "local" | "api"
        local_model_name: str = "qwen2.5-3b-instruct-q4_k_m.gguf",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        whisper_model: str = DEFAULT_WHISPER_MODEL,
        device: str = "auto",
        prompt: Optional[str] = None,
        llm_audit: bool = True,
        script_mode: str = "transcript",
    ):
        if script_mode not in ("reference", "transcript"):
            raise ValueError("script_mode 必須為 reference 或 transcript")
        if llm_provider not in ("local", "api"):
            raise ValueError("llm_provider 必須為 local 或 api")
        self.audio_path = str(Path(audio_path).resolve())
        self.lyrics_source = lyrics_source
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.output_dir = Path(output_dir).resolve() if output_dir else base_dir / "output_luna_pipeline" / uuid.uuid4().hex
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.llm_provider = llm_provider
        self.local_model_name = local_model_name
        self.progress_callback = progress_callback
        self.whisper_model = whisper_model
        self.device = device
        self.prompt = prompt or "繁體中文"
        self.llm_audit = llm_audit
        self.script_mode = script_mode
        self.reference_lines: List[str] = []
        self.lyric_occurrences: List[Dict[str, Any]] = []

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

    def _notify(self, step: int, total: int, msg: str):
        if self.progress_callback:
            try:
                self.progress_callback(step, total, msg)
            except Exception:
                pass
        print(f"  [{step}/{total}] {msg}")

    def step_1_prepare_and_manifest(self) -> Dict[str, Any]:
        """【第 3 節】準備輸入與雜湊建檔"""
        self._notify(1, 5, "正在驗證音訊與歌詞資料，建立 SHA-256 執行紀錄...")
        if not os.path.exists(self.audio_path):
            raise FileNotFoundError(f"找不到音訊檔: {self.audio_path}")

        # 判定 lyrics_source 是檔案還是字串
        lyrics_path_obj = None
        src = self.lyrics_source or ""
        # 只有「單行且長度合理」的字串才可能是檔案路徑；多行歌詞直接視為文字
        if "\n" not in src and "\r" not in src and len(src) < 1024:
            try:
                cand = Path(src)
                if cand.exists() and cand.is_file():
                    lyrics_path_obj = cand
            except (OSError, ValueError):
                lyrics_path_obj = None

        if lyrics_path_obj is not None:
            raw_lyrics_text = lyrics_path_obj.read_text(encoding="utf-8")
            lyrics_filename = lyrics_path_obj.name
            lyrics_hash = compute_sha256_file(str(lyrics_path_obj))
        else:
            raw_lyrics_text = self.lyrics_source
            lyrics_filename = "raw_script_text.txt"
            lyrics_hash = compute_sha256_text(raw_lyrics_text)

        cleaned_lines = []
        for line in raw_lyrics_text.splitlines():
            l = re.sub(r"\[.*?\]|\(.*?\)", "", line).strip()
            if l:
                cleaned_lines.append(l)

        if not cleaned_lines:
            raise ValueError("歌詞原稿內容為空，無法進行對齊")

        self.org_lines = cleaned_lines
        self.reference_lines = cleaned_lines.copy()
        audio_hash = compute_sha256_file(self.audio_path)

        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", self.audio_path]
        dur_str = subprocess.check_output(cmd).decode().strip()
        self.audio_duration = float(dur_str)

        self.manifest = {
            "run_id": f"run_{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "audio_file": Path(self.audio_path).name,
            "audio_sha256": audio_hash,
            "audio_duration": self.audio_duration,
            "lyrics_file": lyrics_filename,
            "lyrics_sha256": lyrics_hash,
            "lyrics_lines_count": len(self.org_lines),
            "script_mode": self.script_mode,
            "reference_lines_count": len(self.reference_lines),
            "whisper_model": self.whisper_model,
            "whisper_backend": "native",
            "alignment_tool": "stable-ts 2.19.1",
            "llm_provider": self.llm_provider,
            "llm_audit_enabled": self.llm_audit,
            "llm_model": self.local_model_name if self.llm_provider == "local" else "gpt-6-luna",
            "reading_extension_sec": 0.16,
            "anomaly_threshold_sec": 0.3
        }
        return self.manifest

    def step_2_whisper_full_asr(self) -> List[Dict[str, Any]]:
        """【第 4 節】Whisper 全曲辨識 (初稿分段 + 逐詞時間戳)"""
        self._notify(2, 5, f"原生 Whisper ({self.whisper_model}) 全曲聲學辨識與逐詞特徵提取中...")
        
        self.raw_asr = transcribe_native_audio(
            audio_path=self.audio_path,
            model_size=self.whisper_model,
            device=self.device,
            initial_prompt=self.prompt,
        )
        self.manifest["whisper_device"] = self.raw_asr.get("device", self.device)

        raw_segs = self.raw_asr.get("raw_segments", [])
        asr_raw_path = self.output_dir / "asr_raw.json"
        with open(asr_raw_path, "w", encoding="utf-8") as f:
            json.dump(self.raw_asr, f, ensure_ascii=False, indent=2)

        clean_segs = []
        for s in raw_segs:
            txt = s.get("text", "").strip()
            words = [dict(word) for word in s.get("words", [])]
            
            clean_segs.append({
                "id": s["id"],
                "start": words[0]["start"] if words else s["start"],
                "end": words[-1]["end"] if words else s["end"],
                "text": txt,
                "words": words
            })

        self.manifest["suspected_hallucinations"] = [
            {"segment_id": s["id"], "text": s["text"], "reason": "keyword_pattern", "action": "retained_for_review"}
            for s in clean_segs if is_hallucination_text(s["text"])
        ]

        self.asr_clean_segments = clean_segs
        if self.script_mode == "reference":
            self.lyric_occurrences = build_lyric_occurrences(self.reference_lines, clean_segs)
            self.org_lines = [item["text"] for item in self.lyric_occurrences]
            self.manifest["lyrics_lines_count"] = len(self.org_lines)
            with (self.output_dir / "lyric_occurrences.json").open("w", encoding="utf-8") as stream:
                json.dump(self.lyric_occurrences, stream, ensure_ascii=False, indent=2)
        return self.asr_clean_segments

    def step_3_and_4_alignment_and_evidence(self) -> List[Dict[str, Any]]:
        """
        【第 5 & 6 & 8 節】
        - 執行 stable-ts 原歌詞強制對齊
        - 雙軌時間比對 (ASR vs stable-ts)
        - 針對異常句子執行局部切音重跑對齊 (Section 8)
        """
        self._notify(3, 5, f"使用 stable-ts 對 {len(self.org_lines)} 句原歌詞強制對齊與雙軌比對...")
        if not self.org_lines:
            self.cue_evidence = []
            return self.cue_evidence
        lyrics_text = "\n".join(self.org_lines)

        st_model = load_native_whisper_model(self.whisper_model, self.device)
        try:
            with tempfile.TemporaryDirectory(dir=self.output_dir, prefix="temp_slices_") as slice_directory:
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
                mapped_lines = self.lyric_occurrences if self.script_mode == "reference" else map_lyrics_to_asr_words(self.org_lines, self.asr_clean_segments)

                # 雙軌比對與異常標記
                evidence_list = []
                temp_dir = Path(slice_directory)

                for line_idx, org_line in enumerate(self.org_lines, 1):
                    st_seg = self.stable_ts_segments[line_idx - 1] if line_idx <= len(self.stable_ts_segments) else None
                    t_align_start = st_seg["start"] if st_seg else 0.0
                    t_align_end = st_seg["end"] if st_seg else 0.0

                    mapping = mapped_lines[line_idx - 1]
                    anchors = mapping["words"]
                    t_asr_start = min((word["start"] for word in anchors), default=t_align_start)
                    t_asr_end = max((word["end"] for word in anchors), default=t_align_end)
                    asr_text = "".join(word["word"] for word in anchors)
                    default_candidate = "cand_asr" if anchors and t_asr_end > t_asr_start else "cand_stable_ts"

                    # 檢測異常指標
                    diff_start = abs(t_asr_start - t_align_start)
                    diff_end = abs(t_asr_end - t_align_end)
                    dur = t_align_end - t_align_start
                    anomalies = []
                    if is_hallucination_text(asr_text):
                        anomalies.append("suspected_hallucination")
                    if self.script_mode == "reference":
                        if mapping["source_line_id"] is None:
                            anomalies.append("asr_only_not_in_reference")
                        if any(word.get("segment_only") for word in anchors):
                            anomalies.append("asr_segment_timing_only")
                    if default_candidate != "cand_asr":
                        anomalies.append("asr_mapping_missing")
                    elif mapping["matched_characters"] < mapping["original_characters"] * .7:
                        anomalies.append("asr_mapping_low_coverage")
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
                        }
                    }
                    if default_candidate == "cand_asr":
                        candidates["cand_asr"] = {
                            "candidate_id": "cand_asr",
                            "source": f"native whisper {self.whisper_model}",
                            "start": round(t_asr_start, 3),
                            "end": round(t_asr_end, 3),
                            "text": asr_text,
                            **mapping,
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
                                    abs_loc_st = round(loc_seg.start + slice_st, 3)
                                    abs_loc_et = round(loc_seg.end + slice_st, 3)
                                    candidates["cand_local_retry"] = {
                                        "candidate_id": "cand_local_retry",
                                        "source": "stable-ts local slice retry",
                                        "start": abs_loc_st,
                                        "end": abs_loc_et
                                    }
                            except Exception:
                                pass
                            finally:
                                if os.path.exists(slice_wav):
                                    os.remove(slice_wav)

                    evidence_item = {
                        "line_id": line_idx,
                        "org_line": org_line,
                        "candidates": candidates,
                        "default_candidate_id": default_candidate,
                        "diff_start": round(diff_start, 3),
                        "diff_end": round(diff_end, 3),
                        "anomalies": anomalies,
                        "needs_review": bool(anomalies)
                    }
                    if self.script_mode == "reference":
                        evidence_item["source_line_id"] = mapping["source_line_id"]
                        evidence_item["occurrence"] = mapping["occurrence"]
                    evidence_list.append(evidence_item)

                self.cue_evidence = evidence_list
                return self.cue_evidence
        finally:
            unload_native_whisper_model(st_model)

    def step_5_and_6_luna_decision(self) -> List[SubtitleSegment]:
        """【第 7 & 9 節】呼叫決策大腦 (Local Qwen2.5 / Luna API) 審核異常句子並選定最佳邊界"""
        decision_path = self.output_dir / "decision_batches.json"
        decision_path.unlink(missing_ok=True)
        anomaly_lines = [ev for ev in self.cue_evidence if ev.get("needs_review")]
        message = f"啟動決策大腦 ({self.llm_provider})，審核 {len(anomaly_lines)} 句異常候選邊界..." if self.llm_audit else f"保留逐詞映射，{len(anomaly_lines)} 句候選差異標記待複核..."
        self._notify(4, 5, message)

        decisions_map: Dict[int, Dict[str, Any]] = {}
        self.manifest["audit_warning"] = None
        if anomaly_lines and self.llm_audit:
            audit_payload = []
            for ev in anomaly_lines:
                idx = ev["line_id"] - 1
                prev_line = self.cue_evidence[idx - 1] if idx > 0 else None
                next_line = self.cue_evidence[idx + 1] if idx + 1 < len(self.cue_evidence) else None

                prev_bound = f"上一句結束: {prev_line['candidates'][prev_line.get('default_candidate_id', 'cand_stable_ts')]['end']:.2f}s" if prev_line else "開頭"
                next_bound = f"下一句開始: {next_line['candidates'][next_line.get('default_candidate_id', 'cand_stable_ts')]['start']:.2f}s" if next_line else "曲尾"

                audit_payload.append({
                    "line_id": ev["line_id"],
                    "text": ev["org_line"],
                    "context": f"{prev_bound} | {next_bound}",
                    "candidates": ev["candidates"],
                    "default_candidate_id": ev.get("default_candidate_id", "cand_stable_ts"),
                    "anomalies": ev["anomalies"]
                })

            sys_prompt = """你是一位專業的繁體中文音樂與影視字幕對齊專家。
任務：針對被標記有時間軸異常的歌詞句子，根據候選時間戳與前後句時間邊界，為每個異常句子選擇最合適的開始 (start) 與結束 (end) 候選識別碼，並說明簡短理由。

規則：
1. 只能從該句提供的 candidates 中選擇候選邊界，嚴禁憑空編造秒數。
2. 保持時間軸單調遞增，不能早於上一句結束時間，不能晚於下一句開始時間。
3. keep 表示保留 default_candidate_id。原詞對應的 Whisper 逐詞映射是主時間；其他候選用於補缺與交叉檢查，沒有明確字詞證據時不要改動。
4. 若選擇特定候選，action 填 "choose_candidate"，並指定 start_candidate_id 與 end_candidate_id (例如 "cand_local_retry", "cand_stable_ts", "cand_asr")。
5. 必須回覆本批次每個 line_id，恰好一次，不得添加其他編號。
6. 只輸出 JSON 物件，decisions 欄位為陣列。每項包含整數 line_id、action、start_candidate_id、end_candidate_id、reason。reason 最多 32 個字，不輸出推理過程。"""

            reasoner = None
            batches = []
            try:
                reasoner = LocalQwenReasoner(self.local_model_name) if self.llm_provider == "local" else CloudLunaReasoner()
                for start in range(0, len(audit_payload), 4):
                    payload = audit_payload[start:start + 4]
                    candidates_by_line = {item["line_id"]: item["candidates"] for item in payload}
                    expected = {item["line_id"] for item in payload}
                    record = {"input": payload, "expected_ids": sorted(expected), "returned_ids": []}
                    try:
                        user_input = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                        raw_res = reasoner.decide(sys_prompt, user_input)
                        record["response"] = raw_res
                        data = _extract_json_payload(raw_res)
                        items = data if isinstance(data, list) else data.get("decisions", [])
                        for item in items:
                            if not isinstance(item, dict) or type(item.get("line_id")) is not int:
                                continue
                            lid = item["line_id"]
                            if lid not in expected or lid in record["returned_ids"]:
                                continue
                            action = item.get("action", "keep")
                            if action not in ("keep", "choose_candidate"):
                                continue
                            if action == "choose_candidate" and any(item.get(field) not in candidates_by_line[lid] for field in ("start_candidate_id", "end_candidate_id")):
                                continue
                            decisions_map[lid] = item
                            record["returned_ids"].append(lid)
                    except Exception as error:
                        record["error"] = str(error)
                    record["missing_ids"] = sorted(expected - set(record["returned_ids"]))
                    batches.append(record)
            except Exception as e:
                print(f"  ⚠️ LLM 推理或 JSON 解析警告: {e}")
            finally:
                if reasoner is not None:
                    reasoner.close()
                with decision_path.open("w", encoding="utf-8") as stream:
                    json.dump({"system": sys_prompt, "batches": batches}, stream, ensure_ascii=False, indent=2)

            missing = len(anomaly_lines) - len(decisions_map)
            if missing:
                self.manifest["audit_warning"] = f"時間審核有 {missing} 段未完成，已保留預設時間並標記待複核。"

        # 彙整最終時間軸與記錄 corrections
        final_segments: List[SubtitleSegment] = []
        corrections: List[Dict[str, Any]] = []
        reviews: List[Dict[str, Any]] = []

        last_end = 0.0
        for index, ev in enumerate(self.cue_evidence):
            lid = ev["line_id"]
            org_line = ev["org_line"]
            cands = ev["candidates"]
            default_candidate = ev.get("default_candidate_id", "cand_stable_ts")
            def_st = cands[default_candidate]["start"]
            def_et = cands[default_candidate]["end"]

            chosen_st = def_st
            chosen_et = def_et
            st_source = default_candidate
            et_source = default_candidate
            decision_action = "keep"
            decision_reason = "採用 Whisper 逐詞映射" if default_candidate == "cand_asr" else "保留強制對齊候選"

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

            remaining = len(self.cue_evidence) - index
            min_duration = min(0.001, self.audio_duration / len(self.cue_evidence))
            latest_end = self.audio_duration - (remaining - 1) * min_duration
            chosen_st = min(max(last_end, chosen_st), latest_end - min_duration)
            if index + 1 < len(self.cue_evidence):
                following = self.cue_evidence[index + 1]
                next_source = following.get("default_candidate_id", "cand_stable_ts")
                next_decision = decisions_map.get(following["line_id"], {})
                if next_decision.get("action") == "choose_candidate" and next_decision.get("start_candidate_id") in following["candidates"]:
                    next_source = next_decision["start_candidate_id"]
                next_start = following["candidates"][next_source]["start"]
                if next_start > chosen_st:
                    chosen_et = min(chosen_et, next_start)
            chosen_et = min(max(chosen_et, chosen_st + min_duration), latest_end)

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

            unresolved = {"asr_mapping_missing", "asr_only_not_in_reference", "asr_segment_timing_only", "suspected_hallucination"}
            status = "needs_review" if (ev["anomalies"] and decision_action == "keep") or unresolved.intersection(ev["anomalies"]) else "passed"
            if def_et <= def_st or def_st >= self.audio_duration:
                status = "needs_review"
                decision_reason = "原始對齊缺少有效時間，已保留最短時間區間，請手動校對"
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
        return final_segments

    def step_7_display_rules_and_export(self, segments: List[SubtitleSegment]) -> SubtitleTrack:
        """【第 10 & 11 節】套用 +0.16s 閱讀延長規則，排版並輸出標準字幕與診斷檔案"""
        self._notify(5, 5, "套用 +0.16s 閱讀延長規則與排版，輸出標準字幕與診斷檔案...")
        processed_segments: List[SubtitleSegment] = []

        for i, seg in enumerate(segments):
            st = seg.start
            et = seg.end

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
            source_file=Path(self.audio_path).stem + ".srt",
            duration=self.audio_duration,
            language="zh",
            segments=processed_segments
        )

        # 標準字幕與診斷檔案
        save_file(to_vtt(self.final_track), str(self.output_dir / "lyrics.vtt"))
        save_file(to_ass(self.final_track), str(self.output_dir / "lyrics.ass"))

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

        negative = sum(1 for s in processed_segments if s.start < 0)
        inverted = sum(1 for s in processed_segments if s.start >= s.end)
        text_match = len(self.org_lines) == len(processed_segments) and all(
            re.sub(r"\s+", "", text) == re.sub(r"\s+", "", segment.text)
            for text, segment in zip(self.org_lines, processed_segments)
        )
        val_report = {
            "total_lyric_lines": len(self.org_lines),
            "output_subtitle_count": len(processed_segments),
            "script_mode": self.script_mode,
            "lyrics_text_100_percent_match": text_match if self.script_mode == "transcript" else None,
            "performed_text_match": text_match,
            "negative_timestamps": negative,
            "inverted_timestamps": inverted,
            "overlaps": overlaps,
            "exceeds_audio_duration": exceeds,
            "validation_passed": (overlaps == 0 and exceeds == 0 and negative == 0 and inverted == 0 and text_match)
        }
        if self.script_mode == "reference":
            expected_anchors = sum(len(segment.get("words") or ([segment] if segment.get("text", "").strip() else [])) for segment in self.asr_clean_segments)
            covered = [index for item in self.lyric_occurrences for index in range(item["word_start"], item["word_end"])]
            coverage_complete = covered == list(range(expected_anchors))
            val_report.update({
                "reference_lines_count": len(self.reference_lines),
                "matched_occurrences": sum(item["source_line_id"] is not None for item in self.lyric_occurrences),
                "asr_only_occurrences": sum(item["source_line_id"] is None for item in self.lyric_occurrences),
                "asr_anchor_count": expected_anchors,
                "asr_coverage_complete": coverage_complete,
            })
            val_report["validation_passed"] &= coverage_complete
        with open(self.output_dir / "validation.json", "w", encoding="utf-8") as f:
            json.dump(val_report, f, ensure_ascii=False, indent=2)

        # 7. run_manifest.json
        self.manifest["execution_duration_sec"] = round(time.time() - self.start_perf_time, 2)
        with open(self.output_dir / "run_manifest.json", "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, ensure_ascii=False, indent=2)

        return self.final_track

    def run(self) -> SubtitleTrack:
        """端到端執行完整管線並回傳 SubtitleTrack"""
        try:
            self.step_1_prepare_and_manifest()
            self.step_2_whisper_full_asr()
            self.step_3_and_4_alignment_and_evidence()
            final_segs = self.step_5_and_6_luna_decision()
            return self.step_7_display_rules_and_export(final_segs)
        finally:
            release_gpu_memory()


def run_luna_pipeline(
    audio_path: str,
    lyrics_source: str,
    output_dir: Optional[str] = None,
    llm_provider: str = "local",
    local_model_name: str = "qwen2.5-3b-instruct-q4_k_m.gguf",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    whisper_model: str = DEFAULT_WHISPER_MODEL,
    device: str = "auto",
    prompt: Optional[str] = None,
    llm_audit: bool = True,
    script_mode: str = "transcript",
) -> SubtitleTrack:
    """高階調用函式：供 Web API 直接呼叫"""
    pipeline = LunaPipeline(
        audio_path=audio_path,
        lyrics_source=lyrics_source,
        output_dir=output_dir,
        llm_provider=llm_provider,
        local_model_name=local_model_name,
        progress_callback=progress_callback,
        whisper_model=whisper_model,
        device=device,
        prompt=prompt,
        llm_audit=llm_audit,
        script_mode=script_mode,
    )
    return pipeline.run()
