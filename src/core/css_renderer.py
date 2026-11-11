import base64
import hashlib
import json
import logging
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..schemas.subtitle import SubtitleStyle, SubtitleTrack
from .font_manager import resolve_font_file

logger = logging.getLogger(__name__)

_PS_RENDER_SCRIPT = Path(__file__).resolve().parent / "_cdp_render.ps1"
_WINDOWS_BROWSER_CANDIDATES = (
    ("/mnt/c/Program Files/Google/Chrome/Application/chrome.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ("/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ("/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)
_LINUX_BROWSER_CANDIDATES = ("google-chrome", "chromium", "chromium-browser", "microsoft-edge")


def normalize_css_text(text: str) -> str:
    """將字幕中的 <br> / <br/> / \\N 正規化為純換行符號 \\n。"""
    if not text:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    return s.replace("\\N", "\n").replace("\r\n", "\n")


def _to_windows_path(path: Path) -> str:
    """將 WSL /mnt/<drive>/... 路徑轉換為 Windows 路徑；其餘嘗試使用 wslpath。"""
    s = str(path.resolve())
    if len(s) >= 6 and s.startswith("/mnt/") and s[6:7] in ("/", ""):
        drive = s[5].upper()
        rest = s[6:].replace("/", "\\")
        return f"{drive}:{rest or '\\'}"
    if os.name == "nt":
        return s
    res = subprocess.run(["wslpath", "-w", s], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return s


def _to_file_uri(path: Path, for_windows_browser: bool) -> str:
    """產生瀏覽器可直接讀取的 file:// URI。"""
    if for_windows_browser:
        win_path = _to_windows_path(path).replace("\\", "/")
        if len(win_path) >= 2 and win_path[1] == ":":
            return f"file:///{win_path}"
    return path.resolve().as_uri()


def _find_playwright_deps_lib_dir() -> Optional[str]:
    """若使用者目錄下有免 sudo 解壓的 Playwright 依賴函式庫目錄，回傳該路徑供 LD_LIBRARY_PATH 使用。"""
    deps_dir = Path.home() / ".cache" / "ms-playwright" / "deps" / "usr" / "lib" / "x86_64-linux-gnu"
    return str(deps_dir) if deps_dir.is_dir() else None


def _build_linux_browser_env() -> Dict[str, str]:
    """組裝原生 Linux Chromium 所需的環境變數（自動帶入本機免 sudo 依賴庫）。"""
    env = dict(os.environ)
    deps_dir = _find_playwright_deps_lib_dir()
    if deps_dir:
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{deps_dir}:{existing}" if existing else deps_dir
    return env


def _find_playwright_chromium_exe() -> Optional[str]:
    """檢查 Playwright 及對應 Chromium / Headless Shell 是否已安裝並回傳可執行檔路徑。"""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return None
    cache_dir = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or (Path.home() / ".cache" / "ms-playwright"))
    if not cache_dir.exists():
        return None
    for pattern in (
        "chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
        "chromium_headless_shell-*/chrome-headless-shell-linux/chrome-headless-shell",
        "chromium_headless_shell-*/chrome-linux64/chrome-headless-shell",
        "chromium_headless_shell-*/chrome-linux/headless_shell",
        "chromium-*/chrome-linux64/chrome",
        "chromium-*/chrome-linux/chrome",
    ):
        matches = sorted(cache_dir.glob(pattern))
        if matches and matches[-1].is_file():
            return str(matches[-1])
    return None


def detect_headless_browser() -> Optional[Tuple[str, str]]:
    """
    偵測可用的 Headless Chromium 核心。
    回傳 ("playwright", exe_path) / ("linux", binary_path) / ("wsl_windows", windows_exe_path)；若無則回傳 None。
    """
    pw_exe = _find_playwright_chromium_exe()
    if pw_exe:
        return ("playwright", pw_exe)

    for exe in _LINUX_BROWSER_CANDIDATES:
        found = shutil.which(exe)
        if found:
            return ("linux", found)

    if shutil.which("powershell.exe"):
        for wsl_path, win_path in _WINDOWS_BROWSER_CANDIDATES:
            if Path(wsl_path).exists():
                return ("wsl_windows", win_path)
    return None


def build_css_timeline_plan(
    track: SubtitleTrack,
    video_duration: float,
) -> Tuple[List[Dict[str, str]], List[Tuple[str, float]]]:
    """
    將字幕軌道切分為互不重疊的時間區段並去重文字內容。

    回傳:
        (unique_render_items, concat_entries)
        - unique_render_items: [{"file": "sub_0001.png", "text": "..."}]
        - concat_entries: [("blank.png" | "sub_0001.png", duration_sec), ...]
    """
    total_dur = max(float(video_duration or 0.0), float(track.duration or 0.0))
    active_segs = []
    for seg in track.segments:
        norm = normalize_css_text(seg.text)
        if not norm.strip():
            continue
        start = max(0.0, float(seg.start))
        end = max(start, float(seg.end))
        if end - start > 1e-4:
            active_segs.append((start, end, norm))
            if end > total_dur:
                total_dur = end

    if total_dur <= 1e-4:
        total_dur = 0.1

    if not active_segs:
        return ([], [("blank.png", total_dur)])

    boundaries = {0.0, total_dur}
    for start, end, _ in active_segs:
        boundaries.add(start)
        boundaries.add(end)
    pts = sorted(boundaries)

    text_to_file: Dict[str, str] = {}
    unique_items: List[Dict[str, str]] = []
    raw_entries: List[Tuple[str, float]] = []

    for i in range(len(pts) - 1):
        t0, t1 = pts[i], pts[i + 1]
        dur = t1 - t0
        if dur <= 1e-4:
            continue
        mid = 0.5 * (t0 + t1)
        texts = [txt for s, e, txt in active_segs if s <= mid <= e]
        if not texts:
            fname = "blank.png"
        else:
            combined = "\n".join(texts)
            fname = text_to_file.get(combined)
            if fname is None:
                idx = len(unique_items) + 1
                fname = f"sub_{idx:04d}.png"
                text_to_file[combined] = fname
                unique_items.append({"file": fname, "text": combined})
        raw_entries.append((fname, dur))

    # 合併相鄰相同的畫面區間，減少 concat 項目與不必要的解碼
    merged: List[Tuple[str, float]] = []
    for fname, dur in raw_entries:
        if merged and merged[-1][0] == fname:
            merged[-1] = (fname, merged[-1][1] + dur)
        else:
            merged.append((fname, dur))

    return (unique_items, merged)


def build_ffconcat_content(concat_entries: List[Tuple[str, float]]) -> str:
    """組裝 FFmpeg concat demuxer 所需的 ffconcat 內容。"""
    if not concat_entries:
        concat_entries = [("blank.png", 0.1)]
    lines = ["ffconcat version 1.0"]
    for fname, dur in concat_entries:
        lines.append(f"file '{fname}'")
        lines.append(f"duration {max(dur, 1e-4):.6f}")
    # ffconcat 規範需在最後重複最後一幀檔名以確保前一段 duration 完整生效
    lines.append(f"file '{concat_entries[-1][0]}'")
    return "\n".join(lines) + "\n"


def build_subtitle_html(
    style: SubtitleStyle,
    width: int,
    height: int,
    font_face_uri: Optional[str] = None,
) -> str:
    """產生與 Web Studio 前端預覽完全一致的透明背景 HTML/CSS 渲染頁面。"""
    align_items = {"top": "flex-start", "middle": "center", "bottom": "flex-end"}[style.vertical_align]
    justify_content = {"left": "flex-start", "center": "center", "right": "flex-end"}[style.horizontal_align]
    is_vertical = style.orientation == "vertical"
    writing_mode = "vertical-rl" if is_vertical else "horizontal-tb"
    if is_vertical:
        text_align = {"top": "start", "middle": "center", "bottom": "end"}[style.vertical_align]
    else:
        text_align = style.horizontal_align

    font_face_block = ""
    font_family_css = f'"{style.font_name}", "Noto Sans CJK TC", "Microsoft JhengHei", sans-serif'
    if font_face_uri:
        font_face_block = f"""
@font-face {{
  font-family: '__AutoSubCustomFont__';
  src: url('{font_face_uri}');
  font-weight: 100 900;
  font-style: normal italic;
}}
"""
        font_family_css = f"'__AutoSubCustomFont__', {font_family_css}"

    stroke_css = "-webkit-text-stroke: 0px transparent; paint-order: normal;"
    if style.outline_enabled and style.outline_width > 0:
        stroke_css = (
            f"-webkit-text-stroke: {style.outline_width * 2:.1f}px {style.outline_color}; "
            "paint-order: stroke fill;"
        )

    shadow_css = (
        f"text-shadow: {style.shadow_offset:.1f}px {style.shadow_offset:.1f}px {style.shadow_offset * 1.5:.1f}px {style.shadow_color};"
        if style.shadow_offset > 0
        else "text-shadow: none;"
    )

    pos_override_css = ""
    if style.pos_x is not None and style.pos_y is not None:
        tx = {"left": "0%", "center": "-50%", "right": "-100%"}[style.horizontal_align]
        ty = {"top": "0%", "middle": "-50%", "bottom": "-100%"}[style.vertical_align]
        pos_override_css = (
            f"position: fixed; left: {style.pos_x}px; top: {style.pos_y}px; "
            f"transform: translate({tx}, {ty});"
        )

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<style>
{font_face_block}
* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}
html, body {{
  width: {width}px;
  height: {height}px;
  overflow: hidden;
  background: transparent !important;
}}
#subtitle-overlay-container {{
  position: fixed;
  inset: 0;
  width: {width}px;
  height: {height}px;
  display: flex;
  align-items: {align_items};
  justify-content: {justify_content};
  padding: {style.padding_top}px {style.padding_right}px {style.padding_bottom}px {style.padding_left}px;
  overflow: hidden;
  background: transparent;
}}
#subtitle-overlay {{
  font-family: {font_family_css};
  font-size: {style.font_size}px;
  line-height: 1.5;
  padding-left: 4px;
  padding-right: 4px;
  color: {style.primary_color};
  font-weight: {'bold' if style.bold else 'normal'};
  font-style: {'italic' if style.italic else 'normal'};
  letter-spacing: {style.letter_spacing}px;
  opacity: {style.opacity};
  {stroke_css}
  {shadow_css}
  writing-mode: {writing_mode};
  text-align: {text_align};
  white-space: pre-wrap;
  {pos_override_css}
}}
</style>
</head>
<body>
  <div id="subtitle-overlay-container">
    <div id="subtitle-overlay"></div>
  </div>
  <script>
    window.setSubText = function(txt) {{
      const el = document.getElementById('subtitle-overlay');
      const normalized = (txt || '').replace(/<br\\s*\\/?>/gi, '\\n').replace(/\\\\N/g, '\\n');
      if (!normalized.trim()) {{
        el.textContent = '';
        el.style.display = 'none';
      }} else {{
        el.textContent = normalized;
        el.style.display = '';
      }}
      void el.offsetHeight;
      return new Promise(r => requestAnimationFrame(() => r(true)));
    }};
  </script>
