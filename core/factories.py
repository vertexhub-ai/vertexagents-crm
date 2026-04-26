"""
factory_boy factories for all CRM models.

Usage in tests or scripts:
    from core.factories import LeadFactory, OpportunityFactory
    lead = LeadFactory()
    opp  = OpportunityFactory(stage="proposal")
"""

import random
from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker as _Faker

from core.models import Account, Activity, Contact, Lead, Opportunity, User

_fake = _Faker()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n:04d}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    role = User.ROLE_REP
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "changeme!")
        manager = cls._get_manager(model_class)
        user = manager.create_user(*args, **kwargs)
        user.set_password(password)
        user.save(update_fields=["password"])
        return user


class AdminUserFactory(UserFactory):
    role = User.ROLE_ADMIN
    is_staff = True
    username = factory.Sequence(lambda n: f"admin{n:04d}")


class AccountFactory(DjangoModelFactory):
    class Meta:
        model = Account

    name = factory.LazyFunction(lambda: _fake.company())
    website = factory.LazyAttribute(
        lambda o: f"https://www.{o.name.lower().replace(' ', '-').replace(',', '').replace('.', '')[:30]}.com"
    )
    industry = factory.Faker(
        "random_element",
        elements=[
            "Software", "Finance", "Healthcare", "Manufacturing",
            "Retail", "Consulting", "Education", "Media",
        ],
    )
    size = factory.Faker(
        "random_element",
        elements=[c[0] for c in Account.SIZE_CHOICES],
    )
    owner = factory.SubFactory(UserFactory)


class ContactFactory(DjangoModelFactory):
    class Meta:
        model = Contact

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(
        lambda o: f"{o.first_name.lower()}.{o.last_name.lower()}@example.com"
    )
    phone = factory.Faker("phone_number")
    title = factory.Faker(
        "random_element",
        elements=[
            "CEO", "VP Sales", "Account Executive", "Sales Director",
            "CFO", "CTO", "Operations Manager", "Procurement Lead",
            "Business Development", "Founder",
        ],
    )
    account = None
    owner = factory.SubFactory(UserFactory)
    source_lead = None


class LeadFactory(DjangoModelFactory):
    class Meta:
        model = Lead

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(
        lambda o: f"{o.first_name.lower()}.{o.last_name.lower()}@prospect.io"
    )
    phone = factory.Faker("phone_number")
    company_name = factory.Faker("company")
    title = factory.Faker(
        "random_element",
        elements=["CEO", "VP Sales", "Director", "Manager", "Owner", "Founder"],
    )
    source = factory.Faker(
        "random_element",
        elements=[c[0] for c in Lead.SOURCE_CHOICES],
    )
    status = Lead.STATUS_NEW
    owner = factory.SubFactory(UserFactory)


class OpportunityFactory(DjangoModelFactory):
    class Meta:
        model = Opportunity

    name = factory.LazyFunction(lambda: f"{_fake.company()} — Opportunity")
    account = None
    primary_contact = None
    amount_cents = factory.LazyFunction(
        lambda: random.choice([None, random.randint(500_00, 500_000_00)])
    )
    currency = "USD"
    stage = Opportunity.STAGE_NEW
    expected_close_date = factory.LazyFunction(
        lambda: (timezone.now() + timedelta(days=random.randint(14, 180))).date()
    )
    closed_at = None
    close_reason = ""
    owner = factory.SubFactory(UserFactory)
    source_lead = None


class ActivityFactory(DjangoModelFactory):
    """
    Caller MUST provide exactly one of lead=, contact=, account=, opportunity=.
    All four default to None here; the CheckConstraint will reject rows where
    that invariant is violated.
    """

    class Meta:
        model = Activity

    kind = factory.Faker(
        "random_element",
        elements=[c[0] for c in Activity.KIND_CHOICES],
    )
    subject = factory.Faker("sentence", nb_words=5)
    body = factory.Faker("paragraph")
    due_at = None
    completed_at = None
    owner = factory.SubFactory(UserFactory)

    lead = None
    contact = None
    account = None
    opportunity = None

    class Params:
        as_task = factory.Trait(
            kind=Activity.KIND_TASK,
            subject=factory.Faker("sentence", nb_words=4),
            due_at=factory.LazyFunction(
                lambda: timezone.now() + timedelta(days=random.randint(1, 30))
            ),
        )
        overdue = factory.Trait(
            kind=Activity.KIND_TASK,
            subject=factory.Faker("sentence", nb_words=4),
            due_at=factory.LazyFunction(
                lambda: timezone.now() - timedelta(days=random.randint(1, 14))
            ),
        )
        note = factory.Trait(kind=Activity.KIND_NOTE)
        call = factory.Trait(kind=Activity.KIND_CALL)
