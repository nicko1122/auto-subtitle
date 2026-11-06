import os
import time
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app, BASE_DIR
from src.core.video_upscaler import (
    find_upscaler_binary,
    get_video_stream_info,
    estimate_upscale_time,
    upscale_video,
    clean_stale_upscale_temp_dirs,
    upscale_manager
)


client = TestClient(app, base_url="http://localhost")


def test_upscaler_binary_detected():
    binary = find_upscaler_binary()
    assert binary is not None
    assert binary.exists()


def test_upscale_status_endpoint():
    res = client.get("/api/upscale/status")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True
    assert "realesr-animevideov3" in [m["id"] for m in data["models"]]
    assert 2 in data["scales"]


def test_upscale_endpoint_missing_params():
    res = client.post("/api/upscale/video", json={})
    assert res.status_code == 400


def test_upscale_endpoint_nonexistent_package():
    res = client.post("/api/upscale/video", json={"package_path": "non_existent_folder"})
    assert res.status_code in (404, 500)


def test_estimate_upscale_time_and_warning():
    # 輕量模型：無警語
    est_compact = estimate_upscale_time(width=1920, height=1080, total_frames=100, model_name="realesr-animevideov3", scale=2)
    assert est_compact["is_heavy_warning"] is False
    assert est_compact["total_frames"] == 100
    assert est_compact["estimated_seconds"] > 0

    # 重型 x4plus 模型且幀數 > 200：觸發紅字警語
    est_heavy = estimate_upscale_time(width=1920, height=1080, total_frames=3000, model_name="realesrgan-x4plus", scale=2)
    assert est_heavy["is_heavy_warning"] is True
    assert "極重型靜態照片模型" in est_heavy["warning_message"]
    assert "Compact 輕量視訊模型" in est_heavy["warning_message"]


def test_clean_stale_upscale_temp_dirs():
    temp_dir = BASE_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    stale_dir = temp_dir / "upscale_fake_stale_123"
    stale_dir.mkdir(parents=True, exist_ok=True)
    (stale_dir / "dummy.txt").write_text("test")

    # 修改 mtime 為 2 小時前
    old_time = time.time() - 7200
    os.utime(str(stale_dir), (old_time, old_time))

    clean_stale_upscale_temp_dirs(max_age_seconds=10)
    assert not stale_dir.exists()


def test_upscale_estimate_endpoint():
    mini_in = BASE_DIR / "temp" / "mini_est.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=0.5:size=160x120:rate=10",
        "-c:v", "libx264",
        str(mini_in)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        res = client.post("/api/upscale/estimate", json={
            "media_path": str(mini_in),
            "scale": 2,
            "model_name": "realesr-animevideov3"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "estimate" in data
        assert data["estimate"]["width"] == 160
    finally:
        mini_in.unlink(missing_ok=True)


def test_upscale_async_start_and_cancel():
    mini_in = BASE_DIR / "temp" / "mini_async.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2.0:size=160x120:rate=10",
        "-c:v", "libx264",
        str(mini_in)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        res = client.post("/api/upscale/start", json={
            "media_path": str(mini_in),
            "scale": 2,
            "model_name": "realesr-animevideov3"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "started"
        task_id = data["task_id"]

        # 查詢狀態
        res_status = client.get(f"/api/upscale/task/{task_id}")
        assert res_status.status_code == 200
        task_data = res_status.json()
        assert task_data["task_id"] == task_id

        # 發出取消
        res_cancel = client.post(f"/api/upscale/task/{task_id}/cancel")
        assert res_cancel.status_code == 200
        assert res_cancel.json()["status"] == "cancelling"

        # 等待一小段時間確認任務狀態變成 cancelled
        time.sleep(0.5)
        res_status2 = client.get(f"/api/upscale/task/{task_id}")
        assert res_status2.json()["stage"] in ("cancelled", "preparing", "extracting", "upscaling")
    finally:
        mini_in.unlink(missing_ok=True)


def test_upscale_end_to_end_on_mini_clip(tmp_path):
    # 建立 0.5 秒 160x120 測試影片
    mini_in = tmp_path / "mini.mp4"
    mini_out = tmp_path / "mini_2x.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=0.5:size=160x120:rate=10",
        "-c:v", "libx264",
        str(mini_in)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out = upscale_video(str(mini_in), str(mini_out), scale=2, model_name="realesr-animevideov3")
    assert Path(out).exists()

    info = get_video_stream_info(out)
    assert info["width"] == 320
    assert info["height"] == 240
