import uuid

from django.db import models

from catalogos.models import Alumno, CarreraOrigen, Materia, Tecnicatura


class TipoResolucion(models.TextChoices):
    NORMAL = "normal", "Normal"
    RECONOCIMIENTO_SABERES = "reconocimiento_saberes", "Reconocimiento de saberes"
    RECTIFICACION = "rectificacion", "Rectificación"


class EstadoResolucion(models.TextChoices):
    GENERADA = "generada", "Generada"
    EN_PROCESO = "en_proceso", "En proceso"
    ERROR = "error", "Error"


class SituacionMateria(models.TextChoices):
    CORRESPONDE = "corresponde", "Corresponde"
    NO_CORRESPONDE = "no_corresponde", "No corresponde"


# Backwards-compatible name used by the first implementation of Ticket 04.
SituacionEquivalencia = SituacionMateria


class Resolucion(models.Model):
    alumno = models.ForeignKey(Alumno, on_delete=models.PROTECT, related_name="resoluciones")
    tecnicatura = models.ForeignKey(Tecnicatura, on_delete=models.PROTECT, related_name="resoluciones")
    tipo = models.CharField(max_length=32, choices=TipoResolucion.choices, default=TipoResolucion.NORMAL)
    estado = models.CharField(max_length=32, choices=EstadoResolucion.choices, default=EstadoResolucion.EN_PROCESO)
    resolucion_nro = models.CharField(max_length=100, blank=True)
    fecha = models.DateField()
    batch_id = models.UUIDField(null=True, blank=True, db_index=True, default=None)
    archivo_docx = models.FileField(upload_to="resoluciones/docx/", null=True, blank=True)
    archivo_pdf = models.FileField(upload_to="resoluciones/pdf/", null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-creado_en"]
        verbose_name = "resolución"
        verbose_name_plural = "resoluciones"

    def __str__(self):
        numero = self.resolucion_nro or "Sin número"
        return f"{numero} — {self.alumno}"


class ResolucionMateria(models.Model):
    resolucion = models.ForeignKey(Resolucion, on_delete=models.CASCADE, related_name="materias")
    materia = models.ForeignKey(Materia, on_delete=models.PROTECT, related_name="equivalencias")
    carrera_origen = models.ForeignKey(CarreraOrigen, on_delete=models.PROTECT, related_name="equivalencias")
    equivalencia = models.TextField()
    anio_cursado = models.PositiveSmallIntegerField()
    institucion = models.CharField(max_length=200)
    situacion = models.CharField(
        max_length=20,
        choices=SituacionEquivalencia.choices,
        default=SituacionEquivalencia.CORRESPONDE,
    )

    class Meta:
        verbose_name = "materia de resolución"
        verbose_name_plural = "materias de resolución"

    def __str__(self):
        return f"{self.materia} — {self.resolucion}"
