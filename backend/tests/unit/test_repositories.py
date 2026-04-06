"""Unit tests — Repositories (Contact and User)."""
import pytest
from app.repositories.contact_repository import ContactRepository
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange


class TestUserRepository:
    def test_create_user(self, db_session):
        repo = UserRepository(db_session)
        # phone_area_code is required in the model
        user = repo.create(
            username="repo_user_new", 
            email="repo_new@example.com", 
            password_hash="hash",
            phone_area_code="11",
            phone_number="12345678"
        )
        assert user.id is not None
        assert user.username == "repo_user_new"

    def test_get_by_id(self, db_session, create_user):
        u = create_user(username="get_by_id")
        repo = UserRepository(db_session)
        fetched = repo.get_by_id(u.id)
        assert fetched.username == "get_by_id"

    def test_get_by_email(self, db_session, create_user):
        u = create_user(email="get_by_email@test.com")
        repo = UserRepository(db_session)
        fetched = repo.get_by_email("get_by_email@test.com")
        assert fetched.id == u.id

    def test_get_by_username(self, db_session, create_user):
        u = create_user(username="get_by_name")
        repo = UserRepository(db_session)
        fetched = repo.get_by_username("get_by_name")
        assert fetched.id == u.id

    def test_get_by_login(self, db_session, create_user):
        import uuid
        uid = str(uuid.uuid4())[:8]
        u = create_user(username=f"login_{uid}", email=f"login_{uid}@test.com")
        repo = UserRepository(db_session)
        assert repo.get_by_login(f"login_{uid}").id == u.id
        assert repo.get_by_login(f"login_{uid}@test.com").id == u.id

    def test_list_users_filters(self, db_session, create_user):
        # Clear users first to avoid pollution
        db_session.query(User).delete()
        create_user(username="alice", email="alice@test.com", role="admin")
        create_user(username="bob", email="bob@test.com", role="user")
        repo = UserRepository(db_session)
        
        # Filter by string
        assert len(repo.list(filter="alice")) == 1
        # Filter by role
        assert len(repo.list(role="user")) == 1
        # Filter by precise username
        assert len(repo.list(username="bob")) == 1

    def test_count_users(self, db_session, create_user):
        repo = UserRepository(db_session)
        initial = repo.count()
        create_user()
        assert repo.count() == initial + 1


class TestContactRepository:
    def test_create_contact(self, db_session, create_user):
        u = create_user()
        # Ensure category exists
        from app.models.category import Category
        cat = db_session.query(Category).first()
        if not cat:
            cat = Category(id=100, name="Test", code="100")
            db_session.add(cat)
            db_session.commit()
            
        repo = ContactRepository(db_session)
        c = repo.create(name="Repo Contact", user_id=u.id, category_id=cat.id)
        assert c.id is not None
        assert c.name == "Repo Contact"

    def test_get_by_id(self, db_session, create_contact):
        c = create_contact(name="SearchMe")
        repo = ContactRepository(db_session)
        assert repo.get_by_id(c.id).name == "SearchMe"

    def test_list_contacts(self, db_session, create_contact):
        # Ensure categories exist with unique codes
        from app.models.category import Category
        import uuid
        c1 = str(uuid.uuid4())[:4]
        c2 = str(uuid.uuid4())[:4]
        
        cat1 = db_session.query(Category).filter(Category.code == c1).first()
        if not cat1:
            cat1 = Category(id=1000 + int(c1, 16) % 1000, name="Test1", code=c1)
            db_session.add(cat1)
        
        cat2 = db_session.query(Category).filter(Category.code == c2).first()
        if not cat2:
            cat2 = Category(id=2000 + int(c2, 16) % 1000, name="Test2", code=c2)
            db_session.add(cat2)
        
        db_session.commit()

        create_contact(category_id=cat1.id)
        create_contact(category_id=cat2.id)
        repo = ContactRepository(db_session)
        assert len(repo.list(category_id=cat1.id)) >= 1

    def test_search_contacts(self, db_session, create_contact):
        create_contact(name="SpecialName", city="Rosario")
        repo = ContactRepository(db_session)
        
        # Search by name
        results = repo.search(q="SpecialName")
        assert any(r.name == "SpecialName" for r in results)
        
        # Search by city
        results = repo.search(q="Rosario")
        assert any(r.city == "Rosario" for r in results)

    def test_get_pending(self, db_session, create_user, create_contact):
        u = create_user()
        c = create_contact(user_id=u.id)
        c.pending_changes_count = 1
        db_session.commit()
        
        repo = ContactRepository(db_session)
        # For moderator
        assert len(repo.get_pending(role="moderator")) >= 1
        # For user
        assert len(repo.get_pending(user_id=u.id, role="user")) >= 1

    def test_delete_contact(self, db_session, create_contact):
        c = create_contact()
        repo = ContactRepository(db_session)
        repo.delete(c)
        assert repo.get_by_id(c.id) is None

    def test_history(self, db_session, create_user, create_contact):
        u = create_user()
        c = create_contact()
        repo = ContactRepository(db_session)
        repo.save_history(c.id, u.id, "name", "Old", "New")
        db_session.commit()
        
        history = repo.get_history(c.id)
        assert len(history) == 1
        assert history[0].new_value == "New"

    def test_changes_lifecycle(self, db_session, create_contact):
        c = create_contact()
        repo = ContactRepository(db_session)
        
        # Create change
        change = repo.create_change(contact_id=c.id, field_name="phone", old_value="1", new_value="2")
        db_session.commit()
        
        # Get multiple
        assert len(repo.get_changes(c.id)) == 1
        # Get one
        assert repo.get_change(change.id, c.id) is not None
        
        # Delete change
        repo.delete_change(change, c)
        assert repo.get_change(change.id, c.id) is None
