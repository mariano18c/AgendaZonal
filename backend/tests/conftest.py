"""Global test fixtures for AgendaZonal — Professional QA Suite 2026.

Database strategy:
- SQLite :memory: with StaticPool for session-level isolation
- PRAGMA foreign_keys=ON, WAL mode, busy_timeout=5000
- Per-function SAVEPOINT rollback for true transactional isolation
- Categories pre-seeded at session level

Async support:
- pytest-asyncio in auto mode
- httpx.AsyncClient with ASGITransport for real async lifecycle

Security:
- Rate limiting disabled via TESTING=1
- CAPTCHA challenges auto-managed
"""
import os
os.environ["TESTING"] = "1"

import re
import bcrypt
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from typing import Generator, AsyncGenerator, Callable
from contextlib import contextmanager

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.category import Category
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange
from app.models.review import Review
from app.models.offer import Offer
from app.models.report import Report
from app.models.utility_item import UtilityItem
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.lead_event import LeadEvent
from app.models.schedule import Schedule
from app.models.contact_photo import ContactPhoto
from app.auth import create_token


# ---------------------------------------------------------------------------
# Database engine (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Create a shared in-memory SQLite engine with production-equivalent PRAGMAs.

    Uses StaticPool so all connections share the same :memory: database.
    Categories are seeded once at session level for performance.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_test_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA cache_size=-20000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    # Seed categories once at session level
    with engine.begin() as conn:
        categories = [
            (100, "Plomero/a", "wrench", "Plomería"),
            (101, "Gasista", "fire", "Gas"),
            (102, "Electricista", "zap", "Electricidad"),
            (103, "Peluquería/Barbería", "scissors", "Peluquería"),
            (104, "Albañil", "hammer", "Construcción"),
            (105, "Pintor", "paint", "Pintura"),
            (106, "Carpintero/a", "wood", "Carpintería"),
            (107, "Supermercado", "cart", "Alimentos"),
            (108, "Carnicería", "meat", "Carnes"),
            (109, "Verdulería", "leaf", "Verduras"),
            (110, "Panadería", "bread", "Pan"),
            (111, "Tienda de ropa", "shirt", "Ropa"),
            (112, "Farmacia", "pill", "Salud"),
            (113, "Librería", "book", "Libros"),
            (114, "Bar", "beer", "Bebidas"),
            (115, "Restaurant", "utensils", "Comida"),
            (116, "Club", "trophy", "Deportes"),
            (117, "Bazar", "store", "Varios"),
            (118, "Veterinaria", "paw", "Mascotas"),
            (119, "Ferretería", "tools", "Herramientas"),
            (120, "Kiosco", "candy", "Snacks"),
            (121, "Juguetería", "game", "Juguetes"),
            (122, "Polirrubro", "shop", "Varios"),
            (999, "Otro", "more", "Otros"),
        ]
        for code, name, icon, desc in categories:
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO categories (code, name, icon, description) "
                    "VALUES (:code, :name, :icon, :desc)"
                ),
                {"code": code, "name": name, "icon": icon, "desc": desc},
            )

    yield engine
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Transactional session with SAVEPOINT rollback (per-function isolation)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Per-test database session with SAVEPOINT-based automatic rollback.

    Each test runs inside a nested transaction (savepoint). On teardown,
    the savepoint is rolled back, undoing ALL changes — including cascades.
    This is faster than recreating tables and provides true isolation.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()

    # Begin a savepoint for nested rollback
    session.begin_nested()

    # Each flush() starts a new savepoint
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Dependency override helper
# ---------------------------------------------------------------------------

def _override_db(session: Session):
    """Override get_db dependency to use the test session."""
    def _override():
        try:
            yield session
        finally:
            pass
    return _override


# ---------------------------------------------------------------------------
# HTTP Clients
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Sync TestClient with transactional DB session override."""
    app.dependency_overrides[get_db] = _override_db(db_session)
    with TestClient(app) as c:
        c.cookies.clear()
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Async httpx client with ASGITransport for real async lifecycle.

    Supports FastAPI lifespan events and real async HTTP requests.
    Shares the same DB session override as the sync client.
    """
    app.dependency_overrides[get_db] = _override_db(db_session)
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
    """Parse CAPTCHA math question and return the numeric answer."""
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


