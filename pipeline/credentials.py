"""Every secret or setting the pipeline may read, grouped by integration and phase.

`python cc.py doctor` reports which are set, but never their values. Keep this list in sync with
`.env.example`; a unit test checks that they match.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Credential:
    key: str
    group: str
    phase: int  # the phase that first needs it
    secret: bool = True  # False for IDs that are not sensitive on their own
    optional: bool = False


# Paths to tools, for when doctor can't find them by itself. Not secrets.
LOCAL_OVERRIDES = ("CC_BLENDER", "CC_FFMPEG", "CC_FFPROBE")

CREDENTIALS = (
    Credential("ANTHROPIC_API_KEY", "LLM helper (optional, paid)", 4, optional=True),
    Credential("IG_USER_ID", "Instagram", 9, secret=False),
    Credential("IG_ACCESS_TOKEN", "Instagram", 9),
    Credential("META_APP_ID", "Instagram", 9, secret=False),
    Credential("META_APP_SECRET", "Instagram", 9),
    Credential("YT_CLIENT_ID", "YouTube", 9, secret=False),
    Credential("YT_CLIENT_SECRET", "YouTube", 9),
    Credential("YT_REFRESH_TOKEN", "YouTube", 9),
)


def groups() -> dict[str, list[Credential]]:
    """Credentials grouped by integration, in a stable order."""
    grouped: dict[str, list[Credential]] = {}
    for credential in CREDENTIALS:
        grouped.setdefault(credential.group, []).append(credential)
    return grouped


def all_keys() -> set[str]:
    return {c.key for c in CREDENTIALS} | set(LOCAL_OVERRIDES)
