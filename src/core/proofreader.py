import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..schemas.subtitle import SubtitleTrack, SubtitleSegment
from .env_utils import preload_cuda_libs, release_gpu_memory

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

BATCH_SYSTEM_PROMPT = """你是一位繁體中文影音字幕校對專家。
任務：修正由語音辨識（ASR）產生的字幕清單中的錯別字（特別是中文同音字與口語誤聽）。

規則：
1. 嚴格保持與輸入相同的 id，不要增減或合併 id。
2. 將同音錯字（如「開平洋」改為「太平洋」、「沒高冬」改為「沒搞懂」）修復為上下文通順的正確用字。
3. 輸出繁體中文，並補上適當標點符號。
4. 必須以純 JSON 格式回傳（不要包含 Markdown 語法以外的多餘說明），格式範例如下：
{
  "results": [
    {"id": 1, "text": "牆上的時鐘它，滴答滴答。你和我沙發上，"},
    {"id": 2, "text": "兩端晃啊晃。像是隔著太平洋，想不想啊。"}
  ]
}"""

BATCH_SYSTEM_PROMPT_WITH_SCRIPT = """你是一位繁體中文影音字幕與歌詞校對專家。
任務：參考使用者提供的【參考原稿/歌詞】，修正由語音辨識（ASR）產生的字幕清單中的錯別字、聽錯詞與同音字。

規則：
1. 嚴格保持與輸入相同的 id，不要增減或合併 id。
2. 仔細比對【參考原稿/歌詞】，將聽錯的同音字（如「開平洋」改為「太平洋」、「挨著洞」改為「愛也結冰」）修正為原稿中的正確詞彙。
3. 若歌曲有反覆唱誦（如副歌重複），請參照原稿中對應的歌詞進行修復。
4. 若有歌手即興感嘆詞（如「Yeah」、「Woo」）未列在原稿中，請予以保留。
5. 必須以純 JSON 格式回傳（不要包含 Markdown 語法以外的多餘說明），格式範例如下：
{
  "results": [
    {"id": 1, "text": "修正後文字"},
    {"id": 2, "text": "修正後文字"}
  ]
}"""


def load_env_config() -> Dict[str, str]:
    """
    動態讀取專案根目錄下的 .env 設定檔（修改 .env 後無需重啟伺服器即刻生效），
    同時相容系統環境變數 os.environ。
    """
    cfg: Dict[str, str] = {}
    if ENV_FILE_PATH.exists():
        try:
            for raw_line in ENV_FILE_PATH.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                cfg[k] = v
        except Exception as e:
            logger.warning(f"讀取 .env 檔案異常: {e}")

    for key in (
        "LLM_PROVIDER",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
    ):
        if not cfg.get(key) and os.environ.get(key):
            cfg[key] = os.environ[key].strip()

    return cfg


def _extract_json_payload(raw_text: str) -> Any:
    """從 LLM 回應字串中安全提取 JSON 物件（自動剝除 ```json ... ``` 區塊）"""
    cleaned = raw_text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
    if m:
        cleaned = m.group(1).strip()
    return json.loads(cleaned)


