"""Migration script for AgendaZonal v3 — Competitive improvements.

Run: python migrate_v3.py
Safe to run multiple times.
"""
import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent / "database" / "agenda.db"


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[áàä]', 'a', text)
    text = re.sub(r'[éèë]', 'e', text)
    text = re.sub(r'[íìï]', 'i', text)
    text = re.sub(r'[óòö]', 'o', text)
    text = re.sub(r'[úùü]', 'u', text)
    text = re.sub(r'ñ', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def migrate():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("=== AgendaZonal v3 Migration ===\n")

    # --- contacts: new columns ---
    cursor.execute("PRAGMA table_info(contacts)")
    columns = [row[1] for row in cursor.fetchall()]

    alters = []
    if "instagram" not in columns:
        alters.append("ALTER TABLE contacts ADD COLUMN instagram VARCHAR(100)")
    if "facebook" not in columns:
        alters.append("ALTER TABLE contacts ADD COLUMN facebook VARCHAR(255)")
    if "about" not in columns:
        alters.append("ALTER TABLE contacts ADD COLUMN about TEXT")
    if "slug" not in columns:
        alters.append("ALTER TABLE contacts ADD COLUMN slug VARCHAR(200)")

    for sql in alters:
        cursor.execute(sql)
        print(f"  + {sql}")
    if not alters:
        print("  contacts: new columns already exist")

    # Generate slugs for existing contacts
    cursor.execute("SELECT id, name FROM contacts WHERE slug IS NULL OR slug = ''")
    for row in cursor.fetchall():
        slug = slugify(row[1])
        # Ensure uniqueness by appending id
        slug = f"{slug}-{row[0]}"
        cursor.execute("UPDATE contacts SET slug = ? WHERE id = ?", (slug, row[0]))
    print("  + Generated slugs for existing contacts")

    # --- new tables ---
    tables = [row[0] for row in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    # contact_photos
    if "contact_photos" not in tables:
        cursor.execute("""
            CREATE TABLE contact_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                photo_path VARCHAR(500) NOT NULL,
                caption VARCHAR(200),
                sort_order INTEGER DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX idx_photos_contact_order ON contact_photos(contact_id, sort_order)")
        print("  + Created table: contact_photos")
    else:
        print("  contact_photos: table already exists")

    # schedules
    if "schedules" not in tables:
        cursor.execute("""
            CREATE TABLE schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                day_of_week INTEGER NOT NULL CHECK(day_of_week >= 0 AND day_of_week <= 6),
                open_time VARCHAR(5),
                close_time VARCHAR(5)
            )
        """)
        cursor.execute("CREATE INDEX idx_schedules_contact ON schedules(contact_id, day_of_week)")
        print("  + Created table: schedules")
    else:
        print("  schedules: table already exists")

    conn.commit()
    conn.close()
    print("\n=== Migration complete ===")


if __name__ == "__main__":
    migrate()
