import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .env_utils import preload_cuda_libs, release_gpu_memory

preload_cuda_libs()

from llama_cpp import Llama
from ..schemas.subtitle import SubtitleTrack, SubtitleSegment
from .download_model import ensure_llm_model

logger = logging.getLogger(__name__)

BATCH_SYSTEM_PROMPT = """你是一位繁體中文影音字幕校對專家。
任務：修正由語音辨識（ASR）產生的字幕清單中的錯別字（特別是中文同音字與口語誤聽）。

規則：
1. 嚴格保持與輸入相同的 id，不要增減或合併 id。
2. 將同音錯字（如「開平洋」改為「太平洋」、「沒高冬」改為「沒搞懂」）修復為上下文通順的正確用字。
3. 輸出繁體中文，並補上逗號或句號等標點符號。
4. 必須以 JSON 格式回傳，格式範例如下：
{
  "results": [
    {"id": 1, "text": "牆上的時鐘它，滴答滴答。你和我沙發上，"},
    {"id": 2, "text": "兩端晃啊晃。像是隔著太平洋，想不想啊。"}
  ]
}"""


class SubtitleProofreader:
    """基於 Edge 本地端 LLM (Qwen2.5) 的字幕智慧校對器"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_gpu_layers: int = -1,
        n_ctx: int = 4096
    ):
        preload_cuda_libs()
        if model_path is None or not Path(model_path).exists():
            model_path = ensure_llm_model()

        logger.info(f"正在載入 Edge LLM 校對模型: {model_path} (GPU layers: {n_gpu_layers})...")
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False
        )

    def proofread_segments_batch(self, segments: List[SubtitleSegment]) -> Dict[int, str]:
        """批次校對一組字幕片段，回傳 id -> corrected_text 對應表"""
        if not segments:
            return {}

        prompt_lines = [f"[{s.id}] {s.text}" for s in segments]
        user_input = "請校對以下字幕片段：\n" + "\n".join(prompt_lines)

        try:
            res = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": BATCH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2048
            )
            raw_json = res["choices"][0]["message"]["content"]
            data = json.loads(raw_json)
            result_map: Dict[int, str] = {}

            # 彈性解析各種 LLM 常見的 JSON 結構變體
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list):
                    items = data["results"]
                elif "subtitles" in data and isinstance(data["subtitles"], list):
                    items = data["subtitles"]
                else:
                    for k, v in data.items():
                        if str(k).isdigit() and isinstance(v, str):
                            result_map[int(k)] = v.strip()
                        elif isinstance(v, dict):
                            items.append(v)

            for item in items:
                if isinstance(item, dict):
                    i_id = item.get("id") if "id" in item else item.get("index")
                    i_text = (
                        item.get("text")
                        or item.get("corrected_text")
                        or item.get("content")
                        or item.get("subtitle")
                    )
                    if i_id is not None and i_text is not None:
                        try:
                            result_map[int(i_id)] = str(i_text).strip()
                        except (ValueError, TypeError):
                            pass

            return result_map
        except Exception as e:
            logger.warning(f"批次校對處理異常: {e}，保留原始字幕文字")
            return {s.id: s.text for s in segments}

    def proofread_track(
        self,
        track: SubtitleTrack,
        batch_size: int = 10,
        progress_callback: Optional[callable] = None
    ) -> SubtitleTrack:
        """
        對完整 SubtitleTrack 進行分批校對，保持原始時間軸起訖點，替換文字內容
        """
        all_segments = track.segments
        new_segments: List[SubtitleSegment] = []

        total_batches = (len(all_segments) + batch_size - 1) // batch_size
        logger.info(f"開始校對字幕軌，共 {len(all_segments)} 句，分 {total_batches} 批處理...")

        for i in range(0, len(all_segments), batch_size):
            batch = all_segments[i:i + batch_size]
            corrected_map = self.proofread_segments_batch(batch)

            for seg in batch:
                corr_text = corrected_map.get(seg.id, seg.text)
                new_seg = SubtitleSegment(
                    id=seg.id,
                    start=seg.start,
                    end=seg.end,
                    text=corr_text,
                    words=seg.words
                )
                new_segments.append(new_seg)

            if progress_callback:
                progress_callback(min(i + batch_size, len(all_segments)), len(all_segments))

        return SubtitleTrack(
            version=track.version,
            source_file=track.source_file,
            duration=track.duration,
            language=track.language,
            segments=new_segments
        )

    def close(self) -> None:
        """關閉並釋放 Llama 模型顯存"""
        if hasattr(self, "llm") and self.llm is not None:
            try:
                self.llm.close()
            except Exception:
                pass
            self.llm = None
        release_gpu_memory()
