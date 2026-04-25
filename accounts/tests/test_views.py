import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="testuser",
        password="GoodPass123!",
        email="test@example.com",
        role="rep",
    )


@pytest.mark.django_db
def test_anonymous_request_redirects_to_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login/" in resp["Location"]


@pytest.mark.django_db
def test_login_page_accessible_without_auth(client):
    resp = client.get("/login/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_authenticated_user_reaches_dashboard(client, regular_user):
    client.force_login(regular_user)
    resp = client.get("/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_password_reset_token_flow(client, regular_user):
    uid = urlsafe_base64_encode(force_bytes(regular_user.pk))
    token = default_token_generator.make_token(regular_user)

    # First GET: valid token → redirect to set-password step (token consumed into session)
    resp = client.get(f"/password_reset/confirm/{uid}/{token}/")
    assert resp.status_code == 302
    set_url = resp["Location"]

    # POST new password to the redirected URL
    resp = client.post(
        set_url,
        {"new_password1": "NewStrongPass123!", "new_password2": "NewStrongPass123!"},
    )
    assert resp.status_code == 302  # redirects to complete page

    regular_user.refresh_from_db()
    assert regular_user.check_password("NewStrongPass123!")


@pytest.mark.django_db
def test_invalid_reset_token_shows_invalid_link(client, regular_user):
    uid = urlsafe_base64_encode(force_bytes(regular_user.pk))
    resp = client.get(f"/password_reset/confirm/{uid}/invalid-token-xyz/")
    assert resp.status_code == 200
    assert resp.context["validlink"] is False
