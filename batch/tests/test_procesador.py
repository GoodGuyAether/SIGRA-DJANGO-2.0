from django.test import SimpleTestCase

from batch.services.procesador import CSVInvalidoError, agrupar_por_dni, parsear_y_validar_csv


class ProcesadorCSVTests(SimpleTestCase):
    def test_agrupa_todas_las_materias_por_dni_en_orden_de_primera_aparicion(self):
        grupos = agrupar_por_dni(
            [
                {"dni": "1", "materia": "A"},
                {"dni": "2", "materia": "B"},
                {"dni": "1", "materia": "C"},
            ]
        )
        self.assertEqual([[fila["materia"] for fila in grupo] for grupo in grupos], [["A", "C"], ["B"]])

    def test_reporta_las_filas_invalidas_en_una_sola_pasada(self):
        contenido = (
            "nombre,apellido,dni,materia,equivalencia,tecnicatura,res_ministerial,año_cursado,institucion,carrera_origen,situacion\n"
            "Ana,Pérez,,Programación,Equivalencia,Tecnicatura,RM 1,2024,Instituto,Carrera,Corresponde\n"
            "Beto,Gómez,2,Matemática,Equivalencia,Tecnicatura,RM 1,no-es-año,Instituto,Carrera,No Corresponde\n"
        ).encode()
        with self.assertRaises(CSVInvalidoError) as context:
            parsear_y_validar_csv(contenido)
        self.assertEqual([error["fila"] for error in context.exception.errores], [2, 3])
