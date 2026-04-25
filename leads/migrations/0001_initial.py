import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    # Depends on C3 (V-169) schema migration and auth.
    # contacts/accounts/opportunities initial migrations must land before this runs.
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contacts", "0001_initial"),
        ("accounts", "0001_initial"),
        ("opportunities", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("first_name", models.CharField(blank=True, max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("company_name", models.CharField(blank=True, max_length=200)),
                ("title", models.CharField(blank=True, max_length=120)),
                (
                    "source",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("web", "Web"),
                            ("referral", "Referral"),
                            ("event", "Event"),
                            ("cold_outbound", "Cold Outbound"),
                            ("other", "Other"),
                        ],
                        max_length=20,
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
                        max_length=20,
                    ),
                ),
                ("disqualified_reason", models.CharField(blank=True, max_length=200)),
                ("converted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_leads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="deleted_leads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "converted_contact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="contacts.contact",
                    ),
                ),
                (
                    "converted_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="accounts.account",
                    ),
                ),
                (
                    "converted_opportunity",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="opportunities.opportunity",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
