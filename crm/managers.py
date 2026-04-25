"""
Soft-delete manager + queryset.

`objects` excludes soft-deleted rows by default; `all_objects` includes them.
Q8 (CEO override) — soft delete is in.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=False)

    def soft_delete(self, user=None) -> int:
        """Bulk soft-delete. Returns number of rows touched."""
        return self.alive().update(deleted_at=timezone.now(), deleted_by=user)

    def restore(self) -> int:
        return self.dead().update(deleted_at=None, deleted_by=None)


class AliveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: hides soft-deleted rows."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return super().get_queryset().alive()


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Sees everything, including soft-deleted rows."""
