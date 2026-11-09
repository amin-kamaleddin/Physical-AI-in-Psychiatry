"""Run the complete computational reproduction workflow."""
from pathlib import Path
import subprocess
import sys
if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    raise SystemExit(subprocess.call([sys.executable, str(root / "analysis" / "run_all.py"), *sys.argv[1:]], cwd=root))
