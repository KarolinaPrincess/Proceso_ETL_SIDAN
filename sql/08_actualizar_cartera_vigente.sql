-- SOLO ejecutar en la base DW (sidan_dw); NO en el OLTP/Laravel.
-- Aplica la nueva regla de KPI-03 y KPI-09 sin recrear tablas ni índices.
-- Se preservan las primeras ocho columnas de mart.cartera_orden.
BEGIN;
-- Cartera cobrable: las vencidas con abonos mantienen una ventana de 30 dias
-- desde su vencimiento ORIGINAL (limite_saldo_en o, en historicos, expira_en).
-- Se conservan las primeras ocho columnas de la vista para compatibilidad.
CREATE OR REPLACE VIEW mart.cartera_orden AS
WITH ingresos AS (
    SELECT id_orden, SUM(importe) AS recaudado
    FROM dw.hecho_cobro
    WHERE NOT es_prueba
    GROUP BY id_orden
), base AS (
    SELECT
        o.id_orden, o.actividad_key, o.fecha_key, o.estado,
        o.total,
        COALESCE(i.recaudado, 0)::NUMERIC(14,2) AS recaudado,
        GREATEST(0, o.total - COALESCE(i.recaudado, 0))::NUMERIC(14,2) AS saldo,
        o.cierre_financiero_estado,
        o.expira_en,
        o.limite_saldo_en,
        COALESCE(o.limite_saldo_en, o.expira_en) AS vencimiento_original
    FROM dw.hecho_orden o
    LEFT JOIN ingresos i USING (id_orden)
    WHERE NOT o.es_prueba
), clasificada AS (
    SELECT b.*,
        (
            b.estado = 'pendiente_pago'
            AND (b.expira_en IS NULL OR b.expira_en > now())
            AND (b.limite_saldo_en IS NULL OR b.limite_saldo_en > now())
            AND b.saldo > 0
        ) AS vigente_ordinaria,
        (
            b.estado = 'vencida'
            AND b.cierre_financiero_estado IN ('regularizacion', 'pendiente_revision')
            AND b.vencimiento_original IS NOT NULL
            AND b.vencimiento_original <= now()
            AND now() < b.vencimiento_original + INTERVAL '30 days'
            AND b.recaudado > 0
            AND b.saldo > 0
        ) AS en_regularizacion
    FROM base b
)
SELECT
    id_orden, actividad_key, fecha_key, estado,
    total, recaudado, saldo,
    (vigente_ordinaria OR en_regularizacion) AS vigente,
    vigente_ordinaria,
    en_regularizacion
FROM clasificada;
COMMIT;
