-- EJECUTAR EN EL DW. Este archivo se debe ejecutar IDENTICO dos veces:
--   (1) SIN indices especificos (antes)
--   (2) DESPUES de 02_marts_indices.sql (despues)
-- No cambie datos, condiciones, SELECT, filtros, configuracion o servidor entre corridas.
-- Ejecutar con auto_sync.py detenido. Las 2 primeras consultas son las originales del proyecto.
ANALYZE dw.hecho_cobro;
ANALYZE dw.hecho_detalle;

-- Q1: Recaudacion 2026 (original sql/04_optimizacion_2_consultas.sql)
EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT fecha_key, actividad_key, SUM(importe) AS recaudo
FROM dw.hecho_cobro
WHERE es_prueba=false AND fecha_key BETWEEN 20260101 AND 20261231
GROUP BY fecha_key,actividad_key;

-- Q2: Ventas reconocidas 2026 (original sql/04_optimizacion_2_consultas.sql)
EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT fecha_key, actividad_key, SUM(venta_reconocida) AS venta
FROM dw.hecho_detalle
WHERE es_prueba=false AND venta_reconocida IS NOT NULL
AND fecha_key BETWEEN 20260101 AND 20261231
GROUP BY fecha_key,actividad_key;

-- Q3-Q4 opcionales: para medir capacidad de acceso por fechas selectivas.
-- Los rangos siguientes son un EJEMPLO. Antes de la primera ejecucion,
-- elegir un rango real de un mes donde haya filas elegibles segun SQL 06.
-- Luego mantenerlo EXACTAMENTE IGUAL en la corrida despues.
EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT fecha_key, actividad_key, SUM(importe) AS recaudo
FROM dw.hecho_cobro
WHERE es_prueba=false AND fecha_key BETWEEN 20261001 AND 20261031
GROUP BY fecha_key,actividad_key;

EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT fecha_key, actividad_key, SUM(venta_reconocida) AS venta
FROM dw.hecho_detalle
WHERE es_prueba=false AND venta_reconocida IS NOT NULL
AND fecha_key BETWEEN 20261001 AND 20261031
GROUP BY fecha_key,actividad_key;
