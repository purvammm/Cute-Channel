"""Well-known repository paths, so no script hard-codes folder names."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TOOLS_DIR = REPO_ROOT / ".tools"  # portable Blender / ffmpeg from scripts/setup_env.sh (gitignored)
CACHE_DIR = REPO_ROOT / ".cache"  # machine-specific results, e.g. which render engines work
VERSIONS_FILE = REPO_ROOT / "scripts" / "versions.env"  # pinned tool versions + checksums
ENV_FILE = REPO_ROOT / ".env"  # your local secrets (gitignored)
ENV_EXAMPLE_FILE = REPO_ROOT / ".env.example"

BLENDER_DIR = REPO_ROOT / "blender"
BRAND_DIR = REPO_ROOT / "brand"
DOCS_DIR = REPO_ROOT / "docs"
EPISODES_DIR = REPO_ROOT / "episodes"

RENDER_CAPABILITIES_FILE = CACHE_DIR / "render_capabilities.json"
RENDER_PROBE_DIR = CACHE_DIR / "render_probe"