def _get_captcha_and_answer(client: TestClient) -> dict[str, str]:
    """Get a fresh CAPTCHA challenge and compute its answer."""
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 200, f"CAPTCHA endpoint failed: {resp.text}"
    data = resp.json()
    answer = _parse_captcha_answer(data["question"])
    return {
        "challenge_id": data["challenge_id"],
        "answer": str(answer),
    }


def _register_and_login(
    client: TestClient,
    username: str,
    email: str,
    password: str = "password123",
    role: str = "user",
) -> dict[str, str]:
    """Register a user via API and return Bearer auth headers."""
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

    # Fallback: try login (user may already exist)
    resp = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": password,
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# CAPTCHA management
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def captcha_cleanup():
    """Clear CaptchaManager challenges before and after each test.

    Prevents cross-test contamination from accumulated/expired challenges.
    """
    from app.captcha import CaptchaManager
    CaptchaManager.CHALLENGES.clear()
    yield
    CaptchaManager.CHALLENGES.clear()


# ---------------------------------------------------------------------------
# CAPTCHA fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def captcha(client: TestClient) -> dict[str, str]:
    """Get a valid CAPTCHA challenge with pre-computed answer."""
    return _get_captcha_and_answer(client)


# ---------------------------------------------------------------------------
# User / Auth fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def create_user(db_session: Session):
    """Factory to create users directly in the database.

    Usage:
        user = create_user(username="alice", role="admin")
    """
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
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _create


@pytest.fixture
def auth_headers(client: TestClient):
    """Factory to register a user and return Bearer auth headers.

    Usage:
        headers = auth_headers(username="alice", email="alice@test.com")
    """
    def _auth(
        username: str = "authuser",
        email: str = "auth@test.com",
        password: str = "password123",
    ) -> dict[str, str]:
        return _register_and_login(client, username, email, password)
    return _auth


@pytest.fixture
def auth_token(client: TestClient):
    """Factory to register a user and return just the JWT token string.

    Usage:
        token = auth_token(username="alice", email="alice@test.com")
    """
    def _token(
        username: str = "authuser",
        email: str = "auth@test.com",
        password: str = "password123",
    ) -> str:
        headers = _register_and_login(client, username, email, password)
        return headers["Authorization"].split(" ", 1)[1]
    return _token


