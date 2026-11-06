import os
import shutil
import struct
import subprocess
import http.client
import ipaddress
import socket
import ssl
import tempfile
import urllib.parse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FONTS_DIR = BASE_DIR / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_FONT_EXTS = {".ttf", ".otf", ".ttc", ".woff2", ".woff"}

# 內建系統基礎字型 (Ubuntu / Linux Fontconfig 已內建)
BUILTIN_SYSTEM_FONTS: List[Dict[str, Any]] = [
    {
        "id": "builtin-noto-sans",
        "family": "Noto Sans CJK TC",
        "display_name": "思源黑體 (Noto Sans CJK TC)",
        "category": "builtin",
        "installed": True,
        "url": None,
        "filename": None,
        "description": "系統內建現代無襯線黑體"
    },
    {
        "id": "builtin-noto-serif",
        "family": "Noto Serif CJK TC",
        "display_name": "思源宋體 (Noto Serif CJK TC)",
        "category": "builtin",
        "installed": True,
        "url": None,
        "filename": None,
        "description": "系統內建傳統襯線明體"
    },
    {
        "id": "builtin-arial",
        "family": "Arial",
        "display_name": "Arial (英文無襯線)",
        "category": "builtin",
        "installed": True,
        "url": None,
        "filename": None,
        "description": "經典英文無襯線字型"
    }
]

# 精選可一鍵下載安裝的開源免費商用繁體中文字型包
INSTALLABLE_OPEN_FONTS: List[Dict[str, Any]] = [
    {
        "id": "openhuninn",
        "family": "jf-openhuninn-2.0",
        "display_name": "jf open 粉圓 2.0 (綜藝圓體)",
        "filename": "jf-openhuninn-2.0.ttf",
        "download_url": "https://github.com/justfont/open-huninn-font/releases/download/v2.0/jf-openhuninn-2.0.ttf",
        "description": "圓潤飽滿，YouTube / Vlog / 綜藝短片最熱門免費商用圓體",
        "license": "SIL OFL 1.1"
    },
    {
        "id": "lxgw-wenkai",
        "family": "LXGW WenKai TC",
        "display_name": "霞鶩文楷 TC Bold (手寫楷體)",
        "filename": "LXGWWenKaiTC-Bold.ttf",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/lxgwwenkaitc/LXGWWenKaiTC-Bold.ttf",
        "description": "溫潤手寫鋼筆楷體，極適合音樂 MV 歌詞、紀錄片與電影對白",
        "license": "SIL OFL 1.1"
    },
    {
        "id": "iansui",
        "family": "Iansui",
        "display_name": "芫荽體 (文青硬筆楷書)",
        "filename": "Iansui-Regular.ttf",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/iansui/Iansui-Regular.ttf",
        "description": "貼近臺灣繁體字形的硬筆仿楷體，清晰溫暖、適合敘事與教學影片",
        "license": "SIL OFL 1.1"
    },
    {
        "id": "chocolate-sans",
        "family": "Chocolate Classical Sans",
        "display_name": "巧克力古典黑體 (人文黑體)",
        "filename": "ChocolateClassicalSans-Regular.ttf",
        "download_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/chocolateclassicalsans/ChocolateClassicalSans-Regular.ttf",
        "description": "融合傳統鉛字印刷韻味的人文黑體，適合深度訪談與知識型頻道",
        "license": "SIL OFL 1.1"
    },
    {
        "id": "cubic-11",
        "family": "Cubic 11",
        "display_name": "俐方體 11號 (復古像素體)",
        "filename": "Cubic_11.ttf",
        "download_url": "https://raw.githubusercontent.com/ACh-K/Cubic-11/main/fonts/ttf/Cubic_11.ttf",
        "description": "繁體中文點陣像素字型，適合遊戲實況、綜藝特效字與復古風格",
        "license": "SIL OFL 1.1"
    }
]

# Windows 本機常見繁中字型對應表 (支援 WSL /mnt/c/Windows/Fonts 或 C:\Windows\Fonts)
WINDOWS_SYSTEM_FONT_CANDIDATES: List[Dict[str, str]] = [
    {
        "id": "win-msjhbd",
        "filename": "msjhbd.ttc",
        "family": "Microsoft JhengHei",
        "display_name": "微軟正黑體 Bold (Windows 系統字型)",
        "description": "從本機 Windows 字型庫匯入微軟正黑體粗體"
    },
    {
        "id": "win-kaiu",
        "filename": "kaiu.ttf",
        "family": "DFKai-SB",
        "display_name": "標楷體 DFKai-SB (Windows 系統字型)",
        "description": "從本機 Windows 字型庫匯入標準標楷體"
    }
]


