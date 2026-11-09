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
        if alpha == 0:
            alpha = int(a, 16)
        else:
            orig_a = int(a, 16)
            op1 = (255 - orig_a) / 255.0
            op2 = (255 - alpha) / 255.0
            comb_op = op1 * op2
            alpha = max(0, min(255, int(round((1.0 - comb_op) * 255))))
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
    - 嚴格實作避頭尾法則 (Kinsoku Shori)：禁止標點符號 (如 。，、！？) 孤立於新列開頭
    - 單列超過 max_chars_per_col 時，優先於標點或自然詞界處換列
    """
    raw_lines = [l.strip() for l in text.replace("\r\n", "\n").split("\n") if l.strip()]
    columns: list[str] = []

    punct_no_start = set("，。！？；、：,!?;:）】』」〉》”’%‰…~～·—–―⋯-")
    punct_no_end = set("（【『「〈《“‘")
    punct_breaks = set("，。！？；、：,!?;: 　")

    for line in raw_lines:
        tokens = re.findall(r'[A-Za-z0-9]+|.', line)
        tokens = [t for t in tokens if t not in ('\r', '\n')]
        if not tokens:
            continue

        while len(tokens) > max_chars_per_col:
            # 若僅超過 1~3 個字元且結尾為標點符號 (如句號或破折號 ——)，容許留在同列，絕不孤立標點到新列
            if len(tokens) <= max_chars_per_col + 3 and tokens[-1] in punct_no_start:
                break

            # 於後半段尋找最佳標點斷點
            split_idx = max_chars_per_col
            for k in range(max_chars_per_col - 1, max(2, max_chars_per_col // 2) - 1, -1):
                if tokens[k] in punct_breaks and (k + 1 < len(tokens)) and tokens[k + 1] not in punct_no_start:
                    split_idx = k + 1
                    break

            # 避頭點檢查：禁止新列以不可開頭的標點符號起始
            while split_idx < len(tokens) and tokens[split_idx] in punct_no_start:
                split_idx += 1

            # 避尾點檢查：禁止前列以開括號等起始標點結尾
            if split_idx > 1 and tokens[split_idx - 1] in punct_no_end:
                split_idx -= 1

            if split_idx >= len(tokens):
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

    # 0. 計算透明度 (ASS alpha: 0x00 為完全不透明, 0xFF 為完全透明)
    op = getattr(style, "opacity", 1.0)
    op = max(0.0, min(1.0, float(op)))
    text_alpha = int(round((1.0 - op) * 255))
    shadow_alpha = int(round(255 - op * (255 - 128)))
    shadow_alpha = max(0, min(255, shadow_alpha))

    pri_col = hex_to_ass_color(style.primary_color, alpha=text_alpha)
    sec_col = f"&H{text_alpha:02X}0000FF&"
    out_col = hex_to_ass_color(style.outline_color, alpha=text_alpha)
    bak_col = hex_to_ass_color(style.shadow_color, alpha=shadow_alpha)

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

    # 3. ASS 字級換算：
    # 瀏覽器 CSS font-size 指的是字型 em 方框；libass (VSFilter 相容) 卻把 Fontsize 當作
    # 字型的 Win 行高 (usWinAscent + usWinDescent)。CJK 字型此比例通常為 1.3~1.45，
    # 若直接沿用數字，燒錄字面會比預覽小約 25~30%。因此依實際字型檔度量換算。
    # Outline / Shadow / Spacing / Margin 在 PlayRes = 影片解析度時即為原生像素，與 CSS 1:1。
    try:
        from .font_manager import get_font_em_ratio
        em_ratio = get_font_em_ratio(style.font_name)
    except Exception:
        em_ratio = 1.0
    css_px = float(style.font_size)
    ass_font_size = max(1.0, round(css_px * em_ratio, 2))
    ass_outline = round(style.outline_width, 1) if style.outline_enabled else 0.0
    ass_shadow = round(style.shadow_offset, 1)
    ass_spacing = round(style.letter_spacing, 1)

    # 4. 組合 ASS Style 定義行
    style_line = (
        f"Style: Default,{style.font_name},{ass_font_size:g},"
        f"{pri_col},{sec_col},{out_col},{bak_col},"
        f"{bold_val},{italic_val},0,0,100,100,{ass_spacing},0,1,"
        f"{ass_outline},{ass_shadow},"
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

    # 直式排版度量 (完全比照預覽 CSS writing-mode: vertical-rl)：
    # - 每字沿直列前進 1em (+ letter-spacing)
    # - 列與列間距 = line-height (預覽為 Tailwind leading-normal = 1.5em)
    char_step = css_px + float(style.letter_spacing or 0)
    col_pitch = css_px * 1.5
    box_pad_x = 4.0  # 預覽字幕框左右內距 (影片原生像素，前端等比縮放)
    avail_height = max(char_step, res_y - style.padding_top - style.padding_bottom)
    avail_width = max(col_pitch, res_x - style.padding_left - style.padding_right)
    max_chars_per_col = max(1, int(avail_height // max(1.0, char_step)))

    def _fmt(v: float) -> str:
        return f"{v:.1f}".rstrip("0").rstrip(".")

    for seg in track.segments:
        start_str = format_ass_timestamp(seg.start)
        end_str = format_ass_timestamp(seg.end)

        if style.orientation == "vertical":
            cols = [c for c in split_vertical_columns(seg.text, max_chars_per_col=max_chars_per_col) if c]
            if not cols:
                continue
            col_tokens = [c.split("\\N") for c in cols]
            block_w = len(cols) * col_pitch
            box_h = max(len(t) for t in col_tokens) * char_step

            # 區塊水平位置 (flex justify-content)；block_right 為文字內容右緣 (扣除字幕框內距)
            if style.pos_x is not None:
                block_right = float(style.pos_x)
            elif style.horizontal_align == "left":
                block_right = style.padding_left + box_pad_x + block_w
            elif style.horizontal_align == "center":
                block_right = style.padding_left + (avail_width + block_w) / 2.0
            else:
                block_right = res_x - style.padding_right - box_pad_x

            # 區塊垂直位置 (flex align-items)
            if style.pos_y is not None:
                box_top = float(style.pos_y)
            elif style.vertical_align == "top":
                box_top = float(style.padding_top)
            elif style.vertical_align == "middle":
                box_top = style.padding_top + (avail_height - box_h) / 2.0
            else:
                box_top = res_y - style.padding_bottom - box_h

            for col_idx, tokens in enumerate(col_tokens):
                col_len = len(tokens) * char_step
                # 列內對齊 (text-align: start / center / end)
                if style.vertical_align == "bottom":
                    col_top = box_top + (box_h - col_len)
                elif style.vertical_align == "middle":
                    col_top = box_top + (box_h - col_len) / 2.0
                else:
                    col_top = box_top
                cx = block_right - (col_idx + 0.5) * col_pitch
                for ch_idx, tok in enumerate(tokens):
                    cy = col_top + (ch_idx + 0.5) * char_step
                    event_lines.append(
                        f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,"
                        f"{{\\an5\\pos({_fmt(cx)},{_fmt(cy)})}}{tok}"
                    )
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
