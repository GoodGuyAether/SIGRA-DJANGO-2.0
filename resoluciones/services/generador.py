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
from resoluciones.models import EstadoResolucion, Resolucion, ResolucionMateria, SituacionEquivalencia, TipoResolucion

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
        "nombre": nombre_en_titulo(alumno.nombre),
        "apellido": nombre_en_titulo(alumno.apellido),
        "dni": alumno.dni,
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
        # Legacy template variable: keep it aligned with the Art. 1 list.
        "equivalencias": ", ".join(
            _valores_unicos([item for item in materias if item["situacion"] == SituacionEquivalencia.CORRESPONDE], "equivalencia")
        ),
        "equivalencias_corresponde": ", ".join(
            _valores_unicos([item for item in materias if item["situacion"] == SituacionEquivalencia.CORRESPONDE], "equivalencia")
        ),
        "equivalencias_no_corresponde": ", ".join(
            _valores_unicos([item for item in materias if item["situacion"] == SituacionEquivalencia.NO_CORRESPONDE], "equivalencia")
        ),
        "materias_unicas": ", ".join(_valores_unicos(materias, "materia")),
        "materias_corresponde": [item for item in materias if item["situacion"] == SituacionEquivalencia.CORRESPONDE],
        "materias_no_corresponde": [item for item in materias if item["situacion"] == SituacionEquivalencia.NO_CORRESPONDE],
        "materias_corresponden": [item for item in materias if item["situacion"] == SituacionEquivalencia.CORRESPONDE],
        "materias_no_corresponden": [item for item in materias if item["situacion"] == SituacionEquivalencia.NO_CORRESPONDE],
        "hay_no_corresponde": any(item["situacion"] == SituacionEquivalencia.NO_CORRESPONDE for item in materias),
        "hay_no_corresponden": any(item["situacion"] == SituacionEquivalencia.NO_CORRESPONDE for item in materias),
        "no_corresponde_texto": ", ".join(
            item["materia"] for item in materias if item["situacion"] == SituacionEquivalencia.NO_CORRESPONDE
        ),
    }


def _nombre_relativo(path: Path) -> str:
    try:
        return path.relative_to(settings.MEDIA_ROOT).as_posix()
    except ValueError as error:
        raise GeneracionResolucionError("OUTPUT_DIR debe estar dentro de MEDIA_ROOT.") from error


def _template_path(materias: list[dict]) -> Path:
    situaciones = {item.get("situacion", SituacionEquivalencia.CORRESPONDE) for item in materias}
    if situaciones == {SituacionEquivalencia.CORRESPONDE}:
        return Path(getattr(settings, "TEMPLATE_OTORGADAS_PATH", settings.TEMPLATE_PATH))
    if situaciones == {SituacionEquivalencia.NO_CORRESPONDE}:
        return Path(getattr(settings, "TEMPLATE_NO_OTORGADAS_PATH", settings.TEMPLATE_PATH))
    return Path(getattr(settings, "TEMPLATE_MIXTA_PATH", settings.TEMPLATE_PATH))


def generar_resolucion(
    alumno: Alumno,
    tecnicatura: Tecnicatura,
    tipo: str,
    materias: list[dict],
    resolucion_nro: str,
    *,
    batch_id: uuid.UUID | None = None,
    output_dir: Path | None = None,
) -> Resolucion:
    """Persist one resolution, render its DOCX and best-effort generate its PDF."""
    if not materias:
        raise GeneracionResolucionError("La resolución debe incluir al menos una materia.")
    if tipo not in TipoResolucion.values:
        raise GeneracionResolucionError("El tipo de resolución no es válido.")
    template_path = _template_path(materias)
    if not template_path.is_file():
        raise GeneracionResolucionError(f"No existe la plantilla DOCX: {template_path}")

    materia_ids = [item["materia_id"] for item in materias]
    carrera_ids = [item["carrera_origen_id"] for item in materias]
    materias_catalogo = Materia.objects.in_bulk(materia_ids)
    carreras_catalogo = CarreraOrigen.objects.in_bulk(carrera_ids)
    if len(materias_catalogo) != len(set(materia_ids)) or len(carreras_catalogo) != len(set(carrera_ids)):
        raise GeneracionResolucionError("Una materia o carrera de origen no existe.")

    output_dir = output_dir or (
        Path(settings.OUTPUT_DIR)
        / timezone.localdate().strftime("%Y")
        / timezone.localdate().strftime("%m")
    )
    output_dir = Path(output_dir)
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
                batch_id=batch_id,
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
                        situacion=item.get("situacion", SituacionEquivalencia.CORRESPONDE),
                    )
                )
                contexto_materias.append(
                    {
                        "materia": texto_en_mayusculas(materia.nombre),
                        "carrera_origen": texto_en_mayusculas(carrera.nombre),
                        "equivalencia": texto_en_mayusculas(item["equivalencia"]),
                        "anio_cursado": item["anio_cursado"],
                        "institucion": texto_en_mayusculas(item["institucion"]),
                        "tecnicatura": texto_en_mayusculas(tecnicatura.nombre),
                        "situacion": item.get("situacion", SituacionEquivalencia.CORRESPONDE),
                        "situacion_label": "No corresponde" if item.get("situacion") == SituacionEquivalencia.NO_CORRESPONDE else "Corresponde",
                    }
                )
            ResolucionMateria.objects.bulk_create(filas)

            try:
                from docxtpl import DocxTemplate
            except ImportError as error:
                raise GeneracionResolucionError(
                    "docxtpl no está instalado. Instale las dependencias del proyecto."
                ) from error
            template = DocxTemplate(str(template_path))
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
        detalle = str(error).strip()
        if detalle:
            raise GeneracionResolucionError(f"No se pudo generar el documento. Causa: {detalle}") from error
        raise GeneracionResolucionError("No se pudo generar el documento de resolución.") from error
