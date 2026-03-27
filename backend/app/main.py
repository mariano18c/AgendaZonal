from pathlib import Path
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.routes import auth, categories, contacts, users

app = FastAPI(
    title="Agenda de la zona API",
    version="1.0.0",
    description="API para agenda de la zona de servicios",
)

# CORS configuration - restrict to specific origins
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(contacts.router)
app.include_router(users.router)

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

@app.get("/add")
def add_page():
    return serve_html("add.html")

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
def edit_page():
    return serve_html("edit.html")

@app.get("/pending")
def pending_page():
    return serve_html("pending.html")

@app.get("/pending/changes")
def pending_changes_page():
    return serve_html("pending-changes.html")

@app.get("/admin/users")
def admin_users_page():
    return serve_html("admin-users.html")

# Routes with .html
@app.get("/index.html")
def index_html():
    return serve_html("index.html")

@app.get("/search.html")
def search_html():
    return serve_html("search.html")

@app.get("/add.html")
def add_html():
    return serve_html("add.html")

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
def edit_html():
    return serve_html("edit.html")

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
    return {"status": "ok"}


# Mount static files AFTER routes (so routes take priority)
if FRONTEND_DIR.exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")

if UPLOADS_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
