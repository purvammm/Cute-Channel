"""A tiny `.env` reader (no python-dotenv dependency) and the pinned-versions file.

Both files use the same simple format, which bash can also `source`:

    # comment
    KEY=value
    export KEY="value with spaces"
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from .paths import ENV_FILE, VERSIONS_FILE


def parse_env_text(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines. Malformed lines are skipped so `doctor` never crashes on them."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key.isidentifier():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]  # quoted: keep everything inside, including '#'
        else:
            value = value.split(" #", 1)[0].rstrip()  # unquoted: allow a trailing comment
        values[key] = value
    return values


def load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Values from your local `.env`, or {} if you haven't created one."""
    if not path.is_file():
        return {}
    return parse_env_text(path.read_text(encoding="utf-8"))


def load_versions(path: Path = VERSIONS_FILE) -> dict[str, str]:
    """Pinned tool versions and checksums (scripts/versions.env)."""
    return parse_env_text(path.read_text(encoding="utf-8"))


def merged_settings(
    environ: Mapping[str, str] | None = None, env_file: Mapping[str, str] | None = None
) -> dict[str, str]:
    """`.env` values overlaid by real environment variables (so CI secrets win over files)."""
    environ = os.environ if environ is None else environ
    env_file = load_env_file() if env_file is None else env_file
    merged = dict(env_file)
    merged.update({k: v for k, v in environ.items() if v})
    return merged
