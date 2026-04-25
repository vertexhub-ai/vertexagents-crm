"""
CRM domain models — V-169.

Five entities (Account, Contact, Lead, Opportunity, Activity) per the V-157 domain spec,
all soft-deletable (Q8 override). UUID pks, `Meta.ordering = ["-created_at"]` everywhere.

Constraint highlights:
- Account.name: case-insensitive unique via functional index on LOWER(name).
- Contact.email: case-insensitive unique via functional index on LOWER(email),
  partial WHERE email IS NOT NULL AND email <> '' (multiple blank emails are allowed).
- Activity: CHECK constraint enforces exactly one of {lead, contact, account, opportunity}
  is non-null.

Unique constraints are partial: they apply only to alive (deleted_at IS NULL) rows,
so soft-deleted records can coexist with live ones bearing the same name/email.
On Postgres these compile to functional unique indexes (LOWER(col)) with WHERE clauses.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .managers import AliveManager, AllObjectsManager


class TimestampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimestampedModel):
    """Adds `deleted_at` + `deleted_by` and the alive/all_objects manager pair."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = AliveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, user=None) -> None:
        """Mark this row deleted. Idempotent; updates the timestamp on subsequent calls."""
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    def restore(self) -> None:
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])


# --------------------------------------------------------------------------- #
# Account
# --------------------------------------------------------------------------- #


