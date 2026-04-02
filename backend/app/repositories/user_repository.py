"""User repository — all database queries for users."""
from sqlalchemy.orm import Session
from app.models.user import User


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_login(self, username_or_email: str) -> User | None:
        return self.db.query(User).filter(
            (User.email == username_or_email) | (User.username == username_or_email)
        ).first()

    def list(self, filter: str | None = None, role: str | None = None,
             username: str | None = None):
        query = self.db.query(User)
        if filter:
            search = f"%{filter}%"
            query = query.filter(
                (User.username.ilike(search)) | (User.email.ilike(search))
            )
        if role:
            query = query.filter(User.role == role)
        if username:
            query = query.filter(User.username == username)
        return query.all()

    def count(self) -> int:
        return self.db.query(User).count()

    def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
