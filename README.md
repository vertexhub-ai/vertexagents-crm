# vertexagents-crm

Small internal CRM (Django 5.x + HTMX + Postgres 16). See V-156 / V-157 for the spec.

## V-169 — Schema + migrations

This branch lands the data layer for Account, Contact, Lead, Opportunity, Activity,
all soft-deletable per CEO-ratified Q8.

- `accounts/` — minimum-viable custom `User` model so `AUTH_USER_MODEL` is set
  before `crm/` migrations reference it. V-168 will extend with auth views,
  `django-axes` lockout, password reset, and seed users.
- `crm/` — the five domain models, soft-delete manager, hand-written migration.

### Run

```bash
pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=config.settings python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings python manage.py migrate crm zero  # backward-clean check
```

### Tests

Constraint tests use Postgres-only features (functional indexes, partial unique,
CHECK). They auto-skip when `connection.vendor != 'postgresql'`.

```bash
# CI / Postgres
pytest

# Local without Postgres
DJANGO_TEST_SQLITE=1 pytest
```
