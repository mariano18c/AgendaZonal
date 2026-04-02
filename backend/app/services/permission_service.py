"""Permission service — business logic for access control."""
from app.models.user import User
from app.models.contact import Contact


def can_edit_field(user: User | None, contact: Contact,
                   field_name: str, current_value) -> tuple[bool, bool]:
    """
    Determine if user can edit a field.
    Returns: (can_edit, needs_verification)
    """
    if not user:
        if current_value is None or current_value == "":
            return True, True
        return False, False

    if user.id == contact.user_id:
        return True, False

    if user.role in ('moderator', 'admin'):
        return True, False

    if current_value is None or current_value == "":
        return True, True

    return False, False


def can_verify_change(user: User | None, contact: Contact) -> bool:
    """Determine if user can verify/reject changes on a contact."""
    if not user:
        return False
    if user.id == contact.user_id:
        return True
    if user.role in ('moderator', 'admin'):
        return True
    return False
