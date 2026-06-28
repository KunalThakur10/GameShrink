from pathlib import Path

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
WORKSPACE_DIR = BASE_DIR / "workspace"

TOP_FILES_COUNT = 20
TOP_FOLDERS_COUNT = 10

REPORTS_DIR.mkdir(exist_ok=True)
WORKSPACE_DIR.mkdir(exist_ok=True)
