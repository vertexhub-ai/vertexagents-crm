"""V-271 fix: remove duplicate core.Account model.

Account is canonical in the `accounts` app. core.Account was a duplicate
that caused Django boot to fail with fields.E304 reverse-accessor
clashes. We drop the model and have core.{Contact,Lead,Opportunity,
Activity} reference "accounts.Account" via string FK instead.

Data migration: copy any rows from core_account → accounts_account that
don't already exist there (matched by lowercased name). Most production
data is already in accounts_account because the live UI writes there;
this is defensive for any seed-data leftovers.
"""

from django.db import migrations, models


def copy_core_accounts_to_accounts_app(apps, schema_editor):
    # Use the historical models so migrations work without the live model.
    try:
        CoreAccount = apps.get_model("core", "Account")
    except LookupError:
        return  # Already removed
    try:
        AccountsAccount = apps.get_model("accounts", "Account")
    except LookupError:
        return  # accounts app not migrated yet — nothing to do
    for ca in CoreAccount.objects.all():
        # Match on lowercased name to avoid case-sensitive duplicates.
        if AccountsAccount.objects.filter(name__iexact=ca.name).exists():
            continue
        AccountsAccount.objects.create(
            id=ca.id,
            name=ca.name,
            name_lower=ca.name.lower(),
            website=getattr(ca, "website", "") or "",
            industry=getattr(ca, "industry", "") or "",
            size=getattr(ca, "size", "") or "unknown",
            owner=ca.owner,
        )


def noop_reverse(apps, schema_editor):
    # Best-effort reverse: leave accounts.Account intact.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_core_accounts_to_accounts_app, noop_reverse),
        # Update FKs in core.Contact/Lead/Opportunity/Activity to point at
        # accounts.Account instead of the local Account.
        migrations.AlterField(
            model_name="contact",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="contacts",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="lead",
            name="converted_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="source_leads",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="opportunity",
            name="account",
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name="opportunities",
                to="accounts.account",
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="activities",
                to="accounts.account",
            ),
        ),
        migrations.DeleteModel(name="Account"),
    ]
