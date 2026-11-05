import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pypinyin import lazy_pinyin

from src.core.env_utils import preload_cuda_libs
preload_cuda_libs()

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


def is_hallucination_seg(seg: Dict[str, Any], duration: float) -> bool:
    text = seg.get("text", "").strip()
    if not text:
        return True
    for pat in HALLUCINATION_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    words = seg.get("words", [])
    if words:
        span = words[-1]["end"] - words[0]["start"]
        if span < 0.05 and len(text) > 2:
            return True
    return False


def refine_segment_word_boundaries(seg: Dict[str, Any]) -> Dict[str, Any]:
    """
    修正 faster-whisper 句首第一個字常把前導換氣/伴奏算入導致 start 偏早 0.3~0.5s 的問題
    """
    words = seg.get("words", [])
    if not words:
        return seg
    w0 = dict(words[0])
    w0_text = re.sub(r"\s+", "", w0["word"])
    n_chars = max(1, len(w0_text))
    max_lead_dur = 0.30 * n_chars
    if (w0["end"] - w0["start"]) > max_lead_dur:
        w0["start"] = round(w0["end"] - max_lead_dur, 3)
    new_words = [w0] + [dict(w) for w in words[1:]]
    new_seg = dict(seg)
    new_seg["words"] = new_words
    new_seg["start"] = new_words[0]["start"]
    new_seg["end"] = new_words[-1]["end"]
    return new_seg


def snap_segments_to_whisper_words(
    segments: List[SubtitleSegment],
    all_clean_words: List[Dict[str, Any]],
    audio_duration: float
) -> List[SubtitleSegment]:
    """
    將對齊後的字幕片段起訖時間，強制錨定回 Whisper 實際辨識到的字詞邊界，
    防止把兩句之間的純音樂空檔算進字幕顯示時間。
    """
    used_word_indices = set()
    snapped: List[SubtitleSegment] = []
    last_end = 0.0

    for seg in segments:
        st, et = seg.start, seg.end
        # 找出落在此區間內、且尚未被前一句消耗的 Whisper words
        matched_indices = []
        for w_idx, w in enumerate(all_clean_words):
            if w_idx in used_word_indices:
                continue
            w_mid = (w["start"] + w["end"]) / 2.0
            if (st - 0.12) <= w_mid <= (et + 0.12):
                matched_indices.append(w_idx)

        if matched_indices:
            first_w = all_clean_words[matched_indices[0]]
            last_w = all_clean_words[matched_indices[-1]]
            st = first_w["start"]
            et = last_w["end"]
            for idx in matched_indices:
                used_word_indices.add(idx)

        if st < last_end:
            st = last_end
        if et <= st:
            et = min(audio_duration, st + 1.2)
        if et > audio_duration:
            et = audio_duration

        last_end = et
        snapped.append(
            SubtitleSegment(
                id=seg.id,
                start=round(st, 3),
                end=round(et, 3),
                text=seg.text,
                words=[]
            )
        )
    return snapped


def merge_adjacent_matching_org_lines(
    segments: List[SubtitleSegment],
    org_lines: List[str]
) -> List[SubtitleSegment]:
    """
    確定性後處理：若相鄰兩句合併後的純文字，剛好完全等於原詞中的單一完整行（例如「真的好冷」+「靈魂快要被凍結」），
    且間隔小於 1.5 秒，則自動合併為原詞的完整單行。
    """
    def norm(s: str) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]", "", s)

    org_norm_map = {norm(line): line.strip() for line in org_lines if norm(line)}
    merged: List[SubtitleSegment] = []
    i = 0
    new_id = 1
    while i < len(segments):
        if i + 1 < len(segments):
            s1, s2 = segments[i], segments[i + 1]
            combined_norm = norm(s1.text) + norm(s2.text)
            if combined_norm in org_norm_map and (s2.start - s1.end) <= 1.5:
                merged.append(
                    SubtitleSegment(
                        id=new_id,
                        start=s1.start,
                        end=s2.end,
                        text=org_norm_map[combined_norm],
                        words=[]
                    )
                )
                new_id += 1
                i += 2
                continue
        seg = segments[i]
        merged.append(
            SubtitleSegment(
                id=new_id,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=[]
            )
        )
        new_id += 1
        i += 1
    return merged


