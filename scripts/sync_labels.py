"""Create or update this repo's GitHub labels from .github/labels.json. Safe to re-run.

    python scripts/sync_labels.py              # uses the `origin` remote to find the repo
    python scripts/sync_labels.py --dry-run    # show what would change
    python scripts/sync_labels.py --repo owner/name

This needs the GitHub CLI (`gh`), logged in. Existing labels that aren't in the file are left alone.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
LABELS_FILE = ROOT / ".github" / "labels.json"


def repo_from_remote() -> str:
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        sys.exit(f"Can't work out owner/repo from the origin URL: {url}")
    return f"{match[1]}/{match[2]}"


def gh(*args: str) -> str:
    return subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="owner/name (default: from the origin remote)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = args.repo or repo_from_remote()
    wanted = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    existing = set(
        gh(f"repos/{repo}/labels?per_page=100", "--paginate", "--jq", ".[].name").split()
    )

    for label in wanted:
        fields = ["-f", f"color={label['color']}", "-f", f"description={label['description']}"]
        if label["name"] in existing:
            action = ["-X", "PATCH", f"repos/{repo}/labels/{quote(label['name'])}", *fields]
            verb = "update"
        else:
            action = ["-X", "POST", f"repos/{repo}/labels", "-f", f"name={label['name']}", *fields]
            verb = "create"
        print(f"{verb:6} {label['name']}")
        if not args.dry_run:
            gh(*action)
    return 0


if __name__ == "__main__":
    sys.exit(main())
