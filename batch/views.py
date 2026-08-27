import csv
import io
import zipfile
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import EstadoLote, LoteCarga
from .services.procesador import COLUMNAS_OBLIGATORIAS, CSVInvalidoError, parsear_y_validar_csv, procesar_lote


@csrf_exempt
@require_POST
def subir_lote(request: HttpRequest):
    archivo = request.FILES.get("file")
    if not archivo:
        return JsonResponse({"error": "Debe adjuntar el archivo CSV en el campo file."}, status=400)
    if archivo.size > settings.MAX_UPLOAD_SIZE:
        return JsonResponse({"error": "El archivo excede el límite de 16 MB."}, status=413)
    try:
        filas = parsear_y_validar_csv(archivo.read())
    except CSVInvalidoError as error:
        return JsonResponse({"error": str(error), "errores": error.errores}, status=400)

    lote = LoteCarga.objects.create(
        archivo_original=Path(archivo.name).name,
        total_filas=len(filas),
        estado=EstadoLote.PENDIENTE,
    )
    lote = procesar_lote(lote, filas)
    return JsonResponse(
        {
            "batch_id": str(lote.batch_id),
            "total_resoluciones": lote.total_resoluciones,
            "errores": lote.errores,
        },
        status=201,
    )


@require_GET
def estado_lote(request: HttpRequest, batch_id):
    try:
        lote = LoteCarga.objects.get(batch_id=batch_id)
    except LoteCarga.DoesNotExist as error:
        raise Http404("Lote inexistente.") from error
    return JsonResponse(
        {
            "batch_id": str(lote.batch_id),
            "archivo_original": lote.archivo_original,
            "estado": lote.estado,
            "total_filas": lote.total_filas,
            "total_resoluciones": lote.total_resoluciones,
            "errores": lote.errores,
            "creado_en": lote.creado_en.isoformat(),
        }
    )


@require_GET
def descargar_lote(request: HttpRequest, batch_id):
    try:
        lote = LoteCarga.objects.get(batch_id=batch_id)
    except LoteCarga.DoesNotExist as error:
        raise Http404("Lote inexistente.") from error
    output_dir = Path(settings.OUTPUT_DIR) / "batches" / str(lote.batch_id)
    archivos = [path for path in output_dir.glob("*") if path.suffix.lower() in {".docx", ".pdf"}]
    if not archivos:
        raise Http404("El lote no tiene documentos para descargar.")

    contenido = io.BytesIO()
    with zipfile.ZipFile(contenido, "w", zipfile.ZIP_DEFLATED) as archivo_zip:
        for archivo in archivos:
            archivo_zip.write(archivo, arcname=archivo.name)
    contenido.seek(0)
    return FileResponse(contenido, as_attachment=True, filename=f"lote-{lote.batch_id}.zip")


@require_GET
def plantilla_csv(request: HttpRequest):
    contenido = io.StringIO(newline="")
    writer = csv.DictWriter(contenido, fieldnames=[*COLUMNAS_OBLIGATORIAS, "resolucion_nro", "observaciones"])
    writer.writeheader()
    writer.writerow(
        {
            "nombre": "Ana",
            "apellido": "Pérez",
            "dni": "12345678",
            "materia": "Programación I",
            "equivalencia": "Aprobada por equivalencia",
            "tecnicatura": "Desarrollo de Software",
            "res_ministerial": "RM 1/2026",
            "año_cursado": "2024",
            "institucion": "Instituto de origen",
            "carrera_origen": "Analista de Sistemas",
        }
    )
    response = FileResponse(
        io.BytesIO(contenido.getvalue().encode("utf-8")),
        as_attachment=True,
        filename="plantilla-carga-sigra.csv",
        content_type="text/csv; charset=utf-8",
    )
    return response
