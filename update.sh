#!/bin/sh
# M42 UI updater for Linux and macOS: sh update.sh
# It looks for a newer M42 UI on GitHub, shows what is new, asks, and updates the app; your models, chats, projects
# and settings stay. Close M42 UI first.
cd "$(dirname "$0")"
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
exec "$PY" m42/updater.py apply "$@"
