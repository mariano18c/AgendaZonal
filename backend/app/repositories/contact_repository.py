"""Contact repository — all database queries for contacts."""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange


class ContactRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, contact_id: int) -> Contact | None:
        return self.db.query(Contact).filter(Contact.id == contact_id).first()

    def list(self, skip: int = 0, limit: int = 100, category_id: int | None = None):
        query = self.db.query(Contact)
        if category_id is not None:
            query = query.filter(Contact.category_id == category_id)
        return query.offset(skip).limit(limit).all()

    def search(self, q: str | None = None, category_id: int | None = None,
               skip: int = 0, limit: int = 100):
        query = self.db.query(Contact)
        if q:
            safe_q = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            search = f"%{safe_q}%"
            query = query.filter(
                or_(
                    Contact.name.ilike(search),
                    Contact.city.ilike(search),
                    Contact.neighborhood.ilike(search),
                    Contact.description.ilike(search),
                    Contact.schedule.ilike(search),
                )
            )
        if category_id is not None:
            query = query.filter(Contact.category_id == category_id)
        return query.offset(skip).limit(limit).all()

    def get_pending(self, user_id: int | None = None, role: str | None = None):
        if role in ('moderator', 'admin'):
            return self.db.query(Contact).filter(Contact.pending_changes_count > 0).all()
        return self.db.query(Contact).filter(
            Contact.user_id == user_id,
            Contact.pending_changes_count > 0,
        ).all()

    def create(self, **kwargs) -> Contact:
        contact = Contact(**kwargs)
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def delete(self, contact: Contact):
        self.db.query(ContactChange).filter(ContactChange.contact_id == contact.id).delete()
        self.db.query(ContactHistory).filter(ContactHistory.contact_id == contact.id).delete()
        self.db.delete(contact)
        self.db.commit()

    # History
    def get_history(self, contact_id: int):
        return self.db.query(ContactHistory).filter(
            ContactHistory.contact_id == contact_id,
        ).order_by(ContactHistory.changed_at.desc()).all()

    def save_history(self, contact_id: int, user_id: int,
                     field_name: str, old_value, new_value):
        if str(old_value) != str(new_value):
            history = ContactHistory(
                contact_id=contact_id,
                user_id=user_id,
                field_name=field_name,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            self.db.add(history)

    # Changes
    def get_changes(self, contact_id: int):
        return self.db.query(ContactChange).filter(
            ContactChange.contact_id == contact_id,
            ContactChange.is_verified == False,
        ).order_by(ContactChange.created_at.desc()).all()

    def get_change(self, change_id: int, contact_id: int) -> ContactChange | None:
        return self.db.query(ContactChange).filter(
            ContactChange.id == change_id,
            ContactChange.contact_id == contact_id,
            ContactChange.is_verified == False,
        ).first()

    def create_change(self, **kwargs) -> ContactChange:
        change = ContactChange(**kwargs)
        self.db.add(change)
        return change

    def delete_change(self, change: ContactChange, contact: Contact):
        self.db.delete(change)
        contact.pending_changes_count = max(0, contact.pending_changes_count - 1)
        self.db.commit()
