"""Admin router — reports, analytics, utilities."""
import csv
import io
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.database import get_db
from app.models.report import Report
from app.models.contact import Contact
from app.models.lead_event import LeadEvent
from app.models.review import Review
from app.models.user import User
from app.models.utility_item import UtilityItem
from app.schemas.report import ReportCreate, ReportResponse
from app.schemas.utility import UtilityItemCreate, UtilityItemResponse
from app.auth import get_current_user
from app.routes.notifications import send_push_to_roles, send_push_to_zone

router = APIRouter(tags=["admin"])

AUTO_FLAG_THRESHOLD = 3  # Reports from distinct users to auto-flag


# ---------------------------------------------------------------------------
# Reports (crowdsourced)
# ---------------------------------------------------------------------------

@router.post("/api/contacts/{contact_id}/report", status_code=201)
def report_contact(
    contact_id: int,
    data: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Report a contact. AUTO-FLAGS at 3 distinct reports."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    # Can't report yourself
    if contact.user_id == user.id:
        raise HTTPException(status_code=400, detail="No puedes reportar tu propio contacto")

    # Check for existing report
    existing = db.query(Report).filter(
        Report.contact_id == contact_id,
        Report.user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ya has reportado este contacto")

    report = Report(
        contact_id=contact_id,
        user_id=user.id,
        reason=data.reason,
        details=data.details,
    )
    db.add(report)
    db.flush()

    # Auto-flag check
    unresolved_count = (
        db.query(sqlfunc.count(sqlfunc.distinct(Report.user_id)))
        .filter(
            Report.contact_id == contact_id,
            Report.is_resolved == False,
        )
        .scalar() or 0
    )
    if unresolved_count >= AUTO_FLAG_THRESHOLD:
        contact.status = "flagged"

    db.commit()

    # Notify admins and moderators
    send_push_to_roles(
        db=db,
        roles=["admin", "moderator"],
        title="⚠️ Contacto Reportado",
        body=f"El contacto '{contact.name}' ha recibido un reporte. Total: {unresolved_count}.",
        url="/admin/reports"
    )

    return {"message": "Reporte registrado", "reports_count": unresolved_count}


@router.get("/api/admin/reports/flagged")
def list_flagged_contacts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List flagged contacts with their reports (mod/admin only)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    flagged = db.query(Contact).filter(Contact.status == "flagged").all()
    result = []
    for contact in flagged:
        reports = (
            db.query(Report)
            .filter(Report.contact_id == contact.id, Report.is_resolved == False)
            .all()
        )
        report_list = []
        for r in reports:
            reporter = db.query(User).filter(User.id == r.user_id).first()
            report_list.append({
                "id": r.id,
                "reason": r.reason,
                "details": r.details,
                "reporter": reporter.username if reporter else "Anónimo",
                "created_at": r.created_at,
            })
        result.append({
            "contact_id": contact.id,
            "contact_name": contact.name,
            "contact_city": contact.city,
            "reports": report_list,
            "reports_count": len(report_list),
        })

    return {"flagged": result, "total": len(result)}


@router.get("/api/admin/reports/pending")
def list_pending_reports(
    threshold: int = Query(1, ge=1),
    status: str = Query("all", pattern="^(all|active|flagged|suspended)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all contacts with unresolved reports, with filters (mod/admin only)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    # Get all contacts with unresolved reports
    contacts_with_reports = (
        db.query(Contact)
        .join(Report, Contact.id == Report.contact_id)
        .filter(Report.is_resolved == False)
        .distinct()
    )

    # Filter by status
    if status != "all":
        contacts_with_reports = contacts_with_reports.filter(Contact.status == status)

    contacts = contacts_with_reports.all()

    result = []
    for contact in contacts:
        reports = (
            db.query(Report)
            .filter(Report.contact_id == contact.id, Report.is_resolved == False)
            .all()
        )

        # Filter by threshold
        if len(reports) < threshold:
            continue

        report_list = []
        for r in reports:
            reporter = db.query(User).filter(User.id == r.user_id).first()
            report_list.append({
                "id": r.id,
                "reason": r.reason,
                "details": r.details,
                "reporter": reporter.username if reporter else "Anónimo",
                "created_at": r.created_at,
            })
        result.append({
            "contact_id": contact.id,
            "contact_name": contact.name,
            "contact_city": contact.city,
            "contact_status": contact.status,
            "reports": report_list,
            "reports_count": len(report_list),
        })

    return {"pending": result, "total": len(result), "threshold": threshold, "status_filter": status}


@router.post("/api/admin/reports/{report_id}/resolve")
def resolve_report(
    report_id: int,
    action: str = Query(..., pattern="^(reactivate|suspend|delete)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resolve a report: reactivate, suspend, or delete contact (mod/admin)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    contact = db.query(Contact).filter(Contact.id == report.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    # Resolve ALL reports for this contact
    db.query(Report).filter(
        Report.contact_id == contact.id,
        Report.is_resolved == False,
    ).update({
        "is_resolved": True,
        "resolved_by": user.id,
        "resolved_at": datetime.now(timezone.utc),
    })

    # Apply action
    if action == "reactivate":
        contact.status = "active"
    elif action == "suspend":
        contact.status = "suspended"
    elif action == "delete":
        contact.status = "suspended"  # Soft suspend, admin can hard-delete separately

    db.commit()
    return {"message": f"Contacto {action}", "contact_id": contact.id, "new_status": contact.status}


@router.get("/api/admin/contacts")
def list_admin_contacts(
    status: str = Query("pending", pattern="^(all|active|flagged|suspended|pending)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List contacts by status for admin management (mod/admin only)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    query = db.query(Contact)
    if status != "all":
        query = query.filter(Contact.status == status)

    total = query.count()
    contacts = query.order_by(Contact.updated_at.desc()).offset(skip).limit(limit).all()

    result = []
    for c in contacts:
        owner = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "city": c.city,
            "status": c.status,
            "category_id": c.category_id,
            "description": c.description,
            "photo_path": c.photo_path,
            "owner": owner.username if owner else "N/A",
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        })

    return {"contacts": result, "total": total, "status_filter": status}


@router.put("/api/admin/contacts/{contact_id}/status")
def update_contact_status(
    contact_id: int,
    new_status: str = Query(..., pattern="^(active|suspended|flagged|pending)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update contact status directly (mod/admin only)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    contact.status = new_status
    db.commit()
    return {"message": f"Estado actualizado a {new_status}", "contact_id": contact.id, "new_status": new_status}


# ---------------------------------------------------------------------------
# Analytics + CSV Export
# ---------------------------------------------------------------------------

@router.get("/api/admin/analytics")
def get_analytics(
    zone: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get analytics by zone (mod/admin only)."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    # Date range
    if date_from:
        dt_from = datetime.fromisoformat(date_from)
    else:
        dt_from = datetime.now(timezone.utc) - timedelta(days=30)
    if date_to:
        dt_to = datetime.fromisoformat(date_to)
    else:
        dt_to = datetime.now(timezone.utc)

    # Base query filter
    contact_filter = Contact.status != "suspended"
    if zone:
        contact_filter = (contact_filter) & (
            (Contact.city.ilike(f"%{zone}%")) | (Contact.neighborhood.ilike(f"%{zone}%"))
        )

    # Counts
    contacts_q = db.query(Contact).filter(contact_filter)
    total_providers = contacts_q.count()
    active_providers = contacts_q.filter(Contact.status == "active").count()

    contact_ids = [c.id for c in contacts_q.all()]
    if contact_ids:
        total_leads = (
            db.query(sqlfunc.count(LeadEvent.id))
            .filter(
                LeadEvent.contact_id.in_(contact_ids),
                LeadEvent.created_at >= dt_from,
                LeadEvent.created_at <= dt_to,
            )
            .scalar() or 0
        )
        total_reviews = (
            db.query(sqlfunc.count(Review.id))
            .filter(
                Review.contact_id.in_(contact_ids),
                Review.created_at >= dt_from,
                Review.created_at <= dt_to,
            )
            .scalar() or 0
        )
        avg_rating = (
            db.query(sqlfunc.avg(Contact.avg_rating))
            .filter(Contact.id.in_(contact_ids), Contact.avg_rating > 0)
            .scalar() or 0
        )
    else:
        total_leads = 0
        total_reviews = 0
        avg_rating = 0

    # Top categories
    from app.models.category import Category
    top_cats = (
        db.query(Category.name, sqlfunc.count(Contact.id).label("count"))
        .join(Contact, Contact.category_id == Category.id)
        .filter(Contact.id.in_(contact_ids) if contact_ids else False)
        .group_by(Category.name)
        .order_by(sqlfunc.count(Contact.id).desc())
        .limit(5)
        .all()
    )

    # Leads by day
    leads_by_day = []
    for i in range(7):
        day = dt_to - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = 0
        if contact_ids:
            count = (
                db.query(sqlfunc.count(LeadEvent.id))
                .filter(
                    LeadEvent.contact_id.in_(contact_ids),
                    LeadEvent.created_at >= day_start,
                    LeadEvent.created_at < day_end,
                )
                .scalar() or 0
            )
        leads_by_day.append({"date": day_start.strftime("%d/%m"), "count": count})
    leads_by_day.reverse()

    return {
        "zone": zone or "Todas",
        "period": {"from": dt_from.isoformat(), "to": dt_to.isoformat()},
        "total_providers": total_providers,
        "active_providers": active_providers,
        "total_leads": total_leads,
        "total_reviews": total_reviews,
        "avg_rating": round(float(avg_rating), 1),
        "top_categories": [{"name": c[0], "count": c[1]} for c in top_cats],
        "leads_by_day": leads_by_day,
    }


@router.get("/api/admin/analytics/export")
def export_analytics(
    zone: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export analytics as CSV."""
    if user.role not in ['moderator', 'admin']:
        raise HTTPException(status_code=403, detail="Requiere rol de moderador o admin")

    query = db.query(Contact).filter(Contact.status != "suspended")
    if zone:
        query = query.filter(
            (Contact.city.ilike(f"%{zone}%")) | (Contact.neighborhood.ilike(f"%{zone}%"))
        )

    contacts = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "nombre", "ciudad", "barrio", "categoria_id",
        "rating_promedio", "cant_reseñas", "nivel_verificación", "estado"
    ])
    for c in contacts:
        writer.writerow([
            c.id, c.name, c.city, c.neighborhood, c.category_id,
            c.avg_rating, c.review_count, c.verification_level, c.status
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )


# ---------------------------------------------------------------------------
# Utilities (barrio services)
# ---------------------------------------------------------------------------

@router.get("/api/utilities", response_model=list[UtilityItemResponse])
def list_utilities(
    type: str | None = None,
    db: Session = Depends(get_db),
):
    """List active utilities (public)."""
    query = db.query(UtilityItem).filter(UtilityItem.is_active == True)
    if type:
        query = query.filter(UtilityItem.type == type)
    return query.order_by(UtilityItem.name).all()


@router.post("/api/admin/utilities", response_model=UtilityItemResponse, status_code=201)
def create_utility(
    data: UtilityItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a utility item (admin/moderator)."""
    if user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Requiere rol de admin o moderador")

    # Extract notification message and remove it from model creation
    notif_msg = data.notification_message
    item_data = data.model_dump()
    item_data.pop("notification_message", None)

    item = UtilityItem(**item_data, created_by=user.id)
    db.add(item)
    db.commit()
    db.refresh(item)

    # Trigger emergency broadcast if priority
    if item.is_priority:
        push_title = f"🚨 Alerta: {item.name}"
        push_body = notif_msg if notif_msg else f"Nueva alerta de utilidad en {item.city or 'la zona'}."
        send_push_to_zone(
            db=db,
            title=push_title,
            body=push_body,
            city=item.city,
            url="/admin/utilities"
        )

    return item


@router.put("/api/admin/utilities/{utility_id}", response_model=UtilityItemResponse)
def update_utility(
    utility_id: int,
    data: UtilityItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a utility item (admin/moderator)."""
    if user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Requiere rol de admin")

    item = db.query(UtilityItem).filter(UtilityItem.id == utility_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Utilidad no encontrada")

    # Update fields excluding notification_message
    update_data = data.model_dump()
    update_data.pop("notification_message", None)

    for key, value in update_data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/api/admin/utilities/{utility_id}", status_code=204)
def delete_utility(
    utility_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete a utility item (admin/moderator)."""
    if user.role not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="Requiere rol de admin")

    item = db.query(UtilityItem).filter(UtilityItem.id == utility_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Utilidad no encontrada")

    item.is_active = False
    db.commit()
    return None
