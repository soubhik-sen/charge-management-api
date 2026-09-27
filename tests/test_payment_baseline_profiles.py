from fastapi.testclient import TestClient
from app.api.v1.charge_management import repository
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-token", "X-Subject": "tester@example.com"}
BASE = "/api/v1/charge-management"


def test_payment_baseline_purpose_persists_and_cannot_be_assigned_to_fx():
    repository.reset()
    body = {"profile_code": "INVOICE_PAYMENT", "profile_name": "Invoice payment baseline",
            "business_purpose": "PAYMENT_BASELINE_DATE", "event_codes": ["INVOICE_DATE"]}
    created = client.post(BASE + "/business-date-profiles", headers=AUTH, json=body)
    assert created.status_code == 201, created.text
    profile = created.json()
    pid, vid = profile['id'], profile['versions'][0]['id']
    # Each request loads a fresh persisted repository.
    assert client.get(BASE + f"/business-date-profiles/{pid}", headers=AUTH).json()['business_purpose'] == 'PAYMENT_BASELINE_DATE'
    assert client.post(BASE + f"/business-date-profile-versions/{vid}/publish", headers=AUTH).status_code == 200
    assignment = dict(scope_type='GLOBAL', shipment_scope='OCEAN_HOUSE', business_purpose='EXCHANGE_RATE_DATE')
    assert client.post(BASE + f"/business-date-profiles/{pid}/assignments", headers=AUTH, json=assignment).status_code == 422
    assignment['business_purpose'] = 'PAYMENT_BASELINE_DATE'
    assigned = client.post(BASE + f"/business-date-profiles/{pid}/assignments", headers=AUTH, json=assignment)
    assert assigned.status_code == 201, assigned.text
    body.update(profile_code='BAD_FX', business_purpose='EXCHANGE_RATE_DATE')
    assert client.post(BASE + '/business-date-profiles', headers=AUTH, json=body).status_code == 422
