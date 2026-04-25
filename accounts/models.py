"""
Custom User model.

Owned by V-168 (auth). Stubbed here as a minimum-viable AbstractUser + role enum so
V-169 (`accounts.User` foreign keys) can land cleanly. V-168 will extend this with
password reset, axes lockout, role helpers, etc. — those additions don't change the
schema columns this migration ships.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        REP = "rep", "Rep"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.REP)

    class Meta:
        db_table = "auth_user_custom"
