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


_SIDEWAYS_CHARS = set("—–―…⋯～~-－ー（）()「」『』【】《》〈〉〔〕［］｛｝:;")
_PUNCT_NO_START = set("，。！？；、：,!?;:）】』」〉》”’%‰…~～·.．")
_PUNCT_NO_END = set("（【『「〈《“‘([")


def _fallback_ascii_ratio(ch: str) -> float:
    if ch == " ":
        return 0.25
    if ch in "ilI1!.,:;|'\"`":
        return 0.28
    if ch in "mwMW@":
        return 0.78
    if ch.isupper():
        return 0.62
    return 0.52


def _measure_ascii_advance(
    text: str, css_px: float, letter_spacing: float, char_adv: dict[str, float]
) -> float:
    total = 0.0
    for ch in text:
        ratio = char_adv.get(ch)
        if ratio is None:
            ratio = _fallback_ascii_ratio(ch)
        total += ratio * css_px + letter_spacing
    return max(1.0, total)


def _layout_vertical_columns(
    text: str,
    css_px: float,
    letter_spacing: float,
    avail_height: float,
    char_adv: dict[str, float],
) -> list[list[tuple[str, str, float]]]:
    """
    將字幕文字精確排版為直式欄位列表 (1:1 模擬 CSS writing-mode: vertical-rl, text-orientation: mixed)：
    - 中日韓全形字元直立堆疊，每字步進 char_step = css_px + letter_spacing
    - 連續 ASCII 英數與空白依字型實際寬度換算為垂直步進並順時針旋轉 90 度 (\\frz-90)
    - 嚴格遵守可用高度 avail_height，並實作避頭尾法則 (Oikomi)
    回傳每欄的 item 列表：[(text, kind, height), ...]，kind 為 "cjk" | "ascii" | "space"
    """
    norm_text = re.sub(r'<br\s*/?>|\\N', '\n', text or "", flags=re.IGNORECASE)
    raw_lines = [l.strip() for l in norm_text.replace("\r\n", "\n").split("\n") if l.strip()]
    if not raw_lines:
        return []

    char_step = css_px + letter_spacing
    columns: list[list[tuple[str, str, float]]] = []

    def _is_ascii_printable(ch: str) -> bool:
        o = ord(ch)
        return 0x21 <= o <= 0x7E

    for line in raw_lines:
        # 切分為字元 / 空白 / ASCII 單詞 token
        tokens: list[tuple[str, str, float]] = []
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            if ch in ("\r", "\n"):
                i += 1
                continue
            if ch in (" ", "\t"):
                j = i + 1
                while j < n and line[j] in (" ", "\t"):
                    j += 1
                # 多個連續半形空白折算為一個空白 (同 CSS white-space: pre-wrap 單空白寬)
                sp_text = line[i:j]
                sp_h = _measure_ascii_advance(sp_text, css_px, letter_spacing, char_adv)
                tokens.append((sp_text, "space", sp_h))
                i = j
            elif ch == "\u3000":
                tokens.append((ch, "space", char_step))
                i += 1
            elif _is_ascii_printable(ch):
                j = i + 1
                while j < n and _is_ascii_printable(line[j]):
                    j += 1
                word = line[i:j]
                w_h = _measure_ascii_advance(word, css_px, letter_spacing, char_adv)
                tokens.append((word, "ascii", w_h))
                i = j
            else:
                tokens.append((ch, "cjk", char_step))
                i += 1

        if not tokens:
            continue

        # 依 avail_height 換欄 + 避頭尾法則
        cur_col: list[tuple[str, str, float]] = []
        cur_h = 0.0

        def _flush_col(col: list[tuple[str, str, float]]):
            while col and col[-1][1] == "space":
                col.pop()
            if col:
                columns.append(col)

        for tok in tokens:
            t_text, t_kind, t_h = tok
            if t_kind == "space" and not cur_col:
                continue  # 欄首忽略前導空白

            if cur_col and t_kind != "space" and (cur_h + t_h > avail_height + 0.5):
                # 需要換欄！檢查避頭尾 (Oikomi)
                pulled: list[tuple[str, str, float]] = []
                is_no_start = (t_text in _PUNCT_NO_START) or (t_text.startswith(".") and len(t_text) >= 2)
                # 剝除欄尾空白再檢查最後一個實質字元
                while cur_col and cur_col[-1][1] == "space":
                    cur_col.pop()
                if is_no_start and len(cur_col) >= 2:
                    pulled.append(cur_col.pop())
                elif cur_col and len(cur_col) >= 2 and cur_col[-1][0] in _PUNCT_NO_END:
                    pulled.append(cur_col.pop())

                _flush_col(cur_col)
                cur_col = list(reversed(pulled))
                cur_h = sum(item[2] for item in cur_col)

                cur_col.append(tok)
                cur_h += t_h
            else:
                cur_col.append(tok)
                cur_h += t_h

        _flush_col(cur_col)

    # 將同一欄中相鄰的 ascii / space 合併為單一橫向旋轉字串，確保英文字距與空白 100% 原生連貫
    merged_columns: list[list[tuple[str, str, float]]] = []
    for col in columns:
        merged: list[tuple[str, str, float]] = []
        for t_text, t_kind, t_h in col:
            if t_kind == "ascii":
                if merged and merged[-1][1] == "ascii":
                    prev_t, _, prev_h = merged[-1]
                    merged[-1] = (prev_t + t_text, "ascii", prev_h + t_h)
                elif len(merged) >= 2 and merged[-1][1] == "space" and merged[-2][1] == "ascii":
                    sp_t, _, sp_h = merged.pop()
                    prev_t, _, prev_h = merged[-1]
                    merged[-1] = (prev_t + sp_t + t_text, "ascii", prev_h + sp_h + t_h)
                else:
                    merged.append((t_text, t_kind, t_h))
            else:
                merged.append((t_text, t_kind, t_h))
        while merged and merged[-1][1] == "space":
            merged.pop()
        if merged:
            merged_columns.append(merged)

    return merged_columns


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


