-- SIDAN BI / Ejecutar en sidan_dw en dos momentos:
-- A) después de ETL inicial y ANTES de 02_marts_indices.sql
-- B) después de 02_marts_indices.sql y ANALYZE de hechos.
-- Copiar la salida en docs/registro_evidencias.md, nunca inventar tiempos.
ANALYZE dw.hecho_cobro;
ANALYZE dw.hecho_detalle;
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT fecha_key,actividad_key,SUM(importe) AS recaudo
FROM dw.hecho_cobro WHERE es_prueba=false
AND fecha_key BETWEEN 20260101 AND 20261231
GROUP BY fecha_key,actividad_key;
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT fecha_key,actividad_key,SUM(venta_reconocida) AS venta
FROM dw.hecho_detalle
WHERE es_prueba=false AND venta_reconocida IS NOT NULL
AND fecha_key BETWEEN 20260101 AND 20261231
GROUP BY fecha_key,actividad_key;
-- Advertencia: si las tablas son pequeñas, el planificador puede preferir Seq Scan.
-- Eso NO es una falla. Documentar buffers, plan, latencia y volumen de filas.
