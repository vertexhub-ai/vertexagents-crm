"""
python manage.py seed_demo

Produces the demo dataset specified in V-157 DoD #2:
  - 2 admin users, 3 rep users
  - ~10 Accounts
  - ~25 Contacts (mix with/without account)
  - ~15 Leads (mix of statuses; converted leads use the real C9 service)
  - ~12 Opportunities (all stages; stage moves use the real C10 service)
  - Activities sprinkled across records

Idempotent by default (truncates then re-seeds).
Pass --no-truncate for an additive run.

Credentials are printed to stdout and written to .seed-creds.txt (gitignored).
"""

import random
import secrets
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.factories import (
    AccountFactory,
    ActivityFactory,
    AdminUserFactory,
    ContactFactory,
    LeadFactory,
    OpportunityFactory,
    UserFactory,
)
from core.models import Account, Activity, Contact, Lead, Opportunity, User
from core.services.leads import AccountChoice, ContactData, ConversionError, OpportunityData, convert_lead
from core.services.opportunities import TransitionError, transition_stage


SEED_ADMIN_USERNAMES = ["alice_admin", "bob_admin"]
SEED_REP_USERNAMES = ["carol_rep", "dan_rep", "eve_rep"]
SEED_PASSWORD = "Demo1234!"

# Exactly the stages each opportunity should pass through before resting.
# The final stage in each list is where it ends up.
OPP_STAGE_PATHS = [
    ["new"],
    ["new"],
    ["new", "qualified"],
    ["new", "qualified"],
    ["new", "qualified", "proposal"],
    ["new", "qualified", "proposal"],
    ["new", "qualified", "proposal", "negotiation"],
    ["new", "qualified", "proposal", "negotiation"],
    # won — requires expected_close_date (already set by factory)
    ["new", "qualified", "proposal", "negotiation", "won"],
    # lost — requires close_reason
    ["new", "qualified", "proposal", "lost"],
    # A couple of extras to reach ~12 total
    ["new", "qualified"],
    ["new", "qualified", "proposal", "negotiation"],
]


