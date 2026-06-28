import logging
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    path: Path
    size: int


@dataclass
class ScanResult:
    game_folder: Path
    total_size: int = 0
    total_files: int = 0
    all_files: list[FileEntry] = field(default_factory=list)
    folder_sizes: dict[Path, int] = field(default_factory=dict)
    extension_counts: dict[str, int] = field(default_factory=dict)
    extension_sizes: dict[str, int] = field(default_factory=dict)


def scan(game_folder: Path) -> ScanResult:
    logger.info(f"Scanning: {game_folder}")
    result = ScanResult(game_folder=game_folder)
    folder_sizes: dict[Path, int] = defaultdict(int)
    extension_counts: dict[str, int] = defaultdict(int)
    extension_sizes: dict[str, int] = defaultdict(int)

    for file_path in game_folder.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            size = file_path.stat().st_size
        except OSError as e:
            logger.warning(f"Cannot stat {file_path}: {e}")
            continue

        result.all_files.append(FileEntry(path=file_path, size=size))
        result.total_size += size
        result.total_files += 1

        ext = file_path.suffix.lower() or "(no extension)"
        extension_counts[ext] += 1
        extension_sizes[ext] += size

        for parent in file_path.parents:
            if parent == game_folder or game_folder in parent.parents or parent == game_folder.parent:
                folder_sizes[parent] += size
            if parent == game_folder:
                break

    result.folder_sizes = dict(folder_sizes)
    result.extension_counts = dict(extension_counts)
    result.extension_sizes = dict(extension_sizes)

    logger.info(f"Scan complete: {result.total_files} files, {result.total_size} bytes")
    return result


def largest_files(result: ScanResult, n: int) -> list[FileEntry]:
    return sorted(result.all_files, key=lambda f: f.size, reverse=True)[:n]


def largest_folders(result: ScanResult, n: int) -> list[tuple[Path, int]]:
    return sorted(result.folder_sizes.items(), key=lambda x: x[1], reverse=True)[:n]
