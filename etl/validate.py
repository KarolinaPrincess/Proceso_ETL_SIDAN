"""Conciliación independiente de totales OLTP y DW (solo lecturas).
Ejecutar DESPUÉS de python pipeline.py --full. No imprime PII.
"""
import os
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv
import psycopg
load_dotenv(Path(__file__).with_name('.env'))
Q={
 'wompi':("""SELECT COALESCE(SUM(p.monto),0) FROM public.tbl_pagos p
 JOIN public.tbl_ordenes o USING(id_orden) WHERE p.proveedor='wompi'
 AND p.estado='confirmado' AND RIGHT(o.estado,7) <> '_prueba'""",
 "SELECT COALESCE(SUM(importe),0) FROM dw.hecho_cobro WHERE origen='wompi' AND NOT es_prueba"),
 'manual':("""SELECT COALESCE(SUM(a.monto_recibido),0) FROM public.tbl_abonos_transferencia a
 JOIN public.tbl_pagos p USING(id_pago) JOIN public.tbl_ordenes o USING(id_orden)
 WHERE p.proveedor IN ('efectivo','transferencia') AND a.estado='confirmado'
 AND RIGHT(o.estado,7) <> '_prueba'""",
 "SELECT COALESCE(SUM(importe),0) FROM dw.hecho_cobro WHERE origen='abono' AND NOT es_prueba"),
 'ventas_reconocidas':("""SELECT COALESCE(SUM(d.venta_neta_confirmada),0)
 FROM public.tbl_detalles_orden d JOIN public.tbl_ordenes o USING(id_orden)
 WHERE d.fecha_confirmacion_financiera IS NOT NULL AND RIGHT(o.estado,7) <> '_prueba'
 AND (d.tipo_concepto <> 'producto' OR d.cantidad_entregada >= d.cantidad)""",
 "SELECT COALESCE(SUM(venta_reconocida),0) FROM dw.hecho_detalle WHERE NOT es_prueba"),
 'ordenes':("SELECT COUNT(*) FROM public.tbl_ordenes", "SELECT COUNT(*) FROM dw.hecho_orden"),
 'inscripciones':("SELECT COUNT(*) FROM public.tbl_inscripciones", "SELECT COUNT(*) FROM dw.hecho_inscripcion"),
 'detalles':("SELECT COUNT(*) FROM public.tbl_detalles_orden", "SELECT COUNT(*) FROM dw.hecho_detalle")
}

def verify():
    ol=os.getenv('OLTP_DSN');dw=os.getenv('DW_DSN')
    if not ol or not dw: raise RuntimeError('Configurar DSN en etl/.env')
    failures=[]
    with psycopg.connect(ol) as src, psycopg.connect(dw) as dest:
        for label,(qs,qd) in Q.items():
            a=src.execute(qs).fetchone()[0]
            b=dest.execute(qd).fetchone()[0]
            print(f'{label:19s} OLTP={a} | DW={b} | {"OK" if a==b else "DIFERENCIA"}')
            if a!=b:failures.append(label)
    if failures:
        raise SystemExit('CONCILIACION FALLIDA en: '+', '.join(failures))
    print('Conciliación aprobada para estos agregados. No sustituye otras verificaciones de calidad.')
if __name__=='__main__': verify()
