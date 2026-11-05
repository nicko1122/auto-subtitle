import os
import shutil
import tempfile
from threading import RLock
from pathlib import Path, PurePosixPath

from ..core.exporter import parse_srt_content, to_srt
from ..schemas.subtitle import SubtitleTrack

mutation_lock = RLock()

MEDIA_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv', '.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg'}
SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.json'}
SCRIPT_EXTENSIONS = {'.txt', '.lrc'}


def resolve_package(root: Path, relative: str, must_exist=True) -> Path:
    parts = PurePosixPath(relative)
    if not relative or '\\' in relative or '\x00' in relative or parts.is_absolute() or any(p.startswith('.') for p in parts.parts):
        raise ValueError('請使用資產庫內的相對資料夾路徑')
    root = root.resolve()
    candidate = root.joinpath(*parts.parts)
    if candidate == root or candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
        raise ValueError('資產包路徑超出資產庫')
    if must_exist and not candidate.is_dir():
        raise FileNotFoundError('找不到資產包')
    return candidate


def package_files(directory: Path):
    items = [p for p in directory.iterdir() if p.is_file() and not p.name.startswith('.') and not p.is_symlink()]
    media = [p for p in items if p.suffix.lower() in MEDIA_EXTENSIONS]
    if len(media) != 1:
        raise ValueError('每個資產包需要一支影片或音訊')
    video = media[0]

    def companion(extension):
        matches = [p for p in items if p.suffix.lower() == extension]
        same_name = [p for p in matches if p.stem.casefold() == video.stem.casefold()]
        if len(same_name) == 1:
            return same_name[0]
        if len(matches) > 1:
            raise ValueError(f'資產包內有多份 {extension}，請使用與影片同名的工作檔案')
        return matches[0] if matches else None

    return video, companion('.srt'), companion('.txt')


def list_packages(root: Path):
    parents = set()
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if path.suffix.lower() in MEDIA_EXTENSIONS and path.is_file() and not path.is_symlink() and len(relative.parts) > 1 and not any(p.startswith('.') for p in relative.parts):
            directory = resolve_package(root, relative.parent.as_posix())
            parents.add(directory)
    return sorted(parents, key=lambda p: max(f.stat().st_mtime_ns for f in p.iterdir() if f.is_file()), reverse=True)


def atomic_write(path: Path, content: str):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, prefix='.saving_', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def group_uploads(files):
    groups = {}
    loose = []
    for filename, stream in files:
        path = PurePosixPath(filename)
        if '\\' in filename or '\x00' in filename or path.is_absolute() or '..' in path.parts:
            raise ValueError('上傳檔案路徑不合法')
        if any(p.startswith('.') for p in path.parts):
            continue
        if path.suffix.lower() not in MEDIA_EXTENSIONS | SUBTITLE_EXTENSIONS | SCRIPT_EXTENSIONS:
            if len(path.parts) > 1:
                continue
            raise ValueError('資產包僅接受影片、音訊、字幕或原稿')
        if len(path.parts) > 1:
            groups.setdefault(path.parent.as_posix(), []).append((path.name, stream))
        else:
            loose.append((path.name, stream))
    media = [item for item in loose if Path(item[0]).suffix.lower() in MEDIA_EXTENSIONS]
    for filename, stream in media:
        key = Path(filename).stem
        groups.setdefault(key, []).append((filename, stream))
    for filename, stream in loose:
        if Path(filename).suffix.lower() in MEDIA_EXTENSIONS:
            continue
        matching = [key for key in groups if Path(key).name.casefold() == Path(filename).stem.casefold()]
        if len(matching) == 1:
            key = matching[0]
        elif len(groups) == 1:
            key = next(iter(groups))
        else:
            raise ValueError('請將字幕／原稿與影片一起匯入，或先開啟要補入檔案的資產包')
        groups[key].append((filename, stream))
    for items in groups.values():
        counts = [sum(Path(name).suffix.lower() in extensions for name, _ in items) for extensions in (MEDIA_EXTENSIONS, SUBTITLE_EXTENSIONS, SCRIPT_EXTENSIONS)]
        if counts[0] != 1 or counts[1] > 1 or counts[2] > 1:
            raise ValueError('每個資產包須有一支影片，搭配至多一份字幕與一份原稿')
    return groups


def check_destination_parent(root: Path, destination: Path):
    for parent in destination.parents:
        if parent == root.resolve():
            break
        if parent.is_dir() and any(p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS for p in parent.iterdir()):
            raise ValueError('目標位置已是資產包，請選擇分類資料夾')


def import_files(root: Path, name: str, items, target=None):
    root.mkdir(parents=True, exist_ok=True)
    if target is not None:
        video, subtitle, script = package_files(target)
        if any(Path(filename).suffix.lower() in MEDIA_EXTENSIONS for filename, _ in items):
            raise ValueError('新增影片請建立新的資產包')
    else:
        video = Path(next(filename for filename, _ in items if Path(filename).suffix.lower() in MEDIA_EXTENSIONS))
        subtitle = script = None
    texts = []
    for filename, stream in items:
        extension = Path(filename).suffix.lower()
        if extension in SUBTITLE_EXTENSIONS | SCRIPT_EXTENSIONS:
            content = stream.read().decode('utf-8-sig')
            if extension in SUBTITLE_EXTENSIONS:
                if extension == '.json':
                    track = SubtitleTrack.model_validate_json(content)
                else:
                    track = parse_srt_content(content)
                content = to_srt(track)
                dest_name = subtitle.name if subtitle else video.stem + '.srt'
            else:
                dest_name = script.name if script else video.stem + '.txt'
            texts.append((dest_name, content))
    if target is not None:
        with mutation_lock:
            for filename, content in texts:
                atomic_write(target / filename, content)
            return target

    candidate = resolve_package(root, name, must_exist=False)
    check_destination_parent(root, candidate)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix='.importing_') as temporary:
        stage = Path(temporary)
        for filename, stream in items:
            if Path(filename).suffix.lower() in MEDIA_EXTENSIONS:
                with (stage / filename).open('wb') as output:
                    shutil.copyfileobj(stream, output)
        for filename, content in texts:
            (stage / filename).write_text(content, encoding='utf-8')
        with mutation_lock:
            index = 1
            while True:
                destination = candidate if index == 1 else candidate.with_name(f'{candidate.name} ({index})')
                try:
                    destination.mkdir()
                    break
                except FileExistsError:
                    index += 1
            try:
                stage.replace(destination)
            except BaseException:
                destination.rmdir()
                raise
    return destination


def move_package(root: Path, source: str, destination: str):
    with mutation_lock:
        current = resolve_package(root, source)
        package_files(current)
        target = resolve_package(root, destination, must_exist=False)
        if target == current:
            return current
        if target.exists():
            raise FileExistsError('目標位置已有同名資產包')
        if target.is_relative_to(current):
            raise ValueError('不能將資產包移到自己的子資料夾')
        check_destination_parent(root, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        current.rename(target)
        return target
