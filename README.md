# SIGRA

Sistema Integral de Generación de Resoluciones Académicas.

## Generación individual

`POST /api/generate/` recibe JSON y devuelve el PDF generado o, si
LibreOffice no está disponible, el DOCX con el header
`X-SIGRA-Document-Format: docx`.

```json
{
  "alumno": {"nombre": "Ana", "apellido": "Pérez", "dni": "12345678"},
  "tecnicatura_id": 1,
  "tipo": "normal",
  "resolucion_nro": "12/2026",
  "materias": [
    {
      "materia_id": 1,
      "carrera_origen_id": 1,
      "equivalencia": "Aprobada por equivalencia",
      "anio_cursado": 2024,
      "institucion": "Instituto de origen",
      "situacion": "Corresponde"
    }
  ]
}
```

La plantilla se encuentra en `resoluciones/templates/template.docx`. Incluye
el bucle `materias` para la tabla y los campos de compatibilidad de una fila:
`materia`, `equivalencia`, `institucion`, `anio_cursado` y
`carrera_origen`. También están disponibles las listas únicas
`carreras_origen_unicas`, `instituciones_unicas` y `equivalencias_unicas`.

Los archivos se guardan bajo `media/salidas/<año>/<mes>/` por defecto. Se
pueden configurar `TEMPLATE_PATH`, `OUTPUT_DIR`, `LIBREOFFICE_BIN` y
`LIBREOFFICE_TIMEOUT` desde el entorno.

## Carga masiva CSV

La carga síncrona se realiza con `POST /batch/upload/` usando el campo
multipart `file`. El procesador usa `csv.DictReader` (sin pandas), valida
encoding UTF-8, encabezados, campos obligatorios, años y el límite de 1000
filas, y reporta todos los errores antes de generar documentos. Las filas se
agrupan por DNI en orden de primera aparición y cada grupo produce una única
resolución persistida con su `batch_id`.

Los endpoints complementarios son `GET /batch/<batch_id>/estado/`,
`GET /batch/<batch_id>/descargar/` (ZIP de DOCX/PDF) y
`GET /batch/template/` (CSV de ejemplo). Los documentos se almacenan en
`media/salidas/batches/<batch_id>/`.
