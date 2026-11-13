import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from ..schemas.subtitle import SubtitleSegment, SubtitleTrack

logger = logging.getLogger(__name__)


def _load_audio_mono_16k(media_path: str, sr: int = 16000) -> np.ndarray:
    """使用 ffmpeg 將影音檔案解碼為 16kHz 單聲道 float32 PCM 陣列 (不依賴 openai-whisper)。"""
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", str(media_path),
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sr),
        "-",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg 解碼音訊失敗: {res.stderr.decode('utf-8', errors='ignore')[-400:]}")
    return np.frombuffer(res.stdout, np.int16).astype(np.float32) / 32768.0

# 三種斷點偵測靈敏度模式設定
BREAKPOINT_MODES: Dict[str, Dict[str, float]] = {
    "dense": {
        "vad_threshold": 0.30,
        "min_silence_ms": 170,
        "speech_pad_ms": 60,
        "merge_gap_sec": 0.14,
        "min_sec": 1.15,
        "target_sec": 2.45,
        "max_sec": 3.55,
        "chars_per_sec": 3.8,
    },
    "balanced": {
        "vad_threshold": 0.35,
        "min_silence_ms": 230,
        "speech_pad_ms": 75,
        "merge_gap_sec": 0.20,
        "min_sec": 1.35,
        "target_sec": 2.85,
        "max_sec": 4.30,
        "chars_per_sec": 3.3,
    },
    "slow": {
        "vad_threshold": 0.32,
        "min_silence_ms": 340,
        "speech_pad_ms": 90,
        "merge_gap_sec": 0.28,
        "min_sec": 1.70,
        "target_sec": 3.60,
        "max_sec": 5.60,
        "chars_per_sec": 2.5,
    },
}


