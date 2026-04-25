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
            name="Lead",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("status", models.CharField(
                    choices=[("new", "New"), ("contacted", "Contacted"), ("qualified", "Qualified"), ("lost", "Lost")],
                    default="new", max_length=20,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("domain", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Contact",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("account", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="contacts", to="crm.account",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Opportunity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("account", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="opportunities", to="crm.account",
                )),
                ("stage", models.CharField(
                    choices=[
                        ("prospect", "Prospect"), ("proposal", "Proposal"),
                        ("negotiation", "Negotiation"), ("closed_won", "Closed Won"),
                        ("closed_lost", "Closed Lost"),
                    ],
                    default="prospect", max_length=30,
                )),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("close_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="Activity",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("kind", models.CharField(
                    choices=[("note", "Note"), ("call", "Call"), ("email", "Email"), ("meeting", "Meeting"), ("task", "Task")],
                    max_length=20,
                )),
                ("subject", models.CharField(max_length=300)),
                ("body", models.TextField(blank=True)),
                ("author", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="activities",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("lead", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="activities", to="crm.lead",
                )),
                ("contact", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="activities", to="crm.contact",
                )),
                ("account", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="activities", to="crm.account",
                )),
                ("opportunity", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="activities", to="crm.opportunity",
                )),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
            options={"abstract": False},
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
