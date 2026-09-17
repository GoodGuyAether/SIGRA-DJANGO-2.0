import importlib.util
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from catalogos.models import Alumno, CarreraOrigen, Materia, Tecnicatura
from resoluciones.models import EstadoResolucion
from resoluciones.services.generador import _contexto_documento, _template_path, generar_resolucion
from types import SimpleNamespace
from resoluciones.models import SituacionMateria


class SeleccionTemplateTests(SimpleTestCase):
    @override_settings(
        TEMPLATE_PATH="base.docx",
        TEMPLATE_OTORGADAS_PATH="otorgadas.docx",
        TEMPLATE_NO_OTORGADAS_PATH="no_otorgadas.docx",
        TEMPLATE_MIXTA_PATH="mixta.docx",
    )
    def test_selecciona_template_segun_situaciones(self):
        corresponde = [{"situacion": SituacionMateria.CORRESPONDE}]
        no_corresponde = [{"situacion": SituacionMateria.NO_CORRESPONDE}]
        mixta = corresponde + no_corresponde
        self.assertEqual(_template_path(corresponde).name, "otorgadas.docx")
        self.assertEqual(_template_path(no_corresponde).name, "no_otorgadas.docx")
        self.assertEqual(_template_path(mixta).name, "mixta.docx")


@skipUnless(importlib.util.find_spec("docxtpl"), "docxtpl no está instalado")
class GeneradorResolucionTests(TestCase):
    def setUp(self):
        self.alumno = Alumno.objects.create(nombre="ana maría", apellido="perez", dni="12345678")
        self.tecnicatura = Tecnicatura.objects.create(nombre="Desarrollo de Software", res_ministerial="RM 1/2026")
        self.carrera = CarreraOrigen.objects.create(nombre="Analista de Sistemas")
        self.materia = Materia.objects.create(nombre="Programación I")

    @patch("resoluciones.services.generador.convertir_a_pdf", return_value=None)
    def test_genera_docx_y_mantiene_estado_generada_si_falla_pdf(self, _convertir_a_pdf):
        with TemporaryDirectory() as temp_dir:
            media_root = f"{temp_dir}/media"
            output_dir = f"{media_root}/salidas"
            with override_settings(MEDIA_ROOT=media_root, OUTPUT_DIR=output_dir):
                resolucion = generar_resolucion(
                    alumno=self.alumno,
                    tecnicatura=self.tecnicatura,
                    tipo="normal",
                    resolucion_nro="1/2026",
                    materias=[
                        {
                            "materia_id": self.materia.pk,
                            "carrera_origen_id": self.carrera.pk,
                            "equivalencia": "Aprobada por equivalencia",
                            "anio_cursado": 2024,
                            "institucion": "Instituto de Prueba",
                        }
                    ],
                )

        self.assertEqual(resolucion.estado, EstadoResolucion.GENERADA)
        self.assertFalse(bool(resolucion.archivo_pdf))
        self.assertTrue(resolucion.archivo_docx.name.startswith("salidas/"))
        self.assertEqual(resolucion.materias.count(), 1)


class ContextoSituacionTests(TestCase):
    def test_separa_materias_por_situacion(self):
        alumno = SimpleNamespace(nombre="Ana", apellido="Pérez", dni="1")
        tecnicatura = SimpleNamespace(nombre="Sistemas", res_ministerial="RM 1")
        materias = [
            {"materia": "A", "equivalencia": "EA", "institucion": "I", "carrera_origen": "C", "anio_cursado": 2024, "situacion": SituacionMateria.CORRESPONDE},
            {"materia": "B", "equivalencia": "EB", "institucion": "I", "carrera_origen": "C", "anio_cursado": 2024, "situacion": SituacionMateria.NO_CORRESPONDE},
        ]
        contexto = _contexto_documento(alumno, tecnicatura, "normal", materias, "1")
        self.assertEqual([item["materia"] for item in contexto["materias_corresponden"]], ["A"])
        self.assertEqual([item["materia"] for item in contexto["materias_no_corresponden"]], ["B"])
        self.assertTrue(contexto["hay_no_corresponden"])
