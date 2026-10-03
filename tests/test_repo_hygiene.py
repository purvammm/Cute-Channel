"""Guards for the working agreement: no secrets, no huge files, valid GitHub config."""

import json
import re
import subprocess

import pytest
import yaml

from pipeline.paths import REPO_ROOT

SECRET_PATTERNS = {
    "Meta/Facebook token": re.compile(r"EAA[A-Za-z0-9]{40,}"),
    "Instagram token": re.compile(r"IGQV[A-Za-z0-9_-]{40,}"),
    "Google OAuth token": re.compile(r"ya29\.[A-Za-z0-9_-]{30,}"),
    "Google refresh token": re.compile(r"1//0[A-Za-z0-9_-]{40,}"),
    "Anthropic key": re.compile(r"sk-ant-[A-Za-z0-9_-]{30,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
MAX_FILE_BYTES = 1_000_000
LARGE_FILE_ALLOWLIST: set[str] = set()


def repo_files() -> list[str]:
    """Tracked files plus new files that aren't ignored (so problems show up before commit)."""
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.skip("not a git checkout")
    return [f for f in proc.stdout.splitlines() if (REPO_ROOT / f).is_file()]


def test_no_secrets_in_repo_files():
    hits = []
    for name in repo_files():
        try:
            text = (REPO_ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits += [f"{name}: {kind}" for kind, rx in SECRET_PATTERNS.items() if rx.search(text)]
    assert not hits, "Possible secrets committed (rotate them!):\n" + "\n".join(hits)


def test_no_huge_files():
    big = [
        name
        for name in repo_files()
        if (REPO_ROOT / name).stat().st_size > MAX_FILE_BYTES and name not in LARGE_FILE_ALLOWLIST
    ]
    assert not big, f"Files over 1 MB belong in CI artifacts, not git: {big}"


def test_gitignore_protects_secrets_and_renders():
    ignored = subprocess.run(
        ["git", "check-ignore", ".env", ".env.local", "render/x.png", "a.blend1", ".tools/x"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout.split()
    assert ignored == [".env", ".env.local", "render/x.png", "a.blend1", ".tools/x"]
    not_ignored = subprocess.run(
        ["git", "check-ignore", ".env.example"], cwd=REPO_ROOT, capture_output=True
    )
    assert not_ignored.returncode == 1


def workflow_files():
    return sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))


@pytest.mark.parametrize("path", workflow_files(), ids=lambda p: p.name)
def test_workflows_are_valid(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "jobs" in data and data.get("name")
    assert True in data or "on" in data  # YAML 1.1 reads the `on:` key as True
    assert "permissions" in data, "declare least-privilege permissions"


def labels():
    return {label["name"] for label in json.loads((REPO_ROOT / ".github/labels.json").read_text())}


def test_labels_file():
    data = json.loads((REPO_ROOT / ".github/labels.json").read_text())
    names = [label["name"] for label in data]
    assert len(names) == len(set(names))
    assert {"needs-human", "approved", "rendering", "ready-to-publish", "published"} <= set(names)
    assert {f"phase-{n}" for n in range(12)} <= set(names)
    assert all(re.fullmatch(r"[0-9a-f]{6}", label["color"]) for label in data)


@pytest.mark.parametrize(
    "path", sorted((REPO_ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml")), ids=lambda p: p.name
)
def test_issue_templates(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if path.name == "config.yml":
        assert "blank_issues_enabled" in data
        return
    assert data["name"] and data["description"] and isinstance(data["body"], list)
    for label in data.get("labels", []):
        assert label in labels() | {"bug"}, f"unknown label {label}"
    for field in data["body"]:
        if field["type"] == "markdown":
            continue
        assert field.get("id") and field["attributes"].get("label")
        if field["type"] == "dropdown":
            assert field["attributes"]["options"]
