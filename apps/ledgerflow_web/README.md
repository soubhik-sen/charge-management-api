# LedgerFlow Web

Responsive Flutter reference client for the LedgerFlow charge-management API.

```bash
flutter pub get
flutter run -d chrome \
  --dart-define=LEDGERFLOW_API_URL=http://localhost:8000 \
  --dart-define=LEDGERFLOW_API_TOKEN=local-dev-token \
  --dart-define=LEDGERFLOW_UI_SCALE=1.0
```

The UI defaults to its normal `1.0` application scale; override `LEDGERFLOW_UI_SCALE` only when a host intentionally needs a different density. When `LEDGERFLOW_API_TOKEN` is provided, the application connects automatically. Without it, the application starts with demo data and **Connect API** accepts a live API URL and bearer token. Never embed production credentials in a web build.

For a reverse-proxied deployment that serves the UI and API from the same origin, build with an empty `LEDGERFLOW_API_URL`. The client will use relative `/api`, `/health`, and `/docs` routes, avoiding browser CORS and `localhost` versus `127.0.0.1` mismatches.

For a transaction smoke test, create and release a party-bound contract in **Contracts**, then open **Quotes** and import [`../../examples/road-quote-request.json`](../../examples/road-quote-request.json). Submit, determine matching contracts, rate, rank, and inspect the charge-line provenance before awarding an option. See [`../../docs/web-application.md`](../../docs/web-application.md) for module and deployment guidance.
