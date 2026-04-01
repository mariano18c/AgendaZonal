from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Enable foreign keys, WAL mode, and busy timeout for SQLite.
    
    Optimizations for production:
    - WAL mode: Better concurrency for reads/writes
    - busy_timeout: Wait up to 5s instead of failing immediately
    - cache_size: 20MB cache (negative = KB)
    - synchronous: NORMAL for better performance (still safe with WAL)
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA cache_size=-20000")  # 20MB
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
