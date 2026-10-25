"""`uv run vetagent`: start the demo server. Works the same on Windows, macOS and Linux."""

import argparse
import os
import shutil
from pathlib import Path

import uvicorn
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the vet care agent demo.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart on code changes")
    parser.add_argument("--reset", action="store_true", help="delete demo state, then start")
    args = parser.parse_args()

    env, example = Path(".env"), Path(".env.example")
    if not env.exists() and example.exists():
        shutil.copy(example, env)  # first run: sensible demo defaults
    load_dotenv(env)

    db = Path(os.getenv("VETAGENT_DB", "vetagent.db"))
    if args.reset and db.exists():
        db.unlink()

    uvicorn.run("vetagent.api.app:create_app", factory=True, port=args.port, reload=args.reload)
