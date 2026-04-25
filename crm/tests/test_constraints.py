"""Database-level constraint tests (Postgres-only)."""

from __future__ import annotations

import pytest
from django.db import IntegrityError, connection, transaction

from crm.models import Account, Activity, Contact, Lead, Opportunity


pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="Functional indexes + CHECK constraints require Postgres.",
    ),
]


def test_account_name_unique_case_insensitive(user):
    Account.objects.create(name="ACME", owner=user)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Account.objects.create(name="acme", owner=user)


def test_account_name_uniqueness_only_among_alive(user):
    """Soft-deleted account doesn't block recreating with the same name."""
    a = Account.objects.create(name="Acme", owner=user)
    a.soft_delete(user=user)
    # Should succeed — the unique constraint is partial WHERE deleted_at IS NULL.
    Account.objects.create(name="acme", owner=user)


def test_contact_email_unique_case_insensitive(user):
    Contact.objects.create(first_name="A", last_name="One", email="X@y.com", owner=user)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Contact.objects.create(first_name="B", last_name="Two", email="x@y.com", owner=user)


def test_contact_email_uniqueness_skips_blanks(user):
    """Multiple contacts with empty email are fine — partial index excludes them."""
    Contact.objects.create(first_name="A", last_name="One", email="", owner=user)
    # Must not raise.
    Contact.objects.create(first_name="B", last_name="Two", email="", owner=user)


def test_activity_check_rejects_two_parents(user):
    a = Account.objects.create(name="Acme", owner=user)
    c = Contact.objects.create(first_name="A", last_name="B", owner=user)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Activity.objects.create(
                kind="note", subject="bad", owner=user, account=a, contact=c,
            )


def test_activity_check_rejects_zero_parents(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Activity.objects.create(kind="note", subject="orphan", owner=user)


def test_activity_check_accepts_exactly_one_parent(user):
    a = Account.objects.create(name="Acme", owner=user)
    Activity.objects.create(kind="note", subject="ok", owner=user, account=a)


def test_lead_disqualified_requires_reason(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Lead.objects.create(
                last_name="X", owner=user, status="disqualified", disqualified_reason="",
            )


def test_lead_disqualified_with_reason_ok(user):
    Lead.objects.create(
        last_name="X", owner=user, status="disqualified", disqualified_reason="bad fit",
    )


def test_opportunity_lost_requires_close_reason(user):
    from django.utils import timezone

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Opportunity.objects.create(
                name="N",
                owner=user,
                stage="lost",
                closed_at=timezone.now(),
                close_reason="",
            )


def test_opportunity_won_requires_closed_at(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Opportunity.objects.create(
                name="N", owner=user, stage="won", closed_at=None,
            )


def test_opportunity_currency_format(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Opportunity.objects.create(name="N", owner=user, currency="usd")
