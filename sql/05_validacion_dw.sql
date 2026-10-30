-- SOLO DW, despues de la carga.
SELECT id_ejecucion,modo,estado,inicio,fin,filas_extraidas,filas_cargadas
FROM meta.ejecucion ORDER BY id_ejecucion DESC LIMIT 10;
SELECT 'ordenes' tabla,COUNT(*) filas FROM dw.hecho_orden
UNION ALL SELECT 'detalles',COUNT(*) FROM dw.hecho_detalle
UNION ALL SELECT 'pagos',COUNT(*) FROM dw.hecho_cobro
UNION ALL SELECT 'inscripciones',COUNT(*) FROM dw.hecho_inscripcion
UNION ALL SELECT 'cierres',COUNT(*) FROM dw.hecho_cierre;
-- Monto recaudado: debe cuadrar con la suma de ambas filas de auditoría OLTP.
SELECT origen,COUNT(*) AS movimientos,SUM(importe) AS importe
FROM dw.hecho_cobro WHERE NOT es_prueba GROUP BY origen;
-- Ventas reconocidas por concepto: debe cuadrar con SQL 00, por tipo.
SELECT tipo_concepto,COUNT(*) AS lineas,SUM(venta_reconocida) AS importe
FROM dw.hecho_detalle WHERE NOT es_prueba AND venta_reconocida IS NOT NULL
GROUP BY tipo_concepto;
-- Las siguientes deben devolver CERO filas:
SELECT id_orden,COUNT(*) FROM dw.hecho_orden GROUP BY 1 HAVING COUNT(*)>1;
SELECT origen,id_movimiento,COUNT(*) FROM dw.hecho_cobro GROUP BY 1,2 HAVING COUNT(*)>1;
SELECT id_detalle_orden FROM dw.hecho_detalle
WHERE tipo_concepto='producto' AND venta_reconocida IS NOT NULL AND cantidad_entregada < cantidad;
-- Actividades presentes no huérfanas:
SELECT COUNT(*) AS actividades_en_hechos_sin_dim
FROM dw.hecho_orden o LEFT JOIN dw.dim_actividad a USING(actividad_key)
WHERE a.actividad_key IS NULL;