def _compute_vocal_energy_envelope(audio: np.ndarray, sr: int = 16000) -> Tuple[np.ndarray, np.ndarray]:
    """
    計算 10ms (100Hz) 解析度的聲學能量包絡：
    1. raw_rms: 原始振幅均方根包絡 (用於計算視覺化波形)
    2. smooth_vocal_rms: 一階差分高通強調後的平滑能量包絡 (凸顯人聲子音與換字邊界，抑制低頻伴奏鼓點)
    """
    hop = sr // 100  # 160 samples = 10ms @ 16kHz
    n_frames = max(1, len(audio) // hop)
    trimmed = audio[: n_frames * hop].reshape(n_frames, hop)

    raw_rms = np.sqrt(np.mean(trimmed ** 2, axis=1) + 1e-10)

    # 一階差分高通濾波，強調 1kHz~4kHz 人聲頻段，減少低頻貝斯/鼓聲把換氣谷底填滿的問題
    diff_sig = np.diff(audio, prepend=audio[0])[: n_frames * hop].reshape(n_frames, hop)
    vocal_rms = np.sqrt(np.mean(diff_sig ** 2, axis=1) + 1e-10)

    # 70ms 移動平均平滑化，消除單一週期震盪
    kernel = np.ones(7, dtype=np.float32) / 7.0
    smooth_vocal_rms = np.convolve(vocal_rms, kernel, mode="same")

    return raw_rms, smooth_vocal_rms


def _downsample_waveform_peaks(raw_rms: np.ndarray, num_bins: int = 360) -> List[float]:
    """將能量包絡降採樣為前端 Canvas 視覺化波形條所需的正規化峰值陣列 (0.0 ~ 1.0)"""
    if len(raw_rms) == 0:
        return [0.0] * num_bins

    indices = np.linspace(0, len(raw_rms), num_bins + 1, dtype=int)
    peaks = []
    for i in range(num_bins):
        s_idx, e_idx = indices[i], max(indices[i] + 1, indices[i + 1])
        seg = raw_rms[s_idx:e_idx]
        peaks.append(float(np.percentile(seg, 85)) if len(seg) > 0 else 0.0)

    arr = np.array(peaks, dtype=np.float32)
    p98 = float(np.percentile(arr, 98)) if len(arr) > 0 else 1.0
    if p98 > 1e-6:
        arr = np.clip(arr / p98, 0.0, 1.0)
    return [round(float(x), 3) for x in arr]


def _clamp_segment_boundaries(
    s_sec: float,
    e_sec: float,
    smooth_rms: np.ndarray,
    raw_rms: np.ndarray
) -> Tuple[float, float]:
    """
    收斂單一句子的起點 (Onset) 與終點 (Offset)，
    切掉開頭尚未發聲的空白與結尾拖太長的伴奏殘響。
    """
    s_idx = max(0, int(s_sec * 100))
    e_idx = min(len(smooth_rms), int(e_sec * 100))
    if e_idx - s_idx < 50:
        return round(s_sec, 2), round(e_sec, 2)

    seg_env = raw_rms[s_idx:e_idx]
    peak = float(np.percentile(seg_env, 85))
    noise_floor = float(np.percentile(raw_rms, 15))
    active_thresh = max(noise_floor * 1.4, peak * 0.14)

    active_indices = np.where(seg_env >= active_thresh)[0]
    if len(active_indices) >= 5:
        # 往外保留 60ms 自然發音緩衝
        new_s_idx = max(s_idx, s_idx + int(active_indices[0]) - 6)
        new_e_idx = min(e_idx, s_idx + int(active_indices[-1]) + 8)
        if new_e_idx - new_s_idx >= 45:
            return round(new_s_idx / 100.0, 2), round(new_e_idx / 100.0, 2)

    return round(s_sec, 2), round(e_sec, 2)


def _subsplit_long_island(
    s_sec: float,
    e_sec: float,
    smooth_vocal_rms: np.ndarray,
    min_sec: float,
    target_sec: float,
    max_sec: float
) -> List[Tuple[float, float]]:
    """
    當一段連續人聲超過 max_sec（例如密集歌詞沒有明顯長靜音）時，
    在 [cur + min_sec, cur + max_sec] 視窗內尋找最深的「聲學能量局部波谷 (Local Valley)」切開。
    """
    results: List[Tuple[float, float]] = []
    cur = s_sec
    n_total = len(smooth_vocal_rms)

    while (e_sec - cur) > max_sec:
        # 若剩餘長度不到 2 * min_sec，對半找波谷切一次即可
        remaining = e_sec - cur
        effective_target = min(target_sec, remaining / 2.0) if remaining < (target_sec + min_sec) else target_sec

        win_start = max(0, int((cur + min_sec) * 100))
        win_end = min(n_total, int(min(e_sec - min_sec, cur + max_sec) * 100))
        if win_end <= win_start + 5:
            break

        window_env = smooth_vocal_rms[win_start:win_end]
        max_val = float(np.max(window_env)) + 1e-8
        norm_env = window_env / max_val

        # 加入輕微的目標長度引力，讓切點兼顧「最深換氣波谷」與「均衡句子長度」
        frames = np.arange(win_start, win_end, dtype=np.float32)
        dist_penalty = 0.16 * np.abs((frames / 100.0) - (cur + effective_target)) / max(1.0, effective_target)

        best_offset = int(np.argmin(norm_env + dist_penalty))
        split_t = round((win_start + best_offset) / 100.0, 2)

        results.append((round(cur, 2), split_t))
        cur = split_t

    if e_sec - cur >= 0.25:
        results.append((round(cur, 2), round(e_sec, 2)))
    elif results:
        # 將極短尾端併入前一段
        prev_s, _ = results[-1]
        results[-1] = (prev_s, round(e_sec, 2))
    else:
        results.append((round(s_sec, 2), round(e_sec, 2)))

    return results


def analyze_audio_breakpoints(
    media_path: str,
    mode: str = "balanced"
) -> Dict[str, Any]:
    """
    【階段一：純聲學斷點分析】
    不需等待漫長的語音辨識，直接利用 Silero VAD + 10ms 人聲能量包絡波谷偵測，
    在 1 秒內產出精準的句子時間軸索引 (#1 ~ #N)、預估每段字數容量與視覺化波形資料。
    """
    from faster_whisper.vad import get_speech_timestamps, VadOptions

    p = Path(media_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"找不到媒體檔案: {media_path}")

    cfg = BREAKPOINT_MODES.get(mode, BREAKPOINT_MODES["balanced"])
    sr = 16000
    audio = _load_audio_mono_16k(str(p), sr=sr)
    total_duration = round(len(audio) / float(sr), 3)

    raw_rms, smooth_vocal_rms = _compute_vocal_energy_envelope(audio, sr=sr)
    waveform_peaks = _downsample_waveform_peaks(raw_rms, num_bins=360)

    # Step 1: 使用 Silero VAD 找出人聲發聲島嶼 (Macro Speech Islands)
    vad_opts = VadOptions(
        threshold=float(cfg["vad_threshold"]),
        min_silence_duration_ms=int(cfg["min_silence_ms"]),
        speech_pad_ms=int(cfg["speech_pad_ms"]),
    )
    raw_chunks = get_speech_timestamps(audio, vad_opts)

    islands: List[Tuple[float, float]] = []
    for c in raw_chunks:
        s_t = round(c["start"] / float(sr), 2)
        e_t = round(c["end"] / float(sr), 2)
        if e_t - s_t >= 0.20:
            islands.append((s_t, e_t))

    # Step 2: 合併間隔極小且合併後不超過 max_sec 的碎片段
    merged_islands: List[Tuple[float, float]] = []
    for s_t, e_t in islands:
        if not merged_islands:
            merged_islands.append((s_t, e_t))
            continue
        prev_s, prev_e = merged_islands[-1]
        gap = s_t - prev_e
        combined_len = e_t - prev_s
        if (gap < cfg["merge_gap_sec"] and combined_len <= cfg["max_sec"]) or (
            (prev_e - prev_s) < 0.75 and gap < 0.30 and combined_len <= cfg["max_sec"]
        ):
            merged_islands[-1] = (prev_s, e_t)
        else:
            merged_islands.append((s_t, e_t))

    # Step 3: 針對超長連續唱段/長句，利用 10ms 人聲高通能量波谷自動切分為自然句子長度
    final_ranges: List[Tuple[float, float]] = []
    for s_t, e_t in merged_islands:
        cs, ce = _clamp_segment_boundaries(s_t, e_t, smooth_vocal_rms, raw_rms)
        sub_segs = _subsplit_long_island(
            cs,
            ce,
            smooth_vocal_rms,
            min_sec=float(cfg["min_sec"]),
            target_sec=float(cfg["target_sec"]),
            max_sec=float(cfg["max_sec"]),
        )
        final_ranges.extend(sub_segs)

    # Step 4: 建立帶編號與預估字數容量的 SubtitleSegment 清單
    global_noise = float(np.percentile(raw_rms, 20))
    segments: List[SubtitleSegment] = []
    for idx, (s_t, e_t) in enumerate(final_ranges, start=1):
        dur = max(0.2, e_t - s_t)
        s_frame = max(0, int(s_t * 100))
        e_frame = min(len(raw_rms), int(e_t * 100))
        seg_rms = raw_rms[s_frame:e_frame]
        if len(seg_rms) > 0:
            voiced_ratio = float(np.mean(seg_rms > global_noise * 1.35))
            voiced_ratio = max(0.45, min(1.0, voiced_ratio))
        else:
            voiced_ratio = 0.8

        active_sec = dur * voiced_ratio
        est_chars = max(2, min(22, int(round(active_sec * cfg["chars_per_sec"]))))

        segments.append(
            SubtitleSegment(
                id=idx,
                start=round(s_t, 2),
                end=round(e_t, 2),
                text="",
                expected_chars=est_chars,
                words=[],
            )
        )

    track = SubtitleTrack(
        version="1.0.0",
        source_file=f"{p.stem}.timeline.srt",
        duration=total_duration,
        language="zh",
        segments=segments,
    )

    return {
        "track": track,
        "mode": mode,
        "duration": total_duration,
        "segment_count": len(segments),
        "waveform_peaks": waveform_peaks,
    }


def snap_time_to_valley(
    media_path: str,
    time_sec: float,
    search_radius_sec: float = 0.18
) -> float:
    """
    當使用者在播放游標處點擊「✂️ 切開」時，
    自動在游標前後 ±search_radius_sec 內尋找聲學能量最低谷 (字與字交界處)，讓切點乾淨不吃字。
    """

    p = Path(media_path).resolve()
    if not p.exists():
        return round(time_sec, 2)

    sr = 16000
    audio = _load_audio_mono_16k(str(p), sr=sr)
    _, smooth_vocal_rms = _compute_vocal_energy_envelope(audio, sr=sr)

    center_frame = int(round(time_sec * 100))
    rad_frames = max(3, int(round(search_radius_sec * 100)))
    w_start = max(0, center_frame - rad_frames)
    w_end = min(len(smooth_vocal_rms), center_frame + rad_frames + 1)

    if w_end <= w_start:
        return round(time_sec, 2)

    local_slice = smooth_vocal_rms[w_start:w_end]
    best_frame = w_start + int(np.argmin(local_slice))
    return round(best_frame / 100.0, 2)
