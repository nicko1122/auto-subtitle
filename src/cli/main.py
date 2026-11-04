import os
import sys
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.core.audio_extractor import extract_audio, check_ffmpeg
from src.core.transcriber import transcribe_audio
from src.core.segmenter import build_subtitle_track
from src.core.aligner import align_script_to_audio
from src.core.proofreader import SubtitleProofreader
from src.core.video_burner import burn_subtitles_to_video
from src.core.exporter import to_srt, to_vtt, to_json, save_file, parse_srt_content
from src.schemas.subtitle import SegmentationConfig, SubtitleTrack, SubtitleStyle

app = typer.Typer(
    name="auto-subtitle",
    help="自動上字幕 CLI 工具箱 - 包含音軌分離、Whisper 本地辨識、智慧斷句與字幕匯出",
    add_completion=False
)
console = Console()


@app.command("extract")
def extract_cmd(
    video_path: str = typer.Argument(..., help="來源影片檔案路徑 (MP4, MOV, MKV 等)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="輸出 WAV 路徑 (預設為同檔名 .wav)"),
    sample_rate: int = typer.Option(16000, "--sr", help="取樣頻率 (Hz)"),
):
    """【步驟 1】從影片中抽取音軌，轉換為 16kHz 單聲道 WAV"""
    if not check_ffmpeg():
        console.print("[bold red]錯誤: 系統未安裝或找不到 ffmpeg 指令！[/bold red]")
        raise typer.Exit(code=1)

    try:
        console.print(f"[cyan]正在從 [bold]{video_path}[/bold] 提取音軌...[/cyan]")
        res = extract_audio(video_path, output_path=output, sample_rate=sample_rate)
        console.print(f"[bold green]✔ 音軌提取成功！[/bold green]")
        console.print(f"  音訊路徑: [yellow]{res['audio_path']}[/yellow]")
        console.print(f"  音訊長度: [yellow]{res['duration']:.2f} 秒[/yellow]")
        console.print(f"  取樣率:   [yellow]{res['sample_rate']} Hz (單聲道)[/yellow]")
    except Exception as e:
        console.print(f"[bold red]提取失敗: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("transcribe")
def transcribe_cmd(
    audio_path: str = typer.Argument(..., help="音訊檔案路徑 (WAV, MP3 等)"),
    model: str = typer.Option("base", "-m", "--model", help="Whisper 模型大小 (tiny, base, small, medium, large-v3)"),
    device: str = typer.Option("auto", "-d", "--device", help="運算裝置 (auto, cuda, cpu)"),
    compute_type: str = typer.Option("default", "--compute-type", help="計算精度 (default, int8, float16)"),
    language: Optional[str] = typer.Option(None, "-l", "--lang", help="語言代碼 (如 zh, en)，未提供則自動辨識"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="提示詞 (例如 '繁體中文' 可強制輸出繁體)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="輸出原始 JSON 路徑"),
):
    """【步驟 2】使用 faster-whisper 進行語音辨識並提取 Word-level 時間戳記"""
    try:
        console.print(f"[cyan]正在以 [bold]{model}[/bold] 模型辨識 [bold]{audio_path}[/bold] (裝置: {device})...[/cyan]")
        res = transcribe_audio(
            audio_path=audio_path,
            model_size=model,
            device=device,
            compute_type=compute_type,
            language=language,
            initial_prompt=prompt
        )
        console.print(f"[bold green]✔ 辨識完成！[/bold green]")
        console.print(f"  辨識語言:   [yellow]{res['language']}[/yellow] (信心度: {res['language_probability']})")
        console.print(f"  音訊長度:   [yellow]{res['duration']:.2f} 秒[/yellow]")
        console.print(f"  總字詞數量: [yellow]{len(res['all_words'])} 個[/yellow]")

        out_file = output or str(Path(audio_path).with_suffix(".raw.json"))
        Path(out_file).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"  原始資料已存至: [yellow]{out_file}[/yellow]")
    except Exception as e:
        console.print(f"[bold red]辨識失敗: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("segment")
def segment_cmd(
    raw_json_path: str = typer.Argument(..., help="transcribe 指令輸出的原始 JSON 檔"),
    max_chars: int = typer.Option(16, "-c", "--max-chars", help="單行字幕最大字數 (中文建議 12-18)"),
    pause: float = typer.Option(0.45, "-p", "--pause", help="視為停頓斷句的間隔秒數"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="輸出 SubtitleTrack JSON 檔名"),
):
    """【步驟 3】依據標點符號、語音停頓與最大字數規則進行智慧斷句"""
    try:
        raw_p = Path(raw_json_path)
        data = json.loads(raw_p.read_text(encoding="utf-8"))
        cfg = SegmentationConfig(max_chars=max_chars, pause_threshold=pause)

        console.print(f"[cyan]正在進行智慧斷句校對 (最大字數: {max_chars}, 停頓閥值: {pause}s)...[/cyan]")
        track = build_subtitle_track(data, cfg)

        out_file = output or str(raw_p.with_name(raw_p.name.replace(".raw.json", ".subtitles.json")))
        save_file(to_json(track), out_file)

        console.print(f"[bold green]✔ 智慧斷句完成！共產生 {len(track.segments)} 條字幕[/bold green]")
        console.print(f"  字幕檔已存至: [yellow]{out_file}[/yellow]")

        # 印出前 5 句預覽
        table = Table(title="字幕片段預覽 (前 5 句)")
        table.add_column("#", justify="right", style="cyan")
        table.add_column("起訖時間", style="magenta")
        table.add_column("字幕內容", style="green")
        for seg in track.segments[:5]:
            table.add_row(str(seg.id), f"{seg.start:.2f}s -> {seg.end:.2f}s", seg.text)
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]斷句失敗: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("export")
def export_cmd(
    subtitle_json: str = typer.Argument(..., help="SubtitleTrack JSON 檔案路徑"),
    fmt: str = typer.Option("srt", "-f", "--format", help="匯出格式 (srt, vtt, json)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="輸出檔案路徑"),
):
    """【步驟 4】將 SubtitleTrack JSON 轉換匯出為標準 SRT / VTT 格式"""
    try:
        data = json.loads(Path(subtitle_json).read_text(encoding="utf-8"))
        track = SubtitleTrack(**data)

        fmt_lower = fmt.lower()
        if fmt_lower == "srt":
            content = to_srt(track)
            ext = ".srt"
        elif fmt_lower == "vtt":
            content = to_vtt(track)
            ext = ".vtt"
        elif fmt_lower == "json":
            content = to_json(track)
            ext = ".json"
        else:
            raise ValueError(f"不支援的格式: {fmt} (僅支援 srt, vtt, json)")

        out_file = output or str(Path(subtitle_json).with_suffix(ext))
        save_file(content, out_file)
        console.print(f"[bold green]✔ 匯出成功！格式: {fmt_lower.upper()}[/bold green]")
        console.print(f"  儲存路徑: [yellow]{out_file}[/yellow]")
    except Exception as e:
        console.print(f"[bold red]匯出失敗: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("pipeline")
def pipeline_cmd(
    media_path: str = typer.Argument(..., help="來源影音檔案路徑 (MP4, MOV, WAV, MP3 等)"),
    model: str = typer.Option("base", "-m", "--model", help="Whisper 模型 (tiny, base, small, medium, large-v3)"),
    device: str = typer.Option("auto", "-d", "--device", help="運算裝置 (auto, cuda, cpu)"),
    language: Optional[str] = typer.Option(None, "-l", "--lang", help="指定語言 (如 zh, en)"),
    prompt: Optional[str] = typer.Option("繁體中文", "--prompt", help="初始提示詞 (預設引導輸出繁體中文)"),
    max_chars: int = typer.Option(16, "-c", "--max-chars", help="單行字幕最大字數"),
    pause: float = typer.Option(0.45, "-p", "--pause", help="停頓斷句間隔 (秒)"),
    out_dir: Optional[str] = typer.Option(None, "-o", "--output-dir", help="輸出目錄 (預設為影音同目錄)"),
):
    """【一鍵全流程】影片 ➔ 提取音訊 ➔ Whisper 辨識 ➔ 智慧斷句 ➔ 匯出 JSON & SRT"""
    input_p = Path(media_path).resolve()
    if not input_p.exists():
        console.print(f"[bold red]找不到檔案: {media_path}[/bold red]")
        raise typer.Exit(code=1)

    target_dir = Path(out_dir).resolve() if out_dir else input_p.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = input_p.stem

    console.rule("[bold cyan]開始執行自動上字幕流水線[/bold cyan]")

    # 1. 音訊處理
    is_video = input_p.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv"]
    if is_video:
        console.print("[1/4] 抽取並轉換音訊 (16kHz Mono WAV)...")
        wav_path = target_dir / f"{stem}.wav"
        extract_res = extract_audio(str(input_p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(input_p)

    # 2. Whisper 語音辨識
    console.print(f"[2/4] Whisper 語音辨識中 (模型: {model}, 裝置: {device}, 提示: {prompt})...")
    trans_res = transcribe_audio(
        audio_path=audio_file,
        model_size=model,
        device=device,
        language=language,
        initial_prompt=prompt
    )

    # 3. 智慧斷句
    console.print(f"[3/4] 智慧斷句切分中 (單行最大 {max_chars} 字, 停頓閥值 {pause}s)...")
    cfg = SegmentationConfig(max_chars=max_chars, pause_threshold=pause)
    track = build_subtitle_track(trans_res, cfg)

    # 4. 匯出檔案
    console.print("[4/4] 匯出檔案 (JSON, SRT & VTT)...")
    json_path = target_dir / f"{stem}.subtitles.json"
    
    # 避免覆蓋使用者可能既有的同名 .srt 參考檔
    raw_srt_path = target_dir / f"{stem}.srt"
    if raw_srt_path.exists():
        srt_path = target_dir / f"{stem}.generated.srt"
        vtt_path = target_dir / f"{stem}.generated.vtt"
    else:
        srt_path = target_dir / f"{stem}.srt"
        vtt_path = target_dir / f"{stem}.vtt"

    save_file(to_json(track), str(json_path))
    save_file(to_srt(track), str(srt_path))
    save_file(to_vtt(track), str(vtt_path))

    console.rule("[bold green]處理完成[/bold green]")
    console.print(f"  ✔ 總字幕句數: [yellow]{len(track.segments)} 句[/yellow]")
    console.print(f"  ✔ JSON 資料 (含逐字時間軸): [green]{json_path}[/green]")
    console.print(f"  ✔ SRT 字幕檔:              [green]{srt_path}[/green]")
    console.print(f"  ✔ VTT 字幕檔:              [green]{vtt_path}[/green]")


@app.command("align")
def align_cmd(
    media_path: str = typer.Argument(..., help="來源影音或音訊檔案路徑 (MP4, WAV 等)"),
    script_path: str = typer.Argument(..., help="原稿或歌詞文字檔案路徑 (TXT)"),
    model: str = typer.Option("small", "-m", "--model", help="Whisper 模型 (建議 small 或 base)"),
    device: str = typer.Option("cuda", "-d", "--device", help="運算裝置 (cuda, cpu, auto)"),
    no_vad: bool = typer.Option(False, "--no-vad", help="關閉 VAD 語音過濾 (適合背景音樂強烈或有微弱尾聲之歌曲)"),
    output_dir: Optional[str] = typer.Option(None, "-o", "--output-dir", help="輸出目錄 (預設為影音同目錄)"),
):
    """【有稿模式】利用已知原稿/歌詞與音訊進行動態規劃強制對齊 (Forced Alignment)"""
    input_p = Path(media_path).resolve()
    script_p = Path(script_path).resolve()

    if not input_p.exists():
        console.print(f"[bold red]找不到影音檔案: {media_path}[/bold red]")
        raise typer.Exit(code=1)
    if not script_p.exists():
        console.print(f"[bold red]找不到原稿檔案: {script_path}[/bold red]")
        raise typer.Exit(code=1)

    target_dir = Path(output_dir).resolve() if output_dir else input_p.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = input_p.stem

    console.rule("[bold cyan]開始執行【有稿模式】強制時間軸對齊[/bold cyan]")

    # 1. 抽取音訊 (若為影片)
    is_video = input_p.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv"]
    if is_video:
        console.print("[1/3] 抽取並轉換音訊 (16kHz Mono WAV)...")
        wav_path = target_dir / f"{stem}.wav"
        extract_res = extract_audio(str(input_p), str(wav_path))
        audio_file = extract_res["audio_path"]
    else:
        audio_file = str(input_p)

    # 2. 取得 Word-level 時間戳記
    console.print(f"[2/3] 語音特徵抽取與時間戳記辨識 (模型: {model}, 裝置: {device}, VAD: {not no_vad})...")
    trans_res = transcribe_audio(
        audio_path=audio_file,
        model_size=model,
        device=device,
        vad_filter=not no_vad,
        word_timestamps=True,
        initial_prompt="繁體中文"
    )

    # 3. 原稿與時間流動態對齊
    console.print(f"[3/3] 正在將原稿文字與語音時間軸強制對齊...")
    track = align_script_to_audio(str(script_p), trans_res)

    # 4. 匯出檔案
    json_path = target_dir / f"{stem}.aligned.json"
    srt_path = target_dir / f"{stem}.aligned.srt"
    vtt_path = target_dir / f"{stem}.aligned.vtt"

    save_file(to_json(track), str(json_path))
    save_file(to_srt(track), str(srt_path))
    save_file(to_vtt(track), str(vtt_path))

    console.rule("[bold green]有稿對齊完成[/bold green]")
    console.print(f"  ✔ 原稿對齊句數: [yellow]{len(track.segments)} 句 (100% 採用原稿文字)[/yellow]")
    console.print(f"  ✔ SRT 字幕檔:  [green]{srt_path}[/green]")
    console.print(f"  ✔ VTT 字幕檔:  [green]{vtt_path}[/green]")
    console.print(f"  ✔ JSON 資料:   [green]{json_path}[/green]")

    # 印出前 6 句預覽
    table = Table(title="有稿對齊字幕預覽 (前 6 句)")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("起訖時間", style="magenta")
    table.add_column("對齊後原稿文字", style="green")
    for seg in track.segments[:6]:
        table.add_row(str(seg.id), f"{seg.start:.2f}s -> {seg.end:.2f}s", seg.text)
    console.print(table)


@app.command("proofread")
def proofread_cmd(
    input_file: str = typer.Argument(..., help="來源檔案 (可為 .subtitles.json、.srt 或影音檔)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="輸出檔案路徑 (預設輸出 .proofread.srt)"),
    batch_size: int = typer.Option(8, "-b", "--batch-size", help="每次批次送入 LLM 校對的字幕句數"),
    gpu_layers: int = typer.Option(-1, "--gpu-layers", help="GPU 卸載層數 (-1 為全層放 GPU)"),
):
    """【無稿模式】使用本地 Edge LLM (Qwen2.5) 自動校正逐字稿錯別字與同音字"""
    input_p = Path(input_file).resolve()
    if not input_p.exists():
        console.print(f"[bold red]找不到輸入檔案: {input_file}[/bold red]")
        raise typer.Exit(code=1)

    console.rule("[bold cyan]開始執行【無稿模式】Edge LLM 智慧校對[/bold cyan]")

    # 1. 取得 SubtitleTrack
    if input_p.suffix.lower() == ".json":
        data = json.loads(input_p.read_text(encoding="utf-8"))
        track = SubtitleTrack(**data)
    elif input_p.suffix.lower() in (".srt", ".vtt"):
        content = input_p.read_text(encoding="utf-8")
        track = parse_srt_content(content, source_file=str(input_p))
    else:
        # 假設為影音檔，先跑 pipeline 核心
        console.print(f"[1/3] 執行快速語音辨識與切分...")
        trans_res = transcribe_audio(str(input_p), model_size="small", device="cuda", initial_prompt="繁體中文")
        track = build_subtitle_track(trans_res)

    console.print(f"[2/3] 載入本地 Qwen2.5-3B-Instruct 模型 (GPU 全速加速)...")
    proofreader = SubtitleProofreader(n_gpu_layers=gpu_layers)

    console.print(f"[3/3] 正在逐批校對字幕 (共 {len(track.segments)} 句)...")
    try:
        with console.status("[bold green]Edge LLM 思考校對中...") as status:
            proofread_track = proofreader.proofread_track(track, batch_size=batch_size)
    finally:
        proofreader.close()

    # 匯出
    out_file = output or str(input_p.parent / f"{input_p.stem}.proofread.srt")
    out_json = str(input_p.parent / f"{input_p.stem}.proofread.json")

    save_file(to_srt(proofread_track), out_file)
    save_file(to_json(proofread_track), out_json)

    console.rule("[bold green]校對完成[/bold green]")
    console.print(f"  ✔ 校對後 SRT:  [green]{out_file}[/green]")
    console.print(f"  ✔ 校對後 JSON: [green]{out_json}[/green]")

    table = Table(title="校對前後對照預覽 (前 6 句)")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("校對前文字", style="yellow")
    table.add_column("Qwen2.5 校對後文字", style="bold green")
    for orig, corr in zip(track.segments[:6], proofread_track.segments[:6]):
        table.add_row(str(orig.id), orig.text, corr.text)
    console.print(table)


@app.command("burn")
def burn_cmd(
    video_path: str = typer.Argument(..., help="來源影片檔案路徑 (MP4, MOV 等)"),
    subtitle_path: str = typer.Argument(..., help="字幕檔案路徑 (.srt, .vtt, 或 .json)"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="輸出影片路徑 (預設為同目錄 .hardsub.mp4)"),
    css: Optional[str] = typer.Option(None, "--css", help="CSS 樣式字串 (如 'font-size: 36px; color: #ffeb3b; -webkit-text-stroke: 3px #000; text-shadow: 2px 2px #000;')"),
    css_file: Optional[str] = typer.Option(None, "--css-file", help="外部 CSS 樣式檔案路徑 (.css)"),
    direction: Optional[str] = typer.Option(None, "--direction", "-d", help="排版方向: horizontal (橫式), vertical (直式)"),
    valign: Optional[str] = typer.Option(None, "--valign", help="垂直對齊: top (靠頂/齊頭), middle (垂直置中), bottom (靠底)"),
    halign: Optional[str] = typer.Option(None, "--halign", help="水平對齊: left (靠左), center (水平置中), right (靠右)"),
    padding: Optional[str] = typer.Option(None, "--padding", help="CSS 邊距簡寫 (如 '50 40' 或 '40' 或 '50 40 60 40')"),
    padding_top: Optional[int] = typer.Option(None, "--padding-top", help="頂部內距 (像素)"),
    padding_bottom: Optional[int] = typer.Option(None, "--padding-bottom", help="底部內距 (像素)"),
    padding_left: Optional[int] = typer.Option(None, "--padding-left", help="左側內距 (像素)"),
    padding_right: Optional[int] = typer.Option(None, "--padding-right", help="右側內距 (像素)"),
    font: Optional[str] = typer.Option(None, "--font", help="字型名稱 (預設 Noto Sans CJK TC)"),
    size: Optional[int] = typer.Option(None, "--size", "-s", help="字型大小 (像素，預設 32)"),
    color: Optional[str] = typer.Option(None, "--color", help="主要字型顏色 (Hex，如 #FFFFFF, #FFFF00)"),
    outline_color: Optional[str] = typer.Option(None, "--outline-color", help="描邊顏色 (Hex，預設 #000000)"),
    outline: Optional[float] = typer.Option(None, "--outline", help="描邊粗細 (像素，預設 2.5)"),
    shadow: Optional[float] = typer.Option(None, "--shadow", help="陰影偏移量 (像素，預設 1.2)"),
    pos_x: Optional[int] = typer.Option(None, "--x", help="精準絕對 X 座標 (像素，指定後將覆蓋對齊設定)"),
    pos_y: Optional[int] = typer.Option(None, "--y", help="精準絕對 Y 座標 (像素，指定後將覆蓋對齊設定)"),
    cpu: bool = typer.Option(False, "--cpu", help="強制使用 CPU (預設自動啟用 NVIDIA NVENC 硬體加速)"),
):
    """【Hardcopy 壓制】將字幕硬燒錄進影片中，支援 CSS 樣式字串/檔案、陰影字、描邊字、Web 盒模型與自訂排版"""
    v_path = Path(video_path).resolve()
    s_path = Path(subtitle_path).resolve()

    if not v_path.exists():
        console.print(f"[bold red]找不到來源影片: {video_path}[/bold red]")
        raise typer.Exit(code=1)
    if not s_path.exists():
        console.print(f"[bold red]找不到字幕檔案: {subtitle_path}[/bold red]")
        raise typer.Exit(code=1)

    # 1. 決定基礎樣式 (從 CSS 字串或 .css 檔案讀取)
    css_content = None
    if css_file:
        css_p = Path(css_file).resolve()
        if not css_p.exists():
            console.print(f"[bold red]找不到指定的 CSS 檔案: {css_file}[/bold red]")
            raise typer.Exit(code=1)
        css_content = css_p.read_text(encoding="utf-8")
    elif css:
        css_content = css

    if css_content:
        style = SubtitleStyle.from_css(css_content)
    else:
        style = SubtitleStyle()

    # 2. 允許 CLI 個別參數覆蓋或設定 (若有指定)
    if direction is not None:
        style.orientation = direction
    if valign is not None:
        style.vertical_align = valign
    if halign is not None:
        style.horizontal_align = halign
    if font is not None:
        style.font_name = font
    if size is not None:
        style.font_size = size
    if color is not None:
        style.primary_color = color
    if outline_color is not None:
        style.outline_color = outline_color
    if outline is not None:
        style.outline_width = outline
    if shadow is not None:
        style.shadow_offset = shadow
    if padding is not None:
        style.set_padding(*[int(p) for p in padding.split() if p.isdigit()])
    if padding_top is not None:
        style.padding_top = padding_top
    if padding_bottom is not None:
        style.padding_bottom = padding_bottom
    if padding_left is not None:
        style.padding_left = padding_left
    if padding_right is not None:
        style.padding_right = padding_right
    if pos_x is not None:
        style.pos_x = pos_x
    if pos_y is not None:
        style.pos_y = pos_y

    console.rule("[bold cyan]開始執行影片字幕硬燒錄 (Hardsub)[/bold cyan]")
    console.print(f"  來源影片: [yellow]{v_path}[/yellow]")
    console.print(f"  套用字幕: [yellow]{s_path}[/yellow]")
    if css_content:
        console.print(f"  樣式來源: [bold green]CSS 樣式解析套用成功[/bold green]")
    console.print(f"  字型外觀: [cyan]{style.font_name}[/cyan] ({style.font_size}px, 顏色: {style.primary_color}, 粗體: {style.bold})")
    console.print(f"  描邊特效: [cyan]{style.outline_color}[/cyan] ({style.outline_width}px)")
    console.print(f"  陰影特效: [cyan]{style.shadow_color}[/cyan] (偏移: {style.shadow_offset}px)")
    console.print(f"  排版方向: [magenta]{'直式 (Vertical)' if style.orientation == 'vertical' else '橫式 (Horizontal)'}[/magenta]")

    if style.pos_x is not None and style.pos_y is not None:
        console.print(f"  定位模式: [magenta]精準絕對座標 (X={style.pos_x}, Y={style.pos_y})[/magenta]")
    else:
        align_desc = f"{style.vertical_align}-{style.horizontal_align} (ASS Code: {style.ass_alignment})"
        padding_desc = f"上={style.padding_top}px, 右={style.padding_right}px, 下={style.padding_bottom}px, 左={style.padding_left}px"
        console.print(f"  對齊模式: [magenta]{align_desc}[/magenta]")
        console.print(f"  內距邊界: [magenta]{padding_desc}[/magenta]")

    try:
        out_file = burn_subtitles_to_video(
            video_path=str(v_path),
            subtitles_source=str(s_path),
            output_path=output,
            style=style,
            use_gpu=not cpu
        )
        console.rule("[bold green]影片壓制完成[/bold green]")
        console.print(f"  ✔ 燒錄影片已產出: [bold green]{out_file}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]壓制失敗: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="監聽主機 IP (0.0.0.0 可供區網存取)"),
    port: int = typer.Option(8000, "--port", "-p", help="監聽連接埠 (預設 8000)"),
    reload: bool = typer.Option(False, "--reload", help="啟用程式碼即時熱重載"),
):
    """【Web 工作台服務】啟動 AutoSubtitle AI 視覺化網頁工作台"""
    import uvicorn
    console.rule("[bold cyan]啟動 AutoSubtitle AI 網頁工作台[/bold cyan]")
    console.print(f"  ✔ 本地瀏覽器網址: [bold green]http://{host}:{port}[/bold green]")
    console.print(f"  ✔ API 文件:        [cyan]http://{host}:{port}/docs[/cyan]")
    console.print(f"  ✔ 按下 Ctrl+C 可停止服務\n")
    uvicorn.run("src.api.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
