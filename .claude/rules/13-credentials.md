# Credential Management (API Auth)

## Applies When

This rule applies **only to tools that authenticate to an external API or service on the user's
behalf** — a CEX client, a cloud provider, a GitHub-style API. If the tool needs no credentials,
this rule does not apply; manage ordinary settings per [04-no-hardcoding.md](04-no-hardcoding.md).

## Credentials Live Behind `<tool> auth` Subcommands

Model the `gh` CLI. Do **not** make the user hand-edit a `.env` or config file to authenticate.
Provide a credential lifecycle as first-class commands:

- `auth login` — add/update credentials (interactive prompt by default; flags for automation)
- `auth logout` — remove credentials (default: the active profile)
- `auth list` — list profiles with the active marker; secrets masked
- `auth status` — show the active profile and run a **live** credential check
- `auth use <name>` — switch the active profile (multi-account support)

Support multiple accounts/profiles plus a one-invocation override (a `--profile` flag and an env
var, e.g. `<TOOL>_PROFILE`).

## OS Keyring Is the Default Secret Backend

- Store secrets in the **OS keyring** (`keyring` package) under a service name (e.g. `<tool>`).
- Keep only **non-secret** profile metadata and the active pointer in a plaintext store
  (`auth.json`) — never the secrets themselves when using the keyring backend.
- Provide a **file backend fallback** (secrets inline in `auth.json`, best-effort `0600`) for
  headless/CI where no keyring exists. Make the backend selectable by flag (`--keyring` /
  `--no-keyring`) and env (`<TOOL>_AUTH_BACKEND`); default to keyring and fall back automatically
  when it is unavailable.

## Env-Vars Are a Fallback, Not the Primary Path

- `<TOOL>_API_KEY` / `<TOOL>_API_SECRET`-style vars resolve **only when no active profile supplies the
  secret** (CI/automation).
- `.env` + `python-dotenv` may still load **non-secret** overrides (exchange, testnet, profile
  selection) — never as the primary credential path.

## Never Put Secrets in Config Files

- `config.toml` and other config files hold **only non-secret settings**.
- Secrets go to the keyring (or the file/env fallback) — never into committed or
  machine-rewritten config.

## Secret Resolution Precedence

1. Active/selected auth profile (`api_key`, `api_secret`, passphrase)
2. Environment-variable fallback

## Invariants (Always)

- Never log, print, or commit secrets; mask in any output (`key[:4]…key[-4:]`).
- `.gitignore` must cover `.env`, `.env.*`, `*.pem`, `*.key`, `*_key.json`, `secrets/`,
  `credentials/` — and the file-backend store (`auth.json`) when it may hold inline secrets.
- Set restrictive permissions (`600`/`700`) on any file holding sensitive data.
