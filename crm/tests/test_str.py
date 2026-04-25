"""__str__ + Meta.ordering smoke tests."""

from __future__ import annotations

import pytest

from crm.models import Account, Activity, Contact, Lead, Opportunity


pytestmark = pytest.mark.django_db


def test_account_str(user):
    a = Account.objects.create(name="Acme", owner=user)
    assert str(a) == "Acme"


def test_contact_str(user):
    c = Contact.objects.create(first_name="Ada", last_name="Lovelace", owner=user)
    assert str(c) == "Ada Lovelace"


def test_lead_str_with_company(user):
    l = Lead.objects.create(last_name="Doe", company_name="Initech", owner=user)
    assert "Initech" in str(l)


def test_opportunity_str(user):
    o = Opportunity.objects.create(name="Big deal", owner=user)
    assert str(o) == "Big deal"


def test_activity_str(user):
    a = Account.objects.create(name="A", owner=user)
    act = Activity.objects.create(kind="call", subject="ring", owner=user, account=a)
    assert "ring" in str(act) and "call" in str(act)


def test_ordering_newest_first(user):
    Account.objects.create(name="First", owner=user)
    Account.objects.create(name="Second", owner=user)
    names = list(Account.objects.values_list("name", flat=True))
    assert names == ["Second", "First"]
