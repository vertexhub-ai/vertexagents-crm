from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


def seed_dev_users(apps, schema_editor):
    if not settings.DEBUG:
        return
    User = apps.get_model("accounts", "User")
    User.objects.create(
        username="admin",
        password=make_password("admin"),
        email="admin@example.com",
        role="admin",
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )
    User.objects.create(
        username="rep",
        password=make_password("rep"),
        email="rep@example.com",
        role="rep",
        is_active=True,
    )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(seed_dev_users, migrations.RunPython.noop),
    ]
