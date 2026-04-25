from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_REP = "rep"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_REP, "Rep"),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_REP)

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
