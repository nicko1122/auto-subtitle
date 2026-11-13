import re
from pathlib import Path
from typing import Optional
from ..schemas.subtitle import SubtitleTrack, SubtitleSegment


_PUNCT_NO_START = set("，。！？；、：,!?;:）】』」〉》”’%‰…~～·.．")
_PUNCT_NO_END = set("（【『「〈《“‘([")


def split_vertical_columns(text: str, max_chars_per_col: int = 12) -> list[str]:
    """
    將直式字幕文字切分為多列 (模擬 CSS writing-mode: vertical-rl 自動換列)：
    - 支援 <br> / <br/> / <br /> / \\N / 換行符號手動強制換列
    - 英數連續詞彙與連續半形句點 (...) 維持塊狀
    - 嚴格遵守每列最大字數上限 max_chars_per_col (絕不超出畫面高度)
    - 實作 CSS / UAX #14 避頭尾法則 (Oikomi 推入下一列)：
      - 禁止閉合/結尾標點 (如 。，、！？）】」等) 孤立於新列開頭 (連同前一字推入下一列)
      - 禁止開啟標點 (如 （【「等) 孤立於本列結尾 (推入下一列)
    """
    max_chars_per_col = max(1, int(max_chars_per_col))
    norm_text = re.sub(r'<br\s*/?>|\\N', '\n', text or "", flags=re.IGNORECASE)
    raw_lines = [l.strip() for l in norm_text.replace("\r\n", "\n").split("\n") if l.strip()]
    columns: list[str] = []

    punct_no_start = _PUNCT_NO_START
    punct_no_end = _PUNCT_NO_END

    for line in raw_lines:
        tokens = re.findall(r'\.{2,}|[A-Za-z0-9]+|.', line)
        tokens = [t for t in tokens if t not in ('\r', '\n')]
        if not tokens:
            continue

        while len(tokens) > max_chars_per_col:
            split_idx = max_chars_per_col

            # 避頭尾法則 (Oikomi)：若斷點處會使新列以禁止行首標點開頭，或使本列以禁止行尾標點結尾，
            # 則將斷點往前推 (把前一字一併推入下一列)，確保單列絕不超過 max_chars_per_col。
            while split_idx > 1 and (
                tokens[split_idx] in punct_no_start
                or (tokens[split_idx].startswith(".") and len(tokens[split_idx]) >= 2)
                or tokens[split_idx - 1] in punct_no_end
            ):
                split_idx -= 1

            if split_idx <= 0:
                split_idx = max_chars_per_col

            col_tokens = [t for t in tokens[:split_idx] if t.strip()]
            if col_tokens:
                columns.append("\\N".join(col_tokens))
            tokens = tokens[split_idx:]

        rem_tokens = [t for t in tokens if t.strip()]
        if rem_tokens:
            columns.append("\\N".join(rem_tokens))

    return columns if columns else [""]


def format_timestamp(seconds: float, decimal_separator: str = ",") -> str:
    """
    將秒數轉為字幕標準格式 (00:00:00,000 或 00:00:00.000)
    :param seconds: 浮點數秒數
    :param decimal_separator: 毫秒分隔符號 (SRT 用 ',', VTT 用 '.')
    """
    if seconds < 0:
        seconds = 0.0

    total_seconds = int(seconds)
    millis = int(round((seconds - total_seconds) * 1000))
    if millis >= 1000:
        total_seconds += 1
        millis = 0

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}{decimal_separator}{millis:03d}"


def _normalize_cue_text(text: str) -> str:
    """將字幕中的 <br> / <br/> / \\N 正規化為純換行符號。"""
    s = re.sub(r'<br\s*/?>|\\N', '\n', text or "", flags=re.IGNORECASE)
    return s.replace("\r\n", "\n")