class SubtitleProofreader:
    """本地 Qwen 或雲端 LLM API 字幕校對器"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_gpu_layers: int = -1,
        n_ctx: int = 8192,
        provider: Optional[str] = None
    ):
        self.cfg = {} if provider == "local" else load_env_config()
        self.llm = None
        if provider == "local":
            preload_cuda_libs()
            from llama_cpp import Llama
            model_path = model_path or str(BASE_DIR / "models" / "qwen2.5-3b-instruct-q4_k_m.gguf")
            self.provider = "local"
            self.model_name = Path(model_path).name
            self.llm = Llama(model_path=model_path, n_ctx=n_ctx, n_gpu_layers=n_gpu_layers, n_threads=8, verbose=False)
        else:
            if provider not in (None, "api"):
                raise ValueError(f"不支援的校對模式: {provider}")
            self.provider, self.model_name = self._resolve_provider()
        logger.info(f"已啟用 LLM 校對引擎: provider={self.provider}, model={self.model_name}")

    def _resolve_provider(self) -> tuple[str, str]:
        provider = (self.cfg.get("LLM_PROVIDER") or "auto").lower().strip()
        gemini_key = self.cfg.get("GEMINI_API_KEY", "").strip()
        openai_key = self.cfg.get("OPENAI_API_KEY", "").strip()
        anthropic_key = self.cfg.get("ANTHROPIC_API_KEY", "").strip()

        if provider == "gemini" or (provider == "auto" and gemini_key):
            if not gemini_key:
                raise RuntimeError("請先在專案根目錄的 .env 檔案中填入 GEMINI_API_KEY！")
            return "gemini", self.cfg.get("GEMINI_MODEL") or "gemini-2.5-flash"

        if provider == "openai" or (provider == "auto" and openai_key):
            if not openai_key:
                raise RuntimeError("請先在專案根目錄的 .env 檔案中填入 OPENAI_API_KEY！")
            return "openai", self.cfg.get("OPENAI_MODEL") or "gpt-4o-mini"

        if provider == "anthropic" or (provider == "auto" and anthropic_key):
            if not anthropic_key:
                raise RuntimeError("請先在專案根目錄的 .env 檔案中填入 ANTHROPIC_API_KEY！")
            return "anthropic", self.cfg.get("ANTHROPIC_MODEL") or "claude-3-5-haiku-latest"

        raise RuntimeError(
            "尚未設定 LLM API Key！請打開專案根目錄的 `.env` 檔案，填入 `GEMINI_API_KEY` 或 `OPENAI_API_KEY` 後再試（無需重啟伺服器）。"
        )

    def _call_llm_api(self, sys_prompt: str, user_input: str) -> str:
        """呼叫明確選定的本地或雲端 LLM"""
        if self.provider == "local":
            response = self.llm.create_chat_completion(
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_input}],
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            return response["choices"][0]["message"]["content"]

        if self.provider == "gemini":
            api_key = self.cfg["GEMINI_API_KEY"].strip()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": sys_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_input}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]

        elif self.provider == "openai":
            api_key = self.cfg["OPENAI_API_KEY"].strip()
            base_url = (self.cfg.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
            url = f"{base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            def _do_openai_call(p: dict) -> str:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(p).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]

            base_payload: Dict[str, Any] = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_input},
                ],
            }

            # 針對不同相容模型（包括 o1 / o3 / gpt-6-luna / deepseek 等推論型模型，其不接受自訂 temperature 或 response_format）
            try:
                # 優先嘗試 response_format
                p = dict(base_payload)
                p["response_format"] = {"type": "json_object"}
                return _do_openai_call(p)
            except urllib.error.HTTPError as he:
                err_text = ""
                try:
                    err_text = he.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                if any(k in err_text.lower() for k in ("temperature", "response_format", "invalid_request_error")):
                    logger.info("偵測到模型對進階參數限制，自動降級以標準 prompt 重試...")
                    return _do_openai_call(base_payload)
                raise urllib.error.HTTPError(he.url, he.code, err_text or he.msg, he.hdrs, None)

        elif self.provider == "anthropic":
            api_key = self.cfg["ANTHROPIC_API_KEY"].strip()
            url = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": self.model_name,
                "max_tokens": 4096,
                "temperature": 0.1,
                "system": sys_prompt,
                "messages": [{"role": "user", "content": user_input}],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["content"][0]["text"]

        raise ValueError(f"不支援的 LLM_PROVIDER: {self.provider}")

    def proofread_segments_batch(
        self,
        segments: List[SubtitleSegment],
        reference_script: Optional[str] = None
    ) -> Dict[int, str]:
        """批次校對一組字幕片段，回傳 id -> corrected_text 對應表"""
        if not segments:
            return {}

        prompt_lines = [f"[{s.id}] {s.text}" for s in segments]
        if reference_script and reference_script.strip():
            sys_prompt = BATCH_SYSTEM_PROMPT_WITH_SCRIPT
            user_input = f"【參考原稿/歌詞】：\n{reference_script.strip()}\n\n【待校對字幕片段】：\n" + "\n".join(prompt_lines)
        else:
            sys_prompt = BATCH_SYSTEM_PROMPT
            user_input = "請校對以下字幕片段：\n" + "\n".join(prompt_lines)

        try:
            raw_json = self._call_llm_api(sys_prompt, user_input)
            data = _extract_json_payload(raw_json)
            result_map: Dict[int, str] = {}

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
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="ignore")[:300]
            except Exception:
                pass
            logger.error(f"雲端 LLM API HTTP 錯誤 ({e.code}): {err_body}")
            raise RuntimeError(f"LLM API 呼叫失敗 (HTTP {e.code}): {err_body or e.reason}")
        except Exception as e:
            logger.warning(f"批次校對處理異常: {e}，保留原始字幕文字")
            return {s.id: s.text for s in segments}

    def proofread_track(
        self,
        track: SubtitleTrack,
        batch_size: int = 25,
        reference_script: Optional[str] = None,
        script_text: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> SubtitleTrack:
        """
        對完整 SubtitleTrack 進行分批雲端 API 校對，保持原始時間軸起訖點，替換文字內容。
        雲端 API Context 充足，預設一次可處理 25 句（整首歌通常 1 批即可秒速完成）。
        """
        effective_script = reference_script or script_text
        all_segments = track.segments
        new_segments: List[SubtitleSegment] = []

        effective_batch_size = max(1, min(batch_size, 8) if self.provider == "local" else batch_size)
        total_batches = (len(all_segments) + effective_batch_size - 1) // effective_batch_size
        logger.info(
            f"開始以 LLM ({self.provider}/{self.model_name}) 校對字幕軌，共 {len(all_segments)} 句，分 {total_batches} 批處理 (附帶原詞: {bool(effective_script)})..."
        )

        for i in range(0, len(all_segments), effective_batch_size):
            batch = all_segments[i:i + effective_batch_size]
            corrected_map = self.proofread_segments_batch(batch, reference_script=effective_script)

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
                progress_callback(min(i + effective_batch_size, len(all_segments)), len(all_segments))

        return SubtitleTrack(
            version=track.version,
            source_file=track.source_file,
            duration=track.duration,
            language=track.language,
            segments=new_segments
        )

    def close(self) -> None:
        if self.llm is not None:
            self.llm.close()
            self.llm = None
            release_gpu_memory()
