# LedgerFlow Web

Responsive Flutter reference client for the LedgerFlow charge-management API.

```bash
flutter pub get
flutter run -d chrome \
  --dart-define=LEDGERFLOW_API_URL=http://localhost:8000 \
  --dart-define=LEDGERFLOW_API_TOKEN=local-dev-token \
  --dart-define=LEDGERFLOW_UI_SCALE=0.8
```

The UI defaults to an `0.8` application scale; override `LEDGERFLOW_UI_SCALE` when a host needs a different density. When `LEDGERFLOW_API_TOKEN` is provided, the application connects automatically. Without it, the application starts with demo data and **Connect API** accepts a live API URL and bearer token. Never embed production credentials in a web build. See [`../../docs/web-application.md`](../../docs/web-application.md) for module and deployment guidance.
