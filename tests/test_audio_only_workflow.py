import io
import json
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app, UPLOADS_DIR
from src.core.video_burner import burn_subtitles_to_video, has_video_stream, get_video_info
from src.schemas.subtitle import SubtitleTrack, SubtitleSegment, SubtitleStyle


def _make_sample_audio(path: Path, fmt: str = "wav"):
    """使用 FFmpeg 產生一段 1.5 秒測試音訊 (440Hz sine wave)"""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.5",
        "-ar", "44100", "-ac", "2",
        str(path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def test_audio_only_upload_and_package_metadata(tmp_path):
    wav_file = tmp_path / "test_audio_only.wav"
    _make_sample_audio(wav_file, "wav")

    mp3_file = tmp_path / "test_audio_only.mp3"
    _make_sample_audio(mp3_file, "mp3")

    client = TestClient(app, base_url="http://localhost")

    # 測試上傳 WAV + TXT
    try:
        res = client.post(
            "/api/upload",
            files=[
                ("files", ("test_audio_only_pkg.wav", wav_file.read_bytes(), "audio/wav")),
                ("files", ("test_audio_only_pkg.txt", "測試純音檔第一行\n".encode("utf-8"), "text/plain")),
            ],
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert len(data["packages"]) == 1
        media = data["packages"][0]["media"]
        assert media["type"] == "audio"
        assert media["is_audio_only"] is True
        assert media["duration"] > 1.0
        assert media["width"] == 1920
        assert media["height"] == 1080

        # 測試 MP3 上傳與音訊斷點分析流程
        res_mp3 = client.post(
            "/api/upload",
            files=[("files", ("test_mp3_pkg.mp3", mp3_file.read_bytes(), "audio/mpeg"))],
        )
        assert res_mp3.status_code == 200, res_mp3.text
        mp3_media = res_mp3.json()["packages"][0]["media"]
        assert mp3_media["type"] == "audio"
        assert mp3_media["is_audio_only"] is True
        assert mp3_media["duration"] > 1.0

        bp_res = client.post(
            "/api/audio/breakpoints",
            json={"media_path": mp3_media["absolute_path"], "mode": "balanced"},
        )
        assert bp_res.status_code == 200, bp_res.text
        assert bp_res.json()["duration"] > 1.0
    finally:
        import shutil
        for name in ("test_audio_only_pkg", "test_mp3_pkg"):
            target = UPLOADS_DIR / name
            if target.exists():
                shutil.rmtree(target)


def test_audio_only_burn_rejected_and_srt_exported_cleanly(tmp_path):
    from src.core.exporter import to_srt

    mp3_file = tmp_path / "song.mp3"
    _make_sample_audio(mp3_file, "mp3")
    assert has_video_stream(str(mp3_file)) is False

    w, h, dur = get_video_info(str(mp3_file))
    assert w == 1920
    assert h == 1080
    assert dur > 1.0

    track = SubtitleTrack(
        source_file="song.mp3",
        segments=[SubtitleSegment(id=1, start=0.1, end=1.2, text="純音檔轉字幕測試")]
    )

    # 純音檔不允許執行 Hardcopy MP4 壓製
    out_mp4 = tmp_path / "song_burned.mp4"
    with pytest.raises(ValueError, match="不支援"):
        burn_subtitles_to_video(
            video_path=str(mp3_file),
            subtitles_source=track,
            output_path=str(out_mp4),
            style=SubtitleStyle(font_size=48, primary_color="#FFFFFF"),
            use_gpu=False,
        )
    assert not out_mp4.exists()

    # 純音檔可正常匯出 SRT
    srt_text = to_srt(track)
    assert "00:00:00,100 --> 00:00:01,200" in srt_text
    assert "純音檔轉字幕測試" in srt_text
