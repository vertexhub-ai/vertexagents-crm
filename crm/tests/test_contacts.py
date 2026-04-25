"""
Tests for Contact CRUD (V-173 / C7).

Coverage:
  TestContactEmailUniqueCI       — 4 cases: DB-level partial unique index behavior
  TestContactSoftDeleteManager   — 3 cases: default manager hides deleted; all_objects exposes them
  TestContactListView            — 8 cases: mine/all filter, search, account filter, login redirect
  TestContactEditPermission      — 4 cases: owner OK, non-owner 403, admin OK, non-owner delete 403
  TestContactSoftDeleteView      — 2 cases: POST soft-deletes + redirects; GET renders confirm
  TestContactCreateView          — 2 cases: valid create succeeds; duplicate email CI rejected
"""

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError

from crm.forms import ContactForm
from crm.models import Account, CRMUser, Contact


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_user(username, role="member", **kwargs):
    return CRMUser.objects.create_user(username=username, password="pw", role=role, **kwargs)


def make_account(owner, name="ACME"):
    return Account.objects.create(name=name, owner=owner)


def make_contact(owner, first="Alice", last="Smith", email=None, account=None):
    return Contact.objects.create(
        first_name=first, last_name=last, email=email, owner=owner, account=account
    )


# ---------------------------------------------------------------------------
# 1. CI partial unique index
# ---------------------------------------------------------------------------

