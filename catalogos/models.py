from django.db import models

from core.models import CatalogoBaseModel


class Alumno(CatalogoBaseModel):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(max_length=20, unique=True, db_index=True)

    class Meta:
        ordering = ["apellido", "nombre"]
        verbose_name = "alumno"
        verbose_name_plural = "alumnos"

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.dni})"


class CarreraOrigen(CatalogoBaseModel):
    nombre = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "carrera de origen"
        verbose_name_plural = "carreras de origen"

    def __str__(self):
        return self.nombre


class Tecnicatura(CatalogoBaseModel):
    nombre = models.CharField(max_length=200, unique=True)
    res_ministerial = models.CharField(max_length=100)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tecnicatura"
        verbose_name_plural = "tecnicaturas"

    def __str__(self):
        return self.nombre


class Materia(CatalogoBaseModel):
    nombre = models.CharField(max_length=200, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "materia"
        verbose_name_plural = "materias"

    def __str__(self):
        return self.nombre
