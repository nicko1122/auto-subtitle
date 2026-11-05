"""Recover the performed lyric sequence from ASR using reusable reference phrases."""
import difflib
import math
import re

from opencc import OpenCC
from pypinyin import lazy_pinyin


def build_lyric_occurrences(lines, segments):
    converter = OpenCC("t2s")

    def normalize(text):
        return "".join(char for char in converter.convert(text).casefold() if char.isalnum())

    def pronunciation(text):
        return lazy_pinyin(text, errors=lambda value: list(value))

    phrases = {}
    for line_id, line in enumerate(lines, 1):
        parts = [line, *re.findall(r".+?(?:——|[，,。.!！？?；;：:]+|$)", line)]
        for text in parts:
            key = normalize(text)
            if len(key) < 2:
                continue
            if key not in phrases:
                phrases[key] = {"text": text.strip(), "source_line_id": line_id}

    words, segment_ids, chars = [], [], []
    word_starts, word_ends = {}, {}
    for segment_id, segment in enumerate(segments):
        anchors = segment.get("words") or ([{"word": segment["text"], "start": segment["start"], "end": segment["end"], "segment_only": True}] if segment.get("text", "").strip() else [])
        for word in anchors:
            index = len(words)
            words.append(word)
            segment_ids.append(segment_id)
            text = normalize(word["word"])
            if text:
                word_starts[len(chars)] = index
                chars.extend(text)
                word_ends[len(chars)] = index + 1
    spoken = "".join(chars)
    spoken_pinyin = pronunciation(spoken)
    candidates = [[] for _ in range(len(words) + 1)]
    for key, phrase in phrases.items():
        n, m = len(key), len(chars)
        phones = pronunciation(key)
        # A free ASR prefix lets each reference phrase match every performance.
        previous = [0.0] * (m + 1)
        back = [bytearray(m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            back[i][0] = 1

        def cost(i, j):
            if key[i] == chars[j]:
                return 0.0
            if phones[i] == spoken_pinyin[j]:
                return .2
            return .65 if difflib.SequenceMatcher(None, phones[i], spoken_pinyin[j]).ratio() >= .65 else 1.15

        for i in range(1, n + 1):
            current = [i * 1.15] + [0.0] * m
            for j in range(1, m + 1):
                choices = (previous[j - 1] + cost(i - 1, j - 1), previous[j] + 1.15, current[j - 1] + 1.15)
                action = min(range(3), key=choices.__getitem__)
                current[j], back[i][j] = choices[action], action
            previous = current
        limit = n * (.2 if n <= 3 else .35)
        for end in word_ends:
            distance = previous[end]
            if distance > limit + 1e-9:
                continue
            i, j, matched = n, end, 0
            while i:
                action = back[i][j]
                if j and action == 0:
                    matched += cost(i - 1, j - 1) <= .65
                    i, j = i - 1, j - 1
                elif action == 1 or not j:
                    i -= 1
                else:
                    j -= 1
            if j not in word_starts or matched < math.ceil(n * .7):
                continue
            if not n * .65 <= end - j <= n * 1.35:
                continue
            score = end - j - 2 * distance
            if score <= 0:
                continue
            first, last = word_starts[j], word_ends[end]
            candidates[last].append({**phrase, "word_start": first, "word_end": last, "matched_characters": matched, "original_characters": n, "match_cost": round(distance, 3), "score": score})

    # Select non-overlapping word windows; prefer complete lines over tied fragments.
    best = [(0.0, 0)] * (len(words) + 1)
    links = [None] * (len(words) + 1)
    for end in range(1, len(words) + 1):
        best[end] = best[end - 1]
        links[end] = (end - 1, None)
        for candidate in candidates[end]:
            start = candidate["word_start"]
            value = (best[start][0] + candidate["score"], best[start][1] - 1)
            if value > best[end]:
                best[end], links[end] = value, (start, candidate)
    selected = []
    end = len(words)
    while end:
        start, candidate = links[end]
        if candidate is not None:
            selected.append(candidate)
        end = start
    selected.reverse()

    occurrences = []

    def append_unknown(first, last):
        while first < last:
            end = first + 1
            while end < last and segment_ids[end] == segment_ids[first]:
                end += 1
            text = "".join(word["word"] for word in words[first:end]).strip()
            if text:
                occurrences.append({"text": text, "source_line_id": None, "word_start": first, "word_end": end, "words": words[first:end], "matched_characters": 0, "original_characters": len(normalize(text)), "match_cost": None})
            first = end

    cursor = 0
    for candidate in selected:
        append_unknown(cursor, candidate["word_start"])
        candidate.pop("score")
        occurrences.append({**candidate, "words": words[candidate["word_start"]:candidate["word_end"]]})
        cursor = candidate["word_end"]
    append_unknown(cursor, len(words))
    counts = {}
    for occurrence in occurrences:
        text = occurrence["text"]
        counts[text] = counts.get(text, 0) + 1
        occurrence["occurrence"] = counts[text]
    return occurrences
