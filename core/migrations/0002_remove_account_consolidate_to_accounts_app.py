"""V-271 fix: remove duplicate core.Account model.

Account is canonical in the `accounts` app. core.Account was a duplicate
that caused Django boot to fail with fields.E304 reverse-accessor
clashes. We drop the model and have core.{Contact,Lead,Opportunity,
Activity} reference "accounts.Account" via string FK instead.

Data migration (three steps):
  1. Copy core_account rows → accounts_account where they don't already
     exist (by lowercased name).  For rows that DO exist (matched by
     name, different UUID) build an id_map.
  2. Using session_replication_role='replica' to suppress FK triggers,
     rewrite account_id FKs in child tables to the canonical
     accounts_account UUIDs.
  3. Schema: AlterField x4, DeleteModel.
"""

from django.db import migrations, models


def copy_and_remap(apps, schema_editor):
    try:
        CoreAccount = apps.get_model("core", "Account")
    except LookupError:
        return  # Already removed
    try:
        AccountsAccount = apps.get_model("accounts", "Account")
    except LookupError:
        return

    id_map = {}  # core_account.id → accounts_account.id (when different)

    for ca in CoreAccount.objects.all():
        existing = AccountsAccount.objects.filter(name__iexact=ca.name).first()
        if existing:
            if existing.id != ca.id:
                id_map[ca.id] = existing.id
        else:
            AccountsAccount.objects.create(
                id=ca.id,
                name=ca.name,
                name_lower=ca.name.lower(),
                website=getattr(ca, "website", "") or "",
                industry=getattr(ca, "industry", "") or "",
                size=getattr(ca, "size", "") or "unknown",
                owner=ca.owner,
            )

    if not id_map:
        return  # All core_account IDs preserved in accounts_account; no remapping.

    db = schema_editor.connection
    cursor = db.cursor()

    # Disable FK constraint enforcement for this session so we can remap
    # account_id values from core_account UUIDs to accounts_account UUIDs
    # before the AlterField changes the FK target.
    cursor.execute("SET session_replication_role = 'replica'")
    try:
        for old_id, new_id in id_map.items():
            for table, col in [
                ("core_contact", "account_id"),
                ("core_lead", "converted_account_id"),
                ("core_opportunity", "account_id"),
                ("core_activity", "account_id"),
            ]:
                cursor.execute(
                    f"UPDATE {table} SET {col} = %s WHERE {col} = %s",
                    [str(new_id), str(old_id)],
                )
    finally:
        cursor.execute("SET session_replication_role = 'origin'")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_and_remap, noop_reverse),
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
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
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