class Command(BaseCommand):
    help = "Seed the database with demo fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-truncate",
            action="store_true",
            default=False,
            help="Add records without truncating first (additive run).",
        )

    def handle(self, *args, **options):
        no_truncate = options["no_truncate"]

        with transaction.atomic():
            if not no_truncate:
                self.stdout.write("Truncating existing seed data …")
                self._truncate()

            self.stdout.write("Seeding users …")
            admins, reps = self._seed_users()

            all_users = admins + reps
            actor = admins[0]  # used as the "system" actor for service calls

            self.stdout.write("Seeding accounts …")
            accounts = self._seed_accounts(all_users)

            self.stdout.write("Seeding contacts …")
            contacts = self._seed_contacts(all_users, accounts)

            self.stdout.write("Seeding leads …")
            leads, converted_contacts, converted_accts = self._seed_leads(
                all_users, accounts, actor
            )

            self.stdout.write("Seeding opportunities …")
            opps = self._seed_opportunities(
                all_users, accounts, contacts, actor
            )

            self.stdout.write("Seeding activities …")
            self._seed_activities(
                all_users, leads, contacts, accounts, opps
            )

        self._write_creds(admins, reps)
        self._print_summary(admins, reps, accounts, contacts, leads, opps)

    # ------------------------------------------------------------------
    # Truncation
    # ------------------------------------------------------------------

    def _truncate(self):
        # Delete in reverse FK order to avoid constraint errors.
        Activity.all_objects.all().delete()
        Opportunity.all_objects.all().delete()
        Lead.all_objects.all().delete()
        Contact.all_objects.all().delete()
        Account.all_objects.all().delete()
        User.objects.filter(
            username__in=SEED_ADMIN_USERNAMES + SEED_REP_USERNAMES
        ).delete()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _seed_users(self):
        pw_hash = make_password(SEED_PASSWORD)

        admins = []
        for uname in SEED_ADMIN_USERNAMES:
            u, _ = User.objects.update_or_create(
                username=uname,
                defaults={
                    "first_name": uname.split("_")[0].capitalize(),
                    "last_name": "Admin",
                    "email": f"{uname}@example.com",
                    "role": User.ROLE_ADMIN,
                    "is_staff": True,
                    "is_superuser": False,
                    "password": pw_hash,
                },
            )
            admins.append(u)

        reps = []
        for uname in SEED_REP_USERNAMES:
            u, _ = User.objects.update_or_create(
                username=uname,
                defaults={
                    "first_name": uname.split("_")[0].capitalize(),
                    "last_name": "Rep",
                    "email": f"{uname}@example.com",
                    "role": User.ROLE_REP,
                    "is_staff": False,
                    "password": pw_hash,
                },
            )
            reps.append(u)

        return admins, reps

    # ------------------------------------------------------------------
    # Accounts (~10)
    # ------------------------------------------------------------------

    def _seed_accounts(self, users):
        accounts = []
        names = [
            "Acme Corp", "Globex Industries", "Initech Solutions",
            "Umbrella Technologies", "Stark Enterprises", "Wayne Capital",
            "Oscorp International", "Massive Dynamics", "Veridian Dynamics",
            "Soylent Corp",
        ]
        for name in names:
            acct = AccountFactory(
                name=name,
                owner=random.choice(users),
            )
            accounts.append(acct)
        return accounts

    # ------------------------------------------------------------------
    # Contacts (~25)
    # ------------------------------------------------------------------

    def _seed_contacts(self, users, accounts):
        contacts = []
        # ~18 contacts with an account
        for _ in range(18):
            c = ContactFactory(
                owner=random.choice(users),
                account=random.choice(accounts),
            )
            contacts.append(c)
        # ~7 contacts without an account (contact-first sales)
        for _ in range(7):
            c = ContactFactory(owner=random.choice(users), account=None)
            contacts.append(c)
        return contacts

    # ------------------------------------------------------------------
    # Leads (~15)
    # ------------------------------------------------------------------

    def _seed_leads(self, users, accounts, actor):
        leads = []
        converted_contacts = []
        converted_accts = []

        statuses_plan = [
            Lead.STATUS_NEW,
            Lead.STATUS_NEW,
            Lead.STATUS_NEW,
            Lead.STATUS_CONTACTED,
            Lead.STATUS_CONTACTED,
            Lead.STATUS_CONTACTED,
            Lead.STATUS_QUALIFIED,
            Lead.STATUS_QUALIFIED,
            Lead.STATUS_DISQUALIFIED,
            Lead.STATUS_DISQUALIFIED,
            # 5 to be converted (status will become converted via C9)
            "TO_CONVERT",
            "TO_CONVERT",
            "TO_CONVERT",
            "TO_CONVERT",
            "TO_CONVERT",
        ]
        random.shuffle(statuses_plan)

        for planned_status in statuses_plan:
            owner = random.choice(users)

            if planned_status == "TO_CONVERT":
                # Create qualified so the C9 service can convert it
                lead = LeadFactory(
                    status=Lead.STATUS_QUALIFIED,
                    owner=owner,
                    company_name=f"{owner.first_name}'s Prospect Inc",
                )
                try:
                    result = convert_lead(
                        lead=lead,
                        contact_data=ContactData(
                            first_name=lead.first_name,
                            last_name=lead.last_name,
                            email=lead.email,
                            phone=lead.phone,
                        ),
                        account_choice=AccountChoice(
                            create_name=lead.company_name or f"{lead.last_name} Corp"
                        ),
                        opportunity_data=OpportunityData(
                            create=True,
                            name=f"{lead.full_name} — Opportunity",
                        ),
                        user=actor,
                    )
                    converted_contacts.append(result.contact)
                    if result.account:
                        converted_accts.append(result.account)
                    lead.refresh_from_db()
                except ConversionError as exc:
                    self.stderr.write(f"  ConversionError on lead {lead}: {exc}")
            else:
                lead = LeadFactory(status=planned_status, owner=owner)
                if planned_status == Lead.STATUS_DISQUALIFIED:
                    lead.disqualified_reason = "Not a fit for our product at this time."
                    lead.save(update_fields=["disqualified_reason"])

            leads.append(lead)

        return leads, converted_contacts, converted_accts

    # ------------------------------------------------------------------
    # Opportunities (~12, all stages covered)
    # ------------------------------------------------------------------

    def _seed_opportunities(self, users, accounts, contacts, actor):
        opps = []

        for stage_path in OPP_STAGE_PATHS:
            owner = random.choice(users)
            is_lost_path = stage_path[-1] == Opportunity.STAGE_LOST

            opp = OpportunityFactory(
                owner=owner,
                account=random.choice(accounts + [None]),
                primary_contact=random.choice(contacts + [None]),
                expected_close_date=(timezone.now() + timedelta(days=random.randint(10, 90))).date(),
                amount_cents=random.randint(1_000_00, 200_000_00),
            )

            # Walk through the stages using the C10 transition service
            for stage in stage_path[1:]:
                try:
                    close_reason = "Budget constraints — revisit next quarter." if is_lost_path and stage == Opportunity.STAGE_LOST else ""
                    opp = transition_stage(opp, stage, actor, close_reason=close_reason)
                except TransitionError as exc:
                    self.stderr.write(f"  TransitionError on {opp}: {exc}")
                    break

            opps.append(opp)

        return opps

    # ------------------------------------------------------------------
    # Activities — sprinkled across all entity types
    # ------------------------------------------------------------------

    def _seed_activities(self, users, leads, contacts, accounts, opps):
        now = timezone.now()

        def _owner():
            return random.choice(users)

        # Notes on leads
        for lead in random.sample(leads, min(8, len(leads))):
            ActivityFactory(lead=lead, owner=_owner(), kind=Activity.KIND_NOTE)

        # Notes on contacts
        for contact in random.sample(contacts, min(10, len(contacts))):
            ActivityFactory(contact=contact, owner=_owner(), kind=Activity.KIND_NOTE)

        # Calls on accounts
        for account in random.sample(accounts, min(6, len(accounts))):
            ActivityFactory(account=account, owner=_owner(), kind=Activity.KIND_CALL)

        # Notes on opportunities (in addition to the stage-transition notes from C10)
        for opp in random.sample(opps, min(8, len(opps))):
            ActivityFactory(opportunity=opp, owner=_owner(), kind=Activity.KIND_NOTE)

        # Open tasks with future due_at (4 tasks)
        for _ in range(4):
            parent_type = random.choice(["lead", "contact", "account", "opportunity"])
            kwargs = {
                parent_type: random.choice(
                    {"lead": leads, "contact": contacts, "account": accounts, "opportunity": opps}[parent_type]
                ),
                "owner": _owner(),
                "kind": Activity.KIND_TASK,
                "due_at": now + timedelta(days=random.randint(3, 30)),
                "completed_at": None,
            }
            ActivityFactory(**kwargs)

        # Overdue tasks (2 tasks — due_at in the past, not completed)
        for _ in range(2):
            parent_type = random.choice(["lead", "contact", "account", "opportunity"])
            kwargs = {
                parent_type: random.choice(
                    {"lead": leads, "contact": contacts, "account": accounts, "opportunity": opps}[parent_type]
                ),
                "owner": _owner(),
                "kind": Activity.KIND_TASK,
                "due_at": now - timedelta(days=random.randint(1, 10)),
                "completed_at": None,
            }
            ActivityFactory(**kwargs)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def _write_creds(self, admins, reps):
        creds_path = Path(".seed-creds.txt")
        lines = [
            "# Demo seed credentials — DO NOT COMMIT",
            f"# Password for all seeded users: {SEED_PASSWORD}",
            "",
            "Admins:",
        ]
        for u in admins:
            lines.append(f"  {u.username}  /  {SEED_PASSWORD}")
        lines.append("Reps:")
        for u in reps:
            lines.append(f"  {u.username}  /  {SEED_PASSWORD}")
        creds_path.write_text("\n".join(lines) + "\n")

    def _print_summary(self, admins, reps, accounts, contacts, leads, opps):
        self.stdout.write(self.style.SUCCESS("\n=== Seed complete ==="))
        self.stdout.write(f"  Users    : {len(admins)} admins, {len(reps)} reps")
        self.stdout.write(f"  Accounts : {len(accounts)}")
        self.stdout.write(f"  Contacts : {len(contacts)}")

        lead_status_counts = {}
        for lead in leads:
            lead.refresh_from_db()
            lead_status_counts[lead.status] = lead_status_counts.get(lead.status, 0) + 1
        self.stdout.write(f"  Leads    : {len(leads)}  {dict(sorted(lead_status_counts.items()))}")

        opp_stage_counts = {}
        for opp in opps:
            opp.refresh_from_db()
            opp_stage_counts[opp.stage] = opp_stage_counts.get(opp.stage, 0) + 1
        self.stdout.write(f"  Opps     : {len(opps)}  {dict(sorted(opp_stage_counts.items()))}")

        activity_count = Activity.objects.count()
        self.stdout.write(f"  Activities: {activity_count}")

        self.stdout.write(
            self.style.WARNING(
                f"\nDefault password for all seeded users: {SEED_PASSWORD}"
            )
        )
        self.stdout.write("Credentials also written to .seed-creds.txt\n")
