import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("name_lower", models.CharField(db_index=True, editable=False, max_length=200)),
                ("website", models.URLField(blank=True)),
                ("industry", models.CharField(blank=True, max_length=80)),
                ("size", models.CharField(
                    choices=[
                        ("1-10", "1–10"),
                        ("11-50", "11–50"),
                        ("51-200", "51–200"),
                        ("201-1000", "201–1,000"),
                        ("1000+", "1,000+"),
                        ("unknown", "Unknown"),
                    ],
                    default="unknown",
                    max_length=20,
                )),
                ("owner", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="owned_accounts",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="deleted_accounts",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["name_lower"],
            },
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True),
                fields=["name_lower"],
                name="unique_active_account_name_ci",
            ),
        ),
    ]
