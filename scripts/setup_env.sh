#!/usr/bin/env bash
# Set up everything the pipeline needs on Linux or macOS: the pinned Blender LTS (a portable
# copy in .tools/), ffmpeg, Mesa software graphics on Linux, and the Python packages.
#
#   bash scripts/setup_env.sh               # your laptop, or the sandbox
#   bash scripts/setup_env.sh --ci          # GitHub Actions (Ubuntu): no .venv, runner's Python
#   bash scripts/setup_env.sh --no-blender  # skip the ~400 MB Blender download
#
# Why a portable Blender in .tools/: every machine then runs the *same* Blender, with the same
# Python API, so scripts that pass in CI also work on your laptop. Downloads are checked against
# the SHA-256 sums pinned in scripts/versions.env. Safe to re-run: finished steps are skipped.
# Windows isn't covered yet; see README.md ("Windows").
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
DOWNLOADS="$TOOLS/downloads"
# shellcheck source=versions.env
source "$ROOT/scripts/versions.env"

CI_MODE=0
WANT_BLENDER=1
for arg in "$@"; do
  case "$arg" in
    --ci) CI_MODE=1 ;;
    --no-blender) WANT_BLENDER=0 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

say()  { printf '\n==> %s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

OS="$(uname -s)"
ARCH="$(uname -m)"
SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then SUDO="sudo"; fi

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# fetch_blender SERIES FILE SHA256: download FILE from the first mirror that serves the exact bytes.
fetch_blender() {
  local series="$1" file="$2" expected="$3" target="$DOWNLOADS/$2" mirror
  mkdir -p "$DOWNLOADS"
  if [ -f "$target" ] && [ "$(sha256_of "$target")" = "$expected" ]; then
    echo "already downloaded and verified: $file"
    return 0
  fi
  for mirror in $BLENDER_MIRRORS; do
    echo "downloading $file from $mirror ..."
    if curl -fL --progress-bar --retry 3 --connect-timeout 20 -o "$target.part" "$mirror/Blender$series/$file"; then
      if [ "$(sha256_of "$target.part")" = "$expected" ]; then
        mv "$target.part" "$target"
        return 0
      fi
      warn "checksum mismatch from $mirror; trying the next mirror"
    fi
    rm -f "$target.part"
  done
  die "could not download $file with the expected SHA-256"
}

install_linux_packages() {
  if command -v apt-get >/dev/null 2>&1; then
    say "Installing system packages (apt): ffmpeg, Blender's libraries, Mesa software graphics"
    local pkgs="ffmpeg xz-utils libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0
      libxkbcommon-x11-0 libsm6 libice6 libgl1 libegl1 libglx-mesa0 libegl-mesa0 libgl1-mesa-dri
      mesa-vulkan-drivers libvulkan1"
    $SUDO apt-get update -qq
    # Fast path: everything at once. Package names drift between Ubuntu releases, so on failure
    # retry one by one and only warn about the missing ones.
    # shellcheck disable=SC2086
    if ! $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends $pkgs >/dev/null; then
      for pkg in $pkgs; do
        $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends "$pkg" >/dev/null \
          || warn "apt could not install $pkg"
      done
    fi
  elif command -v dnf >/dev/null 2>&1; then
    say "Installing system packages (dnf): Blender's libraries, Mesa software graphics"
    $SUDO dnf install -y -q xz libXxf86vm libXi libXfixes libXrender libxkbcommon libxkbcommon-x11 \
      libSM libICE mesa-libGL mesa-libEGL mesa-dri-drivers mesa-vulkan-drivers vulkan-loader \
      || warn "some dnf packages failed; doctor will say if anything important is missing"
  else
    warn "unknown package manager: install ffmpeg and Mesa (libGL, libEGL) yourself"
  fi
}

ensure_ffmpeg() {
  if command -v ffmpeg >/dev/null 2>&1 && ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libx264; then
    echo "ffmpeg with H.264 found: $(command -v ffmpeg)"
    return 0
  fi
  if [ -x "$TOOLS/ffmpeg-static/ffmpeg" ]; then
    echo "ffmpeg found: $TOOLS/ffmpeg-static/ffmpeg"
    return 0
  fi
  case "$OS" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        say "Installing ffmpeg (Homebrew)"
        brew install ffmpeg
      else
        warn "install Homebrew (https://brew.sh), then run: brew install ffmpeg"
      fi ;;
    Linux)
      if [ "$ARCH" != "x86_64" ]; then
        warn "no static ffmpeg for $ARCH here; install ffmpeg with your package manager"
        return 0
      fi
      # Some distros (Fedora's ffmpeg-free, Amazon Linux) ship no H.264 encoder at all.
      say "Downloading a static ffmpeg build (this system has no ffmpeg with H.264)"
      local url="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
      mkdir -p "$DOWNLOADS"
      curl -fL --progress-bar --retry 3 -o "$DOWNLOADS/ffmpeg-static.tar.xz" "$url"
      curl -fsSL -o "$DOWNLOADS/ffmpeg-static.tar.xz.md5" "$url.md5"
      [ "$(md5sum "$DOWNLOADS/ffmpeg-static.tar.xz" | cut -d' ' -f1)" = \
        "$(cut -d' ' -f1 "$DOWNLOADS/ffmpeg-static.tar.xz.md5")" ] || die "ffmpeg download is corrupt (md5 mismatch)"
      rm -rf "$TOOLS/ffmpeg-static"
      mkdir -p "$TOOLS/ffmpeg-static"
      tar -xJf "$DOWNLOADS/ffmpeg-static.tar.xz" -C "$TOOLS/ffmpeg-static" --strip-components=1 ;;
    *) warn "install ffmpeg yourself for $OS" ;;
  esac
}

