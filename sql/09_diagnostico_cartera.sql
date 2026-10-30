-- Ejecutar SOLO en sidan_dw, una vez aplicado 08_actualizar_cartera_vigente.sql.
-- No expone correos ni datos personales. Las cifras son saldos actuales.
-- 1) Totales de toda la cartera productiva; separar ordinaria y regularizacion.
SELECT
    COUNT(*) FILTER (WHERE vigente_ordinaria) AS ordenes_ordinarias,
    COALESCE(SUM(saldo) FILTER (WHERE vigente_ordinaria), 0) AS saldo_ordinario,
    COUNT(*) FILTER (WHERE en_regularizacion) AS ordenes_regularizacion,
    COALESCE(SUM(saldo) FILTER (WHERE en_regularizacion), 0) AS saldo_regularizacion,
    COALESCE(SUM(saldo) FILTER (WHERE vigente), 0) AS saldo_vigente_cobrable
FROM mart.cartera_orden;

-- 2) Por actividad: permite reproducir el filtro de actividad del dashboard.
SELECT a.id_actividad, a.nombre,
    COALESCE(SUM(c.saldo) FILTER (WHERE c.vigente_ordinaria), 0) AS saldo_ordinario,
    COALESCE(SUM(c.saldo) FILTER (WHERE c.en_regularizacion), 0) AS saldo_regularizacion,
    COALESCE(SUM(c.saldo) FILTER (WHERE c.vigente), 0) AS saldo_cobrable
FROM mart.cartera_orden c
JOIN dw.dim_actividad a USING (actividad_key)
GROUP BY a.id_actividad, a.nombre
ORDER BY saldo_cobrable DESC;

-- 3) Por mes de emision: el sidebar filtra fecha_key de la ORDEN, no fecha de pago.
SELECT f.anio, f.mes,
    COALESCE(SUM(c.saldo) FILTER (WHERE c.vigente_ordinaria), 0) AS ordinario,
    COALESCE(SUM(c.saldo) FILTER (WHERE c.en_regularizacion), 0) AS regularizacion,
    COALESCE(SUM(c.saldo) FILTER (WHERE c.vigente), 0) AS total
FROM mart.cartera_orden c
JOIN dw.dim_fecha f USING (fecha_key)
GROUP BY f.anio, f.mes
ORDER BY f.anio, f.mes;

-- 4) Estados y causas de exclusion (incluye ordenes no cobrables con saldo).
SELECT o.estado, o.cierre_financiero_estado,
    COUNT(*) AS ordenes,
    COUNT(*) FILTER (WHERE c.vigente) AS cobrables,
    COALESCE(SUM(c.saldo), 0) AS saldo_total,
    COALESCE(SUM(c.saldo) FILTER (WHERE c.vigente), 0) AS saldo_cobrable
FROM dw.hecho_orden o
JOIN mart.cartera_orden c USING (id_orden)
GROUP BY o.estado, o.cierre_financiero_estado
ORDER BY o.estado, o.cierre_financiero_estado;

-- 5) Ultima ejecucion correcta del ETL (revisar la fecha de corte).
SELECT id_ejecucion, modo, fin, filas_extraidas, filas_cargadas
FROM meta.ejecucion
WHERE estado = 'correcta'
ORDER BY id_ejecucion DESC
LIMIT 1;

-- 6) Invariante: la suma de los dos tipos de cartera debe ser igual a la cartera vigente.
SELECT
    COUNT(*) FILTER (WHERE vigente AND NOT (vigente_ordinaria OR en_regularizacion)) AS mal_clasificadas,
    COUNT(*) FILTER (WHERE vigente_ordinaria AND en_regularizacion) AS doble_clasificadas,
    COALESCE(SUM(saldo) FILTER (WHERE vigente), 0) -
    COALESCE(SUM(saldo) FILTER (WHERE vigente_ordinaria), 0) -
    COALESCE(SUM(saldo) FILTER (WHERE en_regularizacion), 0) AS diferencia_saldos
FROM mart.cartera_orden;
-- Los tres resultados de la consulta 6 deben ser 0.
