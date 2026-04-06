import sqlite3
import os

db_path = "database/agenda.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} no existe.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("""
        SELECT u.username, s.id, s.endpoint, s.created_at 
        FROM push_subscriptions s 
        JOIN users u ON s.user_id = u.id 
        ORDER BY s.id DESC 
        LIMIT 10;
    """)
    rows = cursor.fetchall()
    print("Ultimas suscripciones:")
    for row in rows:
        print(f"User: {row[0]}, ID: {row[1]}, Endpoint: {row[2][:50]}..., Created: {row[3]}")
    
    if not rows:
        print("No hay suscripciones en la tabla push_subscriptions.")
except Exception as e:
    print(f"Error al consultar: {e}")
finally:
    conn.close()
