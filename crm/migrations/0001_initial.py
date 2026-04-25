"""
Initial migration for the CRM domain (V-169).

Creates Account, Contact, Lead, Opportunity, Activity. All five carry soft-delete
columns (`deleted_at`, `deleted_by`). Forward + backward (`migrate crm zero`) are
both clean: the only object created outside `CreateModel` is a set of constraints,
which Django reverses by `DROP CONSTRAINT` automatically.

Constraints attached here (rather than inline `models.options`) so the dependency
order is unambiguous:
- Account: UniqueConstraint on Lower("name") WHERE deleted_at IS NULL
- Contact: UniqueConstraint on Lower("email") WHERE deleted_at IS NULL AND email <> ''
- Activity: CheckConstraint enforcing exactly-one-of {lead, contact, account, opportunity}
- Opportunity: terminal-stage / close_reason / currency-format checks
- Lead: disqualified_reason required when status=disqualified
"""

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -------------------- Account --------------------
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("name", models.CharField(max_length=200)),
                ("website", models.URLField(blank=True)),
                ("industry", models.CharField(blank=True, max_length=80)),
                (
                    "size",
                    models.CharField(
                        choices=[
                            ("1-10", "1-10"),
                            ("11-50", "11-50"),
                            ("51-200", "51-200"),
                            ("201-1000", "201-1000"),
                            ("1000+", "1000+"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=16,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        # -------------------- Lead (created before Contact + Opportunity reference it) --------------------
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("first_name", models.CharField(blank=True, max_length=120)),
                ("last_name", models.CharField(max_length=120)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("company_name", models.CharField(blank=True, max_length=200)),
                ("title", models.CharField(blank=True, max_length=120)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("web", "Web"),
                            ("referral", "Referral"),
                            ("event", "Event"),
                            ("cold_outbound", "Cold outbound"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=24,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("contacted", "Contacted"),
                            ("qualified", "Qualified"),
                            ("disqualified", "Disqualified"),
                            ("converted", "Converted"),
                        ],
                        default="new",
                        max_length=16,
                    ),
                ),
                ("disqualified_reason", models.CharField(blank=True, max_length=200)),
                ("converted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_leads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "converted_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="crm.account",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        # -------------------- Contact --------------------
        migrations.CreateModel(
            name="Contact",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("first_name", models.CharField(max_length=120)),
                ("last_name", models.CharField(max_length=120)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("title", models.CharField(blank=True, max_length=120)),
                (
                    "account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="contacts",
                        to="crm.account",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_contacts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_lead",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="converted_contacts",
                        to="crm.lead",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        # Backfill the Lead.converted_contact FK now that Contact exists.
        migrations.AddField(
            model_name="lead",
            name="converted_contact",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="crm.contact",
            ),
        ),
        # -------------------- Opportunity --------------------
        migrations.CreateModel(
            name="Opportunity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("name", models.CharField(max_length=200)),
                ("amount_cents", models.BigIntegerField(blank=True, null=True)),
                ("currency", models.CharField(default="USD", max_length=3)),
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("qualified", "Qualified"),
                            ("proposal", "Proposal"),
                            ("negotiation", "Negotiation"),
                            ("won", "Won"),
                            ("lost", "Lost"),
                        ],
                        default="new",
                        max_length=16,
                    ),
                ),
                ("expected_close_date", models.DateField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("close_reason", models.CharField(blank=True, max_length=200)),
                (
                    "account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="opportunities",
                        to="crm.account",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_opportunities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "primary_contact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="primary_opportunities",
                        to="crm.contact",
                    ),
                ),
                (
                    "source_lead",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="crm.lead",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        # Backfill Lead.converted_opportunity now that Opportunity exists.
        migrations.AddField(
            model_name="lead",
            name="converted_opportunity",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="crm.opportunity",
            ),
        ),
        # -------------------- Activity --------------------
        migrations.CreateModel(
            name="Activity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("note", "Note"),
                            ("call", "Call"),
                            ("email", "Email"),
                            ("meeting", "Meeting"),
                            ("task", "Task"),
                        ],
                        default="note",
                        max_length=16,
                    ),
                ),
                ("subject", models.CharField(max_length=200)),
                ("body", models.TextField(blank=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="crm.account",
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="crm.contact",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lead",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="crm.lead",
                    ),
                ),
                (
                    "opportunity",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activities",
                        to="crm.opportunity",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_activities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        # -------------------- Constraints (added last so deps are clear) --------------------
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(
                Lower("name"),
                condition=models.Q(deleted_at__isnull=True),
                name="account_name_ci_unique_alive",
            ),
        ),
        migrations.AddConstraint(
            model_name="contact",
            constraint=models.UniqueConstraint(
                Lower("email"),
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(email=""),
                name="contact_email_ci_unique_alive",
            ),
        ),
        migrations.AddConstraint(
            model_name="lead",
            constraint=models.CheckConstraint(
                check=(~models.Q(status="disqualified") | ~models.Q(disqualified_reason="")),
                name="lead_disqualified_reason_required",
            ),
        ),
        migrations.AddConstraint(
            model_name="opportunity",
            constraint=models.CheckConstraint(
                check=(~models.Q(stage="lost") | ~models.Q(close_reason="")),
                name="opportunity_lost_requires_close_reason",
            ),
        ),
        migrations.AddConstraint(
            model_name="opportunity",
            constraint=models.CheckConstraint(
                check=(
                    ~models.Q(stage__in=["won", "lost"])
                    | models.Q(closed_at__isnull=False)
                ),
                name="opportunity_terminal_requires_closed_at",
            ),
        ),
        migrations.AddConstraint(
            model_name="opportunity",
            constraint=models.CheckConstraint(
                check=models.Q(currency__regex=r"^[A-Z]{3}$"),
                name="opportunity_currency_three_letters",
            ),
        ),
        migrations.AddConstraint(
            model_name="activity",
            constraint=models.CheckConstraint(
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
                name="activity_exactly_one_parent",
            ),
        ),
    ]
