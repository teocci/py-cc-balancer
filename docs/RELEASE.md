# RELEASE

Release notes per version. Tag `vX.Y.Z` to trigger the GitHub Release workflow (Phase 10).

## 0.1.1 - 2026-06-21

- F-2: `auth login` now honors the app-wide testnet precedence (flag > `CCB_TESTNET` env > TOML
  `[global] testnet` > default) instead of forcing every new profile onto the sandbox, so valid
  mainnet keys no longer fail verification with `retCode 10003`.
- CI: release workflow bumped to Node-24-era action majors.

## 0.1.0 - 2026-06-21

- Initial release: phased implementation 0–14 plus the multi-profile `auth` command group,
  packaged as portable one-dir bundles for Windows/Linux/macOS. Includes fix F-1 (ccxt
  `adjustForTimeDifference`, resolving Bybit `retCode 10002` under local clock skew).
