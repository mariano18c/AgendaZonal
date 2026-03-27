import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import bcrypt

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.category import Category
from app.models.contact import Contact
from app.models.contact_change import ContactChange


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    categories = [
        Category(code=100, name="Plomero/a", icon="wrench", description="Plomeria"),
        Category(code=101, name="Gasista", icon="fire", description="Gas"),
        Category(code=102, name="Electricista", icon="zap", description="Electricidad"),
        Category(code=103, name="Peluqueria", icon="scissors", description="Peluqueria"),
        Category(code=999, name="Otro", icon="more", description="Otros"),
    ]
    for cat in categories:
        session.add(cat)
    session.commit()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@pytest.fixture
def create_user(db_session):
    def _create(
        username="testuser",
        email="test@test.com",
        password="password123",
        role="user",
        is_active=True,
        phone_area_code="0341",
        phone_number="1234567",
    ):
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
def auth_headers(client):
    def _auth(username="authuser", email="auth@test.com", password="password123"):
        resp = client.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": password,
        })
        if resp.status_code == 201:
            token = resp.json()["token"]
            return {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/auth/login", json={
            "username_or_email": username,
            "password": password,
        })
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    return _auth


@pytest.fixture
def auth_token(client):
    """Returns just the JWT token string (not the header dict)."""
    def _token(username="authuser", email="auth@test.com", password="password123"):
        resp = client.post("/api/auth/register", json={
            "username": username,
            "email": email,
            "phone_area_code": "0341",
            "phone_number": "1234567",
            "password": password,
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
def admin_headers(client):
    """First registered user gets admin role. Returns headers dict."""
    resp = client.post("/api/auth/register", json={
        "username": "adminuser",
        "email": "admin@test.com",
        "phone_area_code": "0341",
        "phone_number": "1111111",
        "password": "adminpass123",
    })
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def moderator_user(client, create_user, db_session):
    """Create a user with moderator role and return (user_obj, headers)."""
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


@pytest.fixture
def contact_factory(client):
    """Factory fixture to create contacts easily.
    Returns a callable: contact_factory(headers, **overrides) -> contact_id
    """
    def _create(headers, name="Test Contact", phone="1234567", **kwargs):
        payload = {"name": name, "phone": phone}
        payload.update(kwargs)
        resp = client.post("/api/contacts", headers=headers, json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]
    return _create


@pytest.fixture
def change_factory(client):
    """Factory fixture to create pending changes on a contact.
    Returns: change_factory(contact_id, other_headers, field_name, new_value) -> change_id
    """
    def _create(contact_id, other_headers, field_name="description", new_value="Sugerencia"):
        resp = client.put(
            f"/api/contacts/{contact_id}/edit",
            headers=other_headers,
            json={field_name: new_value},
        )
        assert resp.status_code == 200
        # Retrieve the change_id from changes endpoint
        changes_resp = client.get(
            f"/api/contacts/{contact_id}/changes",
            headers=other_headers,
        )
        if changes_resp.status_code == 200 and changes_resp.json():
            return changes_resp.json()[-1]["id"]
        return None
    return _create
