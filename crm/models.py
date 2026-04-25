import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
        self._cascade_soft_delete()

    def _cascade_soft_delete(self):
        pass

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class Lead(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("new", "New"),
            ("contacted", "Contacted"),
            ("qualified", "Qualified"),
            ("lost", "Lost"),
        ],
        default="new",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def _cascade_soft_delete(self):
        Activity.objects.filter(lead=self, deleted_at__isnull=True).update(
            deleted_at=self.deleted_at
        )


class Account(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def _cascade_soft_delete(self):
        Activity.objects.filter(account=self, deleted_at__isnull=True).update(
            deleted_at=self.deleted_at
        )


class Contact(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="contacts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def _cascade_soft_delete(self):
        Activity.objects.filter(contact=self, deleted_at__isnull=True).update(
            deleted_at=self.deleted_at
        )


class Opportunity(SoftDeleteMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    account = models.ForeignKey(
        Account, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities"
    )
    stage = models.CharField(
        max_length=30,
        choices=[
            ("prospect", "Prospect"),
            ("proposal", "Proposal"),
            ("negotiation", "Negotiation"),
            ("closed_won", "Closed Won"),
            ("closed_lost", "Closed Lost"),
        ],
        default="prospect",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    close_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def _cascade_soft_delete(self):
        Activity.objects.filter(opportunity=self, deleted_at__isnull=True).update(
            deleted_at=self.deleted_at
        )


KIND_CHOICES = [
    ("note", "Note"),
    ("call", "Call"),
    ("email", "Email"),
    ("meeting", "Meeting"),
    ("task", "Task"),
]

KIND_ICONS = {
    "note": "📝",
    "call": "📞",
    "email": "✉️",
    "meeting": "📅",
    "task": "✅",
}


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    subject = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    author = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="activities"
    )

    # Polymorphic parent — exactly one must be non-null (enforced by DB CHECK constraint)
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

    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        lead__isnull=False,
                        contact__isnull=True,
                        account__isnull=True,
                        opportunity__isnull=True,
                    )
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=False,
                        account__isnull=True,
                        opportunity__isnull=True,
                    )
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=True,
                        account__isnull=False,
                        opportunity__isnull=True,
                    )
                    | models.Q(
                        lead__isnull=True,
                        contact__isnull=True,
                        account__isnull=True,
                        opportunity__isnull=False,
                    )
                ),
                name="activity_exactly_one_parent",
            )
        ]

    def __str__(self):
        return f"[{self.kind}] {self.subject}"

    @property
    def is_pending_task(self):
        return (
            self.kind in ("task", "meeting")
            and self.due_at is not None
            and self.completed_at is None
        )

    @property
    def icon(self):
        return KIND_ICONS.get(self.kind, "•")

    @property
    def parent_type(self):
        if self.lead_id:
            return "lead"
        if self.contact_id:
            return "contact"
        if self.account_id:
            return "account"
        if self.opportunity_id:
            return "opportunity"
        return None

    @property
    def parent_obj(self):
        return self.lead or self.contact or self.account or self.opportunity

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
