"""Global test fixtures for AgendaZonal — Professional QA Suite v2.

Database strategy
-----------------
- SQLite :memory: with StaticPool (shared across one session)
- PRAGMA foreign_keys=ON for referential integrity
- Per-function SAVEPOINT rollback for true transactional isolation
- Categories pre-seeded at session level

HTTP clients
------------
- Sync ``TestClient`` for most tests (faster)
- Async ``httpx.AsyncClient`` available when needed

Helpers
-------
- ``create_user`` / ``create_contact`` / etc. — direct-DB factories
- ``auth_headers`` — register-via-API and return Bearer dict
- ``jwt_helpers`` — craft malicious tokens for security tests
"""
import os

os.environ["TESTING"] = "1"

import re
import uuid
import bcrypt
import jwt as pyjwt
import pytest
from datetime import datetime, timedelta, timezone
from typing import Generator, AsyncGenerator

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


# ──────────────────────────────────────────────────────────────────────
# Database engine (session-scoped, created ONCE for the whole run)
# ──────────────────────────────────────────────────────────────────────

SEED_CATEGORIES = [
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


@pytest.fixture(scope="session")
def test_engine():
    """Shared in-memory SQLite engine with production-equivalent PRAGMAs."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA cache_size=-20000")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

    Base.metadata.create_all(bind=engine)

    # Seed categories once
    with engine.begin() as conn:
        for code, name, icon, desc in SEED_CATEGORIES:
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO categories (code, name, icon, description) "
                    "VALUES (:code, :name, :icon, :desc)"
                ),
                {"code": code, "name": name, "icon": icon, "desc": desc},
            )

    yield engine
    Base.metadata.drop_all(bind=engine)


# ──────────────────────────────────────────────────────────────────────
# Per-function transactional session (SAVEPOINT rollback)
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    """Per-test DB session with automatic rollback via outer transaction.

    Each test runs inside a savepoint.  Route-level ``db.commit()`` calls
    release the savepoint, which is immediately restarted so subsequent
    operations still live inside the outer transaction.  At teardown the
    outer transaction is rolled back, undoing ALL changes.
    """
    connection = test_engine.connect()
    outer_txn = connection.begin()

    factory = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = factory()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, txn):
        if txn.nested and not txn._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    outer_txn.rollback()
    connection.close()


# ──────────────────────────────────────────────────────────────────────
# Dependency override
# ──────────────────────────────────────────────────────────────────────

def _override_get_db(session: Session):
    """Return a FastAPI dependency override that yields *session*."""
    def _inner():
        try:
            yield session
        finally:
            pass
    return _inner


# ──────────────────────────────────────────────────────────────────────
# HTTP clients
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Sync ``TestClient`` bound to the transactional DB session."""
    app.dependency_overrides[get_db] = _override_get_db(db_session)
    with TestClient(app, raise_server_exceptions=False) as c:
        c.cookies.clear()
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
async def async_client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Async ``httpx.AsyncClient`` with ASGITransport."""
    app.dependency_overrides[get_db] = _override_get_db(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────
# CAPTCHA helpers
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _captcha_cleanup():
    """Clear CAPTCHA challenges before AND after each test."""
    from app.captcha import CaptchaManager
    CaptchaManager.CHALLENGES.clear()
    yield
    CaptchaManager.CHALLENGES.clear()


def _parse_captcha_answer(question: str) -> int:
    """Solve a math CAPTCHA question."""
    if " + " in question:
        m = re.match(r"(\d+) \+ (\d+)", question)
        return int(m.group(1)) + int(m.group(2))
    if " - " in question:
        m = re.match(r"(\d+) - (\d+)", question)
        return int(m.group(1)) - int(m.group(2))
    if " × " in question:
        m = re.match(r"(\d+) × (\d+)", question)
        return int(m.group(1)) * int(m.group(2))
    raise ValueError(f"Unknown CAPTCHA: {question}")


def solve_captcha(client: TestClient) -> dict[str, str]:
    """Get + solve a fresh CAPTCHA.  Returns ``{challenge_id, answer}``."""
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    answer = _parse_captcha_answer(data["question"])
    return {"challenge_id": data["challenge_id"], "answer": str(answer)}


@pytest.fixture()
def captcha(client: TestClient) -> dict[str, str]:
    """Ready-to-use CAPTCHA dict for registration payloads."""
    return solve_captcha(client)


# ──────────────────────────────────────────────────────────────────────
# Password helper
# ──────────────────────────────────────────────────────────────────────

def _hash(password: str = "password123") -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# ──────────────────────────────────────────────────────────────────────
# User factory (direct DB)
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def create_user(db_session: Session):
    """Factory: create a ``User`` directly in the DB.

    Every call generates a UUID-based unique username/email so there are
    never UNIQUE-constraint collisions, even with StaticPool.

    Usage::

        user = create_user()                        # defaults
        admin = create_user(role="admin")
        mod = create_user(role="moderator", username="mod1")
    """
    def _make(
        *,
        username: str | None = None,
        email: str | None = None,
        password: str = "password123",
        role: str = "user",
        is_active: bool = True,
        phone_area_code: str = "0341",
        phone_number: str = "1234567",
    ) -> User:
        uid = uuid.uuid4().hex[:8]
        user = User(
            username=username or f"u_{uid}",
            email=email or f"u_{uid}@test.com",
            phone_area_code=phone_area_code,
            phone_number=phone_number,
            password_hash=_hash(password),
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _make


# ──────────────────────────────────────────────────────────────────────
# Auth-header helpers
# ──────────────────────────────────────────────────────────────────────

def _bearer(user: User) -> dict[str, str]:
    """Build ``{"Authorization": "Bearer <token>"}`` for a User row."""
    return {"Authorization": f"Bearer {create_token(user.id)}"}


@pytest.fixture()
def user_headers(create_user) -> dict[str, str]:
    """Headers for a fresh regular user."""
    return _bearer(create_user())


@pytest.fixture()
def admin_user(create_user) -> User:
    """An admin ``User`` object."""
    return create_user(role="admin")


@pytest.fixture()
def admin_headers(admin_user) -> dict[str, str]:
    """Admin Bearer headers."""
    return _bearer(admin_user)


@pytest.fixture()
def mod_user(create_user) -> User:
    """A moderator ``User`` object."""
    return create_user(role="moderator")


@pytest.fixture()
def mod_headers(mod_user) -> dict[str, str]:
    """Moderator Bearer headers."""
    return _bearer(mod_user)


# ──────────────────────────────────────────────────────────────────────
# Contact factory (direct DB)
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def create_contact(db_session: Session, create_user):
    """Factory: create a ``Contact`` directly in the DB.

    If ``user_id`` is omitted a new owner user is auto-created.

    Usage::

        c = create_contact(name="Ferretería Juan")
        c = create_contact(user_id=admin.id, category_id=100)
    """
    def _make(
        *,
        name: str = "Test Contact",
        phone: str = "1234567",
        user_id: int | None = None,
        category_id: int | None = None,
        email: str = "",
        address: str = "",
        city: str = "Rosario",
        neighborhood: str = "Centro",
        description: str = "Test desc",
        latitude: float | None = None,
        longitude: float | None = None,
        status: str = "active",
        verification_level: int = 0,
        slug: str | None = None,
    ) -> Contact:
        if user_id is None:
            user_id = create_user().id
        if category_id is None:
            cat = db_session.query(Category).first()
            category_id = cat.id if cat else None

        contact = Contact(
            name=name, phone=phone, user_id=user_id,
            category_id=category_id, email=email, address=address,
            city=city, neighborhood=neighborhood, description=description,
            latitude=latitude, longitude=longitude,
            status=status, verification_level=verification_level,
            slug=slug,
        )
        db_session.add(contact)
        db_session.commit()
        db_session.refresh(contact)
        return contact
    return _make


# ──────────────────────────────────────────────────────────────────────
# Review / Offer / Report / Utility / Notification / Schedule factories
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def create_review(db_session: Session, create_user):
    def _make(*, contact_id: int, user_id: int | None = None,
              rating: int = 5, comment: str = "Excelente",
              is_approved: bool = False, **kw) -> Review:
        if user_id is None:
            user_id = create_user().id
        r = Review(contact_id=contact_id, user_id=user_id,
                   rating=rating, comment=comment,
                   is_approved=is_approved, **kw)
        db_session.add(r)
        db_session.commit()
        db_session.refresh(r)
        return r
    return _make


@pytest.fixture()
def create_offer(db_session: Session):
    def _make(*, contact_id: int, title: str = "Oferta",
              description: str = "20% off", discount_pct: int = 20,
              expires_in_days: int = 7, is_active: bool = True) -> Offer:
        o = Offer(
            contact_id=contact_id, title=title, description=description,
            discount_pct=discount_pct,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
            is_active=is_active,
        )
        db_session.add(o)
        db_session.commit()
        db_session.refresh(o)
        return o
    return _make


@pytest.fixture()
def create_report(db_session: Session, create_user):
    def _make(*, contact_id: int, user_id: int | None = None,
              reason: str = "spam", details: str = "") -> Report:
        if user_id is None:
            user_id = create_user().id
        r = Report(contact_id=contact_id, user_id=user_id,
                   reason=reason, details=details, is_resolved=False)
        db_session.add(r)
        db_session.commit()
        db_session.refresh(r)
        return r
    return _make


@pytest.fixture()
def create_utility(db_session: Session):
    def _make(*, name: str = "Test Utility", type: str = "otro",
              phone: str = "1234567", address: str = "Calle 1",
              schedule: str = "Lun-Vie 9-18", city: str = "Rosario",
              is_active: bool = True) -> UtilityItem:
        item = UtilityItem(name=name, type=type, phone=phone,
                           address=address, schedule=schedule,
                           city=city, is_active=is_active)
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        return item
    return _make


@pytest.fixture()
def create_notification(db_session: Session):
    def _make(*, user_id: int, message: str = "Test notification",
              notification_type: str = "review",
              is_read: bool = False) -> Notification:
        n = Notification(user_id=user_id, type=notification_type,
                         message=message, is_read=is_read)
        db_session.add(n)
        db_session.commit()
        db_session.refresh(n)
        return n
    return _make


# ──────────────────────────────────────────────────────────────────────
# API-level helpers
# ──────────────────────────────────────────────────────────────────────

def register_user(client: TestClient, **overrides) -> dict:
    """Register a user via API, return the full JSON response body.
    
    After pending activation change, returns {message, username} without token.
    Use create_user() fixture for creating active users directly in DB.
    """
    uid = uuid.uuid4().hex[:8]
    captcha = solve_captcha(client)
    payload = {
        "username": overrides.get("username", f"r_{uid}"),
        "email": overrides.get("email", f"r_{uid}@test.com"),
        "phone_area_code": "0341",
        "phone_number": "1234567",
        "password": overrides.get("password", "password123"),
        "captcha_challenge_id": captcha["challenge_id"],
        "captcha_answer": captcha["answer"],
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    return resp.json()


def login_user(client: TestClient, username_or_email: str,
               password: str = "password123") -> dict:
    """Login via API, return full JSON response body."""
    resp = client.post("/api/auth/login", json={
        "username_or_email": username_or_email,
        "password": password,
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


def api_create_contact(client: TestClient, headers: dict,
                       **overrides) -> dict:
    """Create a contact via API.  Returns the response JSON."""
    payload = {"name": overrides.pop("name", "API Contact"),
               "phone": overrides.pop("phone", "9876543")}
    payload.update(overrides)
    resp = client.post("/api/contacts", headers=headers, json=payload)
    assert resp.status_code == 201, f"Create contact failed: {resp.text}"
    return resp.json()


# ──────────────────────────────────────────────────────────────────────
# JWT helpers for security tests
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture()
def jwt_helpers():
    """Craft malicious / edge-case JWT tokens."""
    from app.config import JWT_SECRET, JWT_ALGORITHM

    class _H:
        @staticmethod
        def expired(user_id: int = 1) -> str:
            return pyjwt.encode(
                {"sub": str(user_id),
                 "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
                JWT_SECRET, algorithm=JWT_ALGORITHM)

        @staticmethod
        def wrong_secret(user_id: int = 1) -> str:
            return pyjwt.encode(
                {"sub": str(user_id),
                 "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                "not_the_real_secret_at_all_xxx", algorithm=JWT_ALGORITHM)

        @staticmethod
        def forged_admin(user_id: int = 99999) -> str:
            return pyjwt.encode(
                {"sub": str(user_id),
                 "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                JWT_SECRET, algorithm=JWT_ALGORITHM)

        @staticmethod
        def no_sub() -> str:
            return pyjwt.encode(
                {"exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                JWT_SECRET, algorithm=JWT_ALGORITHM)

        @staticmethod
        def wrong_algo(user_id: int = 1) -> str:
            return pyjwt.encode(
                {"sub": str(user_id),
                 "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                JWT_SECRET, algorithm="HS384")

        @staticmethod
        def non_numeric_sub() -> str:
            return pyjwt.encode(
                {"sub": "not_a_number",
                 "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                JWT_SECRET, algorithm=JWT_ALGORITHM)

    return _H()