def _parse_ttf_name_table(font_path: Path) -> Optional[str]:
    """
    純 Python 解析 TrueType / OpenType (.ttf / .otf) 的 'name' 表，
    提取英文或本地化的 Font Family Name (NameID = 1)，作為無 fc-query 時的可靠備援。
    """
    try:
        data = font_path.read_bytes()
        if len(data) < 12:
            return None

        # 若為 TTC 字型集合，跳過 TTC Header 讀取第一個字型偏移
        if data[:4] == b"ttcf":
            if len(data) < 16:
                return None
            num_fonts = struct.unpack(">I", data[8:12])[0]
            if num_fonts < 1:
                return None
            offset0 = struct.unpack(">I", data[12:16])[0]
            num_tables = struct.unpack(">H", data[offset0 + 4:offset0 + 6])[0]
            table_dir_offset = offset0 + 12
        else:
            num_tables = struct.unpack(">H", data[4:6])[0]
            table_dir_offset = 12

        name_table_offset = None
        for i in range(num_tables):
            entry_pos = table_dir_offset + i * 16
            if entry_pos + 16 > len(data):
                break
            tag = data[entry_pos:entry_pos + 4]
            if tag == b"name":
                name_table_offset = struct.unpack(">I", data[entry_pos + 8:entry_pos + 12])[0]
                break

        if name_table_offset is None or name_table_offset + 6 > len(data):
            return None

        count = struct.unpack(">H", data[name_table_offset + 2:name_table_offset + 4])[0]
        str_offset = name_table_offset + struct.unpack(">H", data[name_table_offset + 4:name_table_offset + 6])[0]

        candidates = []
        for i in range(count):
            rec_pos = name_table_offset + 6 + i * 12
            if rec_pos + 12 > len(data):
                break
            platform_id, encoding_id, lang_id, name_id, length, offset = struct.unpack(
                ">HHHHHH", data[rec_pos:rec_pos + 12]
            )
            # NameID 1 = Font Family Name
            if name_id != 1:
                continue
            raw_bytes = data[str_offset + offset:str_offset + offset + length]
            try:
                if platform_id in (0, 3):
                    name_str = raw_bytes.decode("utf-16-be").strip("\x00").strip()
                elif platform_id == 1 and encoding_id == 0:
                    name_str = raw_bytes.decode("mac_roman", errors="ignore").strip("\x00").strip()
                else:
                    continue
                if name_str and not name_str.startswith("."):
                    # 優先偏好英文 ASCII Family Name (對 libass 與 CSS 最穩定)
                    is_ascii = all(ord(c) < 128 for c in name_str)
                    candidates.append((0 if is_ascii else 1, name_str))
            except Exception:
                continue

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
    except Exception as e:
        logger.debug(f"TTF name table 解析失敗 ({font_path.name}): {e}")
    return None


