import sys
from pathlib import Path

# ensure the project root is importable as `agent` when running pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
