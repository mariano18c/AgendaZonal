# Data Curator Agent: Specification

## Perfil y Mision
Agente especializado en la **limpieza, normalizacion e ingesta masiva de datos** para AgendaZonal. Transforma fuentes heterogeneas y desestructuradas en entradas validas para la tabla `contacts`, manteniendo integridad y evitando duplicados.

## Fuentes de Datos
- **vCards (.vcf)**: Archivos de contactos estandar de Android/iOS.
- **WhatsApp Chats (.txt)**: Exportaciones de chats con informacion publicitaria.
- **Imagenes (.jpg, .png)**: Capturas de volantes, tarjetas personales y anuncios.
- **Documentos (.ods, .csv, .json)**: Planillas de datos existentes.

## Reglas de Comportamiento (Core Rules)
1. **Normalización de Teléfonos**: Convertir a formato internacional `+549...`. 
   - **Concatenación**: Evitar concatenar números múltiples (separar por `/` o `,`).
   - **Limpieza**: Eliminar caracteres no numéricos excepto el `+` inicial.
   - **Longitud**: Soportar números cortos (3+ dígitos) para emergencias (911, 144).
2. **Detección de Duplicados**:
   - **Cross-status**: No importar como `pending` si el número ya existe como `active`.
   - **Internal**: Mantener solo un registro por número en la cola de moderación, priorizando el que tenga referencia a archivo VCF/Imagen.
3. **vCard Parsing**: Usar regex *non-greedy* (`TEL.*:(.*?)`) para evitar capturar parámetros de metadatos como `waid`. Fallback al campo `FN` si `TEL` falla.
4. **Calidad de Imagen (OCR)**: Al procesar fotos, extraer nombre, rubro, teléfonos, redes sociales y dirección.
5. **Categorización**: Mapear a categorías oficiales (ID 1-45). Si el rubro no es claro, asignar ID 999 (Sin rubro/Por clasificar) y marcar como `pending`.
6. **Confianza OCR**: Los contactos extraídos por OCR van siempre como `pending` para validación humana, a menos que el match con la DB sea del 100%.

## Herramientas y Scripts (`backend/scripts/`)

| Script | Funcion | Entrada |
|---|---|---|
| `data_curator_v2.py` | Parseo de VCF y chats WhatsApp | `.vcf`, `.txt` |
| `ocr_engine.py` | OCR + extraccion de telefonos/categorias | `.jpg`, `.png` |
| `auto_moderate_v3.py` | Reclasificacion automatica por keywords | DB (cat 26) |
| `persist_contacts.py` | Persistencia en SQLite (WAL) | JSON enriquecido |
| `watcher.py` | Demonio: monitorea `./fuente_datos` y ejecuta el pipeline automaticamente | Filesystem events |
| `final_cleanup.py` | Mueve archivos procesados a `importados_ok/no_ok` | `./fuente_datos` |

## Workflow de Trabajo
1. **Ingesta**: Soltar archivo en `./fuente_datos` (o dejar el watcher corriendo).
2. **Transformacion**: El router por extension ejecuta el script correcto.
3. **Validacion**: Chequeo de integridad y deduplicacion por telefono.
4. **Persistencia**: Cargar en la DB via script directo (SQLite WAL mode).
5. **Moderacion**: `auto_moderate_v3.py` reclasifica automaticamente contactos en "Otro".
6. **Finalizacion**: Mover archivos a `./fuente_datos/importados_ok` o `importados_no_ok`.

## Categorias Expandidas (SSOT Parcial)
- **Oficios**: Plomero (1), Gasista (2), Electricista (3), Albañil (5), Pintor (6), Carpintero (7).
- **Comercios**: Supermercado (8), Carniceria (9), Verduleria (10), Panaderia (11), Farmacia (13), Ferreteria (20), Kiosco (21).
- **Gastronomia**: Bar (15), Restaurant (16), Vinoteca (34), Heladeria (35).
- **Servicios**: Peluqueria (4), Veterinaria (19), Escribania (29), Flete (30), Imprenta (31).
- **Nuevas (Moderacion)**: Remis/Taxi (39), Modista/Costura (40), Vivero (41), Arquitectura (42), Gimnasio (43), Cerrajeria (44), Bicicleteria (45).
- **Especiales**: Municipio (27), Apoyo Escolar (28), Sanatorio/Salud (36), Taller (37), Mecanico (38).

## Dependencias del OCR Engine
- **Tesseract OCR**: `apt install tesseract-ocr tesseract-ocr-spa` (RPi/Linux).
- **pytesseract**: Wrapper Python (en `requirements.txt`).
- **Fallback**: Si Tesseract no esta instalado, extrae datos del nombre del archivo.
