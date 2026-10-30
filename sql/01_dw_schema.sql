-- SIDAN BI / v1.0. Ejecutar SOLO en la nueva base sidan_dw, NUNCA en OLTP.
BEGIN;
CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE TABLE IF NOT EXISTS meta.ejecucion (
  id_ejecucion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  modo VARCHAR(16) NOT NULL CHECK(modo IN ('full','incremental')),
  inicio TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
  fin TIMESTAMPTZ,
  estado VARCHAR(15) NOT NULL DEFAULT 'ejecutando' CHECK(estado IN ('ejecutando','correcta','fallida')),
  filas_extraidas INTEGER NOT NULL DEFAULT 0,
  filas_cargadas INTEGER NOT NULL DEFAULT 0,
  detalle_error TEXT
);
CREATE TABLE IF NOT EXISTS meta.control (
  proceso TEXT PRIMARY KEY,
  ultimo_exito TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS stg.registro (
  id_ejecucion BIGINT NOT NULL REFERENCES meta.ejecucion(id_ejecucion),
  entidad TEXT NOT NULL,
  clave TEXT NOT NULL,
  contenido JSONB NOT NULL,
  PRIMARY KEY (id_ejecucion, entidad, clave)
);
CREATE TABLE IF NOT EXISTS dw.dim_fecha (
  fecha_key INTEGER PRIMARY KEY, fecha DATE NOT NULL UNIQUE,
  anio SMALLINT NOT NULL, trimestre SMALLINT NOT NULL, mes SMALLINT NOT NULL,
  nombre_mes VARCHAR(16) NOT NULL, dia SMALLINT NOT NULL,
  semana_iso SMALLINT NOT NULL
);
CREATE TABLE IF NOT EXISTS dw.dim_actividad (
  actividad_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_actividad BIGINT NOT NULL UNIQUE, nombre TEXT NOT NULL,
  categoria TEXT, tipo_participacion VARCHAR(30),
  estado_publicacion VARCHAR(25), estado_operativo VARCHAR(25),
  cupo_total INTEGER, inicio_realizacion TIMESTAMPTZ,
  actualizado_dw TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dw.dim_item (
  item_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_item_actividad BIGINT NOT NULL UNIQUE,
  nombre TEXT NOT NULL, tipo VARCHAR(30),
  actualizado_dw TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dw.hecho_orden (
  id_orden BIGINT PRIMARY KEY,
  actividad_key BIGINT NOT NULL REFERENCES dw.dim_actividad(actividad_key),
  fecha_key INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_key),
  id_inscripcion BIGINT,
  tipo_orden VARCHAR(30) NOT NULL, canal_venta VARCHAR(30),
  modalidad_pago VARCHAR(25), estado VARCHAR(35) NOT NULL,
  cierre_financiero_estado VARCHAR(35),
  total NUMERIC(14,2) NOT NULL, descuento_total NUMERIC(14,2) NOT NULL,
  fecha_orden TIMESTAMPTZ NOT NULL, expira_en TIMESTAMPTZ,
  limite_saldo_en TIMESTAMPTZ,
  es_prueba BOOLEAN NOT NULL DEFAULT FALSE,
  actualizado_dw TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dw.hecho_inscripcion (
  id_inscripcion BIGINT PRIMARY KEY,
  actividad_key BIGINT NOT NULL REFERENCES dw.dim_actividad(actividad_key),
  fecha_key INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_key),
  estado VARCHAR(35) NOT NULL, es_prueba BOOLEAN NOT NULL,
  fecha_inscripcion TIMESTAMPTZ NOT NULL,
  fecha_confirmacion TIMESTAMPTZ,
  actualizado_dw TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dw.hecho_detalle (
  id_detalle_orden BIGINT PRIMARY KEY,
  id_orden BIGINT NOT NULL REFERENCES dw.hecho_orden(id_orden),
  actividad_key BIGINT NOT NULL REFERENCES dw.dim_actividad(actividad_key),
  item_key BIGINT REFERENCES dw.dim_item(item_key),
  fecha_key INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_key),
  tipo_concepto VARCHAR(35), nombre_concepto TEXT,
  cantidad INTEGER NOT NULL, cantidad_entregada INTEGER NOT NULL,
  neto_pedido NUMERIC(14,2) NOT NULL,
  venta_reconocida NUMERIC(14,2),
  costo_reconocido NUMERIC(14,2),
  ganancia_reconocida NUMERIC(14,2),
  fecha_reconocimiento TIMESTAMPTZ,
  es_prueba BOOLEAN NOT NULL,
  actualizado_dw TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dw.hecho_cobro (
  origen VARCHAR(10) NOT NULL CHECK(origen IN ('wompi','abono')),
  id_movimiento BIGINT NOT NULL,
  id_orden BIGINT NOT NULL REFERENCES dw.hecho_orden(id_orden),
  actividad_key BIGINT NOT NULL REFERENCES dw.dim_actividad(actividad_key),
  fecha_key INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_key),
  fecha_cobro TIMESTAMPTZ NOT NULL,
  metodo VARCHAR(25) NOT NULL,
  importe NUMERIC(14,2) NOT NULL CHECK (importe >= 0),
  es_prueba BOOLEAN NOT NULL DEFAULT FALSE,
  actualizado_dw TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(origen,id_movimiento)
);
CREATE TABLE IF NOT EXISTS dw.hecho_cierre (
  id_cierre BIGINT PRIMARY KEY,
  id_orden BIGINT NOT NULL REFERENCES dw.hecho_orden(id_orden),
  actividad_key BIGINT NOT NULL REFERENCES dw.dim_actividad(actividad_key),
  fecha_key INTEGER NOT NULL REFERENCES dw.dim_fecha(fecha_key),
  clasificacion VARCHAR(35) NOT NULL,
  anticipo_sin_entrega NUMERIC(14,2) NOT NULL,
  fecha_cierre TIMESTAMPTZ NOT NULL,
  es_prueba BOOLEAN NOT NULL,
  actualizado_dw TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMIT;