def extract_font_family(font_path: Path) -> Dict[str, str]:
    """
    解析字型檔案的真實 Family Name 與顯示名稱。
    優先使用系統 `fc-query` (與 libass 100% 同源)，若不可用則退回純 Python TTF 解析器。
    """
    family_primary = ""
    family_display = ""

    # 1. 嘗試使用 fc-query (Linux / WSL 內與 libass 使用相同 Fontconfig 解析引擎)
    try:
        res = subprocess.run(
            ["fc-query", "--format=%{family}\\n", str(font_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            first_line = res.stdout.strip().splitlines()[0]
            names = [n.strip() for n in first_line.split(",") if n.strip()]
            if names:
                family_primary = names[0]
                family_display = " / ".join(names[:2]) if len(names) > 1 else names[0]
    except Exception:
        pass

    # 2. 備援：使用純 Python 解析 TrueType name table
    if not family_primary:
        parsed = _parse_ttf_name_table(font_path)
        if parsed:
            family_primary = parsed
            family_display = parsed

    # 3. 最終備援：使用檔名 Stem
    if not family_primary:
        family_primary = font_path.stem
        family_display = font_path.stem

    return {
        "family": family_primary,
        "display_name": family_display
    }


def list_installed_custom_fonts() -> List[Dict[str, Any]]:
    """掃描專案 fonts/ 目錄下所有已安裝的自訂字型"""
    custom_fonts = []
    if not FONTS_DIR.exists():
        return custom_fonts

    preset_by_filename = {item["filename"]: item for item in INSTALLABLE_OPEN_FONTS}
    win_by_filename = {item["filename"]: item for item in WINDOWS_SYSTEM_FONT_CANDIDATES}

    for p in sorted(FONTS_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
        if not p.is_file() or p.suffix.lower() not in ALLOWED_FONT_EXTS:
            continue

        info = extract_font_family(p)
        size_mb = round(p.stat().st_size / (1024 * 1024), 2)

        preset_meta = preset_by_filename.get(p.name) or win_by_filename.get(p.name)
        display_name = preset_meta["display_name"] if preset_meta else f"{info['display_name']} ({p.name})"

        custom_fonts.append({
            "id": preset_meta["id"] if preset_meta else f"custom-{p.stem}",
            "family": info["family"],
            "display_name": display_name,
            "filename": p.name,
            "url": f"/fonts/{p.name}",
            "absolute_path": str(p),
            "size_mb": size_mb,
            "category": "custom",
            "installed": True
        })

    return custom_fonts


def _find_windows_fonts_dir() -> Optional[Path]:
    """尋找本機 Windows 字型目錄 (支援原生 Windows 或 WSL2 /mnt/c/Windows/Fonts)"""
    candidates = [
        Path("/mnt/c/Windows/Fonts"),
        Path("C:/Windows/Fonts"),
    ]
    for c in candidates:
        try:
            if c.exists() and c.is_dir():
                return c
        except Exception:
            continue
    return None


def get_font_catalog() -> Dict[str, Any]:
    """
    回傳完整字型目錄：
    - installed: 已安裝字型 (包含專案 fonts/ 自訂字型 + 系統內建字型)
    - presets: 可一鍵下載安裝的開源繁中字幕字型包 (含是否已安裝狀態)
    - windows_fonts: 可一鍵從本機 Windows 匯入的字型
    """
    custom_installed = list_installed_custom_fonts()
    installed_filenames = {f["filename"] for f in custom_installed}

    presets_status = []
    for item in INSTALLABLE_OPEN_FONTS:
        is_inst = item["filename"] in installed_filenames
        presets_status.append({
            **item,
            "installed": is_inst,
            "url": f"/fonts/{item['filename']}" if is_inst else None
        })

    win_dir = _find_windows_fonts_dir()
    windows_status = []
    if win_dir:
        for w in WINDOWS_SYSTEM_FONT_CANDIDATES:
            src_file = win_dir / w["filename"]
            if src_file.exists():
                is_inst = w["filename"] in installed_filenames
                windows_status.append({
                    **w,
                    "available_on_host": True,
                    "installed": is_inst,
                    "url": f"/fonts/{w['filename']}" if is_inst else None
                })

    return {
        "fonts_dir": str(FONTS_DIR),
        "installed": custom_installed + BUILTIN_SYSTEM_FONTS,
        "custom_count": len(custom_installed),
        "presets": presets_status,
        "windows_fonts": windows_status
    }


def validate_font_file(path: Path) -> None:
    with path.open("rb") as stream:
        if stream.read(4) not in (b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"wOFF", b"wOF2"):
            raise ValueError("內容不是支援的字型檔案")
    try:
        result = subprocess.run(["fc-query", "--format=%{family}", str(path)], capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        if _parse_ttf_name_table(path):
            return
        raise ValueError("無法驗證字型，請安裝 Fontconfig 後再試")
    except subprocess.TimeoutExpired as error:
        raise ValueError("字型驗證逾時") from error
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("字型內容損壞或無法解析")


def install_font_from_file(source_path: str, custom_filename: Optional[str] = None) -> Dict[str, Any]:
    """從本機檔案路徑安裝字型至專案 fonts/ 目錄"""
    src = Path(source_path).resolve()
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"找不到字型檔案: {source_path}")

    safe_name = Path(custom_filename or src.name).name
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_FONT_EXTS:
        raise ValueError(f"不支援的字型副檔名 '{ext}'，僅支援: {', '.join(sorted(ALLOWED_FONT_EXTS))}")

    dest = FONTS_DIR / safe_name
    with tempfile.NamedTemporaryFile(dir=FONTS_DIR, prefix=".installing_", delete=False) as temporary:
        staged = Path(temporary.name)
    try:
        shutil.copyfile(src, staged)
        validate_font_file(staged)
        staged.replace(dest)
    finally:
        staged.unlink(missing_ok=True)

    info = extract_font_family(dest)
    return {
        "filename": safe_name,
        "family": info["family"],
        "display_name": info["display_name"],
        "url": f"/fonts/{safe_name}",
        "absolute_path": str(dest),
        "size_mb": round(dest.stat().st_size / (1024 * 1024), 2)
    }


def _download_font(url: str, destination: Path) -> None:
    for _ in range(6):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("字型下載僅接受公開 HTTP/HTTPS URL")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("字型下載不允許本機或私人網路位址")

        connection = http.client.HTTPConnection(parsed.hostname, port, timeout=60)
        try:
            # Connect to the checked IP; resolving the hostname again would allow DNS rebinding.
            connection.sock = socket.create_connection((addresses[0][4][0], port), timeout=60)
            if parsed.scheme == "https":
                connection.sock = ssl.create_default_context().wrap_socket(connection.sock, server_hostname=parsed.hostname)
            target = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
            connection.request("GET", target, headers={"User-Agent": "AutoSubtitle-FontInstaller/1.0"})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("字型下載重新導向缺少 Location")
                url = urllib.parse.urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(f"字型下載失敗: HTTP {response.status}")
            size = 0
            with destination.open("wb") as output:
                while chunk := response.read(65536):
                    size += len(chunk)
                    if size > 128 * 1024 * 1024:
                        raise ValueError("字型檔案超過 128 MB")
                    output.write(chunk)
            validate_font_file(destination)
            return
        finally:
            connection.close()
    raise ValueError("字型下載重新導向次數過多")


def install_font_from_url(url: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """從遠端 URL 下載並安裝字型至專案 fonts/ 目錄"""
    if not filename:
        url_path = urllib.parse.urlparse(url).path
        filename = Path(url_path).name or "downloaded_font.ttf"

    safe_name = Path(filename).name
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_FONT_EXTS:
        raise ValueError(f"URL 檔案副檔名 '{ext}' 非有效字型格式 ({', '.join(sorted(ALLOWED_FONT_EXTS))})")

    dest = FONTS_DIR / safe_name
    with tempfile.NamedTemporaryFile(dir=FONTS_DIR, prefix=".downloading_", delete=False) as temp:
        temp_dest = Path(temp.name)
    try:
        _download_font(url, temp_dest)
        temp_dest.replace(dest)
    finally:
        temp_dest.unlink(missing_ok=True)

    info = extract_font_family(dest)
    return {
        "filename": safe_name,
        "family": info["family"],
        "display_name": info["display_name"],
        "url": f"/fonts/{safe_name}",
        "absolute_path": str(dest),
        "size_mb": round(dest.stat().st_size / (1024 * 1024), 2)
    }


def install_preset_or_windows_font(preset_id: str) -> Dict[str, Any]:
    """根據精選開源字型 ID 或 Windows 系統字型 ID 一鍵安裝"""
    # 1. 檢查是否為開源字型包
    for item in INSTALLABLE_OPEN_FONTS:
        if item["id"] == preset_id:
            res = install_font_from_url(item["download_url"], filename=item["filename"])
            res["display_name"] = item["display_name"]
            res["id"] = item["id"]
            return res

    # 2. 檢查是否為 Windows 系統字型匯入
    win_dir = _find_windows_fonts_dir()
    if win_dir:
        for w in WINDOWS_SYSTEM_FONT_CANDIDATES:
            if w["id"] == preset_id:
                src_file = win_dir / w["filename"]
                if not src_file.exists():
                    raise FileNotFoundError(f"找不到本機 Windows 字型: {src_file}")
                res = install_font_from_file(str(src_file), custom_filename=w["filename"])
                res["display_name"] = w["display_name"]
                res["id"] = w["id"]
                return res

    raise ValueError(f"未知的字型預設集代號: {preset_id}")


def delete_custom_font(filename: str) -> bool:
    """刪除 fonts/ 目錄下的自訂字型檔案 (含路徑穿越防護)"""
    safe_name = Path(filename).name
    target = FONTS_DIR / safe_name
    if target.exists() and target.is_file():
        target.unlink()
        return True
    return False
