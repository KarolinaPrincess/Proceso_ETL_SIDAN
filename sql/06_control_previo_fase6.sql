-- EJECUTAR SOLO EN EL DATA WAREHOUSE DE PRUEBAS (db_sidan_dw o db_sidan_dw_bench).
-- Solo lectura. Ejecutar antes de las mediciones y de nuevo despues de crear indices.
SELECT current_database() AS base_activa, inet_server_port() AS puerto;

-- Indices especificamente propuestos en el archivo original 02_marts_indices.sql.
-- Si hay resultados en este SELECT, no se dispone de linea base sin esos indices.
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'dw'
AND indexname IN (
 'ix_orden_fecha_act', 'ix_orden_estado', 'ix_cobro_fecha_act',
 'ix_detalle_fecha_act', 'ix_inscripcion_estado_act', 'ix_cierre_act')
ORDER BY tablename,indexname;

-- Cobertura de fechas, tamaño de muestra y filas elegibles del KPI.
SELECT 'cobros' AS entidad, COUNT(*) AS total,
       COUNT(*) FILTER (WHERE NOT es_prueba) AS elegibles,
       COUNT(*) FILTER (WHERE NOT es_prueba AND fecha_key BETWEEN 20260101 AND 20261231) AS elegibles_2026,
       MIN(fecha_key) AS primera_fecha_key,MAX(fecha_key) AS ultima_fecha_key,
       COUNT(DISTINCT actividad_key) AS actividades
FROM dw.hecho_cobro
UNION ALL
SELECT 'detalles',COUNT(*),
       COUNT(*) FILTER (WHERE NOT es_prueba AND venta_reconocida IS NOT NULL),
       COUNT(*) FILTER (WHERE NOT es_prueba AND venta_reconocida IS NOT NULL AND fecha_key BETWEEN 20260101 AND 20261231),
       MIN(fecha_key),MAX(fecha_key),COUNT(DISTINCT actividad_key)
FROM dw.hecho_detalle;

-- Filas elegibles por mes: elegir un mes CON DATOS para mediciones de intervalo selectivo.
SELECT 'cobros' AS entidad, f.anio, f.mes, COUNT(*) AS filas_elegibles
FROM dw.hecho_cobro c JOIN dw.dim_fecha f USING(fecha_key)
WHERE NOT c.es_prueba GROUP BY f.anio,f.mes
UNION ALL
SELECT 'detalles',f.anio,f.mes,COUNT(*)
FROM dw.hecho_detalle d JOIN dw.dim_fecha f USING(fecha_key)
WHERE NOT d.es_prueba AND d.venta_reconocida IS NOT NULL
GROUP BY f.anio,f.mes
ORDER BY anio,mes,entidad;

-- Sumas que deben mantenerse iguales antes y despues de crear indices (misma fuente y mismos filtros).
SELECT 'cobros_2026' AS indicador,COUNT(*) AS filas,COALESCE(SUM(importe),0) AS importe
FROM dw.hecho_cobro WHERE NOT es_prueba AND fecha_key BETWEEN 20260101 AND 20261231
UNION ALL
SELECT 'ventas_2026',COUNT(*),COALESCE(SUM(venta_reconocida),0)
FROM dw.hecho_detalle WHERE NOT es_prueba AND venta_reconocida IS NOT NULL
  AND fecha_key BETWEEN 20260101 AND 20261231;

-- Estado de la ultima ejecucion ETL.
SELECT id_ejecucion, modo, estado, inicio, fin, filas_extraidas, filas_cargadas
FROM meta.ejecucion ORDER BY id_ejecucion DESC LIMIT 5;
