# Phase Auth — Multi-profile credentials (`gh`-style)

- **Phase ID:** Auth (inserted; logically precedes Phase 14 packaging)
- **Version:** 0.1.0 (unreleased)
- **Date:** 2026-06-21
- **Tests:** 341 total (+59 new: `test_auth_store.py` 29, `test_config_profile.py` 13, `test_cli_auth.py` 17)

## Objective

Replace the single `CCB_API_KEY`/`CCB_API_SECRET` `.env` credential model with a `gh`-style
multi-profile auth system: named profiles (one per exchange account), one active at a time,
overridable per-invocation with a global `--profile <slug>` flag.

## What was built

- **`auth` command group** (write category): `login`, `logout`, `list`, `use`, `status`, `whoami`.
  - `login` resolves creds from `--key/--secret/--passphrase`, `--from-env`, or interactive
    `getpass` prompts (passphrase prompted only when the venue requires one, via
    `requiredCredentials`). Verifies by default with `check_required_credentials()` then a live
    `fetch_balance()`; `--no-verify` opts out. A failed check keeps the saved profile (save-then-warn)
    and exits `EXCHANGE_ERROR`.
  - `status` does a three-state live probe (`valid: true | false | null`) and degrades gracefully
    offline (exit `OK`). `whoami` is local-only.
- **Global `--profile NAME` flag** on every command, threaded through a new `_load_config(args)` seam.
- **`AuthProfile` model** + **`stores/auth_store.py`**: `AuthStore` over `auth.json` (atomic write,
  best-effort `0600`), profile name **slug** validation (`^[a-z0-9]+(?:-[a-z0-9]+)*$`,
  case-insensitive), first-profile-becomes-active, active re-points on remove.
- **Two secret backends** behind a `SecretBackend` protocol: `KeyringSecretBackend` (default — secrets
  in the OS keyring, metadata-only `auth.json`) and `FileSecretBackend` (secrets inline, `0600`).
  `make_secret_backend` falls back to file when no keyring is available; `backend_for` honors the
  backend recorded in an existing `auth.json` so reads match writes.
- **Credential resolution** centralized in `config.load_config`: precedence
  flag → active/selected profile → env → TOML → default. A profile supplies exchange + testnet +
  key/secret/passphrase; legacy env path retained for no-profile/CI. `AppConfig` gained
  `profile`/`password`; `masked_summary` reports the profile and masks the passphrase.
- **OKX support**: added to `SUPPORTED_EXCHANGES` with an `exchange_quirks` row (`clientOrderId`,
  len 32); passphrase plumbed through `ExchangeStore` (`password`) and handled generically.

## Files changed

| File | Change |
|---|---|
| `models/auth_profile.py` | new `AuthProfile` (slots) |
| `stores/auth_store.py` | new — `AuthStore`, `SecretBackend`/file+keyring, `make_secret_backend`, `backend_for`, `normalize_profile_name` |
| `config.py` | profile resolution in `load_config` (`profile_override`/`auth_store` seam), `_resolve_profile`/`_resolve_exchange`, `AppConfig.profile`/`password`, masked passphrase, `.env` template pointer |
| `stores/exchange.py` | `password` field + ccxt config, `check_credentials()`, `requires_passphrase()` |
| `stores/exchange_quirks.py` | OKX quirks row |
| `constants.py` | `AUTH_FILENAME`, `ENV_PROFILE`, `ENV_AUTH_BACKEND`, `AUTH_KEYRING_SERVICE`, `DEFAULT_AUTH_BACKEND`, OKX in `SUPPORTED_EXCHANGES` |
| `exceptions.py` | `AuthError` |
| `cli.py` | `auth` group + 6 handlers, `--profile`, `_load_config`, store/verify seams, dispatch + exit map |
| `utils/render.py` | `masked_profile`, `auth_list/status/whoami` responses + lines (always masked) |
| `pyproject.toml` | `keyring==25.7.0` dependency |
| `tests/conftest.py` | clear `CCB_PROFILE`/`CCB_AUTH_BACKEND`, `fake_keyring` fixture, `FakeExchangeStore.check_credentials` + offline `fetch_balance` |
| `tests/test_auth_store.py`, `test_config_profile.py`, `test_cli_auth.py` | new suites |

## Live test results

- File backend: `login`/`list`/`use`/`whoami`/`logout` round-trip; secrets inline in `auth.json`
  (`0600`); masked in all stdout (text + `--json`); no leak.
- Keyring backend (default, Windows `WinVaultKeyring`): secrets land in Credential Manager,
  `auth.json` is metadata-only, `whoami` hydrates from the keyring, `logout` purges the keyring entries.

## Notes / follow-ups

- **Phase 14 packaging:** `keyring` pulls platform backends (`pywin32-ctypes`, etc.); the PyInstaller
  bundle must be tested with these included (or keyring excluded + file default).
- OKX `clOrdId` length (32) and sandbox support to confirm against a live OKX key before trading there.
- `auth whoami` could surface sub-accounts via `fetch_accounts()` (deferred; would add a network call).
