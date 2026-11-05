import re
import math
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


def extract_color_and_rest(val: str) -> Tuple[Optional[str], str]:
    """
    從 CSS 複合屬性值中抽取色彩字串與剩餘內容
    支援 rgba/rgb, hex (#RGB, #RGBA, #RRGGBB, #RRGGBBAA), 以及常見命名色彩
    """
    # 1. rgba 或 rgb
    m_rgb = re.search(r'rgba?\s*\([^)]+\)', val, re.IGNORECASE)
    if m_rgb:
        color_str = m_rgb.group(0)
        rest = val[:m_rgb.start()] + " " + val[m_rgb.end():]
        return color_str, rest.strip()

    # 2. Hex 色彩
    m_hex = re.search(r'#[0-9a-fA-F]{3,8}\b', val)
    if m_hex:
        color_str = m_hex.group(0)
        rest = val[:m_hex.start()] + " " + val[m_hex.end():]
        return color_str, rest.strip()

    # 3. 命名色彩
    NAMED_COLORS = [
        "transparent", "black", "white", "red", "yellow", "gold",
        "blue", "cyan", "magenta", "green", "gray", "grey", "orange",
        "silver", "pink", "purple", "lime", "navy", "teal", "aqua"
    ]
    pattern = r'\b(' + '|'.join(NAMED_COLORS) + r')\b'
    m_named = re.search(pattern, val, re.IGNORECASE)
    if m_named:
        color_str = m_named.group(0)
        rest = val[:m_named.start()] + " " + val[m_named.end():]
        return color_str, rest.strip()

    return None, val


def parse_css_color(val: Optional[str]) -> Optional[str]:
    """將 CSS 色彩值轉換為標準 HEX 格式 (#RRGGBB)"""
    if not val:
        return None
    val = val.strip().lower()

    # Hex
    if val.startswith("#"):
        c = val.lstrip("#")
        if len(c) == 3:
            return f"#{c[0]*2}{c[1]*2}{c[2]*2}".upper()
        elif len(c) == 4:
            return f"#{c[0]*2}{c[1]*2}{c[2]*2}".upper()
        elif len(c) in (6, 8):
            return f"#{c[:6]}".upper()

    # rgb / rgba
    rgba_m = re.match(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d\.]+))?\s*\)', val)
    if rgba_m:
        r, g, b = int(rgba_m.group(1)), int(rgba_m.group(2)), int(rgba_m.group(3))
        return f"#{r:02X}{g:02X}{b:02X}"

    # 常見 CSS 命名色彩字典
    NAMED_COLORS = {
        "white": "#FFFFFF", "black": "#000000", "red": "#FF0000",
        "yellow": "#FFFF00", "gold": "#FFD700", "blue": "#0000FF",
        "cyan": "#00FFFF", "magenta": "#FF00FF", "green": "#00FF00",
        "gray": "#808080", "grey": "#808080", "orange": "#FFA500",
        "transparent": "#000000", "silver": "#C0C0C0", "pink": "#FFC0CB",
        "purple": "#800080", "lime": "#00FF00", "navy": "#000080",
        "teal": "#008080", "aqua": "#00FFFF"
    }
    return NAMED_COLORS.get(val)


def parse_length(val: str, default: float = 0.0) -> float:
    """解析 CSS 長度數值 (px, pt 等)"""
    m = re.search(r'([-+]?\d*\.?\d+)', val)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return default
    return default


