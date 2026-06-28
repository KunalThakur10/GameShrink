import argparse
import logging
import sys
from pathlib import Path

from scanner import scan
from reporter import generate_report, print_latest_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_scan(args: argparse.Namespace) -> None:
    game_folder = Path(args.game_folder).resolve()
    if not game_folder.exists():
        logger.error(f"Folder does not exist: {game_folder}")
        sys.exit(1)
    if not game_folder.is_dir():
        logger.error(f"Not a directory: {game_folder}")
        sys.exit(1)

    result = scan(game_folder)
    report_path = generate_report(result)
    print(f"\nScan complete.")
    print(f"  Files : {result.total_files:,}")
    print(f"  Total : {result.total_size / (1024 ** 3):.2f} GB")
    print(f"  Report: {report_path}")


def cmd_report(_args: argparse.Namespace) -> None:
    print_latest_report()


def cmd_gui(_args: argparse.Namespace) -> None:
    from gui import launch
    launch()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gameshrink",
        description="GameShrink - analyze game folder sizes",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a game folder")
    scan_parser.add_argument("game_folder", help="Path to the game folder")
    scan_parser.set_defaults(func=cmd_scan)

    report_parser = subparsers.add_parser("report", help="Print the latest report")
    report_parser.set_defaults(func=cmd_report)

    gui_parser = subparsers.add_parser("gui", help="Launch the desktop GUI")
    gui_parser.set_defaults(func=cmd_gui)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
