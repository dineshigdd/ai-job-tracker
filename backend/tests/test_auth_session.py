"""Tests for the real cookie-session flow: POST /auth/login -> GET /users/me.

The shared `client` fixture overrides `get_current_user`, so every other test
authenticates by fiat and none of them touch the credential the browser actually
sends. That gap is why a `SameSite`/cookie misconfiguration could reach
production undetected. The client here overrides only the database, leaving the
auth dependency live.
"""
import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.database import get_db
from app.main import app
from app.models import User
from app.utils import hash_password

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="function")
def credentialed_user(db_session):
    """A user whose stored hash matches a password we know."""
    user = User(
        id=uuid4(),
        first_name="Ada",
        last_name="Lovelace",
        email=f"session_{uuid4().hex[:8]}@example.com",
        hashed_password=hash_password(PASSWORD),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_client(db_session):
    """A client with a real `get_current_user`, so the cookie is what counts."""

    def get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client, email, password=PASSWORD):
    return client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )


class TestLoginResponse:
    def test_login_sets_auth_cookie(self, auth_client, credentialed_user):
        response = login(auth_client, credentialed_user.email)
        assert response.status_code == 200
        assert auth_module.COOKIE_NAME in response.cookies

    def test_login_returns_profile_not_token(self, auth_client, credentialed_user):
        """The JWT must never appear in the body — that is the whole point of
        the HttpOnly cookie. The body carries the profile instead."""
        response = login(auth_client, credentialed_user.email)
        body = response.json()
        assert body["email"] == credentialed_user.email
        assert "access_token" not in body

    def test_auth_cookie_is_httponly(self, auth_client, credentialed_user):
        response = login(auth_client, credentialed_user.email)
        set_cookie = response.headers["set-cookie"]
        assert "HttpOnly" in set_cookie

    def test_auth_cookie_restricts_samesite(self, auth_client, credentialed_user):
        """A cookie with no SameSite (or SameSite=None) rides along on cross-site
        state-changing requests, which is a CSRF hole."""
        response = login(auth_client, credentialed_user.email)
        samesite = re.search(
            r"samesite=(\w+)", response.headers["set-cookie"], re.IGNORECASE
        )
        assert samesite is not None
        assert samesite.group(1).lower() in {"lax", "strict"}

    def test_login_rejects_wrong_password(self, auth_client, credentialed_user):
        response = login(auth_client, credentialed_user.email, "not-the-password")
        assert response.status_code == 401
        assert auth_module.COOKIE_NAME not in response.cookies

    def test_login_rejects_unknown_email(self, auth_client):
        response = login(auth_client, "nobody@example.com")
        assert response.status_code == 401

    def test_wrong_password_and_unknown_email_are_indistinguishable(
        self, auth_client, credentialed_user
    ):
        """Otherwise the endpoint tells an attacker which emails have accounts."""
        wrong_password = login(auth_client, credentialed_user.email, "nope")
        unknown_email = login(auth_client, "nobody@example.com")
        assert wrong_password.json() == unknown_email.json()


class TestSessionAuthenticatesMe:
    def test_cookie_from_login_authenticates_me(self, auth_client, credentialed_user):
        """The end-to-end path that was broken in production: log in, then reach
        a protected route carrying nothing but the cookie."""
        login(auth_client, credentialed_user.email)
        response = auth_client.get("/api/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == credentialed_user.email

    def test_me_without_credentials_is_unauthenticated(self, auth_client):
        response = auth_client.get("/api/users/me")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_me_with_garbage_cookie_is_rejected(self, auth_client):
        auth_client.cookies.set(auth_module.COOKIE_NAME, "not-a-jwt")
        response = auth_client.get("/api/users/me")
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_me_with_expired_token_says_so(self, auth_client, credentialed_user):
        from datetime import timedelta

        expired = auth_module.create_access_token(
            {"sub": credentialed_user.email}, expires_delta=timedelta(minutes=-1)
        )
        auth_client.cookies.set(auth_module.COOKIE_NAME, expired)
        response = auth_client.get("/api/users/me")
        assert response.status_code == 401
        assert response.json()["detail"] == "Session expired, please log in again"

    def test_token_signed_with_another_key_is_rejected(
        self, auth_client, credentialed_user
    ):
        """Guards against ever accepting an unverified token."""
        from jose import jwt

        forged = jwt.encode(
            {"sub": credentialed_user.email},
            "a-different-secret",
            algorithm=auth_module.ALGORITHM,
        )
        auth_client.cookies.set(auth_module.COOKIE_NAME, forged)
        response = auth_client.get("/api/users/me")
        assert response.status_code == 401

    def test_logout_clears_the_session(self, auth_client, credentialed_user):
        login(auth_client, credentialed_user.email)
        assert auth_client.get("/api/users/me").status_code == 200

        auth_client.post("/api/auth/logout")
        assert auth_client.get("/api/users/me").status_code == 401


class TestBearerTokenEndpoint:
    """/auth/token serves clients with no cookie jar (Swagger UI, curl, CI)."""

    def test_token_endpoint_returns_bearer_token(self, auth_client, credentialed_user):
        response = auth_client.post(
            "/api/auth/token",
            data={"username": credentialed_user.email, "password": PASSWORD},
        )
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert response.json()["access_token"]

    def test_token_endpoint_sets_no_cookie(self, auth_client, credentialed_user):
        response = auth_client.post(
            "/api/auth/token",
            data={"username": credentialed_user.email, "password": PASSWORD},
        )
        assert auth_module.COOKIE_NAME not in response.cookies

    def test_bearer_header_authenticates_me(self, auth_client, credentialed_user):
        token = auth_client.post(
            "/api/auth/token",
            data={"username": credentialed_user.email, "password": PASSWORD},
        ).json()["access_token"]

        response = auth_client.get(
            "/api/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == credentialed_user.email
