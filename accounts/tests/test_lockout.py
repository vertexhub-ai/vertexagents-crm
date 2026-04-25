import pytest
from axes.models import AccessAttempt
from django.contrib.auth import get_user_model

User = get_user_model()

LOGIN_URL = "/login/"


@pytest.fixture(autouse=True)
def clear_axes(db):
    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="locktest", password="GoodPass123!", role="rep"
    )


@pytest.mark.django_db
def test_failed_attempts_are_recorded(client, user):
    for _ in range(3):
        client.post(LOGIN_URL, {"username": "locktest", "password": "wrongpass"})
    attempt = AccessAttempt.objects.filter(username="locktest").first()
    assert attempt is not None
    assert attempt.failures_since_start == 3


@pytest.mark.django_db
def test_lockout_after_5_failures(client, user):
    for _ in range(5):
        client.post(LOGIN_URL, {"username": "locktest", "password": "wrongpass"})
    # Correct password must not grant access while locked
    resp = client.post(
        LOGIN_URL, {"username": "locktest", "password": "GoodPass123!"}
    )
    assert not resp.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_admin_unlock_clears_lockout(client, user):
    for _ in range(5):
        client.post(LOGIN_URL, {"username": "locktest", "password": "wrongpass"})
    # Simulate admin deleting the AccessAttempt record via Django admin
    AccessAttempt.objects.filter(username="locktest").delete()
    resp = client.post(
        LOGIN_URL,
        {"username": "locktest", "password": "GoodPass123!"},
        follow=True,
    )
    assert resp.wsgi_request.user.is_authenticated
    assert resp.wsgi_request.user.username == "locktest"


@pytest.mark.django_db
def test_reset_on_success_clears_counter(client, user):
    for _ in range(3):
        client.post(LOGIN_URL, {"username": "locktest", "password": "wrongpass"})
    assert AccessAttempt.objects.filter(username="locktest").exists()
    client.post(
        LOGIN_URL,
        {"username": "locktest", "password": "GoodPass123!"},
        follow=True,
    )
    assert not AccessAttempt.objects.filter(username="locktest").exists()


@pytest.mark.django_db
def test_lockout_is_username_scoped(client, db):
    user_a = User.objects.create_user(username="user_a", password="passA123!", role="rep")
    user_b = User.objects.create_user(username="user_b", password="passB123!", role="rep")

    # Lock out user_a with 5 failures
    for _ in range(5):
        client.post(LOGIN_URL, {"username": "user_a", "password": "wrong"})

    # user_b must still be able to log in
    resp = client.post(
        LOGIN_URL,
        {"username": "user_b", "password": "passB123!"},
        follow=True,
    )
    assert resp.wsgi_request.user.is_authenticated
    assert resp.wsgi_request.user.username == "user_b"
