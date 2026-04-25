import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Soft-delete infrastructure
# ---------------------------------------------------------------------------

class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Default manager: hides soft-deleted rows."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    """Exposes every row including soft-deleted ones."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self, user):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by"])
        self._cascade_soft_delete(user)

    def _cascade_soft_delete(self, user):
        """Override in subclasses to cascade to owned Activities."""

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_REP = "rep"
    ROLE_CHOICES = [(ROLE_ADMIN, "Admin"), (ROLE_REP, "Rep")]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_REP)

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN

    def __str__(self):
        return self.get_full_name() or self.username


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class Account(SoftDeleteMixin, TimestampMixin):
    SIZE_1_10 = "1-10"
    SIZE_11_50 = "11-50"
    SIZE_51_200 = "51-200"
    SIZE_201_1000 = "201-1000"
    SIZE_1000_PLUS = "1000+"
    SIZE_UNKNOWN = "unknown"
    SIZE_CHOICES = [
        (SIZE_1_10, "1–10"),
        (SIZE_11_50, "11–50"),
        (SIZE_51_200, "51–200"),
        (SIZE_201_1000, "201–1000"),
        (SIZE_1000_PLUS, "1000+"),
        (SIZE_UNKNOWN, "Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=80, blank=True)
    size = models.CharField(
        max_length=10, choices=SIZE_CHOICES, default=SIZE_UNKNOWN
    )
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_accounts"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def _cascade_soft_delete(self, user):
        Activity.objects.filter(account=self, deleted_at__isnull=True).update(
            deleted_at=timezone.now(), deleted_by=user
        )


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

class Contact(SoftDeleteMixin, TimestampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=120, blank=True)
    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contacts",
    )
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_contacts"
    )
    source_lead = models.ForeignKey(
        "Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_contacts",
    )

    class Meta:
        ordering = ["last_name", "first_name"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name

    def _cascade_soft_delete(self, user):
        Activity.objects.filter(contact=self, deleted_at__isnull=True).update(
            deleted_at=timezone.now(), deleted_by=user
        )


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------

class Lead(SoftDeleteMixin, TimestampMixin):
    STATUS_NEW = "new"
    STATUS_CONTACTED = "contacted"
    STATUS_QUALIFIED = "qualified"
    STATUS_DISQUALIFIED = "disqualified"
    STATUS_CONVERTED = "converted"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_CONTACTED, "Contacted"),
        (STATUS_QUALIFIED, "Qualified"),
        (STATUS_DISQUALIFIED, "Disqualified"),
        (STATUS_CONVERTED, "Converted"),
    ]

    SOURCE_WEB = "web"
    SOURCE_REFERRAL = "referral"
    SOURCE_EVENT = "event"
    SOURCE_COLD_OUTBOUND = "cold_outbound"
    SOURCE_OTHER = "other"
    SOURCE_CHOICES = [
        (SOURCE_WEB, "Web"),
        (SOURCE_REFERRAL, "Referral"),
        (SOURCE_EVENT, "Event"),
        (SOURCE_COLD_OUTBOUND, "Cold Outbound"),
        (SOURCE_OTHER, "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=120, blank=True)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_WEB
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default=STATUS_NEW
    )
    disqualified_reason = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_leads"
    )

    # Filled in during conversion (C9)
    converted_contact = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_leads",
    )
    converted_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_leads",
    )
    converted_opportunity = models.ForeignKey(
        "Opportunity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_leads",
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return self.full_name or self.email or str(self.id)

    def _cascade_soft_delete(self, user):
        Activity.objects.filter(lead=self, deleted_at__isnull=True).update(
            deleted_at=timezone.now(), deleted_by=user
        )


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------

class Opportunity(SoftDeleteMixin, TimestampMixin):
    STAGE_NEW = "new"
    STAGE_QUALIFIED = "qualified"
    STAGE_PROPOSAL = "proposal"
    STAGE_NEGOTIATION = "negotiation"
    STAGE_WON = "won"
    STAGE_LOST = "lost"
    STAGE_CHOICES = [
        (STAGE_NEW, "New"),
        (STAGE_QUALIFIED, "Qualified"),
        (STAGE_PROPOSAL, "Proposal"),
        (STAGE_NEGOTIATION, "Negotiation"),
        (STAGE_WON, "Won"),
        (STAGE_LOST, "Lost"),
    ]

    TERMINAL_STAGES = {STAGE_WON, STAGE_LOST}
    NON_TERMINAL_STAGES = {STAGE_NEW, STAGE_QUALIFIED, STAGE_PROPOSAL, STAGE_NEGOTIATION}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="opportunities",
    )
    primary_contact = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="opportunities",
    )
    amount_cents = models.BigIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    stage = models.CharField(
        max_length=15, choices=STAGE_CHOICES, default=STAGE_NEW
    )
    expected_close_date = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    close_reason = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_opportunities"
    )
    source_lead = models.ForeignKey(
        Lead,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sourced_opportunities",
    )

    class Meta:
        ordering = ["expected_close_date", "name"]
        verbose_name_plural = "opportunities"

    @property
    def amount_display(self):
        if self.amount_cents is None:
            return "—"
        dollars = self.amount_cents / 100
        return f"${dollars:,.2f}"

    def __str__(self):
        return self.name

    def _cascade_soft_delete(self, user):
        Activity.objects.filter(opportunity=self, deleted_at__isnull=True).update(
            deleted_at=timezone.now(), deleted_by=user
        )


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------

class Activity(SoftDeleteMixin, TimestampMixin):
    KIND_NOTE = "note"
    KIND_CALL = "call"
    KIND_EMAIL = "email"
    KIND_MEETING = "meeting"
    KIND_TASK = "task"
    KIND_CHOICES = [
        (KIND_NOTE, "Note"),
        (KIND_CALL, "Call"),
        (KIND_EMAIL, "Email"),
        (KIND_MEETING, "Meeting"),
        (KIND_TASK, "Task"),
    ]

    PINNABLE_KINDS = {KIND_TASK, KIND_MEETING}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_NOTE)
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    lead = models.ForeignKey(
        Lead, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    contact = models.ForeignKey(
        Contact, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    opportunity = models.ForeignKey(
        Opportunity, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )

    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="activities"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "activities"
        constraints = [
            models.CheckConstraint(
                name="activity_exactly_one_parent",
                check=(
                    # lead only
                    models.Q(
                        lead__isnull=False,
                        contact__isnull=True,
                        account__isnull=True,
                        opportunity__isnull=True,
                    )
                    # contact only
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=False,
                        account__isnull=True,
                        opportunity__isnull=True,
                    )
                    # account only
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=True,
                        account__isnull=False,
                        opportunity__isnull=True,
                    )
                    # opportunity only
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=True,
                        account__isnull=True,
                        opportunity__isnull=False,
                    )
                ),
            )
        ]

    @property
    def is_pinned(self):
        return (
            self.kind in self.PINNABLE_KINDS
            and self.due_at is not None
            and self.completed_at is None
        )

    def get_parent(self):
        for field in ("lead", "contact", "account", "opportunity"):
            val = getattr(self, field)
            if val is not None:
                return field, val
        return None, None

    def __str__(self):
        return f"{self.get_kind_display()}: {self.subject}"
