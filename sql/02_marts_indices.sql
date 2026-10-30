-- Solo en sidan_dw, DESPUES de 01_dw_schema.sql
BEGIN;
CREATE INDEX IF NOT EXISTS ix_orden_fecha_act ON dw.hecho_orden(fecha_key, actividad_key);
CREATE INDEX IF NOT EXISTS ix_orden_estado ON dw.hecho_orden(estado, actividad_key) INCLUDE(total);
CREATE INDEX IF NOT EXISTS ix_cobro_fecha_act ON dw.hecho_cobro(fecha_key, actividad_key) INCLUDE(importe) WHERE es_prueba = false;
CREATE INDEX IF NOT EXISTS ix_detalle_fecha_act ON dw.hecho_detalle(fecha_key, actividad_key) INCLUDE(venta_reconocida, costo_reconocido)
  WHERE es_prueba = false AND venta_reconocida IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_inscripcion_estado_act ON dw.hecho_inscripcion(actividad_key, estado);
CREATE INDEX IF NOT EXISTS ix_cierre_act ON dw.hecho_cierre(actividad_key, clasificacion);
-- Vistas: una fila de hecho por origen, nunca unir directamente cobros y detalles.
CREATE OR REPLACE VIEW mart.recaudacion_mensual AS
SELECT a.id_actividad, a.nombre AS actividad, f.anio, f.mes,
       SUM(c.importe) AS recaudado, COUNT(*) AS movimientos
FROM dw.hecho_cobro c JOIN dw.dim_actividad a USING (actividad_key)
JOIN dw.dim_fecha f USING(fecha_key)
WHERE NOT c.es_prueba
GROUP BY a.id_actividad,a.nombre,f.anio,f.mes;
CREATE OR REPLACE VIEW mart.ventas_reconocidas_mensual AS
SELECT a.id_actividad, a.nombre AS actividad, f.anio, f.mes,
       SUM(d.venta_reconocida) AS ventas_reconocidas,
       SUM(d.costo_reconocido) AS costo_conocido,
       SUM(d.ganancia_reconocida) AS ganancia_conocida,
       COUNT(*) FILTER (WHERE d.costo_reconocido IS NOT NULL) AS lineas_con_costo,
       COUNT(*) AS lineas_reconocidas
FROM dw.hecho_detalle d JOIN dw.dim_actividad a USING (actividad_key)
JOIN dw.dim_fecha f USING(fecha_key)
WHERE NOT d.es_prueba AND d.venta_reconocida IS NOT NULL
GROUP BY a.id_actividad,a.nombre,f.anio,f.mes;
CREATE OR REPLACE VIEW mart.cartera_orden AS
WITH ingresos AS (
   SELECT id_orden, SUM(importe) AS recaudado
   FROM dw.hecho_cobro WHERE NOT es_prueba GROUP BY id_orden
)
SELECT o.id_orden, o.actividad_key, o.fecha_key, o.estado,
       o.total, COALESCE(i.recaudado,0)::NUMERIC(14,2) AS recaudado,
       GREATEST(0,o.total - COALESCE(i.recaudado,0))::NUMERIC(14,2) AS saldo,
       (o.estado = 'pendiente_pago'
        AND (o.expira_en IS NULL OR o.expira_en > now())
        AND (o.limite_saldo_en IS NULL OR o.limite_saldo_en > now())) AS vigente
FROM dw.hecho_orden o LEFT JOIN ingresos i USING(id_orden)
WHERE NOT o.es_prueba;
COMMIT;
