from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal, database_url


def main() -> int:
    with SessionLocal() as db:
        version = db.execute(text("select version_num from alembic_version")).scalar_one_or_none()
        component_count = db.execute(text("select count(*) from charge_component")).scalar_one()
        business_date_profile_count = db.execute(text("select count(*) from charge_business_date_profile")).scalar_one()
        assignment_count = db.execute(text("select count(*) from charge_business_date_profile_assignment")).scalar_one()
        settings = db.execute(
            text(
                "select quotation_policy, quote_acceptance_mode, provider_cost_layer_enabled "
                "from charge_management_settings where id = 1"
            )
        ).mappings().first()
    print(f"database_url={_safe_url(database_url())}")
    print(f"alembic_version={version}")
    print(f"charge_component_count={component_count}")
    print(f"business_date_profile_count={business_date_profile_count}")
    print(f"business_date_profile_assignment_count={assignment_count}")
    if settings:
        print(f"quotation_policy={settings['quotation_policy']}")
        print(f"quote_acceptance_mode={settings['quote_acceptance_mode']}")
        print(f"provider_cost_layer_enabled={bool(settings['provider_cost_layer_enabled'])}")
    return 0


def _safe_url(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    prefix, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    userinfo, host = rest.split("@", 1)
    user = userinfo.split(":", 1)[0]
    return f"{prefix}://{user}:***@{host}"


if __name__ == "__main__":
    raise SystemExit(main())
