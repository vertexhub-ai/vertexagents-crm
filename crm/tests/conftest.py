"""
Test fixtures for the CRM domain.

Tests run against Postgres in CI (the only place the functional indexes,
case-insensitive uniqueness, and CHECK constraints can be exercised
end-to-end). On developer machines without Postgres, run with
`DJANGO_TEST_SQLITE=1 pytest` — the constraint-level tests below
are guarded with `pytest.mark.skipif(connection.vendor != 'postgresql')`
so they're skipped, not falsely passing.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(username="rep1", password="x", role="rep")


@pytest.fixture
def admin(db):
    User = get_user_model()
    return User.objects.create_user(username="boss", password="x", role="admin")
