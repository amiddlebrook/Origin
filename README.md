<div align="center">

# ORIGIN

**THE LIVING ARCHIVE**

*Discover the history behind a name. Write the stories that matter. Preserve the voices worth remembering.*

[![Test and deploy Origin](https://github.com/amiddlebrook/Origin/actions/workflows/cloudflare.yml/badge.svg)](https://github.com/amiddlebrook/Origin/actions/workflows/cloudflare.yml)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers%20%2B%20D1-F38020?logo=cloudflare&logoColor=white)](https://developers.cloudflare.com/workers/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

</div>

## What is Origin?

Origin is an independent family-history workspace. Research first names and surnames using public reference sources, transform clues and personal notes into editable stories, and record oral histories directly in your browser.

The app is designed around a simple belief: **a name is a beginning, not a conclusion**. It never claims that sharing a surname proves family lineage or that an automated search produces verified ancestry.

### The workspace

| Area | What it does |
|---|---|
| **Name explorer** | Search Wikimedia reference endpoints for context, get source links, and save research records |
| **Story studio** | Compose source-aware draft narratives, write personal context, edit stories, and export plain text |
| **Voice archive** | Record with the microphone, catalog memories, and download audio for permanent safekeeping |
| **Private account** | Email/password sign-in with per-account D1 records, secure HttpOnly session cookies, and salted password hashes |

**Audio privacy:** Actual audio blobs are stored in browser IndexedDB, **not on Cloudflare**. Recording titles/metadata are stored in D1 if signed in. Browser data removal, incognito/private mode, changing devices, or switching browser profiles can delete or hide audio. **Download a backup immediately after recording.** There is no cross-device audio synchronization in this free, no-billing setup.

## Architecture: Cloudflare-native, no mandatory paid providers

```text
Browser — HTML/CSS/JavaScript (Cloudflare Workers static assets)
  ├─ Name explorer ───── GET /api/research/lookup ─┐
  ├─ Story studio ────── /api/stories ──────────────┤
  ├─ Accounts ────────── /api/auth/* ────────────── Cloudflare Worker (JavaScript)
  └─ Voice archive ──── IndexedDB audio ───────────┤
                         └─ Metadata ───────────────┤
                                                    ↓
                                         Cloudflare D1 (SQLite)

External public references: Wikimedia REST APIs (best-effort, no paid API key)
CI/CD: GitHub Actions → D1 migration → Wrangler deploy → workers.dev
```

No Docker, Python web server, Postgres, Redis, Celery, paid model inference, scheduled worker, or R2 bucket is required. Existing Python files are retired in the Cloudflare-native edition.

Cloudflare Workers and D1 have a Free plan with usage limits. This architecture can run for $0 **within the Free plan limits**; at quota exhaustion operations may stop until reset, rather than requiring a paid infrastructure provider. Cloudflare and GitHub account setup is still required.

## Run locally

Requirements: Node.js 20+ and npm.

```bash
npm install
npm run db:local
npm run dev
```

Open the URL reported by Wrangler (usually `http://localhost:8787`). Wrangler uses a local D1 database for development. The all-zero D1 ID in `wrangler.jsonc` is **only a local placeholder** and cannot provision or select a production database.

```bash
npm run check
npm test
```

The tests exercise route validation, name normalization, narrative disclaimers, cross-origin protection, account registration/login, password verification, session cookies, account isolation, story changes, oral-history metadata, and rate limits using an in-memory SQLite database.

## One-time production setup (Free plan)

1. Use a [Cloudflare Workers Free](https://dash.cloudflare.com/) account and copy its account ID.
2. Create a scoped Cloudflare API token with permission to deploy Workers and create/edit D1 databases in that account.
3. In **GitHub → Origin → Settings → Secrets and variables → Actions**, create these **two repository secrets**:

   | Name | Value |
   |---|---|
   | `CLOUDFLARE_API_TOKEN` | Scoped Cloudflare API token for Workers + D1 |
   | `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID |

4. Push to `main` or run **Actions → Test and deploy Origin → Run workflow**. CI automatically runs `wrangler d1 list --json` and, if absent, `wrangler d1 create origin-archive-db`. It discovers the UUID, applies remote migrations, deploys static assets and Worker, then verifies the production site.
5. The `CLOUDFLARE_D1_DATABASE_ID` secret is **not required**. If you previously set it, its value must match the Wrangler-discovered database ID.
6. The initial verified production deployment is at **https://origin-archive.averymiddlebrook2014.workers.dev**. The site runs on Workers and D1 within their respective Free plan quotas. No paid third-party provider is required.

### Troubleshooting

If the GitHub deploy job fails at `wrangler d1 list` or `wrangler d1 create`, check that the token has **D1 Edit** permissions for the correct Cloudflare account. Workers deployment also requires Workers Scripts Edit permissions. If migrations fail, inspect the Cloudflare D1 migration logs and verify the database name in `wrangler.jsonc`.

**Never post API tokens in GitHub issues, logs, or source control.**

## API reference

| Route | Description |
|---|---|
| `GET /api/health` | No-auth uptime probe |
| `GET /api/research/lookup?name=...` | Best-effort external research, accessible without sign-in |
| `POST /api/auth/register` | New user account |
| `POST /api/auth/login` | Start session |
| `POST /api/auth/logout` | End current session |
| `GET /api/auth/me` | Current account |
| `GET /api/overview` | User's research, stories, recording metadata |
| `POST /api/research` | Research and save a name |
| `POST /api/stories` | Create story, optionally from an owned research ID |
| `PATCH /api/stories/:id` | Edit an owned story |
| `DELETE /api/stories/:id` | Delete an owned story |
| `POST /api/recordings` | Save audio *metadata* after recording locally |
| `DELETE /api/recordings/:id` | Delete owned recording metadata |

Mutating routes validate request origin; account-scoped routes require secure session cookies. Authentication attempts are rate-limited with D1, by account email and by IP when Cloudflare supplies one. Secrets and passwords are not logged.

## Research integrity and limitations

Wikimedia reference services may be unavailable, block automated requests, or return a related-but-different topic. No name meaning, family relationship, etymology, or ancestry is invented when sources fail. The UI shows a transparent fallback and authoritative starting links. Always cross-check against primary records. Public name lookups send the entered name to Wikimedia.

Origin does not automatically migrate data from the retired Python/SQLite backend. If you have an old local database or media folder, keep it backed up until you explicitly migrate those records. The source repository does not contain user data.

## Security & privacy notes

- Server-side password hashing uses PBKDF2-SHA-256 with unique salts; sessions use random tokens whose hashes are stored in D1.
- Cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` on HTTPS deployments.
- D1 SQL uses bound parameters, and UI text is escaped before display.
- Requests cap text lengths and JSON payload sizes; login/registration attempts are throttled.
- Browser audio is device-local. This choice avoids an obligatory object storage account but requires user-managed backups.
- The app is a personal/family project, not an identity-verification or genealogical proof service.

## Project structure

```text
src/worker.js             Worker routes, auth, D1 persistence
src/research.js           Name lookup, source links and source-aware drafts
public/index.html         Responsive application shell
public/styles.css         Visual design system
public/app.js             Research, stories, accounts and voice archive UI
public/_headers           Static asset security headers
migrations/0001_init.sql  D1 tables and indexes
.github/workflows/        GitHub Actions test and Cloudflare deploy
scripts/set-d1-id.mjs     Safe D1 binding setup in CI
```

### Contributing

Use the PR template, run `npm run check && npm test`, and never commit API credentials or personal family recordings. Issues and contributions that make source attribution, audio export, or accessibility stronger are welcome.
