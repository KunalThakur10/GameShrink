import logging
from datetime import datetime
from pathlib import Path

from config import REPORTS_DIR, TOP_FILES_COUNT, TOP_FOLDERS_COUNT
from scanner import ScanResult, largest_files, largest_folders

logger = logging.getLogger(__name__)


def format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def generate_report(result: ScanResult) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    game_name = result.game_folder.name
    report_path = REPORTS_DIR / f"{game_name}_{timestamp}.md"

    lines = _build_report_lines(result)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Report saved: {report_path}")
    return report_path


def _build_report_lines(result: ScanResult) -> list[str]:
    lines: list[str] = []

    lines.append(f"# GameShrink Report: {result.game_folder.name}")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"\nGame Folder: `{result.game_folder}`")

    lines.append("\n## Summary\n")
    lines.append(f"| Item | Value |")
    lines.append(f"|------|-------|")
    lines.append(f"| Total Size | {format_size(int(result.total_size))} |")
    lines.append(f"| Total Files | {result.total_files:,} |")
    lines.append(f"| Unique Extensions | {len(result.extension_counts):,} |")

    lines.append(f"\n## Largest Files (Top {TOP_FILES_COUNT})\n")
    lines.append("| # | File | Size |")
    lines.append("|---|------|------|")
    for i, entry in enumerate(largest_files(result, TOP_FILES_COUNT), 1):
        rel = entry.path.relative_to(result.game_folder)
        lines.append(f"| {i} | `{rel}` | {format_size(entry.size)} |")

    lines.append(f"\n## Largest Folders (Top {TOP_FOLDERS_COUNT})\n")
    lines.append("| # | Folder | Size |")
    lines.append("|---|--------|------|")
    for i, (folder, size) in enumerate(largest_folders(result, TOP_FOLDERS_COUNT), 1):
        try:
            rel = folder.relative_to(result.game_folder)
        except ValueError:
            rel = folder
        lines.append(f"| {i} | `{rel}` | {format_size(size)} |")

    lines.append("\n## File Extensions\n")
    lines.append("| Extension | Count | Total Size |")
    lines.append("|-----------|-------|------------|")
    sorted_exts = sorted(result.extension_sizes.items(), key=lambda x: x[1], reverse=True)
    for ext, size in sorted_exts:
        count = result.extension_counts[ext]
        lines.append(f"| `{ext}` | {count:,} | {format_size(size)} |")

    return lines


def print_latest_report() -> None:
    reports = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        print("No reports found. Run 'scan' first.")
        return
    latest = reports[0]
    print(f"\n--- {latest.name} ---\n")
    print(latest.read_text(encoding="utf-8"))