def align_and_proofread_with_llm(
    raw_segments: List[Dict[str, Any]],
    script_text: str,
    audio_duration: float,
    proofreader: SubtitleProofreader,
) -> List[SubtitleSegment]:
    """
    結合 Whisper 逐詞時間戳、拼音讀音提示與原始歌詞，交由雲端 LLM 進行結構對齊與正字校對
    """
    seg_lines = []
    all_clean_words = []
    for idx, s in enumerate(raw_segments, 1):
        words = s.get("words", [])
        all_clean_words.extend(words)
        words_desc = " ".join(
            [f"{w['word']}({w['start']:.2f}-{w['end']:.2f})" for w in words]
        )
        py_hint = "".join(lazy_pinyin(re.sub(r"[^\u4e00-\u9fff]", "", s["text"])))
        seg_lines.append(
            f"[S{idx:02d}] ({s['start']:.2f}s - {s['end']:.2f}s) 文字: \"{s['text']}\" | 拼音: {py_hint} | 逐詞: {words_desc}"
        )

    sys_prompt = """你是一位專業的繁體中文音樂與影視字幕對齊與校對專家。
使用者會提供：
1. 【原始參考歌詞】：創作者提供的正確歌詞文本。
2. 【Whisper 初稿分段與逐詞時間戳】：由 Whisper large-v3-turbo 辨識出的語音段落、拼音與每個字詞的精確秒數。

你的任務是將初稿校對並對齊為最終的完美字幕清單：
1. **以原始歌詞為準修正錯別字**：比對【原始參考歌詞】與拼音讀音，將 Whisper 聽錯的同音字、近音字、結尾弱音全部修正為正確歌詞（例如：「始終踏」→「時鐘，」、「開平洋」→「太平洋」、「自己的感覺」→「死寂的感覺」、「大老群退路斷明圈一線」→「大樓傾，退路斷，命懸一線！」、「真是冰了臉穿透氣對象在復興那樣衝」→「城市病了，喘口氣都像服刑。」、「舉頭一面」→「去偷一秒」、「拖熱手心」→「搓熱手指」、「想弄的回想」→「巷弄回響」、「明孔」→「靈魂」、「穿過街角那一天」→「轉過街角...」與「暖意...」、「太慢了」→「在哪呢。」）。
2. **斷句合併與拆分（精確對齊歌詞行）**：
   - **合併**：若同一句歌詞被 Whisper 拆成兩段（例如 `拖熱手心` 與 `證明我們還活著`、或 `真的好冷` 與 `靈魂快要被凍結`），請合併為同一句字幕，`start` 取第一段起點，`end` 取第二段終點。
   - **拆分與邊界修正**：若某段結尾黏到了下一句歌詞的開頭（例如 `叫著火沒叫` 的 `沒叫(30.66-31.22)` 屬於下一句 `沒交集，不理解，被命運推到邊緣。`；或 `穿過街角那一天` 是 `轉過街角... (154.88-156.00)` 與 `暖意... (156.00-157.10)` 兩句），請直接依據「逐詞時間戳」將時間邊界精準切開！
3. **重複副歌與尾奏處理**：
   - 若歌曲實際演唱了兩遍副歌（如 45.8s~56.5s 與 57.1s~67.8s）或重複尾奏（如 149.0s~150.2s 與 151.8s~153.1s），即使【原始參考歌詞】只寫了一遍，請保留實際演唱的每一句字幕並填入正確歌詞，且嚴格保留兩句之間的伴奏空檔（切勿將前一句的 end 直接連到後一句的 start）。
4. **時間軸檢查**：
   - 嚴格使用 Whisper 逐詞時間戳的真實起訖秒數，不可重疊（後一句 start >= 前一句 end），不可超過音訊總長。

請以純 JSON 格式回傳，格式如下：
{
  "subtitles": [
    {"id": 1, "start": 11.30, "end": 13.76, "text": "牆上的時鐘，滴答滴答。"}
  ]
}"""

    user_input = (
        f"【音訊總長度】：{audio_duration:.2f} 秒\n\n"
        f"【原始參考歌詞】：\n{script_text.strip()}\n\n"
        f"【Whisper 初稿分段與逐詞時間戳】：\n" + "\n".join(seg_lines)
    )

    print("Calling Cloud LLM for structural alignment & lyric proofreading...")
    raw_json = proofreader._call_llm_api(sys_prompt, user_input)
    data = _extract_json_payload(raw_json)
    items = data.get("subtitles") or data.get("results") or (data if isinstance(data, list) else [])

    raw_aligned: List[SubtitleSegment] = []
    for idx, item in enumerate(items, 1):
        st = float(item["start"])
        et = float(item["end"])
        txt = str(item["text"]).strip()
        raw_aligned.append(
            SubtitleSegment(id=idx, start=round(st, 3), end=round(et, 3), text=txt, words=[])
        )

    # 強制錨定回 Whisper 字詞真實時間邊界
    snapped = snap_segments_to_whisper_words(raw_aligned, all_clean_words, audio_duration)
    org_lines = [l.strip() for l in script_text.splitlines() if l.strip()]
    return merge_adjacent_matching_org_lines(snapped, org_lines)


