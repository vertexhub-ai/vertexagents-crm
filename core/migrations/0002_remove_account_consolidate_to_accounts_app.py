"""V-271 fix: remove duplicate core.Account model.

Account is canonical in the `accounts` app. core.Account was a duplicate
that caused Django boot to fail with fields.E304 reverse-accessor
clashes. We drop the model and have core.{Contact,Lead,Opportunity,
Activity} reference "accounts.Account" via string FK instead.

Data migration:
  Step 1 — For each core_account row:
    a) If accounts_account already has a row with the same name (iexact),
       record the id mapping (core_id → accounts_id).
    b) Otherwise create a new accounts_account row using the core_account
       id so no remapping is needed.
  Step 2 — Rewrite account_id FKs in core_{contact,lead,opportunity,
       activity} to the accounts_account id (needed when Step 1a fired,
       i.e. the IDs differ).
  Step 3 — Schema: AlterField + DeleteModel.
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
        return  # accounts app not migrated yet

    # Build id_map: core_account.id → accounts_account.id
    id_map = {}
    for ca in CoreAccount.objects.all():
        existing = AccountsAccount.objects.filter(name__iexact=ca.name).first()
        if existing:
            if existing.id != ca.id:
                id_map[ca.id] = existing.id
            # else: same id, no remapping needed
        else:
            # Create with the same id so no remapping is needed.
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
        return  # Nothing to remap — all IDs already align.

    # Remap account_id FKs in all four child tables.
    # We use raw SQL because the historical models may not expose account_id
    # directly as an updatable field after the AlterField hasn't run yet.
    db = schema_editor.connection
    for old_id, new_id in id_map.items():
        for table, col in [
            ("core_contact", "account_id"),
            ("core_lead", "converted_account_id"),
            ("core_opportunity", "account_id"),
            ("core_activity", "account_id"),
        ]:
            db.cursor().execute(
                f"UPDATE {table} SET {col} = %s WHERE {col} = %s",
                [str(new_id), str(old_id)],
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(copy_and_remap, noop_reverse),
        # Retarget FKs from core.Account → accounts.Account.
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
