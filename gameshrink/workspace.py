import logging
import shutil
from pathlib import Path

from config import WORKSPACE_DIR

logger = logging.getLogger(__name__)


def workspace_path_for(game_folder: Path) -> Path:
    return WORKSPACE_DIR / game_folder.name


def copy_file_to_workspace(source: Path, game_folder: Path) -> Path:
    rel = source.relative_to(game_folder)
    dest = workspace_path_for(game_folder) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    logger.info(f"Copied to workspace: {dest}")
    return dest


def confirm_and_copy(source: Path, game_folder: Path) -> Path | None:
    rel = source.relative_to(game_folder)
    answer = input(f"Copy '{rel}' to workspace? [y/N]: ").strip().lower()
    if answer != "y":
        print("Skipped.")
        return None
    return copy_file_to_workspace(source, game_folder)


def workspace_exists(game_folder: Path) -> bool:
    return workspace_path_for(game_folder).exists()
