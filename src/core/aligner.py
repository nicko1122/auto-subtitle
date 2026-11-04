import re
from typing import List, Dict, Any, Tuple, Optional
from pypinyin import lazy_pinyin

from ..schemas.subtitle import WordItem, SubtitleSegment, SubtitleTrack


def clean_text_for_alignment(text: str) -> str:
    """去除標點與特殊符號，僅保留中文、字母、數字供對齊計算"""
    return re.sub(r'[^\w\u4e00-\u9fff]', '', text)


def expand_words_to_char_stream(words: List[WordItem]) -> List[Dict[str, Any]]:
    """
    將 Whisper 的逐詞清單展開為逐字元 (Character-level) 時間軸流
    """
    char_stream: List[Dict[str, Any]] = []
    for w in words:
        clean_w = clean_text_for_alignment(w.word)
        if not clean_w:
            continue
        n = len(clean_w)
        dur = max(w.end - w.start, 0.01)
        step = dur / n
        for idx, ch in enumerate(clean_w):
            c_start = w.start + idx * step
            c_end = w.start + (idx + 1) * step
            py = lazy_pinyin(ch)[0] if ch else ""
            char_stream.append({
                "char": ch,
                "pinyin": py,
                "start": round(c_start, 3),
                "end": round(c_end, 3),
                "word_ref": w
            })
    return char_stream


def compute_char_similarity(char_a: str, py_a: str, char_b: str, py_b: str) -> float:
    """計算兩個字符的相似度 (文字全同 > 拼音相同/同音 > 拼音韻母相近 > 不相似)"""
    if char_a == char_b:
        return 2.5
    if py_a and py_b and py_a == py_b:
        # 同音異字 (例如：牆 qiang / 想 xiang 有部分韻母相同，若完全同音如 時/始 shi 則給高分)
        return 2.0
    if py_a and py_b and (py_a.endswith(py_b[-2:]) or py_b.endswith(py_a[-2:])):
        # 押韻或音近
        return 1.0
    return -1.0


