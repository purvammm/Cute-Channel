# Secrets: where they go and where they never go

**Never** put a token in the repo, a chat, an issue, a PR comment or a screenshot. If one leaks,
revoke it at the provider first, then replace it.

## Two places, one list

| Where | Used by | How |
|---|---|---|
| **GitHub Actions secrets** | workflows (publishing, reports) | repo **Settings → Secrets and variables → Actions → New repository secret**; paste the name exactly as listed below |
| **`.env` on your laptop** | `python cc.py ...` locally | `cp .env.example .env`, fill in only what you need. `.env` is gitignored, and doctor fails loudly if it ever gets committed |

Check what's set, without showing any values: `python cc.py doctor`.

**Recommended extra gate for publishing (Phase 9):** put the Instagram/YouTube secrets in a
GitHub **Environment** called `publish` with yourself as **Required reviewer** (Settings →
Environments). Then even an approved workflow pauses until you click "Approve".

## The list

| Name | For | Needed from | Secret? |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | `cc.py new-episode` / `ideas` calling an LLM directly. **Optional and paid**; without it, the CLI prints a prompt for any AI chat | Phase 4/8 | yes |
| `IG_USER_ID` | Instagram professional account id | Phase 9 | no |
| `IG_ACCESS_TOKEN` | Instagram publishing token | Phase 9 | **yes** |
| `META_APP_ID` | Meta developer app (token refresh) | Phase 9 | no |
| `META_APP_SECRET` | Meta developer app secret | Phase 9 | **yes** |
| `YT_CLIENT_ID` | Google OAuth client | Phase 9 | no |
| `YT_CLIENT_SECRET` | Google OAuth client secret | Phase 9 | **yes** |
| `YT_REFRESH_TOKEN` | Long-lived YouTube upload permission | Phase 9 | **yes** |

Local tool overrides, not secrets: `CC_BLENDER`, `CC_FFMPEG`, `CC_FFPROBE`.

The exact steps to create each credential arrive with Phase 9 (`docs/SETUP_INSTAGRAM_API.md` and a
YouTube equivalent), after re-checking the current official API rules. Names may change then; the
test suite keeps `.env.example`, this table and `pipeline/credentials.py` in sync.
