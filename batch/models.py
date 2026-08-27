import uuid

from django.db import models


class EstadoLote(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    PROCESANDO = "procesando", "Procesando"
    COMPLETADO = "completado", "Completado"
    CON_ERRORES = "con_errores", "Con errores"


class LoteCarga(models.Model):
    batch_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    archivo_original = models.CharField(max_length=255)
    total_filas = models.PositiveIntegerField()
    total_resoluciones = models.PositiveIntegerField(default=0)
    errores = models.JSONField(default=list, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoLote.choices,
        default=EstadoLote.PENDIENTE,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "lote de carga"
        verbose_name_plural = "lotes de carga"

    def __str__(self):
        return f"Lote {self.batch_id} ({self.archivo_original})"
