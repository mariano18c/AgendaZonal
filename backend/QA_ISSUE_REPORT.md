# QA Issue Report — AgendaZonal Backend

**Generated**: 2026-04-04
**Auditor**: QA Senior (Staff Level) — Automated Audit
**Scope**: Backend FastAPI + SQLite + JWT Authentication

---

## Issue #1: Bootstrap Admin Endpoint Without Rate Limiting

**Severity**: Critical

**Vector**: Information disclosure + brute-force enumeration

**Description**: The `/api/auth/bootstrap-admin` endpoint has no rate limiting decorator. An attacker can repeatedly hit this endpoint to determine if the database is empty (201 vs 403), enabling targeted attacks during initial deployment.

**Refactor Recommended**:
```python
@router.post("/bootstrap-admin", response_model=AuthResponse, status_code=201)
@limiter.limit("3/minute")  # Add rate limiting
def bootstrap_admin(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    ...
```

---

## Issue #2: Transfer Ownership Uses Raw Dict Without Schema Validation

**Severity**: High

**Vector**: Arbitrary field injection

**Description**: The `transfer_ownership` endpoint in `backend/app/routes/contacts.py` accepts a raw `dict` instead of a Pydantic schema. This allows any JSON field to be passed, and the code manually extracts `new_user_id` while ignoring validation.

**Refactor Recommended**:
```python
class TransferOwnershipRequest(BaseModel):
    new_user_id: int = Field(..., gt=0)

@router.put("/api/contacts/{id}/transfer-ownership")
def transfer_ownership(
    id: int,
    data: TransferOwnershipRequest,  # Use schema
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_or_moderator),
):
    new_user = db.query(User).filter(User.id == data.new_user_id).first()
    ...
```

---

## Issue #3: N+1 Query Pattern in Reviews List

**Severity**: High

**Vector**: Performance degradation (DoS vector)

**Description**: `list_reviews` in `backend/app/routes/reviews.py` executes 1 query for reviews + 2 queries per review (user + reply_user). With 100 reviews, this becomes 201 queries.

**Refactor Recommended**:
```python
from sqlalchemy.orm import joinedload

query = (
    db.query(Review)
    .options(joinedload(Review.user), joinedload(Review.reply_user_rel))
    .filter(Review.contact_id == contact_id, Review.is_approved == True)
)
```

---

## Issue #4: Public Export Endpoint Without Rate Limiting

**Severity**: High

**Vector**: Data exfiltration

**Description**: `/api/contacts/export` is public (no auth required) and has no rate limiting. Anyone can download the entire contacts database as CSV/JSON without restriction.

**Refactor Recommended**:
```python
@router.get("/api/contacts/export")
@limiter.limit("10/minute")  # Add rate limiting
def export_contacts(request: Request, ...):
    ...
```

---

## Issue #5: get_current_user_optional Queries DB on Every Request

**Severity**: Medium

**Vector**: Performance + DoS

**Description**: Even when no Authorization header is present, the function still creates a DB session. Combined with high traffic, this creates unnecessary database connections.

**Refactor Recommended**:
```python
def get_current_user_optional(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        return None  # Early return without DB query
    ...
```

---

## Issue #6: update_schedules Uses Raw list[dict] Without Validation

**Severity**: Medium

**Vector**: Arbitrary data injection

**Description**: The endpoint accepts `list[dict]` with no schema validation. Invalid `day_of_week` values are silently skipped with `continue` instead of returning an error.

**Refactor Recommended**:
```python
class ScheduleEntry(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    open_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    close_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")

@router.put("/api/contacts/{id}/schedules")
def update_schedules(id: int, data: list[ScheduleEntry], ...):
    ...
```

---

## Issue #7: edit_contact Passes None as user_id to save_history

**Severity**: Medium

**Vector**: Data integrity

**Description**: When `current_user=None` (anonymous edit), `save_history` is called with `user_id=None`. The ContactHistory model allows NULL user_id via FK, but this creates orphaned history records.

**Refactor Recommended**:
```python
# In edit_contact, when user is None, use a system user ID or skip history
history_user_id = current_user.id if current_user else None
if history_user_id:
    save_history(db, contact_id, history_user_id, field, old_val, new_val)
```

---

## Issue #8: approve_review Has Double db.commit()

**Severity**: Medium

**Vector**: Data inconsistency

**Description**: `approve_review` calls `db.commit()` twice — once for approval, once for rating recalculation. If the system crashes between commits, the review is approved but rating is not updated.

**Refactor Recommended**:
```python
review.is_approved = True
review.approved_by = user.id
review.approved_at = datetime.now(timezone.utc)

recalculate_rating(db, review.contact_id)  # Updates contact in same session

db.commit()  # Single commit for both operations
db.refresh(review)
```

---

## Issue #9: No Validation of day_of_week in update_schedules

**Severity**: Low

**Vector**: UX issue / silent data loss

**Description**: Invalid `day_of_week` values (e.g., 7, -1, "monday") are silently skipped with `continue`. The user receives a success message but their data is not saved.

**Refactor Recommended**: Use Pydantic schema with `Field(..., ge=0, le=6)` validation (see Issue #6).

---

## Issue #10: Path Traversal in serve_html Not Fully Protected

**Severity**: Medium

**Vector**: Information disclosure

**Description**: The `serve_html` function uses `is_relative_to` to validate paths, but query parameters in `/edit?page=../../etc/passwd` could potentially bypass validation if not properly sanitized.

**Refactor Recommended**:
```python
ALLOWED_PAGES = {"profile", "add", "edit", "login", "register", "dashboard",
                 "history", "pending", "search", "admin_reviews", "admin_reports",
                 "admin_analytics", "admin_utilities", "admin_users"}

if page not in ALLOWED_PAGES:
    raise HTTPException(status_code=404, detail="Page not found")
```

---

## Summary

| Severity | Count | Issues |
|----------|-------|--------|
| Critical | 1 | #1 (bootstrap-admin no rate limit) |
| High | 3 | #2 (transfer-ownership raw dict), #3 (N+1 reviews), #4 (export sin rate limit) |
| Medium | 5 | #5 (DB query sin auth), #6 (schedules raw dict), #7 (None user_id), #8 (double commit), #10 (path traversal) |
| Low | 1 | #9 (day_of_week validation) |

**Total**: 10 issues identified
