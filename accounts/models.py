import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


SIZE_CHOICES = [
    ("1-10", "1–10"),
    ("11-50", "11–50"),
    ("51-200", "51–200"),
    ("201-1000", "201–1,000"),
    ("1000+", "1,000+"),
    ("unknown", "Unknown"),
]


class AccountManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AccountAllManager(models.Manager):
    """Unfiltered manager — used by Django admin and restore logic."""
    pass


class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    name_lower = models.CharField(max_length=200, editable=False, db_index=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=20, choices=SIZE_CHOICES, default="unknown")
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_accounts",
    )

    objects = AccountManager()
    all_objects = AccountAllManager()

    class Meta:
        ordering = ["name_lower"]
        # Unique active name (case-insensitive via name_lower), nulls-distinct not needed
        # since soft-deleted rows are excluded from uniqueness by the form validator.
        constraints = [
            models.UniqueConstraint(
                fields=["name_lower"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_account_name_ci",
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name_lower = self.name.lower()
        super().save(*args, **kwargs)

    def soft_delete(self, user):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by_id", "updated_at"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None
