"""C9 — Lead → Contact / Account / Opportunity conversion service."""

from dataclasses import dataclass, field
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models import Account, Contact, Lead, Opportunity, User


class ConversionError(Exception):
    pass


@dataclass
class ContactData:
    first_name: str
    last_name: str
    email: str = ""
    phone: str = ""
    title: str = ""


@dataclass
class AccountChoice:
    """
    Describes what to do with the Account during conversion.

    - existing_id: link to this Account pk (UUID)
    - create_name: create a new Account with this name
    - skip: attach no Account
    """
    existing_id: Optional[str] = None
    create_name: Optional[str] = None
    skip: bool = False

    def __post_init__(self):
        options = [
            bool(self.existing_id),
            bool(self.create_name),
            self.skip,
        ]
        if sum(options) != 1:
            raise ValueError("Exactly one of existing_id, create_name, skip must be set.")


@dataclass
class OpportunityData:
    create: bool = False
    name: str = ""
    stage: str = Opportunity.STAGE_NEW
    amount_cents: Optional[int] = None
    expected_close_date: Optional[str] = None


@dataclass
class ConversionResult:
    contact: Contact
    account: Optional[Account] = None
    opportunity: Optional[Opportunity] = None


@transaction.atomic
def convert_lead(
    lead: Lead,
    contact_data: ContactData,
    account_choice: AccountChoice,
    opportunity_data: OpportunityData,
    user: User,
) -> ConversionResult:
    """
    Convert a qualified Lead into Contact (+ optionally Account + Opportunity).

    Raises ConversionError on any validation failure; the transaction is
    automatically rolled back, leaving lead.status unchanged.
    """
    if lead.status != Lead.STATUS_QUALIFIED:
        raise ConversionError(
            f"Lead must be in 'qualified' status to convert; current status: {lead.status!r}"
        )

    # -- Contact ---------------------------------------------------------------
    contact = Contact.objects.create(
        first_name=contact_data.first_name,
        last_name=contact_data.last_name,
        email=contact_data.email,
        phone=contact_data.phone,
        title=contact_data.title,
        owner=lead.owner,
        source_lead=lead,
    )

    # -- Account ---------------------------------------------------------------
    account: Optional[Account] = None
    if account_choice.existing_id:
        try:
            account = Account.objects.get(pk=account_choice.existing_id)
        except Account.DoesNotExist:
            raise ConversionError(
                f"Account {account_choice.existing_id!r} does not exist."
            )
        contact.account = account
        contact.save(update_fields=["account"])
    elif account_choice.create_name:
        account = Account.objects.create(
            name=account_choice.create_name,
            owner=lead.owner,
        )
        contact.account = account
        contact.save(update_fields=["account"])

    # -- Opportunity -----------------------------------------------------------
    opportunity: Optional[Opportunity] = None
    if opportunity_data.create:
        opp_name = opportunity_data.name or (
            f"{account.name if account else contact.full_name} — Opportunity"
        )
        opportunity = Opportunity.objects.create(
            name=opp_name,
            account=account,
            primary_contact=contact,
            stage=opportunity_data.stage or Opportunity.STAGE_NEW,
            amount_cents=opportunity_data.amount_cents,
            expected_close_date=opportunity_data.expected_close_date,
            owner=lead.owner,
            source_lead=lead,
        )

    # -- Flip lead status ------------------------------------------------------
    lead.status = Lead.STATUS_CONVERTED
    lead.converted_contact = contact
    lead.converted_account = account
    lead.converted_opportunity = opportunity
    lead.converted_at = timezone.now()
    lead.save(
        update_fields=[
            "status",
            "converted_contact",
            "converted_account",
            "converted_opportunity",
            "converted_at",
        ]
    )

    return ConversionResult(contact=contact, account=account, opportunity=opportunity)
