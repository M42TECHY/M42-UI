#!/bin/sh
# M42 UI installer for macOS: double-click this file in Finder (it opens Terminal and runs install.sh).
cd "$(dirname "$0")"
sh install.sh "$@"
echo
echo "Press Return to close this window."
read -r _
