from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from .models import Account, Contact, Lead, Opportunity


@dataclass
class ConversionResult:
    contact: Contact
    account: Optional[Account]
    opportunity: Optional[Opportunity]


def convert_lead(lead, contact_data, account_choice, opportunity_data, user) -> ConversionResult:
    """
    Convert a qualified lead into Contact + optional Account + optional Opportunity.
    All writes are wrapped in a single atomic transaction; any failure rolls back everything.

    account_choice dict keys:
        mode: 'existing' | 'new' | 'skip'
        account_id: UUID  (only for mode='existing')
        account_name: str (only for mode='new')

    opportunity_data dict keys (or None to skip):
        create: bool
        name: str
        amount: Decimal | None
        expected_close_date: date | None
    """
    if lead.status != 'qualified':
        raise ValueError(
            f'Lead must be qualified to convert; current status: {lead.status}'
        )

    with transaction.atomic():
        contact = Contact.objects.create(
            first_name=contact_data['first_name'],
            last_name=contact_data['last_name'],
            email=contact_data.get('email', ''),
            phone=contact_data.get('phone', ''),
            title=contact_data.get('title', ''),
            owner=user,
            source_lead=lead,
        )

        account = None
        mode = account_choice.get('mode', 'skip')
        if mode == 'existing':
            account = Account.objects.get(id=account_choice['account_id'])
        elif mode == 'new':
            account = Account.objects.create(name=account_choice['account_name'])

        if account:
            contact.account = account
            contact.save(update_fields=['account'])

        opportunity = None
        if opportunity_data and opportunity_data.get('create'):
            opportunity = Opportunity.objects.create(
                name=opportunity_data['name'],
                stage='new',
                account=account,
                contact=contact,
                owner=user,
                amount=opportunity_data.get('amount'),
                expected_close_date=opportunity_data.get('expected_close_date'),
                source_lead=lead,
            )

        lead.status = 'converted'
        lead.converted_contact = contact
        lead.converted_account = account
        lead.converted_opportunity = opportunity
        lead.converted_at = timezone.now()
        lead.save(update_fields=[
            'status', 'converted_contact', 'converted_account',
            'converted_opportunity', 'converted_at',
        ])

    return ConversionResult(contact=contact, account=account, opportunity=opportunity)
