
-- =====================================================
-- SIDAN BI - EVALUACIÓN DE RENDIMIENTO
-- =====================================================
-- Base: db_sidan_dw
--
-- Período anual: 2025
-- Período mensual: junio de 2026
--
-- EJECUTAR DOS VECES:
-- 1. Sin índices experimentales.
-- 2. Con índices experimentales.
--
-- No modificar consultas entre mediciones.
-- Mantener auto_sync.py detenido.
-- =====================================================


-- =====================================================
-- Q1. RECAUDACIÓN CONFIRMADA - AÑO 2025
-- =====================================================

EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT
    fecha_key,
    actividad_key,
    SUM(importe) AS recaudo
FROM dw.hecho_cobro
WHERE es_prueba = false
  AND fecha_key BETWEEN 20250101 AND 20251231
GROUP BY
    fecha_key,
    actividad_key;


-- =====================================================
-- Q2. VENTAS RECONOCIDAS - AÑO 2025
-- =====================================================

EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT
    fecha_key,
    actividad_key,
    SUM(venta_reconocida) AS venta
FROM dw.hecho_detalle
WHERE es_prueba = false
  AND venta_reconocida IS NOT NULL
  AND fecha_key BETWEEN 20250101 AND 20251231
GROUP BY
    fecha_key,
    actividad_key;


-- =====================================================
-- Q3. RECAUDACIÓN CONFIRMADA - JUNIO 2026
-- =====================================================

EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT
    fecha_key,
    actividad_key,
    SUM(importe) AS recaudo
FROM dw.hecho_cobro
WHERE es_prueba = false
  AND fecha_key BETWEEN 20260601 AND 20260630
GROUP BY
    fecha_key,
    actividad_key;


-- =====================================================
-- Q4. VENTAS RECONOCIDAS - JUNIO 2026
-- =====================================================

EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT)
SELECT
    fecha_key,
    actividad_key,
    SUM(venta_reconocida) AS venta
FROM dw.hecho_detalle
WHERE es_prueba = false
  AND venta_reconocida IS NOT NULL
  AND fecha_key BETWEEN 20260601 AND 20260630
GROUP BY
    fecha_key,
    actividad_key;
