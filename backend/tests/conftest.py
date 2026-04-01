"""Global test fixtures for AgendaZonal test suite.

Database strategy:
- SQLite :memory: with StaticPool for isolation
- PRAGMA foreign_keys=ON to match production behavior
- Per-function transaction rollback (SAVEPOINT) for speed
- Categories seeded automatically for each test

Async support:
- httpx.AsyncClient via async_client fixture for async endpoint testing
"""
import os
os.environ["TESTING"] = "1"

import pytest
import re
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import bcrypt

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.category import Category
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Create a shared in-memory SQLite engine for all tests.

    Uses StaticPool so all connections share the same database.
    PRAGMA foreign_keys=ON ensures FK constraints are enforced in tests.
    Categories are seeded once at session level.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_test_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    # Seed categories once at session level
    with engine.connect() as conn:
        for cat_data in [
            (100, "Plomero/a", "wrench", "Plomeria"),
            (101, "Gasista", "fire", "Gas"),
            (102, "Electricista", "zap", "Electricidad"),
            (103, "Peluqueria", "scissors", "Peluqueria"),
            (999, "Otro", "more", "Otros"),
        ]:
            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO categories (code, name, icon, description) VALUES (?, ?, ?, ?)",
                cat_data,
            )
        conn.commit()

    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def database_session(test_engine) -> Generator[Session, None, None]:
    """Create a per-test database session with automatic rollback.

    Each test gets a fresh connection. The outer transaction is rolled back
    at the end, undoing all changes. This provides isolation while being
    fast (no table recreation).
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(database_session: Session) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with database dependency override."""
    def override_get_db():
        try:
            yield database_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        c.cookies.clear()
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(database_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Create an httpx.AsyncClient for async endpoint testing.

    Supports FastAPI lifespan events and real async HTTP requests.
    Shares the same DB session override as the sync client.
    """
    def override_get_db():
        try:
            yield database_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _parse_captcha_answer(question: str) -> int:
    """Parse CAPTCHA question and return the answer."""
    if ' + ' in question:
        match = re.match(r'(\d+) \+ (\d+)', question)
        return int(match.group(1)) + int(match.group(2))
    elif ' - ' in question:
        match = re.match(r'(\d+) - (\d+)', question)
        return int(match.group(1)) - int(match.group(2))
    elif ' × ' in question:
        match = re.match(r'(\d+) × (\d+)', question)
        return int(match.group(1)) * int(match.group(2))
    else:
        raise ValueError(f"Unknown CAPTCHA format: {question}")


def _get_captcha_and_answer(client: TestClient) -> dict:
    """Helper to get a fresh CAPTCHA and compute its answer."""
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    answer = _parse_captcha_answer(data["question"])
    return {
        "challenge_id": data["challenge_id"],
        "answer": str(answer),
    }


# ---------------------------------------------------------------------------
# CAPTCHA fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def captcha(client: TestClient) -> dict[str, str]:
    """Get a valid CAPTCHA challenge and compute the answer."""
    return _get_captcha_and_answer(client)


# ---------------------------------------------------------------------------
# User / Auth fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def create_user(database_session: Session):
    """Factory fixture to create users directly in the database."""
    def _create(
        username: str = "testuser",
        email: str = "test@test.com",
        password: str = "password123",
        role: str = "user",
        is_active: bool = True,
        phone_area_code: str = "0341",
        phone_number: str = "1234567",
    ) -> User:
        user = User(
            username=username,
            email=email,
            phone_area_code=phone_area_code,
            phone_number=phone_number,
            password_hash=_hash_password(password),
            role=role,
            is_active=is_active,
        )
        database_session.add(user)
        database_session.commit()
        database_session.refresh(user)
        return user
    return _create


@pytest.fixture
def auth_headers(client: TestClient):
    """Factory fixture that registers a user and returns Bearer auth headers."""
    def _auth(
        username: str = "authuser",
        email: str = "auth@test.com",
        password: str = "password123",
    ) -> dict[str, str]:
        captcha = _get_captcha_and_answer(client)
        resp = client.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": password,
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        if resp.status_code == 201:
            token = resp.json()["token"]
            return {"Authorization": f"Bearer {token}"}

        # If registration fails, try login
        resp = client.post("/api/auth/login", json={
            "username_or_email": username,
            "password": password,
        })
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    return _auth


@pytest.fixture
def auth_token(client: TestClient):
    """Returns just the JWT token string (not the header dict)."""
    def _token(
        username: str = "authuser",
        email: str = "auth@test.com",
        password: str = "password123",
    ) -> str:
        captcha = _get_captcha_and_answer(client)
        resp = client.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": password,
            "captcha_challenge_id": captcha["challenge_id"],
            "captcha_answer": captcha["answer"],
        })
        if resp.status_code == 201:
            return resp.json()["token"]
        resp = client.post("/api/auth/login", json={
            "username_or_email": username,
            "password": password,
        })
        return resp.json()["token"]
    return _token


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    """Creates admin user via bootstrap-admin endpoint. Returns headers."""
    captcha = _get_captcha_and_answer(client)
    resp = client.post("/api/auth/bootstrap-admin", json={
        "username": "adminuser",
        "email": "admin@test.com",
        "phone_area_code": "0341",
        "phone_number": "1111111",
        "password": "adminpass123",
        "captcha_challenge_id": captcha["challenge_id"],
        "captcha_answer": captcha["answer"],
    })
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def moderator_user(client: TestClient, create_user, database_session: Session):
    """Create a user with moderator role. Returns (user_obj, headers)."""
    user = create_user(
        username="moderator",
        email="mod@test.com",
        password="password123",
        role="moderator",
    )
    resp = client.post("/api/auth/login", json={
        "username_or_email": "moderator",
        "password": "password123",
    })
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    return user, headers


# ---------------------------------------------------------------------------
# Data factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def contact_factory(client: TestClient):
    """Factory fixture to create contacts via the API."""
    def _create(
        headers: dict[str, str],
        name: str = "Test Contact",
        phone: str = "1234567",
        **kwargs,
    ) -> int:
        payload = {"name": name, "phone": phone}
        payload.update(kwargs)
        resp = client.post("/api/contacts", headers=headers, json=payload)
        assert resp.status_code == 201, f"Failed to create contact: {resp.json()}"
        return resp.json()["id"]
    return _create


@pytest.fixture
def change_factory(client: TestClient):
    """Factory fixture to create pending changes on a contact."""
    def _create(
        contact_id: int,
        other_headers: dict[str, str],
        field_name: str = "description",
        new_value: str = "Sugerencia",
    ) -> int | None:
        resp = client.put(
            f"/api/contacts/{contact_id}/edit",
            headers=other_headers,
            json={field_name: new_value},
        )
        assert resp.status_code == 200, f"Failed to create change: {resp.json()}"
        changes_resp = client.get(
            f"/api/contacts/{contact_id}/changes",
            headers=other_headers,
        )
        if changes_resp.status_code == 200 and changes_resp.json():
            return changes_resp.json()[-1]["id"]
        return None
    return _create
