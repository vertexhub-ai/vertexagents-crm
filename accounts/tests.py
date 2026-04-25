from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Account

User = get_user_model()


class AccountModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pw")

    def _make(self, name="Acme", owner=None):
        return Account.objects.create(name=name, owner=owner or self.user)

    # --- uniqueness case-insensitive ---

    def test_name_lower_populated_on_save(self):
        acc = self._make(name="Acme Corp")
        self.assertEqual(acc.name_lower, "acme corp")

    def test_duplicate_name_different_case_blocked_by_form(self):
        """The clean_name validator rejects a case-insensitive duplicate."""
        from .forms import AccountForm
        self._make(name="Acme")
        form = AccountForm(data={"name": "ACME", "owner": self.user.pk, "size": "unknown"})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_duplicate_name_same_case_blocked_by_form(self):
        self._make(name="Acme")
        from .forms import AccountForm
        form = AccountForm(data={"name": "Acme", "owner": self.user.pk, "size": "unknown"})
        self.assertFalse(form.is_valid())

    # --- soft-delete ---

    def test_soft_delete_sets_deleted_at_and_by(self):
        acc = self._make()
        acc.soft_delete(self.user)
        acc.refresh_from_db()
        self.assertIsNotNone(acc.deleted_at)
        self.assertEqual(acc.deleted_by, self.user)
        self.assertTrue(acc.is_deleted)

    def test_soft_deleted_hidden_from_default_manager(self):
        acc = self._make(name="Gone")
        acc.soft_delete(self.user)
        self.assertFalse(Account.objects.filter(pk=acc.pk).exists())

    def test_soft_deleted_visible_via_all_objects(self):
        acc = self._make(name="Gone2")
        acc.soft_delete(self.user)
        self.assertTrue(Account.all_objects.filter(pk=acc.pk).exists())

    def test_deleted_name_allows_new_same_name(self):
        """After soft-delete the unique-ci slot is freed for a new account."""
        from .forms import AccountForm
        acc = self._make(name="Recycled")
        acc.soft_delete(self.user)
        form = AccountForm(data={"name": "Recycled", "owner": self.user.pk, "size": "unknown"})
        self.assertTrue(form.is_valid(), form.errors)


class AccountListViewTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="pw")
        self.bob = User.objects.create_user(username="bob", password="pw")
        self.admin = User.objects.create_user(username="admin", password="pw", is_staff=True)
        self.alice_acc = Account.objects.create(name="Alice Corp", owner=self.alice)
        self.bob_acc = Account.objects.create(name="Bob Ltd", owner=self.bob)
        self.client = Client()

    def _login(self, user):
        self.client.login(username=user.username, password="pw")

    # --- list filters by owner ---

    def test_list_default_shows_only_mine(self):
        self._login(self.alice)
        resp = self.client.get(reverse("accounts:list"))
        names = [a.name for a in resp.context["page_obj"]]
        self.assertIn("Alice Corp", names)
        self.assertNotIn("Bob Ltd", names)

    def test_list_all_shows_all_owners(self):
        self._login(self.alice)
        resp = self.client.get(reverse("accounts:list") + "?owner=all")
        names = [a.name for a in resp.context["page_obj"]]
        self.assertIn("Alice Corp", names)
        self.assertIn("Bob Ltd", names)

    def test_list_search_filters_by_name(self):
        self._login(self.alice)
        resp = self.client.get(reverse("accounts:list") + "?owner=all&q=Alice")
        names = [a.name for a in resp.context["page_obj"]]
        self.assertIn("Alice Corp", names)
        self.assertNotIn("Bob Ltd", names)

    def test_list_excludes_soft_deleted(self):
        self._login(self.alice)
        self.alice_acc.soft_delete(self.alice)
        resp = self.client.get(reverse("accounts:list") + "?owner=all")
        names = [a.name for a in resp.context["page_obj"]]
        self.assertNotIn("Alice Corp", names)

    def test_list_requires_login(self):
        resp = self.client.get(reverse("accounts:list"))
        self.assertRedirects(resp, "/login/?next=/accounts/")

    # --- permission: non-owner cannot edit ---

    def test_non_owner_cannot_edit(self):
        self._login(self.bob)
        resp = self.client.post(
            reverse("accounts:edit", kwargs={"pk": self.alice_acc.pk}),
            {"name": "Hacked", "owner": self.bob.pk, "size": "unknown"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_owner_can_edit(self):
        self._login(self.alice)
        resp = self.client.post(
            reverse("accounts:edit", kwargs={"pk": self.alice_acc.pk}),
            {"name": "Alice Corp Updated", "owner": self.alice.pk, "size": "unknown"},
        )
        # Successful edit redirects to detail
        self.assertEqual(resp.status_code, 302)
        self.alice_acc.refresh_from_db()
        self.assertEqual(self.alice_acc.name, "Alice Corp Updated")

    def test_admin_can_edit_any(self):
        self._login(self.admin)
        resp = self.client.post(
            reverse("accounts:edit", kwargs={"pk": self.alice_acc.pk}),
            {"name": "Alice Corp (admin edit)", "owner": self.alice.pk, "size": "unknown"},
        )
        self.assertEqual(resp.status_code, 302)

    def test_non_owner_cannot_delete(self):
        self._login(self.bob)
        resp = self.client.post(reverse("accounts:delete", kwargs={"pk": self.alice_acc.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_owner_can_soft_delete(self):
        self._login(self.alice)
        resp = self.client.post(reverse("accounts:delete", kwargs={"pk": self.alice_acc.pk}))
        self.assertEqual(resp.status_code, 302)
        self.alice_acc.refresh_from_db()
        self.assertTrue(self.alice_acc.is_deleted)
