import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from reporter import format_size
from scanner import ScanResult


@dataclass
class BuildPlan:
    game_folder: Path
    excluded_extensions: set[str]
    excluded_names: set[str] = field(default_factory=set)
    files_to_copy: list[Path] = field(default_factory=list)
    files_to_skip: list[Path] = field(default_factory=list)
    copy_size: int = 0
    skip_size: int = 0

    @property
    def original_size(self) -> int:
        return self.copy_size + self.skip_size

    @property
    def space_saved(self) -> int:
        return self.skip_size


def make_plan(result: ScanResult, excluded_extensions: set[str], excluded_names: set[str] | None = None) -> BuildPlan:
    plan = BuildPlan(
        game_folder=result.game_folder,
        excluded_extensions={e.lower() for e in excluded_extensions},
        excluded_names={n.lower() for n in (excluded_names or set())},
    )
    for entry in result.all_files:
        ext = entry.path.suffix.lower()
        name = entry.path.name.lower()
        if ext in plan.excluded_extensions or name in plan.excluded_names:
            plan.files_to_skip.append(entry.path)
            plan.skip_size += entry.size
        else:
            plan.files_to_copy.append(entry.path)
            plan.copy_size += entry.size
    return plan


def build_dest_folder() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    downloads = Path.home() / "Downloads"
    downloads.mkdir(exist_ok=True)
    return downloads / f"GameShrink_Build_{timestamp}"


def execute_build(
    plan: BuildPlan,
    dest: Path,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    total = len(plan.files_to_copy)

    for i, src in enumerate(plan.files_to_copy, 1):
        rel = src.relative_to(plan.game_folder)
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if progress_cb:
            progress_cb(i, total, str(rel))

    _write_manifest(plan, dest)
    _write_build_report(plan, dest)
    return dest


def _write_manifest(plan: BuildPlan, dest: Path) -> None:
    lines = ["# Build Manifest", ""]
    lines.append("## Copied Files")
    for f in sorted(plan.files_to_copy):
        lines.append(f"  COPIED  {f.relative_to(plan.game_folder)}")
    lines.append("")
    lines.append("## Skipped Files")
    for f in sorted(plan.files_to_skip):
        lines.append(f"  SKIPPED {f.relative_to(plan.game_folder)}")
    (dest / "manifest.txt").write_text("\n".join(lines), encoding="utf-8")


def _write_build_report(plan: BuildPlan, dest: Path) -> None:
    lines = [
        "# Build Report",
        "",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source: {plan.game_folder}",
        f"Destination: {dest}",
        "",
        "## Size Summary",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| Original Size | {format_size(plan.original_size)} |",
        f"| Build Size | {format_size(plan.copy_size)} |",
        f"| Space Saved | {format_size(plan.space_saved)} |",
        "",
        "## File Summary",
        "",
        "| Item | Count |",
        "|------|-------|",
        f"| Files Copied | {len(plan.files_to_copy):,} |",
        f"| Files Skipped | {len(plan.files_to_skip):,} |",
        "",
        "## Excluded Extensions",
        "",
    ]
    for ext in sorted(plan.excluded_extensions):
        lines.append(f"- `{ext}`")
    (dest / "build_report.md").write_text("\n".join(lines), encoding="utf-8")
