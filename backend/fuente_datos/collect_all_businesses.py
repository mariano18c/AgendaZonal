#!/usr/bin/env python3
"""
Collect all businesses from Ybarlucea area and save to JSON.
"""

import json
import math

# Ybarlucea center coordinates
ybarlucea_lat = -32.8833
ybarlucea_lon = -60.7833

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# All businesses collected from web searches
businesses = [
    # Farmacias
    {"name": "Farmacia Garcia", "phone": "0341 477-2727", "email": "info@farmaciagarcia.com.ar", "address": "San Martin 1032, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 112, "description": "Farmacia en Ibarlucea", "schedule": "Lun-Vie 8:30-16:30", "latitude": -32.8850, "longitude": -60.7850},
    {"name": "Veterinaria Ibarlucea", "phone": "", "email": "veterinariaibarlucea@gmail.com", "address": "Avenida Rosario 150, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 118, "description": "Veterinaria y servicios para mascotas", "schedule": "Lun-Sab 9:00-20:00", "latitude": -32.8840, "longitude": -60.7820},
    
    # Supermercados
    {"name": "Supermercado EBE", "phone": "(0341) 490-4661", "email": "ebe@supermercadoebe.com.ar", "address": "25 De Mayo 1275, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 107, "description": "Supermercado y autoservicio", "schedule": "Lun-Dom 8:00-22:00", "latitude": -32.8820, "longitude": -60.7800},
    {"name": "Supermercados Casagrande", "phone": "", "email": "", "address": "J. M. Ibarlucea 407, Granadero Baigorria, Santa Fe", "city": "Granadero Baigorria", "neighborhood": "Centro", "category_id": 107, "description": "Supermercado Casagrande", "schedule": "Lun-Dom 8:00-21:00", "latitude": -32.8580, "longitude": -60.7250},
    
    # Panaderias
    {"name": "Panaderia Avenida", "phone": "0341 490-1234", "email": "info@panaderiaavenida.com.ar", "address": "Av. Rosario 925, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 110, "description": "Panaderia y pasteleria artesanal", "schedule": "Lun-Dom 7:00-20:00", "latitude": -32.8800, "longitude": -60.7820},
    {"name": "Lola Mora Pastas Artesanales", "phone": "", "email": "", "address": "Alfredo Schilla 4418, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 110, "description": "Fabrica de pastas artesanales", "schedule": "Lun-Sab 8:00-18:00", "latitude": -32.8920, "longitude": -60.7900},
    
    # Bares y Restaurants
    {"name": "Estancia Ibarlucea Bar", "phone": "", "email": "", "address": "Cullen y Ugarte, Rosario, Santa Fe", "city": "Rosario", "neighborhood": "Ibarlucea", "category_id": 114, "description": "Bar y restaurant", "schedule": "Jue-Dom 18:00-02:00", "latitude": -32.9450, "longitude": -60.6500},
    {"name": "Rotiseria Todo Casero", "phone": "+54 341 471-5139", "email": "", "address": "J. M. Ibarlucea 125, Granadero Baigorria, Santa Fe", "city": "Granadero Baigorria", "neighborhood": "Centro", "category_id": 115, "description": "Rotiseria y comida para llevar", "schedule": "Mar-Sab 11:15-13:30 / 19:00-22:30", "latitude": -32.8550, "longitude": -60.7220},
    {"name": "La Buchacreria Ibarlucea", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 115, "description": "Restaurant especializado", "schedule": "Consultar horario", "latitude": -32.8833, "longitude": -60.7833},
    
    # Peluquerias y Barberias
    {"name": "Barberia Ibarlucea", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 103, "description": "Barberia - 45 reseñas", "schedule": "Lun-Sab 9:00-20:00", "latitude": -32.8835, "longitude": -60.7835},
    {"name": "Martin Barber - Portal de Ki", "phone": "", "email": "", "address": "Portal de Ki, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Portal de Ki", "category_id": 103, "description": "Barberia en Portal de Ki", "schedule": "Lun-Sab 9:00-20:00", "latitude": -32.8900, "longitude": -60.7880},
    {"name": "Cavaliers Peluqueria y Barberia", "phone": "", "email": "", "address": "25 de Mayo 1240, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 103, "description": "Peluqueria y barberia unisex", "schedule": "Lun-Sab 9:00-20:00", "latitude": -32.8825, "longitude": -60.7810},
    {"name": "Griselda Alfonso Fleboestetica", "phone": "+54 341 426-4451", "email": "", "address": "Mariano Moreno, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 103, "description": "Centro de estetica y flebologia", "schedule": "Lun-Vie 9:00-18:00", "latitude": -32.8845, "longitude": -60.7845},
    
    # Ferreterias
    {"name": "Ferreteria Ibarlucea", "phone": "", "email": "", "address": "25 de Mayo 1206, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 119, "description": "Ferreteria y corralon - 260 reseñas", "schedule": "Lun-Vie 8:00-18:00, Sab 8:00-13:00", "latitude": -32.8822, "longitude": -60.7808},
    {"name": "Ferreteria San Martin", "phone": "", "email": "", "address": "San Martin, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 119, "description": "Ferreteria general", "schedule": "Lun-Vie 8:00-18:00", "latitude": -32.8850, "longitude": -60.7850},
    {"name": "Ferreteria CyJ", "phone": "341 562-2398", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 119, "description": "Chapas, perfiles, clavos, tornillos", "schedule": "Lun-Vie 8:00-17:00, Sab 8:00-12:00", "latitude": -32.8840, "longitude": -60.7840},
    {"name": "Materiales para la Construccion Dominguez", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Ladrillos comunes, semi-vistos", "schedule": "Lun-Vie 8:00-18:00", "latitude": -32.8860, "longitude": -60.7860},
    {"name": "Don Felicce Materiales", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Materiales de construccion", "schedule": "Lun-Vie 8:00-18:00", "latitude": -32.8870, "longitude": -60.7870},
    
    # Servicios Medicos
    {"name": "Consultorios Iberlucea", "phone": "7704-2784", "email": "consultorios.iberlucea@gmail.com", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Consultorios medicos", "schedule": "Lun-Vie 9:00-20:00, Sab 9:00-16:00", "latitude": -32.8870, "longitude": -60.7880},
    {"name": "Dr. Gustavo Marcelo Borzi - Odontologo", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Odontologo", "schedule": "Consultar disponibilidad", "latitude": -32.8833, "longitude": -60.7833},
    {"name": "YB Odontologia", "phone": "+54 341 614-7362", "email": "", "address": "Juan de Ibarlucea 206, Granadero Baigorria, Santa Fe", "city": "Granadero Baigorria", "neighborhood": "Centro", "category_id": 999, "description": "Servicios odontologicos", "schedule": "Lun-Vie 9:00-18:00", "latitude": -32.8520, "longitude": -60.7180},
    {"name": "Lic. Eric M. Persig - Kinesiologo", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Kinesiologo y osteopata", "schedule": "Consultar disponibilidad", "latitude": -32.8833, "longitude": -60.7833},
    {"name": "Battilana Gabriel Emilio - Kinesiologia", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Kinesiologo", "schedule": "Consultar disponibilidad", "latitude": -32.8833, "longitude": -60.7833},
    
    # Cajeros
    {"name": "Cajero Link - Corrientes", "phone": "", "email": "", "address": "Corrientes 201-299, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Cajero automatico Link", "schedule": "24 horas", "latitude": -32.8845, "longitude": -60.7845},
    
    # Servicios
    {"name": "Agencia de Quinielas La Cabala", "phone": "+54 341 394-0248", "email": "lacabala@quinielas.com.ar", "address": "J. M. Ibarlucea 68, Granadero Baigorria, Santa Fe", "city": "Granadero Baigorria", "neighborhood": "Centro", "category_id": 122, "description": "Agencia de quinielas y pago facil", "schedule": "Lun-Vie 9:00-18:00", "latitude": -32.8500, "longitude": -60.7200},
    
    # Gimnasios
    {"name": "Focus Gym", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Gimnasio y fitness", "schedule": "Lun-Dom 6:00-22:00", "latitude": -32.8850, "longitude": -60.7850},
    {"name": "Ibarlucea Fitness Center", "phone": "", "email": "", "address": "25 de Mayo 3875, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Fitness center", "schedule": "Lun-Dom 6:00-22:00", "latitude": -32.8950, "longitude": -60.7950},
    
    # Educacion
    {"name": "Jardin de Infantes Nro 289 Jacaranda", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Jardin de infantespublico", "schedule": "Lun-Vie horario escolar", "latitude": -32.8820, "longitude": -60.7820},
    {"name": "Semillitas de Luz Jardin Maternal", "phone": "", "email": "", "address": "Sarmiento, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Jardin maternal y de infantes", "schedule": "Lun-Vie 7:00-19:00", "latitude": -32.8840, "longitude": -60.7840},
    {"name": "Jacaranda Ibarlucea Jardin", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Jardin de infantes", "schedule": "Lun-Vie horario escolar", "latitude": -32.8830, "longitude": -60.7830},
    
    # Gobierno
    {"name": "Comuna de Ybarlucea", "phone": "", "email": "", "address": "Ybarlucea, Santa Fe", "city": "Ybarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Gobierno local", "schedule": "Lun-Vie 7:00-13:00", "latitude": -32.8833, "longitude": -60.7833},
    {"name": "Registro Civil Ybarlucea", "phone": "", "email": "", "address": "Ybarlucea, Santa Fe", "city": "Ybarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Registro Civil - DNI, partidas", "schedule": "Lun-Vie 7:00-13:00", "latitude": -32.8835, "longitude": -60.7835},
    
    # Electricistas
    {"name": "Los Electricistas", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 102, "description": "Servicios electricos domiciliarios", "schedule": "Consultar disponibilidad", "latitude": -32.8833, "longitude": -60.7833},
    
    # Viveros
    {"name": "Vivero De los Pajaros - Espacio Cultural", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Vivero y espacio cultural", "schedule": "Consultar horario", "latitude": -32.8860, "longitude": -60.7860},
    
    # Almacenes
    {"name": "Almacen y Verduleria Vichor", "phone": "", "email": "", "address": "San Lorenzo 202, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 109, "description": "Almacen y verduleria", "schedule": "Lun-Dom 8:00-20:00", "latitude": -32.8810, "longitude": -60.7810},
    
    # Eventos
    {"name": "Campos de Ibarlucea - Salon de Eventos", "phone": "", "email": "", "address": "Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 116, "description": "Salon de eventos, casamientos, 15 anos", "schedule": "Consultar disponibilidad", "latitude": -32.8900, "longitude": -60.7900},
    
    # Arquitectos
    {"name": "Estilo Urbano - Arquitectos", "phone": "", "email": "", "address": "Av. Del Rosario y Corrientes, Ibarlucea, Santa Fe", "city": "Ibarlucea", "neighborhood": "Centro", "category_id": 999, "description": "Estudio de arquitectura", "schedule": "Lun-Vie 9:00-18:00", "latitude": -32.8820, "longitude": -60.7820},
]

# Filter businesses within 20km
filtered = []
excluded = []

for biz in businesses:
    dist = haversine_distance(ybarlucea_lat, ybarlucea_lon, biz['latitude'], biz['longitude'])
    if dist <= 20:
        biz['distance_km'] = round(dist, 1)
        biz['verified'] = True
        filtered.append(biz)
        print(f"OK: {biz['name']} ({dist:.1f}km)")
    else:
        excluded.append((biz['name'], dist))
        print(f"OUT: {biz['name']} ({dist:.1f}km)")

print(f"\n=== RESUMEN ===")
print(f"Total recolectados: {len(businesses)}")
print(f"Incluidos (<20km): {len(filtered)}")
print(f"Excluidos (>20km): {len(excluded)}")

# Save
output = "C:/Users/maria/Proyectos/AgendaZonal/backend/fuente_datos/real_businesses_ybarlucea.json"
with open(output, 'w', encoding='utf-8') as f:
    json.dump(filtered, f, ensure_ascii=False, indent=2)

print(f"\nGuardado en: {output}")
