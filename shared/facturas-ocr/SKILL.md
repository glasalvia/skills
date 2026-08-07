---
name: "facturas-ocr"
description: "Pipeline OCR de facturas: flujo chat-driven. OCR con Tesseract, extracción con LLM, subida a Google Drive y consolidación en Google Sheets."
---

# Skill: facturas-ocr

Pipeline completo de OCR para facturas argentinas. Extrae datos estructurados de imágenes de facturas usando Tesseract + LLM, sube las imágenes a Google Drive y consolida los datos en Google Sheets.

**Trigger:** El usuario envía una imagen de factura en el chat → se procesa en el momento, sin watcher ni cron.

## Arquitectura (Chat-Driven)

```
Chat (imagen) → 01_raw/ → [phase1: preprocess+OCR] → [LLM extrae] → [phase2: validate+Drive+Sheets] → ✅
```

## Archivos del Pipeline

| Archivo | Propósito |
|---------|-----------|
| `~/facturas/schema.py` | Modelo Pydantic `FacturaData` |
| `~/facturas/parser.py` | OCR con Tesseract (spa), preparación de prompt |
| `~/facturas/preprocess.py` | OpenCV: grises, binarización, deskew |
| `~/facturas/drive_manager.py` | Upload, share, carpetas en Google Drive |
| `~/facturas/consolidate.py` | Apende filas a Google Sheets vía GOG |
| `~/facturas/process_factura.py` | **Orquestador chat-driven:** phase1 (preprocess+OCR) y phase2 (validate+Drive+Sheets) |
| `~/facturas/drive_ids.env` | IDs de carpetas en Google Drive |

## Estructura en Google Drive

```
📁 Facturas/
├── 📁 01_raw/           ← backup de originales
├── 📁 02_clean/          ← imágenes preprocesadas
├── 📁 03_procesadas/     ← facturas OK, por timestamp
│   └── 📁 2026-07-21_21.30.45/
└── 📁 04_failed/         ← extracciones fallidas
```

## Procedimiento de Ejecución (Chat-Driven)

### Cuando el usuario envía una imagen de factura:

**Paso 1 — Guardar imagen:**
Guardar la imagen recibida en `~/facturas/01_raw/<nombre_original>`.

**Paso 2 — Fase 1: Preprocesado + OCR:**
```bash
cd ~/facturas && source venv/bin/activate && python3 process_factura.py phase1 ~/facturas/01_raw/<imagen>
```
Esto devuelve un JSON con:
- `raw_path`: ruta de la imagen original
- `clean_path`: ruta de la imagen preprocesada
- `ocr_text`: texto extraído por Tesseract
- `ocr_confidence`: confianza promedio del OCR
- `prompt`: prompt listo para enviar al LLM

**Paso 3 — Extracción con LLM:**
Enviar el campo `prompt` al LLM de la sesión y obtener el JSON estructurado con los datos de la factura.

**Paso 4 — Validar y verificar score:**
Validar el JSON contra el schema `FacturaData`. Si `score_confianza > 0.80`, continuar. Si es ≤ 0.80, informar al usuario que la extracción es de baja confianza y preguntar si desea forzar el procesamiento o revisar manualmente.

**Paso 5 — Fase 2: Drive + Sheets:**
```bash
cd ~/facturas && source venv/bin/activate && python3 process_factura.py phase2 '<raw_path>' '<clean_path>' '<json_datos_en_una_linea>'
```
Esto:
- Valida los datos con Pydantic
- Sube raw y clean a Drive (carpetas 01_raw y 03_procesadas/<timestamp>)
- Comparte la imagen clean como pública
- Apende una fila en Google Sheets (pestaña "Facturas")
- Limpia los archivos locales temporales

**Paso 6 — Confirmar al usuario:**
Informar comercio, monto, fecha y link de Drive.

### Si el score es bajo (≤ 0.80):

- La imagen se mueve automáticamente a `04_failed/` en Drive
- Se le informa al usuario con el motivo
- El usuario puede pedir "forzar procesamiento" para subirlo igual ignorando el umbral
- O puede revisar la imagen y corregir los datos manualmente

### Modo Manual (sin imagen en chat)

Decir "procesar factura <ruta>" y seguir el mismo flujo desde el Paso 2.

## Esquema de Datos (Google Sheets)

Columnas en la pestaña "Facturas" (sheet ID: `1Gd_7inpTqJU22GH8cRaqDO0sZcfPOAAo0qbi-sLC-bM`):
| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| Fecha Factura | CUIT | Comercio | Conceptos | Monto Total | Impuestos | Drive Link | Fecha Procesamiento | Score |

## Dependencias

- **Sistema:** tesseract-ocr, tesseract-ocr-spa
- **Python:** opencv-python-headless, pytesseract, pydantic, numpy, Pillow
- **CLI:** GOG (`/home/linuxbrew/.linuxbrew/bin/gog`) autenticado con `raspilasalvia@gmail.com`
- **Venv:** `~/facturas/venv/`

## Notas

- Tesseract usa config `--psm 6` (bloque uniforme de texto) con idioma `spa`
- La confianza se calcula como `campos_encontrados / 7` con penalización si faltan monto o CUIT
- Umbral de score: 0.80 para considerar válida una extracción
- Las imágenes se comparten como `anyone+reader` en Drive para que el link funcione en Sheets
- **Ya no requiere watcher (watchdog) ni cron.** El trigger es directo: imagen en chat → procesamiento inmediato.
- `watcher.py` queda como alternativa legacy si se desea monitoreo por filesystem, pero no es parte del flujo principal.

## Environment
- **cachy-gla:** Pipeline completo: Tesseract OCR, LLM (Ollama/Qwen), Google Drive upload, Google Sheets consolidación.
- **Raspi:** No implementado (dependencias de OCR y GPU no disponibles).
- **Dependencias:** Tesseract, Python 3, `google-auth`, `gspread`. Drive/Sheets tokens en keyring.
