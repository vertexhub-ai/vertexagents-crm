"""Soft-delete manager + cascade semantics."""

from __future__ import annotations

import pytest

from crm.models import Account, Activity, Contact, Lead, Opportunity


pytestmark = pytest.mark.django_db


def test_objects_hides_soft_deleted_rows(user):
    a = Account.objects.create(name="Acme", owner=user)
    assert Account.objects.count() == 1
    a.soft_delete(user=user)
    assert Account.objects.count() == 0
    assert Account.all_objects.count() == 1


def test_restore_brings_back_into_default_queryset(user):
    a = Account.objects.create(name="Acme", owner=user)
    a.soft_delete(user=user)
    a.refresh_from_db()
    a.restore()
    assert Account.objects.filter(pk=a.pk).exists()
    assert a.deleted_at is None
    assert a.deleted_by is None


def test_soft_delete_records_actor(user, admin):
    a = Account.objects.create(name="Acme", owner=user)
    a.soft_delete(user=admin)
    a.refresh_from_db()
    assert a.deleted_at is not None
    assert a.deleted_by_id == admin.id


def test_account_soft_delete_does_not_cascade(user):
    """Per spec: account soft-delete orphans contacts/opps (FKs are nullable)."""
    a = Account.objects.create(name="Acme", owner=user)
    c = Contact.objects.create(first_name="A", last_name="B", account=a, owner=user)
    a.soft_delete(user=user)
    c.refresh_from_db()
    # Contact remains alive; only the account is soft-deleted.
    assert c.deleted_at is None
    assert Contact.objects.filter(pk=c.pk).exists()


def test_activity_cascade_helper_soft_deletes_attached_activities(user):
    a = Account.objects.create(name="Acme", owner=user)
    Activity.objects.create(kind="note", subject="hi", account=a, owner=user)
    Activity.objects.create(kind="note", subject="bye", account=a, owner=user)
    n = Activity.cascade_soft_delete_for(user=user, account=a)
    assert n == 2
    assert Activity.objects.filter(account=a).count() == 0
    assert Activity.all_objects.filter(account=a).count() == 2


def test_queryset_alive_and_dead_helpers(user):
    a1 = Account.objects.create(name="Live", owner=user)
    a2 = Account.objects.create(name="Dead", owner=user)
    a2.soft_delete(user=user)
    assert {a.pk for a in Account.all_objects.alive()} == {a1.pk}
    assert {a.pk for a in Account.all_objects.dead()} == {a2.pk}


def test_bulk_soft_delete_via_queryset(user):
    Account.objects.create(name="A", owner=user)
    Account.objects.create(name="B", owner=user)
    n = Account.objects.all().soft_delete(user=user)
    assert n == 2
    assert Account.objects.count() == 0


def test_lead_status_enum_round_trip(user):
    l = Lead.objects.create(last_name="Doe", owner=user, status=Lead.Status.QUALIFIED)
    l.refresh_from_db()
    assert l.status == "qualified"


def test_opportunity_stage_enum_round_trip(user):
    o = Opportunity.objects.create(
        name="Big deal",
        owner=user,
        stage=Opportunity.Stage.PROPOSAL,
    )
    o.refresh_from_db()
    assert o.stage == "proposal"


def test_activity_kind_enum_round_trip(user):
    a = Account.objects.create(name="X", owner=user)
    act = Activity.objects.create(kind=Activity.Kind.CALL, subject="ring", account=a, owner=user)
    act.refresh_from_db()
    assert act.kind == "call"
