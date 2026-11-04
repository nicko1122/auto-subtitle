from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field, model_validator


class WordItem(BaseModel):
    """單一詞彙/單字的時間與信心度資訊 (Word-level timestamp)"""
    word: str = Field(..., description="辨識出的字詞內容")
    start: float = Field(..., ge=0.0, description="起始時間 (秒)")
    end: float = Field(..., ge=0.0, description="結束時間 (秒)")
    probability: float = Field(default=1.0, ge=0.0, le=1.0, description="辨識信心度")


class SubtitleSegment(BaseModel):
    """單行字幕塊 (代表 Timeline 上的一個可編輯字幕段)"""
    id: int = Field(..., description="字幕序號 (從 1 開始)")
    start: float = Field(..., ge=0.0, description="字幕起點 (秒)")
    end: float = Field(..., ge=0.0, description="字幕終點 (秒)")
    text: str = Field(default="", description="字幕文字內容")
    expected_chars: Optional[int] = Field(default=None, description="根據該段聲學時長與密度預估之合理字數")
    words: List[WordItem] = Field(default_factory=list, description="構成該句的逐字時間清單")


class SubtitleTrack(BaseModel):
    """完整字幕軌道與影音中繼資訊 (前後端通訊的主要 Schema)"""
    version: str = Field(default="1.0.0", description="資料格式版本")
    source_file: str = Field(..., description="來源影音檔名或路徑")
    duration: float = Field(default=0.0, ge=0.0, description="音訊總長度 (秒)")
    language: str = Field(default="zh", description="辨識出的語言代碼 (如 zh, en, ja)")
    segments: List[SubtitleSegment] = Field(default_factory=list, description="字幕片段清單")


class SegmentationConfig(BaseModel):
    """斷句與時間軸校準設定參數"""
    max_chars: int = Field(default=16, ge=4, le=60, description="單行字幕最大字數 (中文建議 12-18)")
    pause_threshold: float = Field(default=0.45, ge=0.1, le=2.0, description="視為斷句的停頓間隔 (秒)")
    split_on_punctuation: bool = Field(default=True, description="是否依標點符號強制切分句子")
    punctuations: str = Field(default="，。！？；、,.!?;:\n", description="觸發斷句的標點符號集合")


class SubtitleLayout(BaseModel):
    """Web CSS 盒模型排版與座標佈局配置"""
    orientation: Literal["horizontal", "vertical"] = Field(
        default="horizontal",
        description="排版方向: horizontal (橫式, 左至右), vertical (直式, 上至下)"
    )
    vertical_align: Literal["top", "middle", "bottom"] = Field(
        default="bottom",
        description="垂直對齊: top (靠頂/齊頭), middle (垂直居中), bottom (靠底)"
    )
    horizontal_align: Literal["left", "center", "right"] = Field(
        default="center",
        description="水平對齊: left (靠左), center (水平居中), right (靠右)"
    )
    padding_top: int = Field(default=50, ge=0, description="頂部內距 (像素，與畫面上邊界距離)")
    padding_bottom: int = Field(default=50, ge=0, description="底部內距 (像素，與畫面下邊界距離)")
    padding_left: int = Field(default=40, ge=0, description="左側內距 (像素，與畫面左邊界距離)")
    padding_right: int = Field(default=40, ge=0, description="右側內距 (像素，與畫面右邊界距離)")

    @property
    def ass_alignment(self) -> int:
        """根據 (vertical_align, horizontal_align) 計算 ASS 標準九宮格對齊碼 (1~9)"""
        mapping = {
            ("top", "left"): 7,
            ("top", "center"): 8,
            ("top", "right"): 9,
            ("middle", "left"): 4,
            ("middle", "center"): 5,
            ("middle", "right"): 6,
            ("bottom", "left"): 1,
            ("bottom", "center"): 2,
            ("bottom", "right"): 3,
        }
        return mapping.get((self.vertical_align, self.horizontal_align), 2)