</body>
</html>
"""


class _CdpSocketClient:
    """純 Python 標準庫實作的極簡本機 WebSocket CDP 用戶端 (供原生 Linux Chrome 使用)。"""

    def __init__(self, ws_url: str, timeout: float = 15.0):
        match = re.match(r"^ws://([^:/]+):(\d+)(/.*)$", ws_url)
        if not match:
            raise ValueError(f"不支援的 CDP WebSocket URL: {ws_url}")
        host, port_str, path = match.groups()
        self.sock = socket.create_connection((host, int(port_str)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port_str}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("CDP WebSocket 握手失敗")
            buf += chunk
        self._extra = buf.split(b"\r\n\r\n", 1)[1]
        self._next_id = 1

    def _read_exact(self, n: int) -> bytes:
        out = bytearray()
        if self._extra:
            take = min(n, len(self._extra))
            out.extend(self._extra[:take])
            self._extra = self._extra[take:]
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise RuntimeError("CDP WebSocket 連線中斷")
            out.extend(chunk)
        return bytes(out)

    def _send_text(self, payload: str) -> None:
        data = payload.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        ln = len(data)
        if ln < 126:
            header.append(0x80 | ln)
        elif ln < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", ln))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", ln))
        header.extend(mask)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + masked)

    def _recv_message(self) -> str:
        fragments = bytearray()
        while True:
            b1, b2 = self._read_exact(2)
            fin = (b1 & 0x80) != 0
            opcode = b1 & 0x0F
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            if (b2 & 0x80) != 0:
                mask = self._read_exact(4)
                raw = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read_exact(length)))
            else:
                raw = self._read_exact(length)
            if opcode == 0x8:
                raise RuntimeError("CDP WebSocket 已關閉")
            if opcode == 0x9:
                # 忽略或簡易跳過 ping
                continue
            fragments.extend(raw)
            if fin:
                return fragments.decode("utf-8")

    def call(self, method: str, params: Optional[dict] = None) -> dict:
        req_id = self._next_id
        self._next_id += 1
        msg = {"id": req_id, "method": method}
        if params is not None:
            msg["params"] = params
        self._send_text(json.dumps(msg))
        while True:
            resp = json.loads(self._recv_message())
            if resp.get("id") == req_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP 呼叫 {method} 失敗: {resp['error']}")
                return resp.get("result", {})

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass


def _render_via_linux_chrome(
    browser_exe: str,
    html_path: Path,
    manifest: List[Dict[str, str]],
    out_dir: Path,
    width: int,
    height: int,
) -> None:
    """在原生 Linux 環境啟動 Headless Chrome/Chromium 並逐段截圖為透明 PNG。"""
    profile_dir = Path(tempfile.mkdtemp(prefix="autosub_linux_cdp_"))
    proc = subprocess.Popen(
        [
            browser_exe,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-sandbox",
            "--remote-allow-origins=*",
            "--allow-file-access-from-files",
            f"--user-data-dir={profile_dir}",
            "--remote-debugging-port=0",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    client: Optional[_CdpSocketClient] = None
    try:
        port_file = profile_dir / "DevToolsActivePort"
        port = None
        for _ in range(80):
            if port_file.exists():
                lines = port_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                if lines and lines[0].strip().isdigit():
                    port = lines[0].strip()
                    break
            time.sleep(0.05)
        if not port:
            raise RuntimeError("Linux Headless Chrome 無法取得 DevToolsActivePort")

        ws_url = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                    targets = json.loads(r.read().decode("utf-8"))
                page = next((t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)
                if page:
                    ws_url = page["webSocketDebuggerUrl"]
                    break
            except Exception:
                pass
            time.sleep(0.05)
        if not ws_url:
            raise RuntimeError("Linux Headless Chrome 找不到可用頁面目標")

        client = _CdpSocketClient(ws_url)
        client.call("Page.enable")
        client.call("Runtime.enable")
        client.call("Emulation.setDeviceMetricsOverride", {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": False,
        })
        client.call("Emulation.setDefaultBackgroundColorOverride", {
            "color": {"r": 0, "g": 0, "b": 0, "a": 0},
        })
        client.call("Page.navigate", {"url": _to_file_uri(html_path, for_windows_browser=False)})
        client.call("Runtime.evaluate", {
            "expression": (
                "new Promise(r => { if (document.readyState === 'complete') "
                "document.fonts.ready.then(() => requestAnimationFrame(() => r('ok'))); "
                "else window.addEventListener('load', () => document.fonts.ready.then(() => requestAnimationFrame(() => r('ok')))); })"
            ),
            "awaitPromise": True,
        })

        client.call("Runtime.evaluate", {"expression": "window.setSubText('')", "awaitPromise": True})
        blank = client.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        (out_dir / "blank.png").write_bytes(base64.b64decode(blank["data"]))

        for item in manifest:
            js_expr = f"window.setSubText({json.dumps(item['text'], ensure_ascii=False)})"
            client.call("Runtime.evaluate", {"expression": js_expr, "awaitPromise": True})
            shot = client.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            (out_dir / item["file"]).write_bytes(base64.b64decode(shot["data"]))
    finally:
        if client is not None:
            client.close()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


def _render_via_playwright(
    html_path: Path,
    manifest: List[Dict[str, str]],
    out_dir: Path,
    width: int,
    height: int,
) -> None:
    """使用原生 Linux Playwright Chromium 渲染透明字幕 PNG (不依賴 Windows Interop)。"""
    from playwright.sync_api import sync_playwright

    launch_env = _build_linux_browser_env()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, env=launch_env)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(_to_file_uri(html_path, for_windows_browser=False), wait_until="load")
            page.evaluate("() => document.fonts.ready")
            page.evaluate("() => window.setSubText('')")
            page.screenshot(path=str(out_dir / "blank.png"), omit_background=True)
            for item in manifest:
                page.evaluate("(txt) => window.setSubText(txt)", item["text"])
                page.screenshot(path=str(out_dir / item["file"]), omit_background=True)
        finally:
            browser.close()


def _refresh_wsl_interop_env() -> Dict[str, str]:
    """若背景 WSL daemon 繼承了已關閉的 WSL_INTEROP socket，自動改用目前存活的 socket。"""
    env = dict(os.environ)
    cur = env.get("WSL_INTEROP")
    if cur and Path(cur).exists():
        return env
    wsl_run = Path("/run/WSL")
    if wsl_run.is_dir():
        sockets = sorted(wsl_run.glob("*_interop"), key=lambda p: p.stat().st_mtime, reverse=True)
        for sock in sockets:
            env["WSL_INTEROP"] = str(sock)
            break
    return env


def _render_via_wsl_windows_browser(
    browser_win_exe: str,
    html_path: Path,
    manifest_path: Path,
    out_dir: Path,
    width: int,
    height: int,
) -> None:
    """從 WSL 呼叫 Windows Headless Chrome/Edge CDP 渲染透明字幕 PNG。"""
    if not _PS_RENDER_SCRIPT.exists():
        raise FileNotFoundError(f"找不到 CDP 渲染腳本: {_PS_RENDER_SCRIPT}")
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", _to_windows_path(_PS_RENDER_SCRIPT),
        "-BrowserExe", browser_win_exe,
        "-HtmlPath", _to_windows_path(html_path),
        "-ManifestJsonPath", _to_windows_path(manifest_path),
        "-OutDir", _to_windows_path(out_dir),
        "-Width", str(width),
        "-Height", str(height),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=_refresh_wsl_interop_env())
    if res.returncode != 0:
        raise RuntimeError(f"Windows Headless Chrome 渲染字幕失敗: {res.stderr or res.stdout}")


def render_css_subtitles_to_pngs(
    track: SubtitleTrack,
    style: SubtitleStyle,
    width: int,
    height: int,
    video_duration: float,
    work_dir: Path,
) -> Path:
    """
    使用真實瀏覽器 CSS 渲染引擎產出每句透明背景 PNG 與 ffconcat 時間軸檔。

    回傳生成的 `subs.ffconcat` 路徑 (位於 work_dir 內)。
    """
    browser = detect_headless_browser()
    if browser is None:
        raise RuntimeError("找不到可用的 Headless Chrome / Edge，無法執行 CSS 精準燒錄；請改用 ASS 模式或安裝 Chrome。")
    kind, browser_path = browser
    for_win = (kind == "wsl_windows")

    work_dir.mkdir(parents=True, exist_ok=True)

    # 若指定字型對應實際檔案，提供給瀏覽器透過 @font-face 載入；若在 Linux 路徑則暫時複製進 work_dir 以便 Windows Chrome 讀取
    font_face_uri: Optional[str] = None
    resolved = resolve_font_file(style.font_name)
    if resolved:
        font_file_path = Path(resolved[0])
        if font_file_path.exists():
            if for_win and not str(font_file_path).startswith("/mnt/"):
                local_font = work_dir / font_file_path.name
                shutil.copyfile(font_file_path, local_font)
                font_face_uri = _to_file_uri(local_font, for_windows_browser=True)
            else:
                font_face_uri = _to_file_uri(font_file_path, for_windows_browser=for_win)

    manifest, concat_entries = build_css_timeline_plan(track, video_duration)

    html_path = work_dir / "render.html"
    html_path.write_text(build_subtitle_html(style, width, height, font_face_uri=font_face_uri), encoding="utf-8")

    manifest_path = work_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    if kind == "playwright":
        _render_via_playwright(html_path, manifest, work_dir, width, height)
    elif for_win:
        _render_via_wsl_windows_browser(browser_path, html_path, manifest_path, work_dir, width, height)
    else:
        _render_via_linux_chrome(browser_path, html_path, manifest, work_dir, width, height)

    concat_path = work_dir / "subs.ffconcat"
    concat_path.write_text(build_ffconcat_content(concat_entries), encoding="utf-8")
    return concat_path
