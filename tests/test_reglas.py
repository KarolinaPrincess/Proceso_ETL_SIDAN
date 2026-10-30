"""Pruebas de reglas puras. Ejecutar con dependencias del ETL instaladas."""
import sys
import unittest
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'etl'))
from pipeline import money,fecha_key,es_prueba
class ReglasTest(unittest.TestCase):
    def test_centavos(self): self.assertEqual(money('12.345'),Decimal('12.35'))
    def test_negativos(self):
        with self.assertRaises(ValueError): money('-1.00')
    def test_nulo(self):
        with self.assertRaises(ValueError): money(None)
        self.assertIsNone(money(None,nullable=True))
    def test_prueba(self):
        self.assertTrue(es_prueba('pagada_prueba'))
        self.assertFalse(es_prueba('pagada'))
    def test_zona_salvador(self):
        self.assertEqual(fecha_key(datetime(2026,10,26,2,0,tzinfo=timezone.utc)),20261025)
    def test_fecha_sin_tz(self):
        with self.assertRaises(ValueError): fecha_key(datetime(2026,10,26))
if __name__=='__main__': unittest.main()
