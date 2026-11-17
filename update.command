#!/bin/sh
# M42 UI updater for macOS: double-click this file in Finder (it opens Terminal and runs update.sh).
cd "$(dirname "$0")"
sh update.sh "$@"
echo
echo "Press Return to close this window."
read -r _
