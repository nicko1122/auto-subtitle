from typing import List, Optional
from pydantic import BaseModel, Field


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
    text: str = Field(..., description="字幕文字內容")
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


class SubtitleStyle(BaseModel):
    """字幕外觀樣式、座標定位與字型排版配置"""
    font_name: str = Field(default="Noto Sans CJK TC", description="字型名稱 (如 Noto Sans CJK TC, Arial)")
    font_size: int = Field(default=28, ge=10, le=120, description="字型大小 (像素/點數)")
    primary_color: str = Field(default="#FFFFFF", description="文字主體顏色 (Hex，如 #FFFFFF 或 #FFFF00)")
    outline_color: str = Field(default="#000000", description="文字外框描邊顏色 (Hex)")
    outline_width: float = Field(default=2.5, ge=0.0, le=10.0, description="描邊寬度")
    shadow_offset: float = Field(default=1.2, ge=0.0, le=10.0, description="陰影偏移量")
    shadow_color: str = Field(default="#000000", description="陰影顏色 (Hex)")
    bold: bool = Field(default=True, description="是否粗體")
    italic: bool = Field(default=False, description="是否斜體")

    # 座標定位與九宮格對齊 (ASS 標準)
    alignment: int = Field(
        default=2,
        ge=1,
        le=9,
        description="九宮格對齊代碼: 1=底左, 2=底中(最常見), 3=底右, 4=中左, 5=正中, 6=中右, 7=頂左, 8=頂中, 9=頂右"
    )
    margin_v: int = Field(default=45, ge=0, description="垂直邊距 (像素，底部或頂部距離邊緣之距離)")
    margin_l: int = Field(default=30, ge=0, description="左側邊距 (像素)")
    margin_r: int = Field(default=30, ge=0, description="右側邊距 (像素)")

    # 精準絕對座標覆蓋 (像素值，若提供則強制釘在畫面上特定 X, Y 位置)
    pos_x: Optional[int] = Field(default=None, description="精確 X 座標 (像素，如 960)")
    pos_y: Optional[int] = Field(default=None, description="精確 Y 座標 (像素，如 980)")
