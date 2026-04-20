"""Migration script for AgendaZonal v4 — Emergency Mode.

Run: python scripts/migrate_v4.py
Safe to run multiple times.
"""
import sqlite3
from pathlib import Path

# DB_PATH relative to the root of the project (backend/)
DB_PATH = Path(__file__).parent.parent / "database" / "agenda.db"


def migrate():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("=== AgendaZonal v4 Migration ===\n")

    # --- utility_items: new columns ---
    cursor.execute("PRAGMA table_info(utility_items)")
    utility_columns = [row[1] for row in cursor.fetchall()]

    if "is_priority" not in utility_columns:
        cursor.execute("ALTER TABLE utility_items ADD COLUMN is_priority BOOLEAN DEFAULT 0 NOT NULL")
        print("  + utility_items: Added column is_priority")
    else:
        print("  utility_items: is_priority already exists")

    # --- push_subscriptions: new columns ---
    cursor.execute("PRAGMA table_info(push_subscriptions)")
    push_columns = [row[1] for row in cursor.fetchall()]

    push_alters = []
    if "latitude" not in push_columns:
        push_alters.append("ALTER TABLE push_subscriptions ADD COLUMN latitude FLOAT")
    if "longitude" not in push_columns:
        push_alters.append("ALTER TABLE push_subscriptions ADD COLUMN longitude FLOAT")
    if "city" not in push_columns:
        push_alters.append("ALTER TABLE push_subscriptions ADD COLUMN city VARCHAR(100)")

    for sql in push_alters:
        cursor.execute(sql)
        print(f"  + push_subscriptions: {sql.split('ADD COLUMN ')[1]} added")

    if push_alters:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_push_city ON push_subscriptions(city)")
        print("  + push_subscriptions: Created index on city")
    else:
        print("  push_subscriptions: location columns already exist")

    conn.commit()
    conn.close()
    print("\n=== Migration complete ===")


if __name__ == "__main__":
    migrate()
