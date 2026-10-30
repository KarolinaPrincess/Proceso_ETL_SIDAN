-- SOLO en db_sidan_dw o db_sidan_dw_bench; ejecutar con rol administrador.
-- Ajustar db_sidan_dw si usa db_sidan_dw_bench.
BEGIN;
DO $safety$ BEGIN
 IF current_database() NOT IN ('db_sidan_dw','db_sidan_dw_bench') THEN
  RAISE EXCEPTION 'La conexion NO es DW de pruebas';
 END IF;
END $safety$;
GRANT USAGE ON SCHEMA meta, stg, dw, mart TO sidan_dw_etl, sidan_dw_visor;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA meta, stg, dw TO sidan_dw_etl;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA meta, stg, dw TO sidan_dw_etl;
GRANT SELECT ON ALL TABLES IN SCHEMA meta, dw TO sidan_dw_visor;
COMMIT;
-- Los privilegios de vistas de mart se conceden después de crearlas:
-- GRANT SELECT ON ALL TABLES IN SCHEMA mart TO sidan_dw_visor;