def parse_css_to_style_dict(css_text_or_path: str) -> Dict[str, Any]:
    """
    解析 CSS 樣式字串或 .css 檔案路徑，映射為相容 SubtitleStyle 的欄位字典。
    支援：
      - font-size, font-family, font-weight, font-style, letter-spacing
      - color (文字主體色)
      - -webkit-text-stroke / text-stroke (描邊寬度與顏色)
      - text-shadow (陰影位移量與陰影色)
      - writing-mode (直書 vertical-rl / 橫書 horizontal-tb)
      - text-align (靠左、置中、靠右)
      - vertical-align / align-items (靠頂、置中、靠底)
      - padding / padding-top / padding-bottom / padding-left / padding-right
      - left, top (精準絕對座標)
    """
    content = css_text_or_path.strip()

    # 若傳入為現有 .css 檔案路徑，讀取其內容
    if "\n" not in content and len(content) < 260:
        try:
            p = Path(content)
            if p.exists() and p.is_file():
                content = p.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # 若包含 CSS 類別選擇器 (如 .sub { ... })，抽取括號內之屬性
    if "{" in content and "}" in content:
        match = re.search(r'\{([^}]+)\}', content)
        if match:
            content = match.group(1)

    style_dict: Dict[str, Any] = {}
    rules = [r.strip() for r in content.split(";") if r.strip()]

    for rule in rules:
        if ":" not in rule:
            continue
        prop, raw_val = rule.split(":", 1)
        prop = prop.strip().lower()
        val = raw_val.strip()

        # 1. 字型大小 font-size
        if prop == "font-size":
            sz = int(round(parse_length(val, 32.0)))
            style_dict["font_size"] = max(10, min(160, sz))

        # 2. 字型名稱 font-family
        elif prop == "font-family":
            first_font = val.split(",")[0].strip().strip("'\"")
            if first_font and first_font.lower() not in ("sans-serif", "serif", "monospace", "cursive", "fantasy"):
                style_dict["font_name"] = first_font

        # 3. 字體粗細 font-weight
        elif prop == "font-weight":
            val_lower = val.lower()
            if val_lower in ("bold", "bolder", "700", "800", "900"):
                style_dict["bold"] = True
            elif val_lower in ("normal", "lighter", "400", "300", "100"):
                style_dict["bold"] = False

        # 4. 字體樣式 font-style
        elif prop == "font-style":
            style_dict["italic"] = (val.lower() in ("italic", "oblique"))

        # 5. 字元間距 letter-spacing
        elif prop == "letter-spacing":
            style_dict["letter_spacing"] = parse_length(val, 0.0)

        # 6. 文字主體顏色 color
        elif prop == "color":
            c = parse_css_color(val)
            if c:
                style_dict["primary_color"] = c

        # 7. 文字描邊 -webkit-text-stroke 或 text-stroke (如: "2.5px #000000")
        elif prop in ("-webkit-text-stroke", "text-stroke"):
            val_clean = val.lower().strip()
            if val_clean in ("none", "0", "0px", "transparent"):
                style_dict["outline_width"] = 0.0
            else:
                color_str, rest = extract_color_and_rest(val)
                if color_str:
                    parsed_c = parse_css_color(color_str)
                    if parsed_c:
                        style_dict["outline_color"] = parsed_c

                nums = re.findall(r'[-+]?\d*\.?\d+', rest)
                if nums:
                    w = parse_length(nums[0], 2.5)
                    style_dict["outline_width"] = max(0.0, min(15.0, w))

        elif prop in ("-webkit-text-stroke-width", "text-stroke-width"):
            style_dict["outline_width"] = max(0.0, min(15.0, parse_length(val, 2.5)))

        elif prop in ("-webkit-text-stroke-color", "text-stroke-color"):
            c = parse_css_color(val)
            if c:
                style_dict["outline_color"] = c

        # 支援外側描邊語法 paint-order: stroke fill
        elif prop in ("paint-order", "-webkit-paint-order"):
            val_lower = val.lower()
            if "stroke" in val_lower and "fill" in val_lower:
                style_dict["_paint_order_stroke_fill"] = True

        # 8. 文字陰影 text-shadow (如: "2px 2px 4px rgba(0,0,0,0.8)")
        elif prop == "text-shadow":
            color_str, rest = extract_color_and_rest(val)
            if color_str:
                parsed_c = parse_css_color(color_str)
                if parsed_c:
                    style_dict["shadow_color"] = parsed_c

            nums = re.findall(r'[-+]?\d*\.?\d+', rest)
            if len(nums) >= 2:
                ox = parse_length(nums[0], 1.2)
                oy = parse_length(nums[1], 1.2)
                offset = math.hypot(ox, oy)
                style_dict["shadow_offset"] = round(offset, 1)

        # 9. 不透明度 opacity (支援 0.0~1.0 或 0%~100%)
        elif prop == "opacity":
            try:
                v_str = val.strip()
                if v_str.endswith("%"):
                    op_val = float(v_str[:-1]) / 100.0
                else:
                    op_val = float(v_str)
                style_dict["opacity"] = max(0.0, min(1.0, round(op_val, 2)))
            except (ValueError, TypeError):
                pass

        # 10. 直排/橫排 writing-mode
        elif prop == "writing-mode":
            val_lower = val.lower()
            if "vertical" in val_lower:
                style_dict["orientation"] = "vertical"
            elif "horizontal" in val_lower:
                style_dict["orientation"] = "horizontal"

        # 10. 水平對齊 text-align
        elif prop == "text-align":
            val_lower = val.lower()
            if val_lower in ("left", "start"):
                style_dict["horizontal_align"] = "left"
            elif val_lower in ("center", "middle"):
                style_dict["horizontal_align"] = "center"
            elif val_lower in ("right", "end"):
                style_dict["horizontal_align"] = "right"

        # 11. 垂直對齊 vertical-align / align-items
        elif prop in ("vertical-align", "align-items"):
            val_lower = val.lower()
            if val_lower in ("top", "start", "flex-start"):
                style_dict["vertical_align"] = "top"
            elif val_lower in ("middle", "center"):
                style_dict["vertical_align"] = "middle"
            elif val_lower in ("bottom", "end", "flex-end"):
                style_dict["vertical_align"] = "bottom"

        # 12. 邊界內距 padding (支援 1, 2, 3, 4 數值標準 CSS)
        elif prop == "padding":
            parts = re.findall(r'[-+]?\d*\.?\d+(?:px|pt)?', val)
            nums = [int(round(parse_length(p))) for p in parts]
            if len(nums) == 1:
                style_dict["padding_top"] = style_dict["padding_bottom"] = nums[0]
                style_dict["padding_left"] = style_dict["padding_right"] = nums[0]
            elif len(nums) == 2:
                style_dict["padding_top"] = style_dict["padding_bottom"] = nums[0]
                style_dict["padding_left"] = style_dict["padding_right"] = nums[1]
            elif len(nums) == 3:
                style_dict["padding_top"] = nums[0]
                style_dict["padding_left"] = style_dict["padding_right"] = nums[1]
                style_dict["padding_bottom"] = nums[2]
            elif len(nums) >= 4:
                style_dict["padding_top"] = nums[0]
                style_dict["padding_right"] = nums[1]
                style_dict["padding_bottom"] = nums[2]
                style_dict["padding_left"] = nums[3]

        elif prop == "padding-top":
            style_dict["padding_top"] = int(round(parse_length(val, 50.0)))
        elif prop == "padding-bottom":
            style_dict["padding_bottom"] = int(round(parse_length(val, 50.0)))
        elif prop == "padding-left":
            style_dict["padding_left"] = int(round(parse_length(val, 40.0)))
        elif prop == "padding-right":
            style_dict["padding_right"] = int(round(parse_length(val, 40.0)))

        # 13. 精準絕對定位 left, top
        elif prop == "left":
            style_dict["pos_x"] = int(round(parse_length(val, 0.0)))
        elif prop == "top":
            style_dict["pos_y"] = int(round(parse_length(val, 0.0)))

    if style_dict.get("_paint_order_stroke_fill") and "outline_width" in style_dict:
        # Web CSS 外擴描邊利用 paint-order 繪製 2 倍直徑，解析回 ASS 時還原為單側外擴寬度
        style_dict["outline_width"] = round(style_dict["outline_width"] / 2.0, 2)
    style_dict.pop("_paint_order_stroke_fill", None)

    return style_dict
