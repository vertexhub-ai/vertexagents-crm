"""Repo-root conftest — sets DJANGO_SETTINGS_MODULE before pytest-django boots."""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
