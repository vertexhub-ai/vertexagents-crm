import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Status(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUALIFIED = "qualified", "Qualified"
    DISQUALIFIED = "disqualified", "Disqualified"
    CONVERTED = "converted", "Converted"


class Source(models.TextChoices):
    WEB = "web", "Web"
    REFERRAL = "referral", "Referral"
    EVENT = "event", "Event"
    COLD_OUTBOUND = "cold_outbound", "Cold Outbound"
    OTHER = "other", "Other"


class LeadManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllLeadManager(models.Manager):
    pass


class Lead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    disqualified_reason = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_leads",
    )
    # Populated only after C9 conversion flow
    converted_contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    converted_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    converted_opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    converted_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_leads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LeadManager()
    all_objects = AllLeadManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or str(self.id)

    @property
    def is_converted(self):
        return self.status == Status.CONVERTED

    def soft_delete(self, user):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by_id"])

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by_id"])
