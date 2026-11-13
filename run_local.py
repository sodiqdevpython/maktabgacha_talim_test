"""Lokal sinov: http://localhost:8000 — brauzerda Telegramsiz ochiladi (soxta "Sinov" foydalanuvchi bilan).

    python run_local.py
"""
import os
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
env = {**os.environ, "DEBUG": "1", "DEV_USER_ID": "1", "PYTHONIOENCODING": "utf-8"}
manage = [sys.executable, str(here / "manage.py")]
port = os.environ.get("PORT") or "8000"
subprocess.run(manage + ["migrate", "--noinput"], cwd=here, env=env, check=True)
sys.exit(subprocess.call(manage + ["runserver", port, "--noreload"], cwd=here, env=env))
