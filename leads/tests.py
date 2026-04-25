from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import DisqualifyForm, LeadForm
from .models import Lead, Status

User = get_user_model()


def make_user(username, role=None, is_staff=False):
    user = User.objects.create_user(username=username, password="pass")
    user.is_staff = is_staff
    if role is not None and hasattr(user, "role"):
        user.role = role
    user.save()
    return user


class LeadManagerTest(TestCase):
    def setUp(self):
        self.user = make_user("mgr_rep")

    def test_default_manager_excludes_soft_deleted(self):
        lead = Lead.objects.create(last_name="Gone", owner=self.user)
        lead.soft_delete(self.user)
        self.assertFalse(Lead.objects.filter(pk=lead.pk).exists())

    def test_default_manager_includes_active(self):
        Lead.objects.create(last_name="Here", owner=self.user)
        self.assertEqual(Lead.objects.count(), 1)

    def test_all_objects_includes_soft_deleted(self):
        lead = Lead.objects.create(last_name="Ghost", owner=self.user)
        lead.soft_delete(self.user)
        self.assertTrue(Lead.all_objects.filter(pk=lead.pk).exists())

    def test_restore_clears_deleted_at(self):
        lead = Lead.objects.create(last_name="Back", owner=self.user)
        lead.soft_delete(self.user)
        lead.restore()
        self.assertIsNone(lead.deleted_at)
        self.assertTrue(Lead.objects.filter(pk=lead.pk).exists())


class LeadFormChoicesTest(TestCase):
    def setUp(self):
        self.user = make_user("form_rep")

    def test_status_excludes_disqualified(self):
        form = LeadForm()
        choice_values = [v for v, _ in form.fields["status"].choices]
        self.assertNotIn(Status.DISQUALIFIED, choice_values)

    def test_status_excludes_converted(self):
        form = LeadForm()
        choice_values = [v for v, _ in form.fields["status"].choices]
        self.assertNotIn(Status.CONVERTED, choice_values)

    def test_status_includes_new_contacted_qualified(self):
        form = LeadForm()
        choice_values = [v for v, _ in form.fields["status"].choices]
        self.assertIn(Status.NEW, choice_values)
        self.assertIn(Status.CONTACTED, choice_values)
        self.assertIn(Status.QUALIFIED, choice_values)

    def test_last_name_required(self):
        data = {
            "first_name": "John",
            "last_name": "",
            "status": Status.NEW,
            "owner": self.user.pk,
        }
        form = LeadForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)

    def test_valid_form_saves(self):
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "status": Status.NEW,
            "owner": self.user.pk,
        }
        form = LeadForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)


class DisqualifyFormTest(TestCase):
    def test_empty_reason_invalid(self):
        form = DisqualifyForm(data={"disqualified_reason": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("disqualified_reason", form.errors)

    def test_whitespace_reason_invalid(self):
        form = DisqualifyForm(data={"disqualified_reason": "   "})
        self.assertFalse(form.is_valid())
        self.assertIn("disqualified_reason", form.errors)

    def test_valid_reason_accepted(self):
        form = DisqualifyForm(data={"disqualified_reason": "Not a good fit"})
        self.assertTrue(form.is_valid())

    def test_reason_max_length(self):
        form = DisqualifyForm(data={"disqualified_reason": "x" * 201})
        self.assertFalse(form.is_valid())
        self.assertIn("disqualified_reason", form.errors)


class ConvertedLeadReadOnlyTest(TestCase):
    def setUp(self):
        self.user = make_user("conv_rep")
        self.client.login(username="conv_rep", password="pass")
        self.lead = Lead.objects.create(
            last_name="Smith",
            status=Status.CONVERTED,
            owner=self.user,
        )

    def test_get_edit_shows_banner(self):
        resp = self.client.get(reverse("leads:edit", args=[self.lead.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["converted_banner"])
        self.assertIsNone(resp.context["form"])

    def test_post_edit_does_not_change_lead(self):
        resp = self.client.post(reverse("leads:edit", args=[self.lead.pk]), {
            "first_name": "Hacked",
            "last_name": "Override",
            "status": Status.NEW,
            "owner": self.user.pk,
        })
        self.assertEqual(resp.status_code, 200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Status.CONVERTED)
        self.assertNotEqual(self.lead.last_name, "Override")

    def test_admin_can_edit_converted(self):
        admin = make_user("conv_admin", is_staff=True)
        self.client.login(username="conv_admin", password="pass")
        resp = self.client.get(reverse("leads:edit", args=[self.lead.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context.get("converted_banner", False))
        self.assertIsNotNone(resp.context["form"])


class LeadListFilterTest(TestCase):
    def setUp(self):
        self.me = make_user("list_me")
        self.other = make_user("list_other")
        self.client.login(username="list_me", password="pass")
        Lead.objects.create(last_name="A", status=Status.NEW, owner=self.me)
        Lead.objects.create(last_name="B", status=Status.QUALIFIED, owner=self.me)
        Lead.objects.create(last_name="C", status=Status.DISQUALIFIED, owner=self.other)
        Lead.objects.create(last_name="D", status=Status.CONVERTED, owner=self.other)

    def test_default_owner_is_mine(self):
        resp = self.client.get(reverse("leads:list"))
        self.assertEqual(len(resp.context["page_obj"].object_list), 2)

    def test_owner_all_returns_all(self):
        resp = self.client.get(reverse("leads:list") + "?owner=all")
        self.assertEqual(len(resp.context["page_obj"].object_list), 4)

    def test_status_filter_new(self):
        resp = self.client.get(reverse("leads:list") + "?owner=all&status=new")
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_status_filter_converted(self):
        resp = self.client.get(reverse("leads:list") + "?owner=all&status=converted")
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_status_filter_disqualified(self):
        resp = self.client.get(reverse("leads:list") + "?owner=all&status=disqualified")
        self.assertEqual(len(resp.context["page_obj"].object_list), 1)

    def test_search_by_last_name(self):
        resp = self.client.get(reverse("leads:list") + "?owner=all&q=Smith")
        self.assertEqual(len(resp.context["page_obj"].object_list), 0)

    def test_search_matches_last_name(self):
        resp = self.client.get(reverse("leads:list") + "?owner=all&q=A")
        names = [l.last_name for l in resp.context["page_obj"].object_list]
        self.assertIn("A", names)


class LeadDeleteTest(TestCase):
    def setUp(self):
        self.user = make_user("del_rep")
        self.client.login(username="del_rep", password="pass")
        self.lead = Lead.objects.create(last_name="Del", owner=self.user)

    def test_get_not_allowed(self):
        resp = self.client.get(reverse("leads:delete", args=[self.lead.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_post_soft_deletes(self):
        resp = self.client.post(reverse("leads:delete", args=[self.lead.pk]))
        self.assertRedirects(resp, reverse("leads:list"), fetch_redirect_response=False)
        self.assertFalse(Lead.objects.filter(pk=self.lead.pk).exists())
        self.assertTrue(Lead.all_objects.filter(pk=self.lead.pk).exists())

    def test_soft_deleted_lead_has_deleted_by(self):
        self.client.post(reverse("leads:delete", args=[self.lead.pk]))
        self.lead.refresh_from_db()
        self.assertEqual(Lead.all_objects.get(pk=self.lead.pk).deleted_by, self.user)
