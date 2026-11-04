import re
from pathlib import Path
from typing import Optional
from ..schemas.subtitle import SubtitleTrack, SubtitleSegment, SubtitleStyle


def hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    """將 Hex 顏色 (#RRGGBB 或 #RRGGBBAA) 轉換為 ASS 格式 (&H[AA]BBGGRR&)"""
    c = hex_color.lstrip("#")
    if len(c) == 6:
        r, g, b = c[0:2], c[2:4], c[4:6]
    elif len(c) == 8:
        r, g, b, a = c[0:2], c[2:4], c[4:6], c[6:8]
        alpha = int(a, 16)
    else:
        r, g, b = "FF", "FF", "FF"
    return f"&H{alpha:02X}{b}{g}{r}&"


def format_ass_timestamp(seconds: float) -> str:
    """將秒數轉為 ASS 標準時間戳 (0:00:00.00，小數點兩位)"""
    if seconds < 0:
        seconds = 0.0

    total_seconds = int(seconds)
    centis = int(round((seconds - total_seconds) * 100))
    if centis >= 100:
        total_seconds += 1
        centis = 0

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def split_vertical_columns(text: str, max_chars_per_col: int = 12) -> list[str]:
    """
    將直式字幕文字切分為多列 (模擬 CSS writing-mode: vertical-rl 自動換列)：
    - 英數連續詞彙維持塊狀 (Tate-chu-yoko 縱中橫)
    - 單列超過 max_chars_per_col 時，優先於標點或空白處換至下一列
    """
    raw_lines = [l.strip() for l in text.replace("\r\n", "\n").split("\n") if l.strip()]
    columns: list[str] = []

    punct_breaks = set("，。！？；、,.!?;: 　")

    for line in raw_lines:
        tokens = re.findall(r'[A-Za-z0-9]+|.', line)
        tokens = [t for t in tokens if t not in ('\r', '\n')]
        if not tokens:
            continue

        while len(tokens) > max_chars_per_col:
            # 尋找最佳斷點 (在 max_chars_per_col 附近尋找標點符號)
            split_idx = max_chars_per_col
            for k in range(max_chars_per_col - 1, max(2, max_chars_per_col // 2) - 1, -1):
                if tokens[k] in punct_breaks:
                    split_idx = k + 1
                    break
            col_tokens = [t for t in tokens[:split_idx] if t.strip()]
            if col_tokens:
                columns.append("\\N".join(col_tokens))
            tokens = tokens[split_idx:]

        rem_tokens = [t for t in tokens if t.strip()]
        if rem_tokens:
            columns.append("\\N".join(rem_tokens))

    return columns if columns else [""]


def format_text_for_layout(text: str, orientation: str = "horizontal", max_chars_per_col: int = 12) -> str:
    """
    根據排版方向格式化單列字幕文字內容：
    - horizontal: 橫排文字，保留或轉為 ASS 的 \\N 換行
    - vertical: 直排文字，英數連續詞彙維持塊狀，中文字元垂直堆疊
    """
    if orientation != "vertical":
        return text.replace("\r\n", "\\N").replace("\n", "\\N")

    cols = split_vertical_columns(text, max_chars_per_col=max_chars_per_col)
    return cols[0] if cols else ""


def to_ass(
    track: SubtitleTrack,
    style: Optional[SubtitleStyle] = None,
    res_x: int = 1920,
    res_y: int = 1080
) -> str:
    """
    將 SubtitleTrack 轉換為支援 Web Box Model (Padding、九宮格對齊、直排/橫排) 的 ASS 格式
    """
    if style is None:
        style = SubtitleStyle()

    pri_col = hex_to_ass_color(style.primary_color)
    sec_col = "&H000000FF&"
    out_col = hex_to_ass_color(style.outline_color)
    bak_col = hex_to_ass_color(style.shadow_color, alpha=128)

    bold_val = -1 if style.bold else 0
    italic_val = -1 if style.italic else 0

    # 1. 計算九宮格對齊碼 (1~9)
    alignment = style.ass_alignment

    # 2. 計算與畫面邊界的內距 (Padding -> Margin)
    if style.vertical_align == "top":
        margin_v = style.padding_top
    elif style.vertical_align == "bottom":
        margin_v = style.padding_bottom
    else:
        margin_v = max(style.padding_top, style.padding_bottom)

    margin_l = style.padding_left
    margin_r = style.padding_right

    # 3. 組合 ASS Style 定義行
    style_line = (
        f"Style: Default,{style.font_name},{style.font_size},"
        f"{pri_col},{sec_col},{out_col},{bak_col},"
        f"{bold_val},{italic_val},0,0,100,100,{style.letter_spacing},0,1,"
        f"{style.outline_width},{style.shadow_offset},"
        f"{alignment},{margin_l},{margin_r},{margin_v},1"
    )

    header = f"""[Script Info]
Title: Auto Subtitle Burn-in
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {res_x}
PlayResY: {res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

    event_lines = [header]

    # 計算直式排版時，單列可容納的最大字數與列間距
    avail_height = max(180, res_y - style.padding_top - style.padding_bottom)
    char_step = max(12, int(style.font_size * 1.18))
    max_chars_per_col = max(4, avail_height // char_step)
    col_spacing = int(style.font_size * 1.45)

    for seg in track.segments:
        start_str = format_ass_timestamp(seg.start)
        end_str = format_ass_timestamp(seg.end)

        if style.orientation == "vertical":
            cols = split_vertical_columns(seg.text, max_chars_per_col=max_chars_per_col)
            for col_idx, col_text in enumerate(cols):
                if style.pos_x is not None and style.pos_y is not None:
                    # 精準座標模式下，每多一列往左偏移 col_spacing
                    cx = max(0, style.pos_x - col_idx * col_spacing)
                    text_field = f"{{\\pos({cx},{style.pos_y})}}{col_text}"
                    event_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text_field}")
                else:
                    # 盒模型邊距模式下，根據對齊方向偏移 MarginR 或 MarginL (模擬 vertical-rl 右至左換列)
                    if style.horizontal_align == "left":
                        ml = margin_l + col_idx * col_spacing
                        mr = margin_r
                    else:
                        ml = margin_l
                        mr = margin_r + col_idx * col_spacing
                    event_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,{ml},{mr},{margin_v},,{col_text}")
        else:
            formatted_text = format_text_for_layout(seg.text, orientation="horizontal")
            if style.pos_x is not None and style.pos_y is not None:
                text_field = f"{{\\pos({style.pos_x},{style.pos_y})}}{formatted_text}"
            else:
                text_field = formatted_text
            event_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text_field}")

    return "\n".join(event_lines) + "\n"


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


def to_srt(track: SubtitleTrack) -> str:
    """將 SubtitleTrack 轉成標準 SRT 格式字串"""
    lines = []
    for seg in track.segments:
        start_str = format_timestamp(seg.start, decimal_separator=",")
        end_str = format_timestamp(seg.end, decimal_separator=",")
        lines.append(str(seg.id))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(seg.text)
        lines.append("")  # 空行分隔
    return "\n".join(lines)


def to_vtt(track: SubtitleTrack) -> str:
    """將 SubtitleTrack 轉成 WebVTT 格式字串"""
    lines = ["WEBVTT", ""]
    for seg in track.segments:
        start_str = format_timestamp(seg.start, decimal_separator=".")
        end_str = format_timestamp(seg.end, decimal_separator=".")
        lines.append(str(seg.id))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(seg.text)
        lines.append("")
    return "\n".join(lines)


def to_json(track: SubtitleTrack, indent: int = 2) -> str:
    """將 SubtitleTrack 序列化為格式化的 JSON 字串"""
    return track.model_dump_json(indent=indent)


def parse_srt_content(content: str, source_file: str = "manual") -> SubtitleTrack:
    """
    強健解析 SRT 字串為 SubtitleTrack 物件
    自動處理 UTF-8 BOM、CRLF/LF 換行與多行字幕
    """
    content = content.lstrip("\ufeff").strip()
    blocks = re.split(r'\r?\n\s*\r?\n', content)
    segments = []

    for idx, b in enumerate(blocks, start=1):
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        if not lines:
            continue

        time_line_idx = -1
        seg_id = idx
        for i, line in enumerate(lines[:3]):
            if "-->" in line:
                time_line_idx = i
                break

        if time_line_idx == -1:
            continue

        if time_line_idx > 0 and lines[0].isdigit():
            seg_id = int(lines[0])

        time_match = re.search(r'(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)', lines[time_line_idx])
        if not time_match:
            continue

        def parse_t(t_str: str) -> float:
            t_str = t_str.replace(",", ".")
            parts = t_str.split(":")
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

        start_sec = parse_t(time_match.group(1))
        end_sec = parse_t(time_match.group(2))
        text = " ".join(lines[time_line_idx + 1:])
        segments.append(SubtitleSegment(id=seg_id, start=start_sec, end=end_sec, text=text))

    duration = segments[-1].end if segments else 0.0
    return SubtitleTrack(source_file=source_file, duration=duration, segments=segments)


def save_file(content: str, output_path: str, encoding: str = "utf-8") -> str:
    """儲存字幕內容至檔案"""
    p = Path(output_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding=encoding)
    return str(p)
