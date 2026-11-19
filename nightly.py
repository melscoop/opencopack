#!/usr/bin/env python3
"""Publish one queued guide, rebuild the site, and log the result.

Usage (from /workspace/mogul/site):
  ../.venv/bin/python nightly.py

The queue lives in data/queue.json. Items are pre-written; this script does
not invent new company facts. Scheduling is left to the operator.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "data" / "queue.json"
GUIDES = ROOT / "src" / "guides"
LOG = ROOT / "logs" / "nightly.log"
VENV_PY = ROOT.parent / ".venv" / "bin" / "python"
TODAY = date.today().isoformat()


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    with LOG.open("a") as fh:
        fh.write(line + "\n")
    print(msg)


def main() -> int:
    queue = json.loads(QUEUE.read_text())
    items = queue["items"]
    next_item = next((it for it in items if it.get("status") == "queued"), None)
    if not next_item:
        log("No queued items remain. Nothing published.")
        return 0

    dest = GUIDES / f"{next_item['slug']}.json"
    if dest.exists():
        log(f"SKIP {next_item['slug']}: guide file already exists")
        return 1

    guide = {
        "slug": next_item["slug"],
        "title": next_item["title"],
        "kicker": next_item.get("kicker", "Guide"),
        "date": TODAY,
        "updated": TODAY,
        "description": next_item["description"],
        "body": next_item["body"],
    }
    GUIDES.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(guide, indent=2, ensure_ascii=False) + "\n")

    next_item["status"] = "published"
    next_item["published_on"] = TODAY
    QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n")

    py = str(VENV_PY if VENV_PY.exists() else sys.executable)
    result = subprocess.run(
        [py, str(ROOT / "scripts" / "build.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log(f"BUILD FAILED after publishing {next_item['slug']}\n{result.stdout}\n{result.stderr}")
        return result.returncode

    remaining = sum(1 for it in items if it.get("status") == "queued")
    log(f"PUBLISHED guides/{next_item['slug']}/ — {next_item['title']} ({remaining} items left in queue)")
    if result.stdout.strip():
        log(result.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
