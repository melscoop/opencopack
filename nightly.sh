#!/bin/sh
# Publish one queued page and rebuild. Does not schedule itself.
set -e
cd "$(dirname "$0")"
if [ -x ../.venv/bin/python ]; then
  PY=../.venv/bin/python
else
  PY=python3
fi
exec "$PY" ./nightly.py
