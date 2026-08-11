from django.test import TestCase

from resoluciones.models import Resolucion


class GenerarResolucionViewTests(TestCase):
    def test_payload_sin_dni_devuelve_400_y_no_crea_resolucion(self):
        response = self.client.post(
            "/api/generate/",
            data="""{
                "alumno": {"nombre": "Ana", "apellido": "Pérez"},
                "tecnicatura_id": 1,
                "tipo": "normal",
                "materias": []
            }""",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Resolucion.objects.count(), 0)