class TestContactEmailUniqueCI(TestCase):

    def setUp(self):
        self.user = make_user("u1")

    def test_duplicate_email_same_case_raises(self):
        make_contact(self.user, email="alice@example.com")
        with self.assertRaises((IntegrityError, Exception)):
            with transaction.atomic():
                Contact.objects.create(
                    first_name="Alice2", last_name="", email="alice@example.com", owner=self.user
                )

    def test_duplicate_email_different_case_raises_via_form(self):
        make_contact(self.user, email="alice@example.com")
        form = ContactForm(data={
            "first_name": "Bob", "last_name": "", "email": "ALICE@EXAMPLE.COM",
            "phone": "", "title": "", "account": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_two_contacts_empty_email_allowed(self):
        make_contact(self.user, first="C1", email=None)
        make_contact(self.user, first="C2", email=None)
        self.assertEqual(Contact.objects.filter(owner=self.user).count(), 2)

    def test_cross_user_duplicate_email_raises_via_form(self):
        other = make_user("u2")
        make_contact(other, email="shared@example.com")
        form = ContactForm(data={
            "first_name": "Bob", "last_name": "", "email": "shared@example.com",
            "phone": "", "title": "", "account": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


# ---------------------------------------------------------------------------
# 2. Soft-delete manager
# ---------------------------------------------------------------------------

class TestContactSoftDeleteManager(TestCase):

    def setUp(self):
        self.user = make_user("u1")
        self.contact = make_contact(self.user, email="del@example.com")

    def test_soft_deleted_hidden_from_default_manager(self):
        self.contact.soft_delete(self.user)
        self.assertFalse(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_soft_deleted_visible_via_all_objects(self):
        self.contact.soft_delete(self.user)
        self.assertTrue(Contact.all_objects.filter(pk=self.contact.pk).exists())

    def test_deleted_by_is_set(self):
        self.contact.soft_delete(self.user)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.deleted_by, self.user)
        self.assertIsNotNone(self.contact.deleted_at)


# ---------------------------------------------------------------------------
# 3. List view
# ---------------------------------------------------------------------------

class TestContactListView(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.other = make_user("other")
        self.acct = make_account(self.owner, name="GloboCorp")
        self.c1 = make_contact(self.owner, first="Alice", last="Smith", email="alice@ex.com", account=self.acct)
        self.c2 = make_contact(self.owner, first="Bob", last="Jones", email="bob@ex.com")
        self.c3 = make_contact(self.other, first="Carol", last="Lee", email="carol@ex.com")
        self.url = reverse("contacts:list")

    def _login(self, user):
        self.client.force_login(user)

    def test_mine_filter_shows_only_owned(self):
        self._login(self.owner)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        names = [c.full_name for c in resp.context["page_obj"]]
        self.assertIn("Alice Smith", names)
        self.assertIn("Bob Jones", names)
        self.assertNotIn("Carol Lee", names)

    def test_all_filter_shows_all_contacts(self):
        self._login(self.owner)
        resp = self.client.get(self.url + "?owner=all")
        names = [c.full_name for c in resp.context["page_obj"]]
        self.assertIn("Carol Lee", names)

    def test_soft_deleted_excluded(self):
        self.c1.soft_delete(self.owner)
        self._login(self.owner)
        resp = self.client.get(self.url + "?owner=all")
        pks = [c.pk for c in resp.context["page_obj"]]
        self.assertNotIn(self.c1.pk, pks)

    def test_search_by_first_name(self):
        self._login(self.owner)
        resp = self.client.get(self.url + "?q=Alice&owner=all")
        names = [c.full_name for c in resp.context["page_obj"]]
        self.assertIn("Alice Smith", names)
        self.assertNotIn("Bob Jones", names)

    def test_search_by_email(self):
        self._login(self.owner)
        resp = self.client.get(self.url + "?q=bob%40ex.com&owner=all")
        names = [c.full_name for c in resp.context["page_obj"]]
        self.assertIn("Bob Jones", names)

    def test_search_by_account_name(self):
        self._login(self.owner)
        resp = self.client.get(self.url + "?q=Globo&owner=all")
        names = [c.full_name for c in resp.context["page_obj"]]
        self.assertIn("Alice Smith", names)
        self.assertNotIn("Bob Jones", names)

    def test_account_filter(self):
        self._login(self.owner)
        resp = self.client.get(self.url + f"?account={self.acct.pk}&owner=all")
        names = [c.full_name for c in resp.context["page_obj"]]
        self.assertIn("Alice Smith", names)
        self.assertNotIn("Bob Jones", names)

    def test_login_required(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, f"/auth/login/?next={self.url}")


# ---------------------------------------------------------------------------
# 4. Edit permissions
# ---------------------------------------------------------------------------

class TestContactEditPermission(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.other = make_user("stranger")
        self.admin = make_user("admin_user", role="admin")
        self.contact = make_contact(self.owner, email="perm@ex.com")
        self.edit_url = reverse("contacts:edit", kwargs={"pk": self.contact.pk})

    def test_owner_can_get_edit(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self.edit_url)
        self.assertEqual(resp.status_code, 200)

    def test_non_owner_gets_403(self):
        self.client.force_login(self.other)
        resp = self.client.get(self.edit_url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_get_edit(self):
        self.client.force_login(self.admin)
        resp = self.client.get(self.edit_url)
        self.assertEqual(resp.status_code, 200)

    def test_non_owner_delete_gets_403(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("contacts:delete", kwargs={"pk": self.contact.pk}))
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# 5. Soft-delete view
# ---------------------------------------------------------------------------

class TestContactSoftDeleteView(TestCase):

    def setUp(self):
        self.owner = make_user("owner")
        self.contact = make_contact(self.owner)
        self.delete_url = reverse("contacts:delete", kwargs={"pk": self.contact.pk})

    def test_post_soft_deletes_and_redirects(self):
        self.client.force_login(self.owner)
        resp = self.client.post(self.delete_url)
        self.assertRedirects(resp, reverse("contacts:list"))
        self.contact.refresh_from_db()
        # contact is now soft-deleted — all_objects finds it but objects does not
        self.assertIsNotNone(Contact.all_objects.get(pk=self.contact.pk).deleted_at)
        self.assertFalse(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_get_renders_confirm_template(self):
        self.client.force_login(self.owner)
        resp = self.client.get(self.delete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Delete Contact")


# ---------------------------------------------------------------------------
# 6. Create view
# ---------------------------------------------------------------------------

class TestContactCreateView(TestCase):

    def setUp(self):
        self.user = make_user("creator")
        self.url = reverse("contacts:create")

    def test_valid_create_succeeds(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.url, {
            "first_name": "New", "last_name": "Person",
            "email": "new@example.com", "phone": "", "title": "", "account": "",
        })
        self.assertEqual(Contact.objects.filter(email__iexact="new@example.com").count(), 1)
        contact = Contact.objects.get(email__iexact="new@example.com")
        self.assertRedirects(resp, reverse("contacts:detail", kwargs={"pk": contact.pk}))

    def test_duplicate_email_ci_rejected(self):
        make_contact(self.user, email="taken@example.com")
        self.client.force_login(self.user)
        resp = self.client.post(self.url, {
            "first_name": "Dup", "last_name": "",
            "email": "TAKEN@EXAMPLE.COM", "phone": "", "title": "", "account": "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context["form"], "email", "A contact with this email already exists.")