def to_srt(track: SubtitleTrack) -> str:
    """將 SubtitleTrack 轉成標準 SRT 格式字串 (支援 <br> 轉換為換行)"""
    lines = []
    for seg in track.segments:
        start_str = format_timestamp(seg.start, decimal_separator=",")
        end_str = format_timestamp(seg.end, decimal_separator=",")
        clean_text = _normalize_cue_text(seg.text)
        lines.append(str(seg.id))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(clean_text)
        lines.append("")  # 空行分隔
    return "\n".join(lines)


def to_vtt(track: SubtitleTrack) -> str:
    """將 SubtitleTrack 轉成 WebVTT 格式字串 (支援 <br> 轉換為換行)"""
    lines = ["WEBVTT", ""]
    for seg in track.segments:
        start_str = format_timestamp(seg.start, decimal_separator=".")
        end_str = format_timestamp(seg.end, decimal_separator=".")
        clean_text = _normalize_cue_text(seg.text)
        lines.append(str(seg.id))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(clean_text)
        lines.append("")
    return "\n".join(lines)


def to_openshot(track: SubtitleTrack) -> str:
    """將 SubtitleTrack 轉成 OpenShot Caption 格式 (無序號、無空行連續時間軸與文字)"""
    lines = []
    for seg in track.segments:
        text_lines = [line for line in _normalize_cue_text(seg.text).splitlines() if line.strip()]
        if not text_lines:
            continue
        start_str = format_timestamp(seg.start, decimal_separator=",")
        end_str = format_timestamp(seg.end, decimal_separator=",")
        lines.append(f"{start_str} --> {end_str}")
        lines.extend(text_lines)
    return ("\n".join(lines) + "\n") if lines else ""


def to_json(track: SubtitleTrack, indent: int = 2) -> str:
    """將 SubtitleTrack 序列化為格式化的 JSON 字串"""
    return track.model_dump_json(indent=indent)


def parse_srt_content(content: str, source_file: str = "manual", strict: bool = False) -> SubtitleTrack:
    """解析 SRT 與 WebVTT，保留多行文字並支援省略小時的 VTT 時間戳。"""
    lines = content.lstrip("\ufeff").replace("\r\n", "\n").splitlines()
    timestamp = r"(?:\d+:)?\d{2}:\d{2}[,.]\d+"
    timing = re.compile(rf"^({timestamp})\s*-->\s*({timestamp})(?:\s+.*)?$")

    def parse_t(value):
        parts = value.replace(",", ".").split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])

    segments = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in ("STYLE", "REGION", "NOTE") or line.startswith("NOTE "):
            while i < len(lines) and lines[i].strip():
                i += 1
            continue
        match = timing.fullmatch(line)
        if not match:
            if strict and line and not line.startswith("WEBVTT") and not (i + 1 < len(lines) and timing.fullmatch(lines[i + 1].strip())):
                raise ValueError(f"字幕第 {i + 1} 行格式無法解析")
            i += 1
            continue
        seg_id = int(lines[i - 1]) if i > 0 and lines[i - 1].strip().isdigit() else len(segments) + 1
        i += 1
        text = []
        while i < len(lines) and lines[i].strip() and not timing.fullmatch(lines[i].strip()):
            if strict and "-->" in lines[i]:
                raise ValueError(f"字幕第 {i + 1} 行時間格式無法解析")
            if lines[i].strip().isdigit() and i + 1 < len(lines) and timing.fullmatch(lines[i + 1].strip()):
                break
            text.append(lines[i])
            i += 1
        start, end = parse_t(match[1]), parse_t(match[2])
        if strict and start >= end:
            raise ValueError(f"字幕第 {seg_id} 段結束時間必須晚於開始")
        segments.append(SubtitleSegment(id=seg_id, start=start, end=end, text="\n".join(text).strip()))

    duration = max((s.end for s in segments), default=0.0)
    return SubtitleTrack(source_file=source_file, duration=duration, segments=segments)



def save_file(content: str, output_path: str, encoding: str = "utf-8") -> str:
    """儲存字幕內容至檔案"""
    p = Path(output_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)
    return str(p)
