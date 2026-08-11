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
      "institucion": "Instituto de origen"
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
