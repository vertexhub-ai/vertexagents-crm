# vertexagents-crm

## V-170 — Django admin (emergency back-office)

`/admin` is the ops-only back-office. Every model that ships in this repo is
registered there with searchable / filterable list views and the
soft-deleted rows visible (admins use the `all_objects` manager to bypass the
default "alive only" filter). Conversion audit fields, `id`, timestamps, and
soft-delete bookkeeping are read-only — the admin is for observation and
hand-corrected rescue, not for casually rewriting history.

| Model    | App        | Admin module      | Soft-deletes visible | Restore action |
|----------|------------|-------------------|----------------------|----------------|
| Account  | `accounts` | `accounts.admin`  | yes (`all_objects`)  | yes            |
| Lead     | `leads`    | `leads.admin`     | yes (`all_objects`)  | yes            |

Models that are not yet in the codebase (Contact, Opportunity, Activity)
will get the same admin treatment when they land — see the V-170 issue for
the follow-up scope.

### Runbook: undo a wrong lead conversion

When a rep accidentally converts a Lead in the app UI, ops can use `/admin`
to reverse it. The conversion creates / links rows in three other tables
(`Contact`, `Account`, `Opportunity`); the `Lead` row keeps `converted_*`
audit FKs and a `converted_at` timestamp. Undoing is a multi-step manual
procedure because we never want to silently delete real customer data — ops
must explicitly decide which downstream rows to keep, soft-delete, or
re-attach.

> **Auth gate.** Only staff with `is_superuser=True` (or the `crm.undo_conversion`
> permission once V-168 ships it) should run this procedure. Log the
> reason — ticket / Slack thread / who asked — before you start.

**Step 1 — Observe.** Open the Lead in `/admin`, copy the four read-only
audit values: `converted_at`, `converted_contact`, `converted_account`,
`converted_opportunity`. Cross-reference each downstream row in its admin
list. You are deciding, per row:

- *Keep alive* — the record is independently valid (e.g. the Contact
  represents a real person who exists in your CRM regardless of the bad
  conversion). Leave it; only detach it from the Lead.
- *Soft-delete* — the record only exists because of the bad conversion and
  has no other meaning. Use the model's standard "Delete" admin action,
  which calls `soft_delete(user)` and sets `deleted_at` / `deleted_by`.
- *Hard-delete* — almost never. Only when the row was created seconds ago
  by the bad conversion and has zero downstream references. Always prefer
  soft-delete.

**Step 2 — Mutate (single transaction).** From a Django shell on a host
with database write access:

```python
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from leads.models import Lead, Status

User = get_user_model()
me = User.objects.get(username="<your-staff-username>")
lead = Lead.all_objects.get(id="<lead-uuid>")

with transaction.atomic():
    # Decide per row what to do with the downstream artefacts:
    if lead.converted_opportunity_id:
        opp = lead.converted_opportunity
        opp.soft_delete(me)            # or opp.save() with detach, per Step 1
    if lead.converted_contact_id:
        c = lead.converted_contact
        c.soft_delete(me)              # only if the Contact has no other use
    # Account is rarely soft-deleted on undo — Accounts represent companies
    # that usually exist independent of a single bad conversion.

    # Detach + revert the Lead itself.
    lead.converted_contact = None
    lead.converted_account = None
    lead.converted_opportunity = None
    lead.converted_at = None
    lead.status = Status.NEW           # or whatever pre-conversion status applies
    lead.save(update_fields=[
        "converted_contact", "converted_account", "converted_opportunity",
        "converted_at", "status", "updated_at",
    ])
```

**Step 3 — Verify.** Reload the Lead in `/admin`; confirm the four
`converted_*` fields are blank, status is correct, and the soft-deleted
downstream rows show the expected `deleted_at` / `deleted_by`.

**Step 4 — Document.** Comment on the original support ticket (or
the squad's incident channel) with the Lead UUID, the downstream UUIDs you
touched, and the action taken (keep / soft-delete / hard-delete). The audit
trail is the read-only `deleted_at` / `deleted_by` columns plus your
written record.

#### Restoring an over-zealous undo

If you soft-deleted the wrong downstream row, find it in `/admin` (it is
visible because the admin uses `all_objects`), select it, and use the
"Restore selected …" action — that resets `deleted_at` and `deleted_by` to
`NULL`. If you also blanked the Lead's `converted_*` audit FKs, repopulate
them by hand from the values you recorded in Step 1.
