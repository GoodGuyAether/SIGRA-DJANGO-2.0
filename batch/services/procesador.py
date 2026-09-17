"""CSV parsing, validation and synchronous batch processing.

The standard-library ``csv.DictReader`` is used instead of pandas: this keeps
the upload path lightweight and makes row numbers/error reporting explicit.
"""
import csv
import io
import logging
from collections import OrderedDict
from pathlib import Path

from django.conf import settings

from batch.models import EstadoLote, LoteCarga
from catalogos.models import Alumno, CarreraOrigen, Materia, Tecnicatura
from resoluciones.models import TipoResolucion, SituacionMateria
from resoluciones.services.generador import GeneracionResolucionError, generar_resolucion

logger = logging.getLogger(__name__)

COLUMNAS_OBLIGATORIAS = (
    "nombre",
    "apellido",
    "dni",
    "materia",
    "equivalencia",
    "tecnicatura",
    "res_ministerial",
    "año_cursado",
    "institucion",
    "carrera_origen",
    "situacion",
)
COLUMNAS_OPCIONALES = ("resolucion_nro", "observaciones")


class CSVInvalidoError(ValueError):
    def __init__(self, errores: list[dict], total_filas: int = 0):
        super().__init__("El CSV contiene errores de validación.")
        self.errores = errores
        self.total_filas = total_filas


def parsear_y_validar_csv(contenido: bytes, max_filas: int | None = None) -> list[dict]:
    """Decode strict UTF-8 and return normalized rows or every validation error."""
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise CSVInvalidoError([{"fila": 1, "error": "El archivo debe estar codificado en UTF-8."}]) from error

    reader = csv.DictReader(io.StringIO(texto, newline=""))
    if not reader.fieldnames:
        raise CSVInvalidoError([{"fila": 1, "error": "El CSV no contiene encabezados."}])
    encabezados = {header.strip() for header in reader.fieldnames if header}
    faltantes = [columna for columna in COLUMNAS_OBLIGATORIAS if columna not in encabezados]
    if faltantes:
        raise CSVInvalidoError([{"fila": 1, "error": f"Faltan columnas obligatorias: {', '.join(faltantes)}."}])

    max_filas = max_filas if max_filas is not None else settings.BATCH_MAX_ROWS
    filas: list[dict] = []
    errores: list[dict] = []
    for numero_fila, fila in enumerate(reader, start=2):
        if numero_fila - 1 > max_filas:
            errores.append({"fila": numero_fila, "error": f"El lote supera el límite de {max_filas} filas."})
            break
        limpia = {(clave or "").strip(): (valor or "").strip() for clave, valor in fila.items()}
        campos_vacios = [campo for campo in COLUMNAS_OBLIGATORIAS if not limpia.get(campo)]
        if campos_vacios:
            errores.append({"fila": numero_fila, "error": f"Campos obligatorios vacíos: {', '.join(campos_vacios)}."})
            continue
        try:
            limpia["año_cursado"] = int(limpia["año_cursado"])
            if not 1900 <= limpia["año_cursado"] <= 3000:
                raise ValueError
        except ValueError:
            errores.append({"fila": numero_fila, "error": "El año cursado debe ser un número entre 1900 y 3000."})
            continue
        situacion = limpia["situacion"].strip().lower().replace(" ", "_")
        if situacion not in SituacionMateria.values:
            errores.append({"fila": numero_fila, "error": "La situacion debe ser Corresponde o No Corresponde."})
            continue
        limpia["situacion"] = situacion
        limpia["_fila"] = numero_fila
        filas.append(limpia)

    if not filas and not errores:
        errores.append({"fila": 1, "error": "El CSV no contiene filas de datos."})
    if errores:
        raise CSVInvalidoError(errores, total_filas=len(filas) + len(errores))
    return filas


def agrupar_por_dni(filas: list[dict]) -> list[list[dict]]:
    """Group in first-seen order; each group produces exactly one resolution."""
    grupos: OrderedDict[str, list[dict]] = OrderedDict()
    for fila in filas:
        grupos.setdefault(fila["dni"], []).append(fila)
    return list(grupos.values())


def _advertir_inconsistencias(grupo: list[dict]) -> None:
    primera = grupo[0]
    for campo in ("nombre", "apellido", "tecnicatura", "res_ministerial"):
        if any(fila[campo] != primera[campo] for fila in grupo[1:]):
            logger.warning(
                "DNI %s: valores inconsistentes para %s; se utiliza la fila %s.",
                primera["dni"],
                campo,
                primera["_fila"],
            )


def _obtener_catalogos(primera: dict) -> tuple[Alumno, Tecnicatura]:
    alumno, creado = Alumno.objects.get_or_create(
        dni=primera["dni"],
        defaults={"nombre": primera["nombre"], "apellido": primera["apellido"]},
    )
    if not creado and not alumno.activo:
        raise GeneracionResolucionError("El alumno está dado de baja.")
    tecnicatura, creada = Tecnicatura.objects.get_or_create(
        nombre=primera["tecnicatura"],
        defaults={"res_ministerial": primera["res_ministerial"]},
    )
    if not creada and not tecnicatura.activo:
        raise GeneracionResolucionError("La tecnicatura está dada de baja.")
    return alumno, tecnicatura


def _materias_para_generador(grupo: list[dict]) -> list[dict]:
    materias = []
    for fila in grupo:
        materia, creada = Materia.objects.get_or_create(nombre=fila["materia"])
        carrera, creada_carrera = CarreraOrigen.objects.get_or_create(nombre=fila["carrera_origen"])
        if not materia.activo or not carrera.activo:
            raise GeneracionResolucionError("Una materia o carrera de origen está dada de baja.")
        materias.append(
            {
                "materia_id": materia.pk,
                "carrera_origen_id": carrera.pk,
                "equivalencia": fila["equivalencia"],
                "anio_cursado": fila["año_cursado"],
                "institucion": fila["institucion"],
                "situacion": fila["situacion"].lower().replace(" ", "_"),
            }
        )
    return materias


def procesar_lote(lote: LoteCarga, filas: list[dict]) -> LoteCarga:
    """Generate all DNI groups synchronously and persist traceability in ``lote``."""
    lote.estado = EstadoLote.PROCESANDO
    lote.save(update_fields=["estado"])
    errores: list[dict] = []
    total = 0
    output_dir = Path(settings.OUTPUT_DIR) / "batches" / str(lote.batch_id)
    for grupo in agrupar_por_dni(filas):
        primera = grupo[0]
        _advertir_inconsistencias(grupo)
        try:
            alumno, tecnicatura = _obtener_catalogos(primera)
            generar_resolucion(
                alumno=alumno,
                tecnicatura=tecnicatura,
                tipo=TipoResolucion.NORMAL,
                materias=_materias_para_generador(grupo),
                resolucion_nro=primera.get("resolucion_nro", ""),
                batch_id=lote.batch_id,
                output_dir=output_dir,
            )
            total += 1
        except GeneracionResolucionError as error:
            logger.exception("Falló la generación del DNI %s en lote %s.", primera["dni"], lote.batch_id)
            errores.append({"fila": primera["_fila"], "error": str(error)})

    lote.total_resoluciones = total
    lote.errores = errores
    lote.estado = EstadoLote.CON_ERRORES if errores else EstadoLote.COMPLETADO
    lote.save(update_fields=["total_resoluciones", "errores", "estado"])
    return lote
