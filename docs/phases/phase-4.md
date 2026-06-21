# Phase 4 — Exchange store (only network code)

- **Objective:** Thin mockable ccxt wrapper for Bybit/Binance + sandbox.
- **Deliverables:** `stores/exchange.py` (`load_markets`, `fetch_balance`, `fetch_ticker`, `fetch_open_orders`, `create_order`, `cancel_order`; sandbox toggle); `conftest.FakeExchangeStore`.
- **Definition of Done:** unit tests run fully on `FakeExchangeStore` (no network); manual testnet smoke lists balances.
- **Out of scope:** Decision / execution logic.
