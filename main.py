"""
Project-root launcher — loads FastAPI app from backend/main.py.

Run from repo root (with backend venv active):
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import importlib.util
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_spec = importlib.util.spec_from_file_location(
    "backend_fastapi_main",
    _BACKEND / "main.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
app = _mod.app
