
"""SIDAN BI - Autorun de sincronizacion.

Cambios pequenos: ETL por orden.
Cambios grandes o no identificables: ETL tradicional.

No escribe directamente en las tablas de hechos.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import time

from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

import psycopg
from psycopg import sql
from dotenv import load_dotenv

from pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(Path(__file__).with_name(".env"))

TABLAS = (
    "tbl_actividades",
    "tbl_categorias",
    "tbl_items_actividad",
    "tbl_ordenes",
    "tbl_detalles_orden",
    "tbl_inscripciones",
    "tbl_pagos",
    "tbl_abonos_transferencia",
    "tbl_cierres_orden",
    "tbl_entregas_detalle",
    "tbl_aplicaciones_abono",
)

EVENTOS_ORDEN = {
    "tbl_ordenes",
    "tbl_ordenes_estados",
    "tbl_detalles_orden",
    "tbl_detalles_reconocidos",
    "tbl_pagos",
    "tbl_pagos_estados",
    "tbl_abonos_transferencia",
    "tbl_abonos_estados",
    "tbl_cierres_orden",
    "tbl_entregas_detalle",
    "tbl_aplicaciones_abono",
}

RECONCILIAR_TODO = {
    "tbl_entregas_detalle",
    "tbl_aplicaciones_abono",
}

FECHAS = (
    "updated_at",
    "created_at",
    "fecha_confirmacion_financiera",
    "revisado_en",
)

DETENER = False


def detener(_senal, _frame):
    global DETENER
    DETENER = True


def configurar_log():
    carpeta = ROOT / "logs"
    carpeta.mkdir(parents=True, exist_ok=True)

    log = logging.getLogger("sidan_autosync")
    log.setLevel(logging.INFO)
    log.propagate = False

    if not log.handlers:
        formato = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        handlers = (
            RotatingFileHandler(
                carpeta / "auto_sync.log",
                maxBytes=2_000_000,
                backupCount=3,
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        )

        for handler in handlers:
            handler.setFormatter(formato)
            log.addHandler(handler)

    return log


def leer_huella(dsn):
    huella = {}

    with psycopg.connect(
        dsn, connect_timeout=8
    ) as conn:

        conn.execute("SET TRANSACTION READ ONLY")

        for nombre in TABLAS:
            columnas = {
                fila[0]
                for fila in conn.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                """, (nombre,))
            }

            if not columnas:
                raise RuntimeError(
                    f"No existe public.{nombre}"
                )

            fechas = [
                c for c in FECHAS
                if c in columnas
            ]

            if fechas:
                expresion = sql.SQL(
                    "GREATEST({})"
                ).format(
                    sql.SQL(",").join(
                        sql.Identifier(c)
                        for c in fechas
                    )
                )

                consulta = sql.SQL(
                    "SELECT COUNT(*), MAX({}) FROM {}"
                ).format(
                    expresion,
                    sql.Identifier("public", nombre),
                )
            else:
                consulta = sql.SQL("""
                    SELECT COUNT(*), NULL::timestamptz
                    FROM {}
                """).format(
                    sql.Identifier("public", nombre)
                )

            cantidad, fecha = conn.execute(
                consulta
            ).fetchone()

            huella[nombre] = (
                cantidad,
                str(fecha),
            )

        huella["tbl_ordenes_estados"] = tuple(
            conn.execute("""
                SELECT
                    estado,
                    cierre_financiero_estado,
                    COUNT(*)
                FROM public.tbl_ordenes
                GROUP BY
                    estado,
                    cierre_financiero_estado
                ORDER BY
                    estado,
                    cierre_financiero_estado
            """).fetchall()
        )

        huella["tbl_pagos_estados"] = tuple(
            conn.execute("""
                SELECT
                    proveedor,
                    estado,
                    COUNT(*),
                    COALESCE(SUM(monto), 0)
                FROM public.tbl_pagos
                GROUP BY proveedor, estado
                ORDER BY proveedor, estado
            """).fetchall()
        )

        huella["tbl_abonos_estados"] = tuple(
            conn.execute("""
                SELECT
                    estado,
                    COUNT(*),
                    COALESCE(SUM(monto_recibido), 0)
                FROM public.tbl_abonos_transferencia
                GROUP BY estado
                ORDER BY estado
            """).fetchall()
        )

        huella["tbl_detalles_reconocidos"] = (
            conn.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE venta_neta_confirmada
                        IS NOT NULL
                    ),
                    COALESCE(
                        SUM(venta_neta_confirmada), 0
                    ),
                    COALESCE(
                        SUM(cantidad_entregada), 0
                    )
                FROM public.tbl_detalles_orden
            """).fetchone()
        )

    return huella


def obtener_ids_afectados(src, dw, desde):
    """
    Identifica ordenes nuevas, estados diferentes
    y movimientos financieros recientes.
    """

    estados_dw = {
        fila[0]: fila[1:]
        for fila in dw.execute("""
            SELECT
                id_orden,
                estado,
                cierre_financiero_estado,
                expira_en,
                limite_saldo_en
            FROM dw.hecho_orden
        """)
    }

    estados_sidan = {
        fila[0]: fila[1:]
        for fila in src.execute("""
            SELECT
                id_orden,
                estado,
                cierre_financiero_estado,
                expira_en,
                limite_saldo_en
            FROM public.tbl_ordenes
        """)
    }

    diferentes = {
        oid
        for oid, datos in estados_sidan.items()
        if oid not in estados_dw
        or estados_dw[oid] != datos
    }

    # Detectar tambien modificaciones financieras
    # cuando el estado de la orden no cambia.
    recientes = {
        fila[0]
        for fila in src.execute("""
            WITH limite AS (
                SELECT %s::timestamptz AS desde
            )

            SELECT DISTINCT id_orden
            FROM (
                SELECT o.id_orden
                FROM public.tbl_ordenes o, limite l
                WHERE
                    o.created_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR o.updated_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP

                UNION ALL

                SELECT p.id_orden
                FROM public.tbl_pagos p, limite l
                WHERE
                    p.created_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR p.updated_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP

                UNION ALL

                SELECT d.id_orden
                FROM public.tbl_detalles_orden d, limite l
                WHERE
                    d.created_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR d.updated_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR d.fecha_confirmacion_financiera
                        BETWEEN l.desde AND CURRENT_TIMESTAMP

                UNION ALL

                SELECT p.id_orden
                FROM public.tbl_abonos_transferencia a
                JOIN public.tbl_pagos p
                    ON p.id_pago = a.id_pago
                CROSS JOIN limite l
                WHERE
                    a.created_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR a.updated_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR a.revisado_en BETWEEN
                        l.desde AND CURRENT_TIMESTAMP

                UNION ALL

                SELECT c.id_orden
                FROM public.tbl_cierres_orden c, limite l
                WHERE
                    c.created_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR c.updated_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP

                UNION ALL

                SELECT d.id_orden
                FROM public.tbl_entregas_detalle e
                JOIN public.tbl_detalles_orden d
                    ON d.id_detalle_orden =
                       e.id_detalle_orden
                CROSS JOIN limite l
                WHERE
                    e.created_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR e.updated_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP

                UNION ALL

                SELECT p.id_orden
                FROM public.tbl_aplicaciones_abono aa
                JOIN public.tbl_abonos_transferencia a
                    ON a.id_abono = aa.id_abono
                JOIN public.tbl_pagos p
                    ON p.id_pago = a.id_pago
                CROSS JOIN limite l
                WHERE
                    aa.created_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
                    OR aa.updated_at BETWEEN
                        l.desde AND CURRENT_TIMESTAMP
            ) movimientos
        """, (desde,))
    }

    return sorted(diferentes | recientes)


def sincronizar_ordenes(
    oltp_dsn,
    dw_dsn,
    desde,
    log,
    limite=20,
):
    """
    Usa el ETL por orden para cambios pequenos.

    Si no puede identificar una cantidad pequena
    de ordenes, devuelve False para utilizar
    el ETL tradicional.
    """

    with psycopg.connect(
        oltp_dsn, connect_timeout=8
    ) as src, psycopg.connect(
        dw_dsn, connect_timeout=8
    ) as dw:

        src.execute("SET TRANSACTION READ ONLY")

        origen = src.execute(
            "SELECT current_database()"
        ).fetchone()[0]

        destino = dw.execute(
            "SELECT current_database()"
        ).fetchone()[0]

        if origen != "db_sidan":
            raise RuntimeError(
                "OLTP_DSN no apunta a db_sidan"
            )

        if destino != "db_sidan_dw":
            raise RuntimeError(
                "DW_DSN no apunta a db_sidan_dw"
            )

        ids = obtener_ids_afectados(
            src, dw, desde
        )

    if not ids or len(ids) > limite:
        log.warning(
            "%s ordenes detectadas; "
            "se utilizara ETL tradicional",
            len(ids),
        )
        return False

    log.info(
        "Sincronizacion selectiva: %s ordenes",
        len(ids),
    )

    for id_orden in ids:
        log.info(
            "Actualizando orden %s",
            id_orden,
        )

        # Mantiene la logica financiera original.
        run_pipeline(
            solo_orden_id=id_orden
        )

    return True


def ciclo(intervalo, full_inicio, sin_inicial):
    log = configurar_log()

    oltp_dsn = os.getenv("OLTP_DSN")
    dw_dsn = os.getenv("DW_DSN")

    if (
        not oltp_dsn
        or not dw_dsn
        or oltp_dsn == dw_dsn
    ):
        raise RuntimeError(
            "Revisar etl/.env"
        )

    anterior = None
    ultimo_sondeo = None
    primera = True

    log.info(
        "Monitoreo iniciado; intervalo=%s segundos",
        intervalo,
    )

    while not DETENER:
        inicio_sondeo = datetime.now(timezone.utc)

        try:
            actual = leer_huella(oltp_dsn)

            cambios = (
                set(actual)
                if anterior is None
                else {
                    k
                    for k in set(anterior) | set(actual)
                    if anterior.get(k) != actual.get(k)
                }
            )

            if primera and sin_inicial:
                log.info(
                    "Inicio sin ETL masivo"
                )

                # Detectar ordenes nuevas o con estados
                # diferentes sin ejecutar una carga full.
                with psycopg.connect(
                    oltp_dsn
                ) as src, psycopg.connect(
                    dw_dsn
                ) as dw:

                    src.execute(
                        "SET TRANSACTION READ ONLY"
                    )

                    estados = {
                        r[0]: r[1:]
                        for r in dw.execute("""
                            SELECT
                                id_orden,
                                estado,
                                cierre_financiero_estado,
                                expira_en,
                                limite_saldo_en
                            FROM dw.hecho_orden
                        """)
                    }

                    ids = [
                        r[0]
                        for r in src.execute("""
                            SELECT
                                id_orden,
                                estado,
                                cierre_financiero_estado,
                                expira_en,
                                limite_saldo_en
                            FROM public.tbl_ordenes
                        """)
                        if r[0] not in estados
                        or estados[r[0]] != r[1:]
                    ]

                if 0 < len(ids) <= 20:
                    for id_orden in ids:
                        run_pipeline(
                            solo_orden_id=id_orden
                        )
                elif ids:
                    log.warning(
                        "%s ordenes pendientes "
                        "de reconciliacion",
                        len(ids),
                    )

            elif primera:
                run_pipeline(
                    full=full_inicio
                )

            elif cambios:
                log.info(
                    "Cambios: %s",
                    ", ".join(sorted(cambios)),
                )

                inicio_etl = time.monotonic()

                if cambios <= EVENTOS_ORDEN:
                    desde = (
                        ultimo_sondeo or inicio_sondeo
                    ) - timedelta(minutes=2)

                    correcto = sincronizar_ordenes(
                        oltp_dsn,
                        dw_dsn,
                        desde,
                        log,
                    )

                    if not correcto:
                        run_pipeline(
                            full=bool(
                                cambios & RECONCILIAR_TODO
                            )
                        )

                else:
                    # Conservar sincronizacion tradicional
                    # para catalogos e inscripciones.
                    run_pipeline(
                        full=bool(
                            cambios & RECONCILIAR_TODO
                        )
                    )

                log.info(
                    "Sincronizacion terminada en %.2fs",
                    time.monotonic() - inicio_etl,
                )

            anterior = actual
            ultimo_sondeo = inicio_sondeo
            primera = False

        except Exception:
            log.exception(
                "Error de sincronizacion; "
                "se reintentara"
            )

        for _ in range(intervalo):
            if DETENER:
                break
            time.sleep(1)

    log.info("Monitoreo detenido")


def main():
    parser = argparse.ArgumentParser(
        description="SIDAN BI Autorun"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=30,
    )

    parser.add_argument(
        "--full-inicio",
        action="store_true",
    )

    parser.add_argument(
        "--sin-inicial",
        action="store_true",
    )

    args = parser.parse_args()

    if args.interval < 15:
        parser.error(
            "El intervalo minimo es 15 segundos"
        )

    if args.full_inicio and args.sin_inicial:
        parser.error(
            "No combinar --full-inicio "
            "con --sin-inicial"
        )

    signal.signal(
        signal.SIGINT,
        detener
    )

    signal.signal(
        signal.SIGTERM,
        detener
    )

    ciclo(
        args.interval,
        args.full_inicio,
        args.sin_inicial,
    )


if __name__ == "__main__":
    main()
