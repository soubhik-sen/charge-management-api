#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
flutter_root="${HOME}/.cache/ledgerflow-flutter"

if [[ ! -x "${flutter_root}/bin/flutter" ]]; then
  rm -rf "${flutter_root}"
  git clone --depth 1 --branch stable https://github.com/flutter/flutter.git "${flutter_root}"
fi

"${flutter_root}/bin/flutter" config --enable-web
cd "${repo_root}/apps/ledgerflow_web"
"${flutter_root}/bin/flutter" pub get
"${flutter_root}/bin/flutter" build web \
  --release \
  --dart-define="LEDGERFLOW_API_URL=${LEDGERFLOW_API_URL:-http://localhost:8000}"
