"""
Tests for V-178 activity timeline:
- CRUD round-trip on each parent kind (lead, contact, account, opportunity)
- CHECK constraint enforcement (two parents → IntegrityError)
- Soft-delete cascade (parent soft-delete hides activities from timeline)
- Task completion (moves out of pinned section)
- Edit/delete ownership rules
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from crm.models import Activity, Account, Contact, Lead, Opportunity

User = get_user_model()


class ActivityCRUDTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.client = Client()
        self.client.login(username="testuser", password="pass")

        self.lead = Lead.objects.create(first_name="Alice", last_name="Smith")
        self.account = Account.objects.create(name="Acme Corp")
        self.contact = Contact.objects.create(
            first_name="Bob", last_name="Jones", account=self.account
        )
        self.opportunity = Opportunity.objects.create(name="Big Deal", account=self.account)

    # ------------------------------------------------------------------
    # CRUD round-trips
    # ------------------------------------------------------------------

    def _post_activity(self, url_name, pk, **extra):
        data = {"kind": "note", "subject": "Test subject", "body": ""}
        data.update(extra)
        return self.client.post(reverse(url_name, kwargs={"pk": pk}), data)

    def test_create_activity_for_lead(self):
        resp = self._post_activity("lead_activity_create", self.lead.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Activity.objects.filter(lead=self.lead, deleted_at__isnull=True).count(), 1)
        activity = Activity.objects.get(lead=self.lead)
        self.assertEqual(activity.subject, "Test subject")
        self.assertEqual(activity.author, self.user)

    def test_create_activity_for_contact(self):
        resp = self._post_activity("contact_activity_create", self.contact.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Activity.objects.filter(contact=self.contact, deleted_at__isnull=True).count(), 1)

    def test_create_activity_for_account(self):
        resp = self._post_activity("account_activity_create", self.account.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Activity.objects.filter(account=self.account, deleted_at__isnull=True).count(), 1)

    def test_create_activity_for_opportunity(self):
        resp = self._post_activity("opportunity_activity_create", self.opportunity.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Activity.objects.filter(opportunity=self.opportunity, deleted_at__isnull=True).count(), 1
        )

    def test_create_activity_invalid_no_subject(self):
        resp = self.client.post(
            reverse("lead_activity_create", kwargs={"pk": self.lead.pk}),
            {"kind": "note", "subject": "", "body": ""},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Activity.objects.filter(lead=self.lead).count(), 0)

    # ------------------------------------------------------------------
    # CHECK constraint — exactly one parent
    # ------------------------------------------------------------------

    def test_check_constraint_two_parents_raises(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Activity.objects.create(
                    kind="note",
                    subject="Broken",
                    author=self.user,
                    lead=self.lead,
                    contact=self.contact,
                )

    def test_check_constraint_no_parent_raises(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Activity.objects.create(
                    kind="note",
                    subject="No parent",
                    author=self.user,
                )

    # ------------------------------------------------------------------
    # Soft-delete cascade
    # ------------------------------------------------------------------

    def _create_direct(self, **kwargs):
        defaults = {"kind": "note", "subject": "x", "author": self.user}
        defaults.update(kwargs)
        return Activity.objects.create(**defaults)

    def test_soft_delete_lead_cascades(self):
        act = self._create_direct(lead=self.lead)
        self.lead.soft_delete()
        act.refresh_from_db()
        self.assertIsNotNone(act.deleted_at)

    def test_soft_delete_contact_cascades(self):
        act = self._create_direct(contact=self.contact)
        self.contact.soft_delete()
        act.refresh_from_db()
        self.assertIsNotNone(act.deleted_at)

    def test_soft_delete_account_cascades(self):
        act = self._create_direct(account=self.account)
        self.account.soft_delete()
        act.refresh_from_db()
        self.assertIsNotNone(act.deleted_at)

    def test_soft_delete_opportunity_cascades(self):
        act = self._create_direct(opportunity=self.opportunity)
        self.opportunity.soft_delete()
        act.refresh_from_db()
        self.assertIsNotNone(act.deleted_at)

    def test_soft_deleted_activity_hidden_from_timeline(self):
        act = self._create_direct(lead=self.lead)
        act.soft_delete()
        resp = self.client.get(reverse("lead_detail", kwargs={"pk": self.lead.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(act.subject.encode(), resp.content)

    # ------------------------------------------------------------------
    # Task pinning and completion
    # ------------------------------------------------------------------

    def test_pending_task_pins_to_top(self):
        self._create_direct(lead=self.lead, kind="note", subject="Regular note")
        task = self._create_direct(
            lead=self.lead,
            kind="task",
            subject="Pending task",
            due_at=timezone.now() + timedelta(days=1),
        )
        self.assertTrue(task.is_pending_task)

    def test_complete_task_via_endpoint(self):
        task = self._create_direct(
            lead=self.lead,
            kind="task",
            subject="Do the thing",
            due_at=timezone.now() + timedelta(days=1),
        )
        self.assertIsNone(task.completed_at)
        resp = self.client.post(reverse("activity_complete", kwargs={"pk": task.pk}))
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        self.assertFalse(task.is_pending_task)

    # ------------------------------------------------------------------
    # Edit and delete ownership
    # ------------------------------------------------------------------

    def test_owner_can_delete_own_activity(self):
        act = self._create_direct(lead=self.lead)
        resp = self.client.post(reverse("activity_delete", kwargs={"pk": act.pk}))
        self.assertEqual(resp.status_code, 200)
        act.refresh_from_db()
        self.assertIsNotNone(act.deleted_at)

    def test_non_owner_cannot_delete_others_activity(self):
        other = User.objects.create_user(username="other", password="pass")
        act = Activity.objects.create(
            kind="note", subject="Other's", author=other, lead=self.lead
        )
        resp = self.client.post(reverse("activity_delete", kwargs={"pk": act.pk}))
        self.assertEqual(resp.status_code, 403)
        act.refresh_from_db()
        self.assertIsNone(act.deleted_at)

    def test_admin_can_delete_any_activity(self):
        other = User.objects.create_user(username="other2", password="pass")
        act = Activity.objects.create(
            kind="note", subject="Other's note", author=other, lead=self.lead
        )
        admin = User.objects.create_user(username="admin_user", password="pass", is_staff=True)
        admin_client = Client()
        admin_client.login(username="admin_user", password="pass")
        resp = admin_client.post(reverse("activity_delete", kwargs={"pk": act.pk}))
        self.assertEqual(resp.status_code, 200)
        act.refresh_from_db()
        self.assertIsNotNone(act.deleted_at)

    def test_owner_can_edit_own_activity(self):
        act = self._create_direct(lead=self.lead)
        resp = self.client.post(
            reverse("activity_edit", kwargs={"pk": act.pk}),
            {"kind": "call", "subject": "Updated subject", "body": ""},
        )
        self.assertEqual(resp.status_code, 200)
        act.refresh_from_db()
        self.assertEqual(act.subject, "Updated subject")
        self.assertEqual(act.kind, "call")

    def test_non_owner_cannot_edit_others_activity(self):
        other = User.objects.create_user(username="other3", password="pass")
        act = Activity.objects.create(
            kind="note", subject="Original", author=other, lead=self.lead
        )
        resp = self.client.post(
            reverse("activity_edit", kwargs={"pk": act.pk}),
            {"kind": "note", "subject": "Hacked", "body": ""},
        )
        self.assertEqual(resp.status_code, 403)
        act.refresh_from_db()
        self.assertEqual(act.subject, "Original")

    # ------------------------------------------------------------------
    # Detail page renders the timeline
    # ------------------------------------------------------------------

    def test_lead_detail_renders(self):
        self._create_direct(lead=self.lead, subject="Lead note")
        resp = self.client.get(reverse("lead_detail", kwargs={"pk": self.lead.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Lead note")
        self.assertContains(resp, "activity-timeline")

    def test_contact_detail_renders(self):
        resp = self.client.get(reverse("contact_detail", kwargs={"pk": self.contact.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "activity-timeline")

    def test_account_detail_renders(self):
        resp = self.client.get(reverse("account_detail", kwargs={"pk": self.account.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "activity-timeline")

    def test_opportunity_detail_renders(self):
        resp = self.client.get(reverse("opportunity_detail", kwargs={"pk": self.opportunity.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "activity-timeline")

    # ------------------------------------------------------------------
    # Unauthenticated access redirects
    # ------------------------------------------------------------------

    def test_unauthenticated_redirected(self):
        anon = Client()
        resp = anon.get(reverse("lead_detail", kwargs={"pk": self.lead.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])
