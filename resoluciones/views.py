import json
from pathlib import Path

from django.http import FileResponse, HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from catalogos.models import Alumno, Tecnicatura
from .forms import GenerarResolucionForm
from .services.generador import GeneracionResolucionError, generar_resolucion


def _datos_formulario(payload: dict) -> dict:
    alumno = payload.get("alumno") or {}
    return {
        "nombre": alumno.get("nombre"),
        "apellido": alumno.get("apellido"),
        "dni": alumno.get("dni"),
        "tecnicatura_id": payload.get("tecnicatura_id"),
        "tipo": payload.get("tipo"),
        "resolucion_nro": payload.get("resolucion_nro", ""),
        "materias": payload.get("materias"),
    }


@csrf_exempt
@require_POST
def generar_resolucion_view(request: HttpRequest):
    try:
        payload = json.loads(request.body)
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "El cuerpo debe ser JSON válido."}, status=400)

    form = GenerarResolucionForm(_datos_formulario(payload))
    if not form.is_valid():
        return JsonResponse({"error": "Payload inválido.", "details": form.errors.get_json_data()}, status=400)

    data = form.cleaned_data
    alumno, created = Alumno.objects.get_or_create(
        dni=data["dni"],
        defaults={"nombre": data["nombre"], "apellido": data["apellido"]},
    )
    if not created and not alumno.activo:
        return JsonResponse({"error": "El alumno está dado de baja."}, status=400)
    tecnicatura = Tecnicatura.objects.get(pk=data["tecnicatura_id"])
    try:
        resolucion = generar_resolucion(
            alumno=alumno,
            tecnicatura=tecnicatura,
            tipo=data["tipo"],
            materias=data["materias"],
            resolucion_nro=data["resolucion_nro"],
        )
    except GeneracionResolucionError as error:
        return JsonResponse({"error": str(error)}, status=500)

    archivo = resolucion.archivo_pdf if resolucion.archivo_pdf else resolucion.archivo_docx
    response = FileResponse(open(Path(archivo.path), "rb"), as_attachment=True, filename=Path(archivo.name).name)
    if not resolucion.archivo_pdf:
        response["X-SIGRA-Document-Format"] = "docx"
    return response
