from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from crm_app.models import Account, Contact, Lead, Opportunity
from crm_app.services import convert_lead


class ConvertLeadServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('svctest', 'svc@example.com', 'password')
        self.lead = Lead.objects.create(
            first_name='Alice',
            last_name='Wonder',
            email='alice@example.com',
            phone='555-0001',
            title='CTO',
            company_name='Wonderland Inc',
            status='qualified',
            owner=self.user,
        )

    def _contact_data(self):
        return {
            'first_name': self.lead.first_name,
            'last_name': self.lead.last_name,
            'email': self.lead.email,
            'phone': self.lead.phone,
            'title': self.lead.title,
        }

    def test_happy_path_creates_contact_account_opportunity(self):
        """Happy path: all three records created and lead flipped to converted."""
        result = convert_lead(
            lead=self.lead,
            contact_data=self._contact_data(),
            account_choice={'mode': 'new', 'account_name': 'Wonderland Inc'},
            opportunity_data={
                'create': True,
                'name': 'Wonderland Inc — Opportunity',
                'amount': None,
                'expected_close_date': None,
            },
            user=self.user,
        )
        self.lead.refresh_from_db()

        # Lead state
        self.assertEqual(self.lead.status, 'converted')
        self.assertIsNotNone(self.lead.converted_at)
        self.assertEqual(self.lead.converted_contact_id, result.contact.pk)
        self.assertEqual(self.lead.converted_account_id, result.account.pk)
        self.assertEqual(self.lead.converted_opportunity_id, result.opportunity.pk)

        # Audit FKs on created records point back to lead
        self.assertEqual(result.contact.source_lead_id, self.lead.pk)
        self.assertEqual(result.opportunity.source_lead_id, self.lead.pk)

        # DB counts
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(Opportunity.objects.count(), 1)

    def test_atomic_rollback_on_opportunity_integrity_error(self):
        """
        If Opportunity.objects.create raises IntegrityError mid-transaction,
        Contact and Account are also rolled back and lead stays qualified.
        """
        with patch('crm_app.services.Opportunity.objects.create') as mock_create:
            mock_create.side_effect = IntegrityError('forced failure')
            with self.assertRaises(IntegrityError):
                convert_lead(
                    lead=self.lead,
                    contact_data=self._contact_data(),
                    account_choice={'mode': 'new', 'account_name': 'Wonderland Inc'},
                    opportunity_data={
                        'create': True,
                        'name': 'Wonderland Inc — Opportunity',
                    },
                    user=self.user,
                )

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'qualified')
        self.assertIsNone(self.lead.converted_at)
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_skip_account_and_no_opportunity(self):
        """Convert with no account and no opportunity."""
        result = convert_lead(
            lead=self.lead,
            contact_data=self._contact_data(),
            account_choice={'mode': 'skip'},
            opportunity_data=None,
            user=self.user,
        )
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'converted')
        self.assertIsNone(result.account)
        self.assertIsNone(result.opportunity)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_link_existing_account(self):
        """Can link to an already-existing account; no new account is created."""
        existing = Account.objects.create(name='Pre-existing Corp')
        result = convert_lead(
            lead=self.lead,
            contact_data=self._contact_data(),
            account_choice={'mode': 'existing', 'account_id': existing.id},
            opportunity_data=None,
            user=self.user,
        )
        self.assertEqual(result.account, existing)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(result.contact.account, existing)

    def test_raises_value_error_if_lead_not_qualified(self):
        for bad_status in ('new', 'contacted', 'disqualified', 'converted'):
            with self.subTest(status=bad_status):
                self.lead.status = bad_status
                self.lead.save()
                with self.assertRaises(ValueError):
                    convert_lead(
                        lead=self.lead,
                        contact_data=self._contact_data(),
                        account_choice={'mode': 'skip'},
                        opportunity_data=None,
                        user=self.user,
                    )
