from django.db import models


class CatalogoBaseModel(models.Model):
    """Common fields for catalog records that support logical deletion."""

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
