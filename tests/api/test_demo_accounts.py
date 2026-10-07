"""Demo accounts must not be usable once production mode is enabled."""

from __future__ import annotations

from caremate.api.security import hash_password
from caremate.db.models_core import User
from caremate.scripts.seed import (
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    DEMO_DOCTOR_EMAIL,
    DEMO_PATIENT_EMAIL,
    DEMO_PATIENT_PASSWORD,
    disable_demo_accounts,
)


def _login(client, email, password):
    return client.post("/auth/token", json={"email": email, "password": password})


def test_demo_accounts_disabled_in_production(client, db):
    # Startup (development mode) seeded the demo accounts.
    assert _login(client, DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD).status_code == 200

    # An operator who changed a demo password keeps that account.
    doctor = db.query(User).filter(User.email == DEMO_DOCTOR_EMAIL).one()
    doctor.hashed_password = hash_password("a-private-password")
    db.commit()

    assert disable_demo_accounts() == 2

    assert _login(client, DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD).status_code == 401
    assert _login(client, DEMO_PATIENT_EMAIL, DEMO_PATIENT_PASSWORD).status_code == 401
    assert _login(client, DEMO_DOCTOR_EMAIL, "a-private-password").status_code == 200