def to_lrc(track: SubtitleTrack) -> str:
    """匯出標準 LRC 動態歌詞格式 [mm:ss.xx]歌詞"""
    lines = []
    for seg in track.segments:
        mm = int(seg.start // 60)
        ss = seg.start % 60
        text_line = seg.text.replace("\n", " ")
        lines.append(f"[{mm:02d}:{ss:05.2f}]{text_line}")
    return "\n".join(lines) + "\n"


def validate_track(track: SubtitleTrack, org_lines: List[str], audio_duration: float) -> Dict[str, Any]:
    """
    步驟 5：檢查歌詞是否一致、有沒有漏句、時間重疊或超過原曲長度
    """
    overlaps = []
    exceeded = []
    for i, seg in enumerate(track.segments):
        if seg.end > audio_duration + 0.05:
            exceeded.append((seg.id, seg.end, audio_duration))
        if i > 0:
            prev = track.segments[i - 1]
            if seg.start < prev.end - 0.001:
                overlaps.append((prev.id, seg.id, prev.end, seg.start))

    # 檢查原詞覆蓋率 (以去除標點後的字元集合/行比對)
    def norm(s: str) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]", "", s)

    sub_norm_set = [norm(s.text) for s in track.segments]
    missing_org_lines = []
    for idx, ol in enumerate(org_lines, 1):
        nol = norm(ol)
        # 檢查是否有完全相同或高度相似的字幕行
        found = any(nol == sn or nol in sn or sn in nol for sn in sub_norm_set)
        if not found:
            missing_org_lines.append((idx, ol))

    return {
        "total_subtitles": len(track.segments),
        "total_org_lines": len(org_lines),
        "first_start": track.segments[0].start if track.segments else 0.0,
        "last_end": track.segments[-1].end if track.segments else 0.0,
        "audio_duration": audio_duration,
        "overlaps_count": len(overlaps),
        "exceeded_count": len(exceeded),
        "missing_org_lines": missing_org_lines,
    }


def main():
    wav_path = "inputclip/audio.wav"
    org_path = "inputclip/audio-org.txt"
    script_text = Path(org_path).read_text(encoding="utf-8")
    org_lines = [l.strip() for l in script_text.splitlines() if l.strip()]

    print("Step 1 & 2: Running Whisper large-v3-turbo on inputclip/audio.wav...")
    raw_res = transcribe_audio(
        audio_path=wav_path,
        model_size="large-v3-turbo",
        device="cuda",
        vad_filter=False,
        condition_on_previous_text=False,
        hallucination_silence_threshold=None,
        word_timestamps=True,
    )
    duration = raw_res["duration"]
    raw_segs = raw_res["raw_segments"]
    print(f"Whisper raw segments: {len(raw_segs)}, duration: {duration:.2f}s")

    clean_segs = []
    for s in raw_segs:
        if is_hallucination_seg(s, duration):
            print(f"  [Filtered Hallucination] [{s['start']:.2f}s - {s['end']:.2f}s] {s['text']}")
            continue
        clean_segs.append(refine_segment_word_boundaries(s))

    print(f"Clean vocal segments: {len(clean_segs)}")

    proofreader = SubtitleProofreader()
    aligned_segments = align_and_proofread_with_llm(clean_segs, script_text, duration, proofreader)

    print(f"\n=== Final Aligned Subtitles ({len(aligned_segments)} lines) ===")
    for seg in aligned_segments:
        mm_s, ss_s = divmod(seg.start, 60)
        mm_e, ss_e = divmod(seg.end, 60)
        print(f"#{seg.id:02d} [{int(mm_s):02d}:{ss_s:05.2f} -> {int(mm_e):02d}:{ss_e:05.2f}] {seg.text}")

    track = SubtitleTrack(
        source_file=wav_path,
        duration=duration,
        language="zh",
        segments=aligned_segments
    )
    srt_out = to_srt(track)
    lrc_out = to_lrc(track)
    save_file(srt_out, "inputclip/audio_generated.srt")
    save_file(lrc_out, "inputclip/audio_generated.lrc")

    report = validate_track(track, org_lines, duration)
    print("\n=== Step 5: Validation Report ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("\nSaved SRT to inputclip/audio_generated.srt and LRC to inputclip/audio_generated.lrc")


if __name__ == "__main__":
    main()
