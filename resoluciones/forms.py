from django import forms

from catalogos.models import CarreraOrigen, Materia, Tecnicatura
from resoluciones.models import SituacionEquivalencia, TipoResolucion


class GenerarResolucionForm(forms.Form):
    nombre = forms.CharField(max_length=100)
    apellido = forms.CharField(max_length=100)
    dni = forms.CharField(max_length=20)
    tecnicatura_id = forms.IntegerField(min_value=1)
    tipo = forms.ChoiceField(choices=TipoResolucion.choices)
    resolucion_nro = forms.CharField(max_length=100, required=False)
    materias = forms.JSONField()

    def clean_tecnicatura_id(self):
        tecnicatura_id = self.cleaned_data["tecnicatura_id"]
        if not Tecnicatura.objects.filter(pk=tecnicatura_id, activo=True).exists():
            raise forms.ValidationError("La tecnicatura no existe o está dada de baja.")
        return tecnicatura_id

    def clean_materias(self):
        materias = self.cleaned_data["materias"]
        if not isinstance(materias, list) or not materias:
            raise forms.ValidationError("Debe enviar al menos una materia.")

        errores = []
        normalizadas = []
        for index, item in enumerate(materias, start=1):
            try:
                materia_id = int(item["materia_id"])
                carrera_origen_id = int(item["carrera_origen_id"])
                equivalencia = str(item["equivalencia"]).strip()
                anio_cursado = int(item["anio_cursado"])
                institucion = str(item["institucion"]).strip()
                situacion = str(item.get("situacion", SituacionEquivalencia.CORRESPONDE)).strip().lower().replace(" ", "_")
            except (KeyError, TypeError, ValueError):
                errores.append(f"Materia {index}: datos incompletos o inválidos.")
                continue
            if situacion not in SituacionEquivalencia.values:
                errores.append(f"Materia {index}: situación debe ser Corresponde o No corresponde.")
                continue
            if not equivalencia or not institucion or not 1900 <= anio_cursado <= 3000:
                errores.append(f"Materia {index}: equivalencia, institución y año son obligatorios.")
                continue
            if not Materia.objects.filter(pk=materia_id, activo=True).exists():
                errores.append(f"Materia {index}: la materia no existe o está dada de baja.")
            if not CarreraOrigen.objects.filter(pk=carrera_origen_id, activo=True).exists():
                errores.append(f"Materia {index}: la carrera de origen no existe o está dada de baja.")
            normalizadas.append(
                {
                    "materia_id": materia_id,
                    "carrera_origen_id": carrera_origen_id,
                    "equivalencia": equivalencia,
                    "anio_cursado": anio_cursado,
                    "institucion": institucion,
                    "situacion": situacion,
                }
            )
        if errores:
            raise forms.ValidationError(errores)
        return normalizadas
