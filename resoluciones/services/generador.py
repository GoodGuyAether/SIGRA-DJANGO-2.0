"""Domain service for a single academic-resolution generation."""
import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from catalogos.models import Alumno, CarreraOrigen, Materia, Tecnicatura
from core.services.pdf import convertir_a_pdf
from core.textutils import nombre_en_titulo, texto_en_mayusculas
from resoluciones.models import EstadoResolucion, Resolucion, ResolucionMateria, TipoResolucion

logger = logging.getLogger(__name__)


class GeneracionResolucionError(RuntimeError):
    """Raised when the DOCX cannot be generated and the transaction must roll back."""


def _valores_unicos(materias: list[dict], key: str) -> list[str]:
    return list(dict.fromkeys(item[key] for item in materias))


def _contexto_documento(alumno: Alumno, tecnicatura: Tecnicatura, tipo: str, materias: list[dict], resolucion_nro: str) -> dict:
    primera = materias[0]
    return {
        "alumno_nombre": nombre_en_titulo(alumno.nombre),
        "alumno_apellido": nombre_en_titulo(alumno.apellido),
        "alumno_nombre_completo": f"{nombre_en_titulo(alumno.nombre)} {nombre_en_titulo(alumno.apellido)}",
        "alumno_dni": alumno.dni,
        "tecnicatura": tecnicatura.nombre,
        "res_ministerial": tecnicatura.res_ministerial,
        "tipo": TipoResolucion(tipo).label,
        "resolucion_nro": resolucion_nro,
        "fecha": timezone.localdate().strftime("%d/%m/%Y"),
        "materias": materias,
        # Compatibility fields for single-row templates.
        "materia": primera["materia"],
        "equivalencia": primera["equivalencia"],
        "institucion": primera["institucion"],
        "anio_cursado": primera["anio_cursado"],
        "carrera_origen": primera["carrera_origen"],
        "carreras_origen_unicas": _valores_unicos(materias, "carrera_origen"),
        "instituciones_unicas": _valores_unicos(materias, "institucion"),
        "equivalencias_unicas": _valores_unicos(materias, "equivalencia"),
    }


def _nombre_relativo(path: Path) -> str:
    try:
        return path.relative_to(settings.MEDIA_ROOT).as_posix()
    except ValueError as error:
        raise GeneracionResolucionError("OUTPUT_DIR debe estar dentro de MEDIA_ROOT.") from error


def generar_resolucion(
    alumno: Alumno,
    tecnicatura: Tecnicatura,
    tipo: str,
    materias: list[dict],
    resolucion_nro: str,
) -> Resolucion:
    """Persist one resolution, render its DOCX and best-effort generate its PDF."""
    if not materias:
        raise GeneracionResolucionError("La resolución debe incluir al menos una materia.")
    if tipo not in TipoResolucion.values:
        raise GeneracionResolucionError("El tipo de resolución no es válido.")
    if not Path(settings.TEMPLATE_PATH).is_file():
        raise GeneracionResolucionError(f"No existe la plantilla DOCX: {settings.TEMPLATE_PATH}")

    materia_ids = [item["materia_id"] for item in materias]
    carrera_ids = [item["carrera_origen_id"] for item in materias]
    materias_catalogo = Materia.objects.in_bulk(materia_ids)
    carreras_catalogo = CarreraOrigen.objects.in_bulk(carrera_ids)
    if len(materias_catalogo) != len(set(materia_ids)) or len(carreras_catalogo) != len(set(carrera_ids)):
        raise GeneracionResolucionError("Una materia o carrera de origen no existe.")

    output_dir = Path(settings.OUTPUT_DIR) / timezone.localdate().strftime("%Y") / timezone.localdate().strftime("%m")
    output_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    docx_path = output_dir / f"resolucion-{token}.docx"
    pdf_path: Path | None = None

    try:
        with transaction.atomic():
            resolucion = Resolucion.objects.create(
                alumno=alumno,
                tecnicatura=tecnicatura,
                tipo=tipo,
                estado=EstadoResolucion.EN_PROCESO,
                resolucion_nro=resolucion_nro,
                fecha=timezone.localdate(),
            )
            filas = []
            contexto_materias = []
            for item in materias:
                materia = materias_catalogo[item["materia_id"]]
                carrera = carreras_catalogo[item["carrera_origen_id"]]
                filas.append(
                    ResolucionMateria(
                        resolucion=resolucion,
                        materia=materia,
                        carrera_origen=carrera,
                        equivalencia=item["equivalencia"],
                        anio_cursado=item["anio_cursado"],
                        institucion=item["institucion"],
                    )
                )
                contexto_materias.append(
                    {
                        "materia": texto_en_mayusculas(materia.nombre),
                        "carrera_origen": texto_en_mayusculas(carrera.nombre),
                        "equivalencia": texto_en_mayusculas(item["equivalencia"]),
                        "anio_cursado": item["anio_cursado"],
                        "institucion": texto_en_mayusculas(item["institucion"]),
                    }
                )
            ResolucionMateria.objects.bulk_create(filas)

            try:
                from docxtpl import DocxTemplate
            except ImportError as error:
                raise GeneracionResolucionError(
                    "docxtpl no está instalado. Instale las dependencias del proyecto."
                ) from error
            template = DocxTemplate(str(settings.TEMPLATE_PATH))
            template.render(_contexto_documento(alumno, tecnicatura, tipo, contexto_materias, resolucion_nro))
            template.save(str(docx_path))
            if not docx_path.is_file():
                raise GeneracionResolucionError("La plantilla no produjo un archivo DOCX.")

            pdf_path = convertir_a_pdf(docx_path, output_dir)
            resolucion.archivo_docx.name = _nombre_relativo(docx_path)
            if pdf_path:
                resolucion.archivo_pdf.name = _nombre_relativo(pdf_path)
            resolucion.estado = EstadoResolucion.GENERADA
            resolucion.save(update_fields=["archivo_docx", "archivo_pdf", "estado"])
            return resolucion
    except Exception as error:
        for path in (docx_path, pdf_path):
            if path and path.exists():
                path.unlink()
        logger.exception("Falló la generación del DOCX; se revierte la resolución.")
        if isinstance(error, GeneracionResolucionError):
            raise
        raise GeneracionResolucionError("No se pudo generar el documento de resolución.") from error
