-- Todas estas consultas se ejecutan en sidan_dw (solo lectura).
-- KPI: recaudacion efectiva por mes, excluye sandbox Wompi.
SELECT anio,mes,SUM(recaudado) AS recaudado
FROM mart.recaudacion_mensual GROUP BY anio,mes ORDER BY anio,mes;
-- Consulta CORRECTA de margen por mes (mismo conjunto de lineas para numerador y denominador).
SELECT f.anio,f.mes, SUM(d.ganancia_reconocida) AS ganancia_bruta,
 ROUND(100*SUM(d.ganancia_reconocida)/NULLIF(SUM(d.venta_reconocida),0),2) AS margen_pct
FROM dw.hecho_detalle d JOIN dw.dim_fecha f USING(fecha_key)
WHERE NOT d.es_prueba AND d.costo_reconocido IS NOT NULL AND d.venta_reconocida IS NOT NULL
GROUP BY f.anio,f.mes ORDER BY f.anio,f.mes;
-- Comparacion multidimensional por actividad, canal y mes de emision (importe de ordenes, NO ingreso).
SELECT a.nombre, f.anio,f.mes,o.canal_venta,
       COUNT(*) AS ordenes, SUM(o.total) AS importe_ordenado
FROM dw.hecho_orden o JOIN dw.dim_actividad a USING(actividad_key)
JOIN dw.dim_fecha f USING(fecha_key) WHERE NOT o.es_prueba
GROUP BY GROUPING SETS ((a.nombre,f.anio,f.mes,o.canal_venta),(f.anio,f.mes),());
-- Cuadratura interna de recaudacion a nivel de movimientos y fact.
SELECT origen, COUNT(*) AS movimientos, SUM(importe) AS total
FROM dw.hecho_cobro WHERE NOT es_prueba GROUP BY origen;
-- Control de duplicados (debe retornar cero filas).
SELECT origen,id_movimiento,COUNT(*) FROM dw.hecho_cobro GROUP BY 1,2 HAVING COUNT(*)>1;
-- Control de ventas reconocidas solo en entregas completas para tipo producto (cero filas).
SELECT id_detalle_orden FROM dw.hecho_detalle
WHERE tipo_concepto = 'producto' AND venta_reconocida IS NOT NULL AND cantidad_entregada < cantidad;
-- Para lineas sin costo, no se presume ganancia.
SELECT count(*) AS lineas_reconocidas_sin_costo FROM dw.hecho_detalle
WHERE venta_reconocida IS NOT NULL AND costo_reconocido IS NULL AND NOT es_prueba;
