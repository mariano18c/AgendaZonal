from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.category import Category
from app.models.contact import Contact, ContactHistory
from app.models.contact_change import ContactChange
from app.models.notification import Notification
from app.models.review import Review
from app.models.offer import Offer
from app.models.lead_event import LeadEvent
from app.models.report import Report
from app.models.utility_item import UtilityItem


CATEGORIES = [
    (100, "Plomero/a", "wrench", "Plomería y gas"),
    (101, "Gasista", "fire", "Instalaciones de gas"),
    (102, "Electricista", "zap", "Instalaciones eléctricas"),
    (103, "Peluquería/Barbería", "scissors", "Servicios de peluquería"),
    (104, "Albañil", "hard-hat", "Construcción"),
    (105, "Pintor", "paintbrush", "Pintura"),
    (106, "Carpintero/a", "hammer", "Carpintería"),
    (107, "Supermercado", "shopping-cart", "Alimentos"),
    (108, "Carnicería", "beef", "Carnes"),
    (109, "Verdulería", "apple", "Frutas y verduras"),
    (110, "Panadería", "bread", "Pan y pastelería"),
    (111, "Tienda de ropa", "shirt", "Indumentaria"),
    (112, "Farmacia", "pill", "Medicamentos"),
    (113, "Librería", "book", "Libros y útiles"),
    (114, "Bar", "beer", "Bebidas y comidas"),
    (115, "Restaurant", "utensils", "Gastronomía"),
    (116, "Club", "music", "Entretenimiento"),
    (117, "Bazar", "gift", "Artículos varios"),
    (118, "Veterinaria", "cat", "Salud animal"),
    (119, "Ferretería", "tool", "Herramientas"),
    (120, "Kiosco", "store", "Kioskos"),
    (121, "Juguetería", "toy", "Juguetes"),
    (122, "Polirrubro", "grid", "Varios"),
    (123, "Cuidado de personas", "heart", "Cuidado personal y salud"),
    (124, "Alquiler", "home", "Alquiler de inmuebles"),
    (999, "Otro", "more-horizontal", "Otros servicios"),
]


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def init_categories():
    db = SessionLocal()
    try:
        for code, name, icon, desc in CATEGORIES:
            existing = db.query(Category).filter(Category.code == code).first()
            if not existing:
                cat = Category(code=code, name=name, icon=icon, description=desc)
                db.add(cat)
        db.commit()
        print(f"Categories initialized: {len(CATEGORIES)} categories")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    init_categories()
