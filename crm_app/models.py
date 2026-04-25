import uuid
from django.db import models
from django.contrib.auth.models import User


LEAD_STATUS_CHOICES = [
    ('new', 'New'),
    ('contacted', 'Contacted'),
    ('qualified', 'Qualified'),
    ('disqualified', 'Disqualified'),
    ('converted', 'Converted'),
]

OPPORTUNITY_STAGE_CHOICES = [
    ('new', 'New'),
    ('discovery', 'Discovery'),
    ('proposal', 'Proposal'),
    ('negotiation', 'Negotiation'),
    ('closed_won', 'Closed Won'),
    ('closed_lost', 'Closed Lost'),
]


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=100, blank=True)
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='contacts'
    )
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='contacts'
    )
    # Audit FK back to the originating lead
    source_lead = models.OneToOneField(
        'Lead', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='converted_contact_record',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Opportunity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    stage = models.CharField(max_length=50, choices=OPPORTUNITY_STAGE_CHOICES, default='new')
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name='opportunities'
    )
    contact = models.ForeignKey(
        Contact, null=True, blank=True, on_delete=models.SET_NULL, related_name='opportunities'
    )
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='opportunities'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_close_date = models.DateField(null=True, blank=True)
    # Audit FK back to the originating lead
    source_lead = models.ForeignKey(
        'Lead', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='source_opportunities',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Lead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='new')
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='leads'
    )

    # Populated on conversion — FK references added after Contact/Opportunity tables exist
    converted_contact = models.OneToOneField(
        Contact, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='lead_conversion',
    )
    converted_account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='converted_from_leads',
    )
    converted_opportunity = models.OneToOneField(
        Opportunity, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='lead_conversion',
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_converted(self):
        return self.status == 'converted'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