@pytest.fixture
def admin_headers(db_session: Session, client: TestClient) -> dict[str, str]:
    """Return admin auth headers. Creates admin in DB if needed.

    Creates the admin user directly in the DB to avoid rate limiting
    on the bootstrap-admin endpoint.
    """
    import bcrypt
    from app.models.user import User

    # Check if admin exists in current transaction
    existing = db_session.query(User).filter(User.role == "admin").first()
    if existing:
        token = create_token(existing.id)
        return {"Authorization": f"Bearer {token}"}

    # Create admin directly in DB
    password_hash = bcrypt.hashpw(
        "adminpass123".encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")
    admin = User(
        username="adminuser",
        email="admin@test.com",
        phone_area_code="0341",
        phone_number="1111111",
        password_hash=password_hash,
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    token = create_token(admin.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def moderator_user(client: TestClient, create_user):
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
    assert resp.status_code == 200
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}
    return user, headers


# ---------------------------------------------------------------------------
# Data factory fixtures (direct DB creation — corrected)
# ---------------------------------------------------------------------------

@pytest.fixture
def create_contact(db_session: Session):
    """Factory to create contacts directly in the database.

    Creates a Contact with valid defaults, linked to a user.
    If user_id is not provided, creates a new user automatically.

    Usage:
        contact = create_contact(name="Mi Negocio", category_id=1)
    """
    def _create(
        name: str = "Test Contact",
        phone: str = "1234567",
        user_id: int | None = None,
        category_id: int | None = None,
        email: str = "",
        address: str = "",
        city: str = "",
        neighborhood: str = "",
        description: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
        status: str = "active",
        verification_level: int = 0,
    ) -> Contact:
        if user_id is None:
            user = User(
                username=f"contact_owner_{name[:8]}_{id}",
                email=f"contact_{name[:8]}_{id}@test.com",
                phone_area_code="0341",
                phone_number="9999999",
                password_hash=_hash_password("password123"),
                role="user",
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            user_id = user.id

        if category_id is None:
            cat = db_session.query(Category).first()
            if cat:
                category_id = cat.id

        contact = Contact(
            name=name,
            phone=phone,
            user_id=user_id,
            category_id=category_id,
            email=email,
            address=address,
            city=city,
            neighborhood=neighborhood,
            description=description,
            latitude=latitude,
            longitude=longitude,
            status=status,
            verification_level=verification_level,
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        return contact
    return _create


@pytest.fixture
def create_review(db_session: Session):
    """Factory to create reviews linked to a contact and user.

    FIXED: Uses is_approved (Boolean) instead of non-existent status field.

    Usage:
        review = create_review(contact_id=1, rating=5, is_approved=True)
    """
    def _create(
        contact_id: int,
        user_id: int | None = None,
        rating: int = 5,
        comment: str = "Great service!",
        is_approved: bool = False,
        reply_text: str | None = None,
    ) -> Review:
        if user_id is None:
            user = User(
                username=f"reviewer_{contact_id}_{id}",
                email=f"reviewer_{contact_id}_{id}@test.com",
                phone_area_code="0341",
                phone_number="8888888",
                password_hash=_hash_password("password123"),
                role="user",
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            user_id = user.id

        review = Review(
            contact_id=contact_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
            is_approved=is_approved,
            reply_text=reply_text,
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)
        return review
    return _create


@pytest.fixture
def create_offer(db_session: Session):
    """Factory to create offers with future expires_at.

    FIXED: Uses is_active (not 'active') and removes non-existent starts_at.

    Usage:
        offer = create_offer(contact_id=1, discount_pct=25)
    """
    def _create(
        contact_id: int,
        title: str = "Special Offer",
        description: str = "20% off",
        discount_pct: int = 20,
        expires_in_days: int = 7,
        is_active: bool = True,
    ) -> Offer:
        offer = Offer(
            contact_id=contact_id,
            title=title,
            description=description,
            discount_pct=discount_pct,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
            is_active=is_active,
        )
        db_session.add(offer)
        db_session.commit()
        db_session.refresh(offer)
        return offer
    return _create


@pytest.fixture
def create_report(db_session: Session):
    """Factory to create reports for a contact.

    FIXED: Uses user_id (not 'reporter_id') and is_resolved (not 'status').

    Usage:
        report = create_report(contact_id=1, reason="spam")
    """
    def _create(
        contact_id: int,
        user_id: int | None = None,
        reason: str = "spam",
        details: str = "",
        is_resolved: bool = False,
    ) -> Report:
        if user_id is None:
            user = User(
                username=f"reporter_{contact_id}_{id}",
                email=f"reporter_{contact_id}_{id}@test.com",
                phone_area_code="0341",
                phone_number="7777777",
                password_hash=_hash_password("password123"),
                role="user",
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            user_id = user.id

        report = Report(
            contact_id=contact_id,
            user_id=user_id,
            reason=reason,
            details=details,
            is_resolved=is_resolved,
        )
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
        return report
    return _create


@pytest.fixture
def create_utility(db_session: Session):
    """Factory to create UtilityItem with valid defaults.

    Usage:
        utility = create_utility(name="Escuela Primaria", type="educacion")
    """
    def _create(
        name: str = "Test Utility",
        type: str = "otro",
        phone: str = "1234567",
        address: str = "Test St 123",
        schedule: str = "Lun-Vie 9-18",
        city: str = "Rosario",
        is_active: bool = True,
    ) -> UtilityItem:
        item = UtilityItem(
            name=name,
            type=type,
            phone=phone,
            address=address,
            schedule=schedule,
            city=city,
            is_active=is_active,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        return item
    return _create


@pytest.fixture
def create_notification(db_session: Session):
    """Factory to create notifications for a user.

    Usage:
        notification = create_notification(user_id=1, message="New review!")
    """
    def _create(
        user_id: int,
        notification_type: str = "review",
        message: str = "Notification message",
        contact_id: int | None = None,
        is_read: bool = False,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            message=message,
            contact_id=contact_id,
            is_read=is_read,
        )
        db_session.add(notification)
        db_session.commit()
        db_session.refresh(notification)
        return notification
    return _create


# ---------------------------------------------------------------------------
# API factory fixtures (create via HTTP endpoints)
# ---------------------------------------------------------------------------

@pytest.fixture
def contact_factory(client: TestClient):
    """Factory to create contacts via the API.

    Usage:
        contact_id = contact_factory(headers, name="Mi Negocio")
    """
    def _create(
        headers: dict[str, str],
        name: str = "Test Contact",
        phone: str = "1234567",
        **kwargs,
    ) -> int:
        payload = {"name": name, "phone": phone}
        payload.update(kwargs)
        resp = client.post("/api/contacts", headers=headers, json=payload)
        assert resp.status_code == 201, f"Failed to create contact: {resp.text}"
        return resp.json()["id"]
    return _create


@pytest.fixture
def change_factory(client: TestClient):
    """Factory to create pending changes on a contact.

    Usage:
        change_id = change_factory(contact_id, headers, field_name="description", new_value="Nuevo")
    """
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
        assert resp.status_code == 200, f"Failed to create change: {resp.text}"
        changes_resp = client.get(
            f"/api/contacts/{contact_id}/changes",
            headers=other_headers,
        )
        if changes_resp.status_code == 200 and changes_resp.json():
            return changes_resp.json()[-1]["id"]
        return None
    return _create


# ---------------------------------------------------------------------------
# JWT helpers for security tests
# ---------------------------------------------------------------------------

@pytest.fixture
def jwt_helpers():
    """Utility for crafting malicious/edge-case JWT tokens."""
    from app.config import JWT_SECRET, JWT_ALGORITHM

    class JWTHelpers:
        @staticmethod
        def expired_token(user_id: int = 1) -> str:
            """Token that expired 1 hour ago."""
            return jwt.encode(
                {
                    "sub": str(user_id),
                    "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                },
                JWT_SECRET,
                algorithm=JWT_ALGORITHM,
            )

        @staticmethod
        def wrong_secret_token(user_id: int = 1) -> str:
            """Token signed with wrong secret."""
            return jwt.encode(
                {
                    "sub": str(user_id),
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                },
                "wrong_secret_key_that_does_not_match",
                algorithm=JWT_ALGORITHM,
            )

        @staticmethod
        def forged_admin_token(user_id: int = 999) -> str:
            """Valid token structure but for non-existent admin user."""
            return jwt.encode(
                {
                    "sub": str(user_id),
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                },
                JWT_SECRET,
                algorithm=JWT_ALGORITHM,
            )

        @staticmethod
        def token_without_sub() -> str:
            """Token missing the 'sub' claim."""
            return jwt.encode(
                {"exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                JWT_SECRET,
                algorithm=JWT_ALGORITHM,
            )

        @staticmethod
        def token_with_wrong_algorithm(user_id: int = 1) -> str:
            """Token signed with HS384 instead of HS256."""
            return jwt.encode(
                {
                    "sub": str(user_id),
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                },
                JWT_SECRET,
                algorithm="HS384",
            )

    return JWTHelpers()


# ---------------------------------------------------------------------------
# Bootstrap helper for admin tests
# ---------------------------------------------------------------------------

@pytest.fixture
def bootstrap_admin_once(client: TestClient, db_session: Session):
    """Ensure exactly one admin exists. Returns admin headers.

    Idempotent: works whether admin already exists or not.
    Handles rate limiting (429) gracefully by falling back to login.
    """
    # Check if admin already exists in current session
    existing_admin = db_session.query(User).filter(User.role == "admin").first()
    if existing_admin:
        token = create_token(existing_admin.id)
        return {"Authorization": f"Bearer {token}"}

    # Try to bootstrap
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

    if resp.status_code == 201:
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    # 429 (rate limited) or 403 (already exists) — try login
    if resp.status_code in [429, 403]:
        login_resp = client.post("/api/auth/login", json={
            "username_or_email": "adminuser",
            "password": "adminpass123",
        })
        if login_resp.status_code == 200:
            token = login_resp.json()["token"]
            return {"Authorization": f"Bearer {token}"}

    raise AssertionError(f"Bootstrap admin failed: {resp.text}")
