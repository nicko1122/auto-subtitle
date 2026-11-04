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
