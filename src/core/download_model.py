from pathlib import Path
from huggingface_hub import hf_hub_download

DEFAULT_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
DEFAULT_FILE = "qwen2.5-3b-instruct-q4_k_m.gguf"


def ensure_llm_model(
    repo_id: str = DEFAULT_REPO,
    filename: str = DEFAULT_FILE,
    models_dir: str = "models"
) -> str:
    """下載或取得本地 GGUF LLM 模型路徑"""
    target_dir = Path(models_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    expected_path = target_dir / filename

    if expected_path.exists() and expected_path.stat().st_size > 100 * 1024 * 1024:
        return str(expected_path)

    print(f"正在從 Hugging Face 下載 Edge 校對模型 [{repo_id} / {filename}]...")
    path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=str(target_dir)
    )
    return str(path)


if __name__ == "__main__":
    p = ensure_llm_model()
    print("模型準備就緒:", p)