def format_text_for_layout(text: str, orientation: str = "horizontal", max_chars_per_col: int = 12) -> str:
    """
    根據排版方向格式化單列字幕文字內容：
    - horizontal: 橫排文字，保留或轉為 ASS 的 \\N 換行 (支援 <br>)
    - vertical: 直排文字，英數連續詞彙維持塊狀，中文字元垂直堆疊 (支援 <br>)
    """
    norm_text = re.sub(r'<br\s*/?>', '\n', text or "", flags=re.IGNORECASE)
    if orientation != "vertical":
        return norm_text.replace("\r\n", "\\N").replace("\n", "\\N")

    cols = split_vertical_columns(norm_text, max_chars_per_col=max_chars_per_col)
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

    # 3. ASS 字級換算與字元寬度解析：
    # 瀏覽器 CSS font-size 指的是字型 em 方框；libass (VSFilter 相容) 卻把 Fontsize 當作
    # 字型的 Win 行高 (usWinAscent + usWinDescent)。CJK 字型此比例通常為 1.3~1.45，
    # 若直接沿用數字，燒錄字面會比預覽小約 25~30%。因此依實際字型檔度量換算。
    # Outline / Shadow / Spacing / Margin 在 PlayRes = 影片解析度時即為原生像素，與 CSS 1:1。
    try:
        from .font_manager import get_font_em_ratio, get_font_char_advances
        em_ratio = get_font_em_ratio(style.font_name)
        char_adv = get_font_char_advances(style.font_name)
    except Exception:
        em_ratio = 1.0
        char_adv = {}
    css_px = float(style.font_size)
    ass_font_size = max(1.0, round(css_px * em_ratio, 2))
    ass_outline = round(style.outline_width, 1) if style.outline_enabled else 0.0
    ass_shadow = round(style.shadow_offset, 1)
    ass_spacing = round(style.letter_spacing, 1)

    # 橫式模式下防呆：避免切換自直式時殘留過大的左右邊距把橫排文字擠成窄條
    if style.orientation != "vertical":
        min_text_w = max(css_px * 3.0, res_x * 0.25)
        if margin_l + margin_r > res_x - min_text_w:
            avail_margin = max(0.0, res_x - min_text_w)
            scale_m = avail_margin / max(1.0, float(margin_l + margin_r))
            margin_l = int(round(margin_l * scale_m))
            margin_r = int(round(margin_r * scale_m))

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

    def _fmt(v: float) -> str:
        return f"{v:.1f}".rstrip("0").rstrip(".")

    for seg in track.segments:
        start_str = format_ass_timestamp(seg.start)
        end_str = format_ass_timestamp(seg.end)

        if style.orientation == "vertical":
            cols = _layout_vertical_columns(
                seg.text,
                css_px=css_px,
                letter_spacing=float(style.letter_spacing or 0),
                avail_height=avail_height,
                char_adv=char_adv,
            )
            if not cols:
                continue
            block_w = len(cols) * col_pitch
            col_heights = [sum(item[2] for item in col) for col in cols]
            box_h = max(col_heights)

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

            for col_idx, col_items in enumerate(cols):
                col_len = col_heights[col_idx]
                # 列內對齊 (text-align: start / center / end)
                if style.vertical_align == "bottom":
                    cur_y = box_top + (box_h - col_len)
                elif style.vertical_align == "middle":
                    cur_y = box_top + (box_h - col_len) / 2.0
                else:
                    cur_y = box_top
                cx = block_right - (col_idx + 0.5) * col_pitch
                for tok, kind, h_px in col_items:
                    if kind == "space":
                        cur_y += h_px
                        continue
                    cy = cur_y + h_px * 0.5
                    if kind == "ascii":
                        rot = "\\frz-90"
                    else:
                        rot = "\\frz-90" if (tok in _SIDEWAYS_CHARS or (tok.startswith(".") and len(tok) >= 2)) else ""
                    event_lines.append(
                        f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,"
                        f"{{\\an5\\pos({_fmt(cx)},{_fmt(cy)}){rot}}}{tok}"
                    )
                    cur_y += h_px
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