class SubtitleStyle(BaseModel):
    """字幕外觀樣式、字型排版與 Web 盒模型座標定位配置 (完整支援 CSS 語法)"""
    # 1. 字型與文字外觀
    font_name: str = Field(default="Noto Sans CJK TC", description="字型名稱 (如 Noto Sans CJK TC, Arial)")
    font_size: int = Field(default=32, ge=10, le=160, description="字型大小 (像素)")
    primary_color: str = Field(default="#FFFFFF", description="文字主體顏色 (Hex，如 #FFFFFF, #FFFF00)")
    outline_color: str = Field(default="#000000", description="文字外框描邊顏色 (Hex)")
    outline_width: float = Field(default=2.5, ge=0.0, le=15.0, description="描邊寬度 (像素)")
    shadow_offset: float = Field(default=1.2, ge=0.0, le=15.0, description="陰影偏移量 (像素)")
    shadow_color: str = Field(default="#000000", description="陰影顏色 (Hex)")
    bold: bool = Field(default=True, description="是否粗體")
    italic: bool = Field(default=False, description="是否斜體")
    letter_spacing: float = Field(default=0.0, description="字元間距 (Spacing)")

    # 2. Web 盒模型佈局 (Web CSS Box Model)
    orientation: Literal["horizontal", "vertical"] = Field(
        default="horizontal",
        description="排版方向: horizontal (橫式, 左至右), vertical (直式, 上至下)"
    )
    vertical_align: Literal["top", "middle", "bottom"] = Field(
        default="bottom",
        description="垂直對齊: top (靠頂/齊頭), middle (垂直置中), bottom (靠底)"
    )
    horizontal_align: Literal["left", "center", "right"] = Field(
        default="center",
        description="水平對齊: left (靠左), center (水平置中), right (靠右)"
    )
    padding_top: int = Field(default=50, ge=0, description="頂部內距 (像素，與畫面上邊界距離)")
    padding_bottom: int = Field(default=50, ge=0, description="底部內距 (像素，與畫面下邊界距離)")
    padding_left: int = Field(default=40, ge=0, description="左側內距 (像素，與畫面左邊界距離)")
    padding_right: int = Field(default=40, ge=0, description="右側內距 (像素，與畫面右邊界距離)")

    # 3. 精準絕對座標覆蓋 (像素值，若提供則強制釘在畫面上特定 X, Y 位置，用於進階自訂)
    pos_x: Optional[int] = Field(default=None, description="精確絕對 X 座標 (像素)")
    pos_y: Optional[int] = Field(default=None, description="精確絕對 Y 座標 (像素)")

    @property
    def ass_alignment(self) -> int:
        """根據 (vertical_align, horizontal_align) 計算 ASS 標準九宮格對齊碼 (1~9)"""
        mapping = {
            ("top", "left"): 7,
            ("top", "center"): 8,
            ("top", "right"): 9,
            ("middle", "left"): 4,
            ("middle", "center"): 5,
            ("middle", "right"): 6,
            ("bottom", "left"): 1,
            ("bottom", "center"): 2,
            ("bottom", "right"): 3,
        }
        return mapping.get((self.vertical_align, self.horizontal_align), 2)

    @classmethod
    def from_css(cls, css_text_or_path: str, **overrides) -> "SubtitleStyle":
        """從 CSS 樣式字串或檔案直接生成 SubtitleStyle 物件"""
        from ..core.css_parser import parse_css_to_style_dict
        parsed = parse_css_to_style_dict(css_text_or_path)
        parsed.update(overrides)
        return cls(**parsed)

    def to_css(self) -> str:
        """將目前 SubtitleStyle 序列化為標準 CSS 樣式字串 (供前端 UI 預覽直接使用)"""
        writing_mode = "vertical-rl" if self.orientation == "vertical" else "horizontal-tb"
        lines = [
            f"font-family: '{self.font_name}', sans-serif;",
            f"font-size: {self.font_size}px;",
            f"color: {self.primary_color};",
            f"font-weight: {'bold' if self.bold else 'normal'};",
            f"font-style: {'italic' if self.italic else 'normal'};",
            f"-webkit-text-stroke: {self.outline_width}px {self.outline_color};",
            f"text-shadow: {self.shadow_offset}px {self.shadow_offset}px {self.shadow_offset*1.5:.1f}px {self.shadow_color};",
            f"writing-mode: {writing_mode};",
            f"text-align: {self.horizontal_align};",
            f"vertical-align: {self.vertical_align};",
            f"padding: {self.padding_top}px {self.padding_right}px {self.padding_bottom}px {self.padding_left}px;",
        ]
        if self.letter_spacing > 0:
            lines.append(f"letter-spacing: {self.letter_spacing}px;")
        if self.pos_x is not None:
            lines.append(f"left: {self.pos_x}px;")
        if self.pos_y is not None:
            lines.append(f"top: {self.pos_y}px;")
        return "\n".join(lines)

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_and_shorthand(cls, data: Any):
        if not isinstance(data, dict):
            return data

        # 支援直接傳入 CSS 字串
        if "css" in data and isinstance(data["css"], str):
            from ..core.css_parser import parse_css_to_style_dict
            parsed_css = parse_css_to_style_dict(data["css"])
            for k, v in parsed_css.items():
                if k not in data or data[k] is None:
                    data[k] = v

        # 相容舊版 alignment 參數 (1~9)
        if "alignment" in data and "vertical_align" not in data and "horizontal_align" not in data:
            align = data["alignment"]
            rev_map = {
                7: ("top", "left"), 8: ("top", "center"), 9: ("top", "right"),
                4: ("middle", "left"), 5: ("middle", "center"), 6: ("middle", "right"),
                1: ("bottom", "left"), 2: ("bottom", "center"), 3: ("bottom", "right"),
            }
            if align in rev_map:
                data["vertical_align"], data["horizontal_align"] = rev_map[align]

        # 相容舊版 margin 參數
        if "margin_v" in data:
            if "padding_bottom" not in data:
                data["padding_bottom"] = data["margin_v"]
            if "padding_top" not in data:
                data["padding_top"] = data["margin_v"]
        if "margin_l" in data and "padding_left" not in data:
            data["padding_left"] = data["margin_l"]
        if "margin_r" in data and "padding_right" not in data:
            data["padding_right"] = data["margin_r"]

        # 支援 CSS padding 簡寫 (如 "50 40" 或 "40")
        if "padding" in data and isinstance(data["padding"], str):
            parts = [int(p) for p in data["padding"].split() if p.isdigit()]
            if len(parts) == 1:
                data["padding_top"] = data["padding_bottom"] = data["padding_left"] = data["padding_right"] = parts[0]
            elif len(parts) == 2:
                data["padding_top"] = data["padding_bottom"] = parts[0]
                data["padding_left"] = data["padding_right"] = parts[1]
            elif len(parts) == 4:
                data["padding_top"], data["padding_right"], data["padding_bottom"], data["padding_left"] = parts

        return data

    def set_padding(self, *args):
        """
        支援 CSS 語法的快速設定 Padding:
        - 1 個參數: all (如 set_padding(40))
        - 2 個參數: vertical, horizontal (如 set_padding(50, 40))
        - 4 個參數: top, right, bottom, left (如 set_padding(50, 40, 60, 40))
        """
        if len(args) == 1:
            val = int(args[0])
            self.padding_top = self.padding_bottom = self.padding_left = self.padding_right = val
        elif len(args) == 2:
            v_val, h_val = int(args[0]), int(args[1])
            self.padding_top = self.padding_bottom = v_val
            self.padding_left = self.padding_right = h_val
        elif len(args) == 4:
            self.padding_top = int(args[0])
            self.padding_right = int(args[1])
            self.padding_bottom = int(args[2])
            self.padding_left = int(args[3])
