import pytest
from django.contrib.auth import get_user_model

from accounts.permissions import filter_for_user

User = get_user_model()


@pytest.mark.django_db
class TestRoleEnum:
    def test_role_constants(self):
        assert User.ROLE_ADMIN == "admin"
        assert User.ROLE_REP == "rep"

    def test_default_role_is_rep(self):
        user = User.objects.create_user(username="newuser", password="pass")
        assert user.role == User.ROLE_REP

    def test_is_admin_true_for_admin_role(self):
        user = User(username="a", role=User.ROLE_ADMIN)
        assert user.is_admin is True

    def test_is_admin_false_for_rep_role(self):
        user = User(username="r", role=User.ROLE_REP)
        assert user.is_admin is False

    def test_role_choices_contain_both_values(self):
        values = [choice[0] for choice in User.ROLE_CHOICES]
        assert "admin" in values
        assert "rep" in values


@pytest.mark.django_db
class TestFilterForUser:
    def test_admin_sees_all(self):
        admin = User.objects.create_user(username="adm", password="p", role=User.ROLE_ADMIN)
        User.objects.create_user(username="rep1", password="p", role=User.ROLE_REP)
        User.objects.create_user(username="rep2", password="p", role=User.ROLE_REP)
        result = filter_for_user(admin, User.objects.all(), owner_field="pk")
        assert result.count() == User.objects.count()

    def test_rep_filtered_to_own_record(self):
        rep = User.objects.create_user(username="rep1", password="p", role=User.ROLE_REP)
        User.objects.create_user(username="rep2", password="p", role=User.ROLE_REP)
        # filter(pk=rep) returns only the rep's own record
        result = filter_for_user(rep, User.objects.all(), owner_field="pk")
        assert result.count() == 1
        assert result.first().username == "rep1"
