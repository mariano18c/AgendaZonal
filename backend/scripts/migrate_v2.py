"""Migration script for AgendaZonal v2 — Hiperzonal evolution.

Run: python migrate_v2.py
Safe to run multiple times (checks column existence before ALTER).
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "database" / "agenda.db"


def get_existing_columns(cursor, table):
    """Get list of column names for a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def get_existing_indexes(cursor, table):
    """Get list of index names for a table."""
    cursor.execute(f"PRAGMA index_list({table})")
    return [row[1] for row in cursor.fetchall()]


def column_exists(cursor, table, column):
    return column in get_existing_columns(cursor, table)


def index_exists(cursor, table, index_name):
    return index_name in get_existing_indexes(cursor, table)


def migrate():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run init_db.py first to create the database.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("=== AgendaZonal v2 Migration ===\n")

    # --- contacts: new columns ---
    contacts_columns = get_existing_columns(cursor, "contacts")
    alters = []

    if "avg_rating" not in contacts_columns:
        alters.append("ALTER TABLE contacts ADD COLUMN avg_rating REAL DEFAULT 0")
    if "review_count" not in contacts_columns:
        alters.append("ALTER TABLE contacts ADD COLUMN review_count INTEGER DEFAULT 0")
    if "verification_level" not in contacts_columns:
        alters.append("ALTER TABLE contacts ADD COLUMN verification_level INTEGER DEFAULT 0")
    if "status" not in contacts_columns:
        alters.append("ALTER TABLE contacts ADD COLUMN status VARCHAR(20) DEFAULT 'active'")

    for sql in alters:
        cursor.execute(sql)
        print(f"  + {sql}")

    if not alters:
        print("  contacts: all columns already exist")

    # Migrate is_verified -> verification_level
    cursor.execute(
        "UPDATE contacts SET verification_level = 1 WHERE is_verified = 1 AND verification_level = 0"
    )
    if cursor.rowcount > 0:
        print(f"  + Migrated {cursor.rowcount} verified contacts to verification_level=1")

    # --- contacts: indexes ---
    contacts_indexes = get_existing_indexes(cursor, "contacts")
    index_sqls = []

    if "idx_contacts_geo" not in contacts_indexes:
        index_sqls.append("CREATE INDEX IF NOT EXISTS idx_contacts_geo ON contacts(latitude, longitude)")
    if "idx_contacts_status" not in contacts_indexes:
        index_sqls.append("CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status)")
    if "idx_contacts_verification" not in contacts_indexes:
        index_sqls.append("CREATE INDEX IF NOT EXISTS idx_contacts_verification ON contacts(verification_level)")
    if "idx_contacts_rating" not in contacts_indexes:
        index_sqls.append("CREATE INDEX IF NOT EXISTS idx_contacts_rating ON contacts(avg_rating)")

    for sql in index_sqls:
        cursor.execute(sql)
        print(f"  + {sql}")

    if not index_sqls:
        print("  contacts: all indexes already exist")

    # --- new tables ---
    tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    # reviews
    if "reviews" not in tables:
        cursor.execute("""
            CREATE TABLE reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                comment TEXT CHECK(length(comment) <= 500),
                photo_path VARCHAR(500),
                is_approved BOOLEAN NOT NULL DEFAULT 0,
                approved_by INTEGER REFERENCES users(id),
                approved_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(contact_id, user_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_contact ON reviews(contact_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_approved ON reviews(is_approved)")
        print("  + Created table: reviews")
    else:
        print("  reviews: table already exists")

    # offers
    if "offers" not in tables:
        cursor.execute("""
            CREATE TABLE offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                description VARCHAR(500),
                discount_pct INTEGER CHECK(discount_pct >= 1 AND discount_pct <= 99),
                expires_at DATETIME NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_contact ON offers(contact_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_active ON offers(is_active, expires_at)")
        print("  + Created table: offers")
    else:
        print("  offers: table already exists")

    # lead_events
    if "lead_events" not in tables:
        cursor.execute("""
            CREATE TABLE lead_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id),
                source VARCHAR(20) NOT NULL DEFAULT 'whatsapp',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_contact ON lead_events(contact_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_date ON lead_events(created_at)")
        print("  + Created table: lead_events")
    else:
        print("  lead_events: table already exists")

    # reports
    if "reports" not in tables:
        cursor.execute("""
            CREATE TABLE reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id),
                reason VARCHAR(20) NOT NULL CHECK(reason IN ('spam', 'falso', 'inapropiado', 'cerrado')),
                details TEXT,
                is_resolved BOOLEAN NOT NULL DEFAULT 0,
                resolved_by INTEGER REFERENCES users(id),
                resolved_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(contact_id, user_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_contact ON reports(contact_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_unresolved ON reports(is_resolved)")
        print("  + Created table: reports")
    else:
        print("  reports: table already exists")

    # utility_items
    if "utility_items" not in tables:
        cursor.execute("""
            CREATE TABLE utility_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type VARCHAR(20) NOT NULL DEFAULT 'otro',
                name VARCHAR(200) NOT NULL,
                address VARCHAR(255),
                phone VARCHAR(20),
                schedule VARCHAR(200),
                lat REAL,
                lon REAL,
                city VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_by INTEGER REFERENCES users(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_utilities_type ON utility_items(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_utilities_active ON utility_items(is_active)")
        print("  + Created table: utility_items")
    else:
        print("  utility_items: table already exists")

    # notifications (may exist already)
    if "notifications" not in tables:
        cursor.execute("""
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                type VARCHAR(50) NOT NULL,
                message VARCHAR(500) NOT NULL,
                contact_id INTEGER REFERENCES contacts(id),
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
        print("  + Created table: notifications")
    else:
        print("  notifications: table already exists")

    conn.commit()
    conn.close()

    print("\n=== Migration complete ===")


if __name__ == "__main__":
    migrate()