install_blender() {
  case "$OS-$ARCH" in
    Linux-x86_64)
      local dir="$TOOLS/blender-$BLENDER_VERSION-linux-x64"
      if [ -x "$dir/blender" ]; then
        echo "Blender $BLENDER_VERSION already installed: $dir"
        return 0
      fi
      say "Installing Blender $BLENDER_VERSION LTS (portable; ~400 MB download)"
      fetch_blender "$BLENDER_SERIES" "blender-$BLENDER_VERSION-linux-x64.tar.xz" "$BLENDER_LINUX_SHA256"
      tar -xJf "$DOWNLOADS/blender-$BLENDER_VERSION-linux-x64.tar.xz" -C "$TOOLS" ;;
    Darwin-arm64|Darwin-x86_64)
      # UNTESTED on a real Mac so far: tell Kiro if any step fails.
      local version="$BLENDER_VERSION" series="$BLENDER_SERIES" sha="$BLENDER_MACOS_ARM64_SHA256" arch="arm64"
      if [ "$ARCH" = "x86_64" ]; then  # Intel Mac: Blender 5.x dropped Intel, so 4.5 LTS (guide §3.1)
        version="$BLENDER_INTEL_MAC_VERSION"; series="$BLENDER_INTEL_MAC_SERIES"
        sha="$BLENDER_INTEL_MAC_SHA256"; arch="x64"
      fi
      local installed="/Applications/Blender.app/Contents/MacOS/Blender"
      if [ -x "$installed" ] && "$installed" --version 2>/dev/null | grep -q "Blender $series"; then
        echo "Blender $series already installed in /Applications"
        return 0
      fi
      local app="$TOOLS/Blender-$version.app"
      if [ -d "$app" ]; then
        echo "Blender $version already installed: $app"
        return 0
      fi
      say "Installing Blender $version LTS for macOS ($arch) into .tools/"
      local dmg="blender-$version-macos-$arch.dmg" mount
      fetch_blender "$series" "$dmg" "$sha"
      mount="$(mktemp -d)"
      hdiutil attach -nobrowse -readonly -mountpoint "$mount" "$DOWNLOADS/$dmg" >/dev/null
      cp -R "$mount/Blender.app" "$app"
      hdiutil detach "$mount" >/dev/null ;;
    Linux-aarch64|Linux-arm64)
      warn "Blender has no official Linux ARM build; install it yourself and set CC_BLENDER in .env" ;;
    *)
      warn "no automatic Blender install for $OS-$ARCH; get it from https://www.blender.org/download/" ;;
  esac
}

find_python() {
  if [ -n "${PYTHON:-}" ]; then echo "$PYTHON"; return 0; fi
  local candidate
  for candidate in python3.12 python3.11 python3.13 python3.10 python3 python \
      "$HOME"/.pyenv/versions/3.1[0-9]*/bin/python; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

PY_RUN=""
setup_python() {
  if [ "$CI_MODE" = 1 ]; then
    # In CI, actions/setup-python puts the right interpreter first on PATH as `python`.
    PY_RUN="$(command -v python || command -v python3)"
    say "Installing Python packages into $("$PY_RUN" --version 2>&1)"
    "$PY_RUN" -m pip install -q -r "$ROOT/requirements-dev.txt"
    return 0
  fi
  local py
  py="$(find_python)" || die "Python 3.10+ not found. Install Python 3.11 (python.org or your package manager), then re-run."
  if [ ! -x "$ROOT/.venv/bin/python" ]; then
    say "Creating .venv with $("$py" --version 2>&1)"
    "$py" -m venv "$ROOT/.venv"
  fi
  say "Installing Python packages into .venv"
  "$ROOT/.venv/bin/python" -m pip install -q --upgrade pip
  "$ROOT/.venv/bin/python" -m pip install -q -r "$ROOT/requirements-dev.txt"
  PY_RUN="$ROOT/.venv/bin/python"
}

say "Cute Channel setup ($OS $ARCH)"
mkdir -p "$TOOLS"
if [ "$OS" = "Linux" ]; then install_linux_packages; fi
ensure_ffmpeg
if [ "$WANT_BLENDER" = 1 ]; then install_blender; fi
setup_python

say "Checking the result: python cc.py doctor"
"$PY_RUN" "$ROOT/cc.py" doctor || true
if [ "$CI_MODE" = 0 ]; then
  echo
  echo "Done. Use the project's Python from now on:  source .venv/bin/activate"
fi