def align_script_lines_with_char_stream(
    script_lines: List[str],
    char_stream: List[Dict[str, Any]]
) -> List[SubtitleSegment]:
    """
    使用動態規劃序列比對 (Needleman-Wunsch / Monotonic DP)，
    將原稿每行句子與 Whisper 逐字時間流進行最佳化強制對齊
    """
    # 建立原稿的扁平字元清單，同時記錄每個字元屬於哪一行 (line_idx)
    flat_script_chars: List[Dict[str, Any]] = []
    line_clean_lengths: List[int] = []

    for l_idx, line in enumerate(script_lines):
        clean_line = clean_text_for_alignment(line)
        line_clean_lengths.append(len(clean_line))
        for c_idx, ch in enumerate(clean_line):
            py = lazy_pinyin(ch)[0] if ch else ""
            flat_script_chars.append({
                "char": ch,
                "pinyin": py,
                "line_idx": l_idx,
                "char_idx_in_line": c_idx
            })

    N = len(flat_script_chars)
    M = len(char_stream)

    if N == 0 or M == 0:
        return []

    # 動態規劃比對: DP[i][j]
    # 限制搜尋帶 (Band Search)，因為時間基本上是單調遞增的，避免 O(N*M) 過大
    GAP_PENALTY = -0.8
    dp = {}
    parent = {}

    dp[(0, 0)] = 0.0

    # 考量速度與時間順序，計算動態規劃矩陣
    for i in range(N + 1):
        for j in range(M + 1):
            if (i, j) not in dp:
                continue
            curr_score = dp[(i, j)]

            # 1. 匹配 (i+1, j+1)
            if i < N and j < M:
                sc = flat_script_chars[i]
                wc = char_stream[j]
                sim = compute_char_similarity(sc["char"], sc["pinyin"], wc["char"], wc["pinyin"])
                next_score = curr_score + sim
                if (i + 1, j + 1) not in dp or next_score > dp[(i + 1, j + 1)]:
                    dp[(i + 1, j + 1)] = next_score
                    parent[(i + 1, j + 1)] = (i, j, "match")

            # 2. 原稿跳過 (刪除/插入)
            if i < N:
                next_score = curr_score + GAP_PENALTY
                if (i + 1, j) not in dp or next_score > dp[(i + 1, j)]:
                    dp[(i + 1, j)] = next_score
                    parent[(i + 1, j)] = (i, j, "skip_script")

            # 3. Whisper 跳過 (語音贅字/雜音)
            if j < M:
                next_score = curr_score + GAP_PENALTY
                if (i, j + 1) not in dp or next_score > dp[(i, j + 1)]:
                    dp[(i, j + 1)] = next_score
                    parent[(i, j + 1)] = (i, j, "skip_whisper")

    # 回溯 (Backtrack) 找出最佳對齊路徑
    curr = (N, M)
    aligned_matches: Dict[int, List[Dict[str, Any]]] = {idx: [] for idx in range(len(script_lines))}

    while curr != (0, 0):
        if curr not in parent:
            break
        pi, pj, action = parent[curr]
        if action == "match":
            script_char_info = flat_script_chars[pi]
            whisper_char_info = char_stream[pj]
            l_idx = script_char_info["line_idx"]
            aligned_matches[l_idx].append(whisper_char_info)
        curr = (pi, pj)

    # 針對每一行計算最終時間軸起訖點
    segments: List[SubtitleSegment] = []
    last_end = 0.0

    for l_idx, line in enumerate(script_lines):
        matched_chars = aligned_matches[l_idx]
        # 反轉回正序
        matched_chars.reverse()

        if matched_chars:
            start_t = matched_chars[0]["start"]
            end_t = matched_chars[-1]["end"]
            # 確保結束時間大於開始時間
            if end_t <= start_t:
                end_t = start_t + max(len(clean_text_for_alignment(line)) * 0.25, 1.0)
            # 確保時間單調性
            if start_t < last_end:
                start_t = last_end
            if end_t <= start_t:
                end_t = start_t + 1.0
        else:
            # 萬一該行完全沒有匹配到，使用前一行的結束時間推估
            est_dur = max(len(clean_text_for_alignment(line)) * 0.25, 1.2)
            start_t = last_end
            end_t = start_t + est_dur

        last_end = end_t

        segments.append(
            SubtitleSegment(
                id=l_idx + 1,
                start=round(start_t, 3),
                end=round(end_t, 3),
                text=line.strip(),
                words=[]
            )
        )

    return segments


def align_script_to_audio(
    script_text_or_path: str,
    transcription_data: Dict[str, Any]
) -> SubtitleTrack:
    """
    有稿對齊入口函數：傳入原稿文字 (或檔案路徑) 與 Whisper 辨識資料，
    回傳完整對齊後的 SubtitleTrack
    """
    # 讀取原稿行
    text = script_text_or_path
    from pathlib import Path
    p = Path(script_text_or_path)
    if p.exists() and p.is_file():
        text = p.read_text(encoding="utf-8")

    raw_lines = [line.strip() for line in text.splitlines()]
    script_lines = [l for l in raw_lines if l]

    # 取出所有 words
    raw_words = transcription_data.get("all_words", [])
    word_items = [WordItem(**w) if isinstance(w, dict) else w for w in raw_words]

    char_stream = expand_words_to_char_stream(word_items)
    aligned_segments = align_script_lines_with_char_stream(script_lines, char_stream)

    duration = transcription_data.get("duration", 0.0)
    if aligned_segments and aligned_segments[-1].end > duration:
        duration = aligned_segments[-1].end

    return SubtitleTrack(
        version="1.0.0",
        source_file=transcription_data.get("source_file", ""),
        duration=duration,
        language=transcription_data.get("language", "zh"),
        segments=aligned_segments
    )
