import logging
import shutil
from pathlib import Path
import os
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy.orm import Session
from app.routes import auth, categories, contacts, users, notifications, reviews, offers, provider, admin
from app.database import engine, get_db
from app.rate_limit import limiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agenda de la zona API",
    version="1.0.0",
    description="API para agenda de la zona de servicios",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)


# Security headers middleware (custom implementation)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # SEC-02: X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # SEC-03: X-Frame-Options (prevents clickjacking)
        response.headers["X-Frame-Options"] = "DENY"
        
        # SEC-04: Strict-Transport-Security (only if HTTPS)
        # Note: Enable in production with proper HTTPS setup
        from app.config import HTTPS
        if HTTPS:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # SEC-05: Referrer-Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content-Security-Policy (restrictive for production)
        # Local CSS/JS served from same origin, external resources for maps
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; "
            "style-src-elem 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com https://*.openstreetmap.org; "
            "connect-src 'self' http://localhost:* http://127.0.0.1:* https://*.tile.openstreetmap.org https://*.openstreetmap.org https://unpkg.com; "
            "font-src 'self';"
        )
        
        # Overwrite server header to prevent information disclosure
        # (starlette doesn't expose pop for MutableHeaders)
        
        return response


app.add_middleware(SecurityHeadersMiddleware)


# X-RateLimit headers middleware
class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Add X-RateLimit headers to API responses for client awareness."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only add headers to API responses
        if request.url.path.startswith("/api/"):
            response.headers["X-RateLimit-Limit"] = "60"
            response.headers["X-RateLimit-Remaining"] = "-"  # SlowAPI tracks internally
            response.headers["X-RateLimit-Reset"] = "60"

        return response


app.add_middleware(RateLimitHeadersMiddleware)