class Account(SoftDeleteModel):
    class Size(models.TextChoices):
        XS = "1-10", "1-10"
        S = "11-50", "11-50"
        M = "51-200", "51-200"
        L = "201-1000", "201-1000"
        XL = "1000+", "1000+"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=16, choices=Size.choices, default=Size.UNKNOWN)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_accounts",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Case-insensitive uniqueness on alive rows only — UniqueConstraint
            # creates a partial unique functional index on LOWER(name).
            models.UniqueConstraint(
                Lower("name"),
                name="account_name_ci_unique_alive",
                condition=models.Q(deleted_at__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def soft_delete(self, user=None) -> None:
        # Account soft-delete does NOT cascade (per spec). FKs from Contact/Opportunity
        # are nullable, so they simply orphan. Activities attached directly to this
        # Account are cascaded by Activity.objects.cascade_soft_delete_for(account=...)
        # — invoked from the view layer that owns the delete action.
        super().soft_delete(user=user)


# --------------------------------------------------------------------------- #
# Contact
# --------------------------------------------------------------------------- #


class Contact(SoftDeleteModel):
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=120, blank=True)

    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contacts",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_contacts",
    )
    source_lead = models.ForeignKey(
        "crm.Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_contacts",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # CI-unique on email, alive rows only, and only when email is set.
            # Multiple contacts with empty email are permitted (email is optional).
            models.UniqueConstraint(
                Lower("email"),
                name="contact_email_ci_unique_alive",
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(email=""),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


# --------------------------------------------------------------------------- #
# Lead
# --------------------------------------------------------------------------- #


class Lead(SoftDeleteModel):
    class Source(models.TextChoices):
        WEB = "web", "Web"
        REFERRAL = "referral", "Referral"
        EVENT = "event", "Event"
        COLD_OUTBOUND = "cold_outbound", "Cold outbound"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        DISQUALIFIED = "disqualified", "Disqualified"
        CONVERTED = "converted", "Converted"

    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=24, choices=Source.choices, default=Source.OTHER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    disqualified_reason = models.CharField(max_length=200, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_leads",
    )

    # Conversion audit fks — populated by V-176 conversion flow.
    converted_contact = models.ForeignKey(
        Contact, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    converted_account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    converted_opportunity = models.ForeignKey(
        "crm.Opportunity", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # If status == disqualified, disqualified_reason must be non-empty.
            models.CheckConstraint(
                name="lead_disqualified_reason_required",
                check=(
                    ~models.Q(status="disqualified")
                    | ~models.Q(disqualified_reason="")
                ),
            ),
        ]

    def __str__(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        if self.company_name:
            return f"{full} ({self.company_name})" if full else self.company_name
        return full or str(self.id)


# --------------------------------------------------------------------------- #
# Opportunity
# --------------------------------------------------------------------------- #


class Opportunity(SoftDeleteModel):
    class Stage(models.TextChoices):
        NEW = "new", "New"
        QUALIFIED = "qualified", "Qualified"
        PROPOSAL = "proposal", "Proposal"
        NEGOTIATION = "negotiation", "Negotiation"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    name = models.CharField(max_length=200)
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities",
    )
    primary_contact = models.ForeignKey(
        Contact, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="primary_opportunities",
    )
    amount_cents = models.BigIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    stage = models.CharField(max_length=16, choices=Stage.choices, default=Stage.NEW)
    expected_close_date = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    close_reason = models.CharField(max_length=200, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_opportunities",
    )
    source_lead = models.ForeignKey(
        Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # `lost` requires close_reason; `won`/`lost` require closed_at.
            models.CheckConstraint(
                name="opportunity_lost_requires_close_reason",
                check=(~models.Q(stage="lost") | ~models.Q(close_reason="")),
            ),
            models.CheckConstraint(
                name="opportunity_terminal_requires_closed_at",
                check=(
                    ~models.Q(stage__in=["won", "lost"])
                    | models.Q(closed_at__isnull=False)
                ),
            ),
            models.CheckConstraint(
                name="opportunity_currency_three_letters",
                check=models.Q(currency__regex=r"^[A-Z]{3}$"),
            ),
        ]

    def __str__(self) -> str:
        return self.name


# --------------------------------------------------------------------------- #
# Activity
# --------------------------------------------------------------------------- #


class Activity(SoftDeleteModel):
    class Kind(models.TextChoices):
        NOTE = "note", "Note"
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        TASK = "task", "Task"

    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.NOTE)
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    lead = models.ForeignKey(
        Lead, null=True, blank=True, on_delete=models.CASCADE, related_name="activities",
    )
    contact = models.ForeignKey(
        Contact, null=True, blank=True, on_delete=models.CASCADE, related_name="activities",
    )
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.CASCADE, related_name="activities",
    )
    opportunity = models.ForeignKey(
        Opportunity, null=True, blank=True, on_delete=models.CASCADE, related_name="activities",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_activities",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Exactly one of the four parent fks must be non-null.
            # In SQL: (lead IS NOT NULL)::int + (contact IS NOT NULL)::int + ... = 1.
            # Django Q-expression equivalent: enumerate the four exclusive cases.
            models.CheckConstraint(
                name="activity_exactly_one_parent",
                check=(
                    models.Q(
                        lead__isnull=False,
                        contact__isnull=True,
                        account__isnull=True,
                        opportunity__isnull=True,
                    )
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=False,
                        account__isnull=True,
                        opportunity__isnull=True,
                    )
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=True,
                        account__isnull=False,
                        opportunity__isnull=True,
                    )
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=True,
                        account__isnull=True,
                        opportunity__isnull=False,
                    )
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.kind}] {self.subject}"

    @classmethod
    def cascade_soft_delete_for(
        cls,
        *,
        user=None,
        lead: Lead | None = None,
        contact: Contact | None = None,
        account: Account | None = None,
        opportunity: Opportunity | None = None,
    ) -> int:
        """Soft-delete all activities attached to the given parent.

        Spec: soft-deleting a parent of `Activity` cascades soft-delete to the activities.
        Call this from the view that owns the parent's soft_delete().
        """
        filters = {}
        if lead is not None:
            filters["lead"] = lead
        if contact is not None:
            filters["contact"] = contact
        if account is not None:
            filters["account"] = account
        if opportunity is not None:
            filters["opportunity"] = opportunity
        if not filters:
            return 0
        return cls.all_objects.filter(**filters).alive().soft_delete(user=user)
