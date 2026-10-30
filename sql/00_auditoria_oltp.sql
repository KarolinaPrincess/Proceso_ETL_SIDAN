-- SIDAN BI - EJECUTAR EN LA BASE OLTP DE SIDAN CON SOLO LECTURA.
-- NO crea, actualiza ni borra datos. Adjuntar resultados SIN datos personales.
SELECT current_database() AS base_actual, current_setting('server_version') AS version_pg;
SELECT table_name FROM information_schema.tables
WHERE table_schema='public' AND table_name IN (
 'tbl_actividades','tbl_categorias','tbl_items_actividad','tbl_inscripciones',
 'tbl_ordenes','tbl_detalles_orden','tbl_pagos','tbl_abonos_transferencia',
 'tbl_aplicaciones_abono','tbl_entregas_detalle','tbl_cierres_orden')
ORDER BY table_name;
-- Revisión de columnas (sin valores privados).
SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name IN ('tbl_ordenes','tbl_detalles_orden','tbl_pagos','tbl_abonos_transferencia')
ORDER BY table_name,ordinal_position;
-- Estado de procesos.
SELECT 'ordenes' AS entidad, estado,COUNT(*) AS cantidad FROM public.tbl_ordenes GROUP BY estado
UNION ALL
SELECT 'inscripciones', estado,COUNT(*) FROM public.tbl_inscripciones GROUP BY estado
UNION ALL
SELECT 'pagos',estado,COUNT(*) FROM public.tbl_pagos GROUP BY estado
ORDER BY entidad,estado;
-- Volúmenes independientes (no realizar joins 1:N al sumar).
SELECT 'actividades' AS tabla,COUNT(*) AS filas FROM public.tbl_actividades
UNION ALL SELECT 'ordenes',COUNT(*) FROM public.tbl_ordenes
UNION ALL SELECT 'detalles',COUNT(*) FROM public.tbl_detalles_orden
UNION ALL SELECT 'inscripciones',COUNT(*) FROM public.tbl_inscripciones
UNION ALL SELECT 'pagos',COUNT(*) FROM public.tbl_pagos
UNION ALL SELECT 'abonos',COUNT(*) FROM public.tbl_abonos_transferencia
UNION ALL SELECT 'cierres',COUNT(*) FROM public.tbl_cierres_orden;
-- CUADRATURA 1: recaudacion real = Wompi confirmado + abonos manuales confirmados.
SELECT 'WOMPI' AS origen,COUNT(*) AS movimientos,COALESCE(SUM(p.monto),0) AS recaudado
FROM public.tbl_pagos p JOIN public.tbl_ordenes o USING(id_orden)
WHERE p.proveedor='wompi' AND p.estado='confirmado' AND o.estado NOT LIKE '%_prueba'
UNION ALL
SELECT 'ABONOS',COUNT(*),COALESCE(SUM(a.monto_recibido),0)
FROM public.tbl_abonos_transferencia a JOIN public.tbl_pagos p USING(id_pago)
JOIN public.tbl_ordenes o USING(id_orden)
WHERE p.proveedor IN ('efectivo','transferencia') AND a.estado='confirmado'
AND o.estado NOT LIKE '%_prueba';
-- CUADRATURA 2: ingreso reconocido, sin duplicar ni computar anticipos como venta.
SELECT d.tipo_concepto,COUNT(*) AS lineas,
 COALESCE(SUM(d.venta_neta_confirmada),0) AS venta_reconocida,
 COALESCE(SUM(d.costo_total_confirmado),0) AS costo_documentado
FROM public.tbl_detalles_orden d JOIN public.tbl_ordenes o USING(id_orden)
WHERE d.fecha_confirmacion_financiera IS NOT NULL AND o.estado NOT LIKE '%_prueba'
AND (d.tipo_concepto <> 'producto' OR d.cantidad_entregada >= d.cantidad)
GROUP BY d.tipo_concepto;
-- Control de datos faltantes: informar al desarrollador el conteo.
SELECT COUNT(*) AS reconocidas_sin_costo
FROM public.tbl_detalles_orden d JOIN public.tbl_ordenes o USING(id_orden)
WHERE d.fecha_confirmacion_financiera IS NOT NULL AND d.costo_total_confirmado IS NULL
AND o.estado NOT LIKE '%_prueba';
-- Alerta de integridad financiera: abonos confirmados sin importe.
SELECT COUNT(*) AS abonos_sin_importe FROM public.tbl_abonos_transferencia
WHERE estado='confirmado' AND monto_recibido IS NULL;
-- Detectar componentes todavía no registrados en la BD (sin adivinar).
SELECT to_regclass('public.tbl_gastos') AS tabla_gastos,
 to_regclass('public.tbl_asistencias') AS tabla_asistencias;