# CORS configuration - restrict to specific origins (needed by exception handlers)
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1,http://localhost:8000,http://127.0.0.1:8000").split(",")]


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
    origin = request.headers.get("origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    origin = request.headers.get("origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(contacts.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(reviews.router)
app.include_router(offers.router)
app.include_router(provider.router)
app.include_router(admin.router)


# Public endpoint for user dropdowns (no auth required)
@app.get("/api/public/users")
def list_active_users_public(db: Session = Depends(get_db)):
    """List active users (public, for dropdowns)."""
    from app.models.user import User
    users = db.query(User.id, User.username).filter(User.is_active == True).order_by(User.username).all()
    return [{"id": u.id, "username": u.username} for u in users]


@app.on_event("startup")
async def startup_security_check():
    """Log security configuration on startup and ensure DB schema is up to date."""
    from app.config import JWT_SECRET
    from app.database import engine
    from sqlalchemy import inspect, text
    
    # Auto-migrate: add missing review reply columns
    inspector = inspect(engine)

    if "reviews" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("reviews")]
        with engine.connect() as conn:
            if "reply_text" not in columns:
                conn.execute(text("ALTER TABLE reviews ADD COLUMN reply_text TEXT"))
                conn.commit()
                logger.info("Migration: added reply_text to reviews")
            if "reply_at" not in columns:
                conn.execute(text("ALTER TABLE reviews ADD COLUMN reply_at DATETIME"))
                conn.commit()
                logger.info("Migration: added reply_at to reviews")
            if "reply_by" not in columns:
                conn.execute(text("ALTER TABLE reviews ADD COLUMN reply_by INTEGER"))
                conn.commit()
                logger.info("Migration: added reply_by to reviews")

    # Auto-migrate: create push_subscriptions table if not exists
    if "push_subscriptions" not in inspector.get_table_names():
        from app.database import Base
        from app.models.push_subscription import PushSubscription
        Base.metadata.create_all(bind=engine, tables=[PushSubscription.__table__])
        logger.info("Migration: created push_subscriptions table")
    
    from app.config import JWT_SECRET, HTTPS
    
    logger.info("=" * 50)
    logger.info("SECURITY CONFIGURATION CHECK")
    logger.info("=" * 50)
    logger.info(f"JWT_SECRET length: {len(JWT_SECRET)} bytes (min: 32)")
    logger.info(f"JWT_ISSUER: {os.getenv('JWT_ISSUER', 'agendazonal')}")
    logger.info(f"JWT_AUDIENCE: {os.getenv('JWT_AUDIENCE', 'agendazonal-api')}")
    logger.info("SQLite WAL mode: enabled")
    logger.info("Rate limiting: enabled (slowapi)")
    logger.info("Security headers: enabled")
    logger.info(f"HTTPS mode: {HTTPS}")
    if HTTPS:
        logger.info("HSTS: ENABLED (Strict-Transport-Security header active)")
    logger.info("=" * 50)
    logger.info("RECOMMENDED: Run Caddy for reverse proxy + static files:")
    logger.info("  .\\caddy\\caddy.exe run --config Caddyfile")
    logger.info("  Then open: http://localhost")
    logger.info("=" * 50)


# Serve frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "backend" / "uploads"


def serve_html(filename: str):
    file_path = (FRONTEND_DIR / filename).resolve()
    if not file_path.is_relative_to(FRONTEND_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if file_path.exists():
        return HTMLResponse(content=file_path.read_text(encoding="utf-8"), media_type="text/html")
    return {"detail": "Not Found"}


# Routes without .html
@app.get("/")
def index():
    return serve_html("index.html")

@app.get("/search")
def search_page():
    return serve_html("search.html")

@app.get("/contact-form")
def contact_form_page():
    return serve_html("contact-form.html")

@app.get("/add")
def add_page():
    return RedirectResponse("/contact-form?mode=add", status_code=301)

@app.get("/login")
def login_page():
    return serve_html("login.html")

@app.get("/register")
def register_page():
    return serve_html("register.html")

@app.get("/history")
def history_page():
    return serve_html("history.html")

@app.get("/edit")
def edit_page(request: Request):
    contact_id = request.query_params.get('id', '')
    return RedirectResponse(f"/contact-form?id={contact_id}", status_code=301)

@app.get("/pending")
def pending_page():
    return serve_html("pending.html")

@app.get("/pending/changes")
def pending_changes_page():
    return serve_html("pending-changes.html")

@app.get("/admin/users")
def admin_users_page():
    return serve_html("admin-users.html")

@app.get("/profile")
def profile_page():
    return serve_html("profile.html")

@app.get("/c/{slug}")
def profile_friendly(slug: str, db: Session = Depends(get_db)):
    """Friendly URL: /c/juan-perez-plomero-1 → redirect to /profile?id=X"""
    from app.models.contact import Contact as _Contact
    from fastapi.responses import RedirectResponse
    contact = db.query(_Contact).filter(_Contact.slug == slug).first()
    if contact:
        return RedirectResponse(url=f"/profile?id={contact.id}", status_code=301)
    raise HTTPException(status_code=404, detail="Contacto no encontrado")

@app.get("/admin/reviews")
def admin_reviews_page():
    return serve_html("admin-reviews.html")

@app.get("/dashboard")
def dashboard_page():
    return serve_html("dashboard.html")

@app.get("/admin/analytics")
def admin_analytics_page():
    return serve_html("admin-analytics.html")

@app.get("/admin/reports")
def admin_reports_page():
    return serve_html("admin-reports.html")

@app.get("/admin/utilities")
def admin_utilities_page():
    return serve_html("admin-utilities.html")

# PWA static files
@app.get("/sw.js")
def service_worker():
    path = FRONTEND_DIR / "sw.js"
    if path.exists():
        return FileResponse(str(path), media_type="application/javascript")
    raise HTTPException(status_code=404)

@app.get("/manifest.json")
def manifest():
    path = FRONTEND_DIR / "manifest.json"
    if path.exists():
        return FileResponse(str(path), media_type="application/json")
    raise HTTPException(status_code=404)

@app.get("/offline.html")
def offline_page():
    return serve_html("offline.html")

# Routes with .html
@app.get("/index.html")
def index_html():
    return serve_html("index.html")

@app.get("/search.html")
def search_html():
    return serve_html("search.html")

@app.get("/add.html")
def add_html():
    return RedirectResponse("/contact-form?mode=add", status_code=301)

@app.get("/login.html")
def login_html():
    return serve_html("login.html")

@app.get("/register.html")
def register_html():
    return serve_html("register.html")

@app.get("/history.html")
def history_html():
    return serve_html("history.html")

@app.get("/edit.html")
def edit_html(request: Request):
    contact_id = request.query_params.get('id', '')
    return RedirectResponse(f"/contact-form?id={contact_id}", status_code=301)

@app.get("/pending.html")
def pending_html():
    return serve_html("pending.html")

@app.get("/pending-changes.html")
def pending_changes_html():
    return serve_html("pending-changes.html")

@app.get("/admin-users.html")
def admin_users_html():
    return serve_html("admin-users.html")


@app.get("/health")
def health():
    checks = {"status": "ok", "checks": {}}

    # DB check
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        checks["checks"]["database"] = "ok"
    except Exception as e:
        checks["status"] = "degraded"
        checks["checks"]["database"] = f"error: {str(e)}"

    # Disk check (critical for RPi with SD card)
    try:
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (1024**3)
        checks["checks"]["disk_free_gb"] = free_gb
        if free_gb < 1:
            checks["status"] = "warning"
            checks["checks"]["disk_warning"] = "Less than 1GB free"
    except Exception:
        pass

    return checks


# Serve a simple 1x1 transparent GIF as favicon (avoids 404)
@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response
    # 1x1 transparent GIF
    return Response(
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
        media_type="image/gif"
    )


# Mount static files AFTER routes (so routes take priority)
if FRONTEND_DIR.exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    if (FRONTEND_DIR / "icons").exists():
        app.mount("/icons", StaticFiles(directory=str(FRONTEND_DIR / "icons")), name="icons")

if UPLOADS_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
