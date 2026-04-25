from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from crm_app.models import Account, Contact, Lead, Opportunity


class LeadDetailConvertButtonTest(TestCase):
    """Convert button visibility rules on the lead detail page."""

    def setUp(self):
        self.user = User.objects.create_user('detailtest', 'detail@example.com', 'pass')
        self.client = Client()
        self.client.login(username='detailtest', password='pass')

    def _make_lead(self, status):
        return Lead.objects.create(
            first_name='Test',
            last_name='Lead',
            status=status,
            owner=self.user,
        )

    def test_convert_button_visible_for_qualified(self):
        lead = self._make_lead('qualified')
        response = self.client.get(reverse('lead_detail', kwargs={'pk': lead.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Convert Lead')

    def test_convert_button_hidden_for_new(self):
        lead = self._make_lead('new')
        response = self.client.get(reverse('lead_detail', kwargs={'pk': lead.pk}))
        self.assertNotContains(response, 'Convert Lead')

    def test_convert_button_hidden_for_contacted(self):
        lead = self._make_lead('contacted')
        response = self.client.get(reverse('lead_detail', kwargs={'pk': lead.pk}))
        self.assertNotContains(response, 'Convert Lead')

    def test_convert_button_hidden_for_disqualified(self):
        lead = self._make_lead('disqualified')
        response = self.client.get(reverse('lead_detail', kwargs={'pk': lead.pk}))
        self.assertNotContains(response, 'Convert Lead')

    def test_convert_button_hidden_for_converted(self):
        lead = self._make_lead('converted')
        response = self.client.get(reverse('lead_detail', kwargs={'pk': lead.pk}))
        self.assertNotContains(response, 'Convert Lead')

    def test_readonly_banner_shown_for_converted_lead(self):
        lead = self._make_lead('converted')
        response = self.client.get(reverse('lead_detail', kwargs={'pk': lead.pk}))
        self.assertContains(response, 'read-only')

    def test_no_readonly_banner_for_qualified_lead(self):
        lead = self._make_lead('qualified')
        response = self.client.get(reverse('lead_detail', kwargs={'pk': lead.pk}))
        self.assertNotContains(response, 'read-only')


class LeadConvertViewTest(TestCase):
    """GET/POST tests for the lead conversion wizard."""

    def setUp(self):
        self.user = User.objects.create_user('cvtest', 'cv@example.com', 'pass')
        self.client = Client()
        self.client.login(username='cvtest', password='pass')
        self.lead = Lead.objects.create(
            first_name='Bob',
            last_name='Builder',
            email='bob@example.com',
            phone='555-9999',
            company_name='BuildCo',
            status='qualified',
            owner=self.user,
        )

    def test_get_shows_prefilled_form(self):
        response = self.client.get(reverse('lead_convert', kwargs={'pk': self.lead.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bob')
        self.assertContains(response, 'BuildCo')

    def test_redirect_if_lead_not_qualified(self):
        self.lead.status = 'new'
        self.lead.save()
        response = self.client.get(reverse('lead_convert', kwargs={'pk': self.lead.pk}))
        self.assertRedirects(response, reverse('lead_detail', kwargs={'pk': self.lead.pk}))

    def test_post_full_conversion_creates_all_records(self):
        response = self.client.post(
            reverse('lead_convert', kwargs={'pk': self.lead.pk}),
            {
                'contact-first_name': 'Bob',
                'contact-last_name': 'Builder',
                'contact-email': 'bob@example.com',
                'contact-phone': '555-9999',
                'contact-title': '',
                'account-account_mode': 'new',
                'account-new_account_name': 'BuildCo',
                'account-existing_account': '',
                'opp-create_opportunity': 'on',
                'opp-opportunity_name': 'BuildCo — Opportunity',
                'opp-amount': '',
                'opp-expected_close_date': '',
            },
        )
        self.assertRedirects(response, reverse('lead_detail', kwargs={'pk': self.lead.pk}))
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'converted')
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(Opportunity.objects.count(), 1)

    def test_post_skip_account_and_no_opportunity(self):
        response = self.client.post(
            reverse('lead_convert', kwargs={'pk': self.lead.pk}),
            {
                'contact-first_name': 'Bob',
                'contact-last_name': 'Builder',
                'contact-email': '',
                'contact-phone': '',
                'contact-title': '',
                'account-account_mode': 'skip',
                'account-new_account_name': '',
                'account-existing_account': '',
                'opp-create_opportunity': '',
                'opp-opportunity_name': '',
                'opp-amount': '',
                'opp-expected_close_date': '',
            },
        )
        self.assertRedirects(response, reverse('lead_detail', kwargs={'pk': self.lead.pk}))
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'converted')
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_post_existing_account(self):
        existing = Account.objects.create(name='Pre-existing Corp')
        response = self.client.post(
            reverse('lead_convert', kwargs={'pk': self.lead.pk}),
            {
                'contact-first_name': 'Bob',
                'contact-last_name': 'Builder',
                'contact-email': '',
                'contact-phone': '',
                'contact-title': '',
                'account-account_mode': 'existing',
                'account-new_account_name': '',
                'account-existing_account': str(existing.pk),
                'opp-create_opportunity': '',
                'opp-opportunity_name': '',
                'opp-amount': '',
                'opp-expected_close_date': '',
            },
        )
        self.assertRedirects(response, reverse('lead_detail', kwargs={'pk': self.lead.pk}))
        self.assertEqual(Account.objects.count(), 1)
        contact = Contact.objects.get()
        self.assertEqual(contact.account, existing)

    def test_post_missing_contact_name_shows_errors(self):
        response = self.client.post(
            reverse('lead_convert', kwargs={'pk': self.lead.pk}),
            {
                'contact-first_name': '',
                'contact-last_name': '',
                'contact-email': '',
                'contact-phone': '',
                'contact-title': '',
                'account-account_mode': 'skip',
                'account-new_account_name': '',
                'account-existing_account': '',
                'opp-create_opportunity': '',
                'opp-opportunity_name': '',
                'opp-amount': '',
                'opp-expected_close_date': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'qualified')
        self.assertEqual(Contact.objects.count(), 0)

    def test_unauthenticated_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse('lead_convert', kwargs={'pk': self.lead.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])
