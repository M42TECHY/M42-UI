#!/bin/sh
# M42 UI installer for Linux and macOS: Python, its packages (in .venv), then m42/setup.py checks this PC, picks the
# model that fits (2B for 8 GB RAM, 4B for 16 GB or a graphics card), asks, downloads and starts the app.
#   sh install.sh            (macOS: double-click install.command)
#   sh install.sh --yes      no questions
set -e
cd "$(dirname "$0")"
OS="$(uname -s)"
echo "M42 UI installer ($OS)"
echo

ask() {  # ask "question" -> 0 for yes (the default)
  printf "%s [Y/n] " "$1"
  case " $* " in *" --yes "*) echo y; return 0 ;; esac
  read -r a || a=""
  case "$a" in n|N|no|No) return 1 ;; *) return 0 ;; esac
}

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 or newer was not found."
  if [ "$OS" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1 && ask "Install Python 3.12 with Homebrew?" "$@"; then
      brew install python@3.12; PY="$(brew --prefix)/bin/python3.12"
    else
      echo "Install it from https://www.python.org/downloads/macos/ and run this again."; exit 1
    fi
  elif command -v apt-get >/dev/null 2>&1; then
    if ask "Install Python with apt (needs your password: sudo)?" "$@"; then
      sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip; PY=python3
    else exit 1; fi
  elif command -v dnf >/dev/null 2>&1; then
    if ask "Install Python with dnf (sudo)?" "$@"; then sudo dnf install -y python3 python3-pip; PY=python3; else exit 1; fi
  elif command -v pacman >/dev/null 2>&1; then
    if ask "Install Python with pacman (sudo)?" "$@"; then sudo pacman -S --needed python python-pip; PY=python; else exit 1; fi
  else
    echo "Install Python 3.10+ with your system's package manager, then run this again."; exit 1
  fi
fi

if [ ! -x .venv/bin/python ]; then
  echo "Making M42 UI's own Python environment in .venv ..."
  if ! "$PY" -m venv .venv 2>/dev/null; then
    echo "Python's venv module is missing."
    if command -v apt-get >/dev/null 2>&1 && ask "Install python3-venv with apt (sudo)?" "$@"; then
      sudo apt-get install -y python3-venv && "$PY" -m venv .venv
    else exit 1; fi
  fi
fi
VPY=.venv/bin/python

echo
echo "M42 UI installs its Python packages into .venv (about 700 MB: the page tools, speech, PyTorch for the CPU)."
ask "Install them now?" "$@" || { echo "Nothing was installed."; exit 1; }
"$VPY" -m pip install --upgrade pip
"$VPY" -m pip install -r requirements.txt
if [ "$OS" = "Darwin" ]; then
  "$VPY" -m pip install torch || echo "PyTorch did not install: the Tanglish speech model stays off."
else
  "$VPY" -m pip install torch --index-url https://download.pytorch.org/whl/cpu || echo "PyTorch did not install: the Tanglish speech model stays off."
fi

# the app window and the page checks need a Chromium browser (Chrome, Chromium, Edge or Brave)
if [ "$OS" = "Linux" ] && ! command -v google-chrome >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1 \
   && ! command -v chromium-browser >/dev/null 2>&1 && ! command -v microsoft-edge >/dev/null 2>&1 && ! command -v brave-browser >/dev/null 2>&1; then
  echo "No Chrome / Chromium found: M42 UI opens in your default browser, and the page checks need one."
  if command -v apt-get >/dev/null 2>&1 && ask "Install Chromium with apt (sudo)?" "$@"; then
    sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser || true
  fi
fi
if [ "$OS" = "Linux" ] && ! command -v vulkaninfo >/dev/null 2>&1; then
  echo "(Tip: for a graphics card, install its Vulkan driver, e.g. 'sudo apt install mesa-vulkan-drivers'; without it the processor runs the model.)"
fi

echo
exec "$VPY" m42/setup.py "$@"
