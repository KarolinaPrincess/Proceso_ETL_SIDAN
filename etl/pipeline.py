"""SIDAN BI / ETL PostgreSQL->PostgreSQL, sin escribir en el OLTP.
Python 3.11+, psycopg 3. Carga inicial o incremental por orden modificada,
con reconciliación de cobros de las órdenes tocadas. Las dimensiones se
actualizan tipo 1; véase LIMITACIONES.md antes de interpretar historia.
"""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

load_dotenv(Path(__file__).with_name('.env'))
ZONE = ZoneInfo(os.getenv('BI_TIMEZONE', 'America/El_Salvador'))

# Todos los SELECT explícitos impiden extraer correos, nombres de personas o comprobantes.
SQL_ACTIVIDADES = """
SELECT a.id_actividad,a.nombre,a.tipo_participacion,a.estado_publicacion,
       a.estado_operativo,a.cupo_total,a.realizacion_desde,c.nombre AS categoria
FROM public.tbl_actividades a LEFT JOIN public.tbl_categorias c USING(id_categoria)
"""
SQL_ITEMS = "SELECT id_item_actividad,nombre,tipo FROM public.tbl_items_actividad"
SQL_ORDENES = """
SELECT id_orden,id_actividad,id_inscripcion,tipo_orden,canal_venta,
       modalidad_pago,estado,cierre_financiero_estado,total,descuento_total,
       created_at,updated_at,expira_en,limite_saldo_en
FROM public.tbl_ordenes WHERE id_orden = ANY(%s)
"""
SQL_INSCRIPCIONES = """
SELECT id_inscripcion,id_actividad,estado,created_at,updated_at,fecha_confirmacion
FROM public.tbl_inscripciones WHERE id_inscripcion = ANY(%s)
"""
SQL_DETALLES = """
SELECT id_detalle_orden,id_orden,id_item_actividad,tipo_concepto,nombre_concepto,
       cantidad,cantidad_entregada,subtotal,descuento,
       venta_neta_confirmada,costo_total_confirmado,ganancia_bruta_confirmada,
       fecha_confirmacion_financiera
FROM public.tbl_detalles_orden WHERE id_orden = ANY(%s)
"""
SQL_COBROS = """
SELECT 'wompi'::text AS origen,p.id_pago AS id_movimiento,p.id_orden,
       'wompi'::text AS metodo,p.monto AS importe,
       COALESCE(p.fecha_confirmacion,p.updated_at) AS fecha_cobro
FROM public.tbl_pagos p
WHERE p.id_orden = ANY(%s) AND p.proveedor='wompi' AND p.estado='confirmado'
UNION ALL
SELECT 'abono'::text,a.id_abono,p.id_orden,a.metodo,a.monto_recibido,
       COALESCE(a.revisado_en,a.updated_at,a.created_at)
FROM public.tbl_abonos_transferencia a
JOIN public.tbl_pagos p ON p.id_pago=a.id_pago
WHERE p.id_orden = ANY(%s) AND p.proveedor IN ('transferencia','efectivo')
  AND a.estado='confirmado'
"""
SQL_CIERRES = """
SELECT c.id_cierre,c.id_orden,c.clasificacion,c.anticipo_sin_entrega,c.created_at
FROM public.tbl_cierres_orden c WHERE c.id_orden = ANY(%s)
"""


def fecha_key(value: datetime) -> int:
    if value is None: raise ValueError('Falta fecha obligatoria')
    if value.tzinfo is None: raise ValueError('Fecha sin zona horaria en origen')
    return int(value.astimezone(ZONE).strftime('%Y%m%d'))


def money(value, *, nullable=False) -> Decimal | None:
    if value is None:
        if nullable: return None
        raise ValueError('Importe obligatorio nulo')
    amount = Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    if amount.is_nan() or amount.is_infinite() or amount < 0:
        raise ValueError('Importe inválido (negativo/no finito)')
    return amount


def es_prueba(estado: str) -> bool:
    return str(estado).endswith('_prueba')


def upsert(conn, table: str, keycols: list[str], data: dict) -> int:
    """Carga idempotente, actualiza solamente cambios; no crea registros duplicados."""
    from psycopg import sql
    cols = list(data)
    columns = sql.SQL(',').join(map(sql.Identifier, cols))
    placeholders = sql.SQL(',').join([sql.Placeholder()] * len(cols))
    keys = sql.SQL(',').join(map(sql.Identifier,keycols))
    changed = [c for c in cols if c not in keycols and c != 'actualizado_dw']
    if not changed: raise ValueError('Upsert sin datos actualizables')
    assigns = sql.SQL(',').join(sql.SQL('{}=EXCLUDED.{}').format(sql.Identifier(c),sql.Identifier(c)) for c in changed)
    # Todas las dimensiones y hechos cargados por este método tienen esta columna.
    assigns = assigns + sql.SQL(',actualizado_dw=now()')
    diffs = sql.SQL(' OR ').join(sql.SQL('t.{} IS DISTINCT FROM EXCLUDED.{}').format(sql.Identifier(c),sql.Identifier(c)) for c in changed)
    q = sql.SQL('INSERT INTO {} AS t ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {} WHERE {} RETURNING 1').format(
      sql.SQL(table),columns,placeholders,keys,assigns,diffs)
    result=conn.execute(q,[data[c] for c in cols]).fetchone()
    return 1 if result else 0


def add_date(conn, instant: datetime):
    local = instant.astimezone(ZONE)
    dt = local.date()
    conn.execute("""
      INSERT INTO dw.dim_fecha(fecha_key,fecha,anio,trimestre,mes,nombre_mes,dia,semana_iso)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
      (fecha_key(instant),dt,dt.year,(dt.month-1)//3+1,dt.month,
       ('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre')[dt.month-1],dt.day,dt.isocalendar().week))


def fetch(conn, query, params=None):
    return conn.execute(query,params).fetchall()


def stage(dest, run_id, entidad, datos, llave):
    for record in datos:
        dest.execute("INSERT INTO stg.registro(id_ejecucion,entidad,clave,contenido) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (run_id,entidad,str(record[llave]),Jsonb(json.loads(json.dumps(record, default=str)))))


def get_changed_order_ids(src, cutoff):
    if cutoff is None:
        return [r['id_orden'] for r in fetch(src,'SELECT id_orden FROM public.tbl_ordenes ORDER BY id_orden')]
    # Escanear eventos/cambios: actualizaciones en detalle por entrega, pago,
    # revisión de abono, clasificación de cierre y fecha financiera de trigger.
    q="""
    SELECT DISTINCT id_orden FROM (
      SELECT id_orden FROM public.tbl_ordenes
       WHERE updated_at >= %s OR created_at >= %s
      UNION ALL
      SELECT id_orden FROM public.tbl_pagos
       WHERE updated_at >= %s OR created_at >= %s
      UNION ALL
      SELECT id_orden FROM public.tbl_detalles_orden
       WHERE updated_at >= %s OR created_at >= %s OR fecha_confirmacion_financiera >= %s
      UNION ALL
      SELECT p.id_orden FROM public.tbl_abonos_transferencia a
       JOIN public.tbl_pagos p ON p.id_pago=a.id_pago
       WHERE a.updated_at >= %s OR a.created_at >= %s OR a.revisado_en >= %s
      UNION ALL
      SELECT id_orden FROM public.tbl_cierres_orden
       WHERE updated_at >= %s OR created_at >= %s
    ) x ORDER BY id_orden
    """
    return [r['id_orden'] for r in fetch(src,q,[cutoff]*12)]


def get_changed_inscripcion_ids(src, cutoff, orders):
    if cutoff is None:
        ins_rows=fetch(src,'SELECT id_inscripcion FROM public.tbl_inscripciones')
    else:
        ins_rows=fetch(src,'SELECT id_inscripcion FROM public.tbl_inscripciones WHERE updated_at >= %s OR created_at >= %s',(cutoff,cutoff))
    ids = {r['id_inscripcion'] for r in ins_rows}
    if orders:
        ids.update(r['id_inscripcion'] for r in fetch(src,
            'SELECT DISTINCT id_inscripcion FROM public.tbl_ordenes WHERE id_orden = ANY(%s) AND id_inscripcion IS NOT NULL', (orders,)))
    return sorted(ids)


def run_pipeline(full=False, solo_orden_id: int | None = None):
    src_dsn=os.environ.get('OLTP_DSN'); dw_dsn=os.environ.get('DW_DSN')
    if not src_dsn or not dw_dsn: raise RuntimeError('Configurar OLTP_DSN y DW_DSN en etl/.env')
    if src_dsn==dw_dsn: raise RuntimeError('OLTP y DW no pueden ser la misma conexión')
    started=datetime.now(timezone.utc)
    mode='full' if full else 'incremental'
    # Bitácora persistente incluso ante fallo en transacción de la carga.
    with psycopg.connect(dw_dsn,autocommit=True) as log:
        log.execute('SET search_path TO public')
        row=log.execute('INSERT INTO meta.ejecucion(modo) VALUES(%s) RETURNING id_ejecucion',(mode,)).fetchone()
        run_id=row[0]
        try:
            with psycopg.connect(src_dsn,row_factory=dict_row) as src, psycopg.connect(dw_dsn) as dest:
                with src.transaction():
                    src.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                    locked=dest.execute('SELECT pg_try_advisory_xact_lock(73512026)').fetchone()[0]
                    if not locked: raise RuntimeError('Ya hay otra ejecución ETL en curso')
                    if src.execute('SELECT current_database()').fetchone()['current_database']==dest.execute('SELECT current_database()').fetchone()[0]:
                        raise RuntimeError('La base origen coincide con la base destino')
                    ctl=dest.execute("SELECT ultimo_exito FROM meta.control WHERE proceso='sidan'").fetchone()
                    watermark=None if full or not ctl else ctl[0]-timedelta(days=1)
                    actividades=fetch(src,SQL_ACTIVIDADES)
                    items=fetch(src,SQL_ITEMS)
                    if solo_orden_id is not None:
                        # Sincronizar exclusivamente la orden solicitada.
                        orderids = [
                            r['id_orden']
                            for r in fetch(
                                src,
                                """
                                SELECT id_orden
                                FROM public.tbl_ordenes
                                WHERE id_orden = %s
                                """,
                                (solo_orden_id,)
                            )
                        ]

                        if not orderids:
                            raise ValueError(
                                f'La orden {solo_orden_id} no existe en SIDAN'
                            )

                        # Solo las inscripciones vinculadas a esta orden.
                        insids = [
                            r['id_inscripcion']
                            for r in fetch(
                                src,
                                """
                                SELECT DISTINCT id_inscripcion
                                FROM public.tbl_ordenes
                                WHERE id_orden = %s
                                AND id_inscripcion IS NOT NULL
                                """,
                                (solo_orden_id,)
                            )
                        ]
                    else:
                        # Funcionamiento incremental habitual.
                        orderids = get_changed_order_ids(src, watermark)
                        insids = get_changed_inscripcion_ids(
                            src, watermark, orderids
                        )
                    ordenes=fetch(src,SQL_ORDENES,(orderids,)) if orderids else []
                    inscripciones=fetch(src,SQL_INSCRIPCIONES,(insids,)) if insids else []
                    detalles=fetch(src,SQL_DETALLES,(orderids,)) if orderids else []
                    cobros=fetch(src,SQL_COBROS,(orderids,orderids)) if orderids else []
                    cierres=fetch(src,SQL_CIERRES,(orderids,)) if orderids else []
                    count_extr=sum(map(len,(actividades,items,ordenes,inscripciones,detalles,cobros,cierres)))
                    for entidad,rows,key in [
                        ('actividad',actividades,'id_actividad'),('item',items,'id_item_actividad'),
                        ('orden',ordenes,'id_orden'),('inscripcion',inscripciones,'id_inscripcion'),
                        ('detalle',detalles,'id_detalle_orden'),('cierre',cierres,'id_cierre')]:
                        stage(dest,run_id,entidad,rows,key)
                    # Claves compuestas de movimientos: garantizan unicidad entre fuentes.
                    for record in cobros:
                        dest.execute('INSERT INTO stg.registro(id_ejecucion,entidad,clave,contenido) VALUES(%s,%s,%s,%s)',
                          (run_id,'cobro',f"{record['origen']}:{record['id_movimiento']}",Jsonb(json.loads(json.dumps(record, default=str)))))
                    modified=0
                    for a in actividades:
                        modified+=upsert(dest,'dw.dim_actividad',['id_actividad'],dict(
                           id_actividad=a['id_actividad'],nombre=a['nombre'],categoria=a['categoria'],
                           tipo_participacion=a['tipo_participacion'],estado_publicacion=a['estado_publicacion'],
                           estado_operativo=a['estado_operativo'],cupo_total=a['cupo_total'],
                           inicio_realizacion=a['realizacion_desde']))
                    for i in items:
                        modified+=upsert(dest,'dw.dim_item',['id_item_actividad'],dict(
                           id_item_actividad=i['id_item_actividad'],nombre=i['nombre'],tipo=i['tipo']))
                    ak={row[0]:row[1] for row in dest.execute('SELECT id_actividad,actividad_key FROM dw.dim_actividad')}
                    ik={row[0]:row[1] for row in dest.execute('SELECT id_item_actividad,item_key FROM dw.dim_item')}
                    status={row['id_orden']:es_prueba(row['estado']) for row in ordenes}
                    act={row['id_orden']:row['id_actividad'] for row in ordenes}
                    for o in ordenes:
                        add_date(dest,o['created_at'])
                        modified+=upsert(dest,'dw.hecho_orden',['id_orden'],dict(
                          id_orden=o['id_orden'],actividad_key=ak[o['id_actividad']],
                          fecha_key=fecha_key(o['created_at']),id_inscripcion=o['id_inscripcion'],
                          tipo_orden=o['tipo_orden'],canal_venta=o['canal_venta'],modalidad_pago=o['modalidad_pago'],
                          estado=o['estado'],cierre_financiero_estado=o['cierre_financiero_estado'],
                          total=money(o['total']),descuento_total=money(o['descuento_total']),
                          fecha_orden=o['created_at'],expira_en=o['expira_en'],limite_saldo_en=o['limite_saldo_en'],
                          es_prueba=status[o['id_orden']]))
                    for i in inscripciones:
                        add_date(dest,i['created_at'])
                        modified+=upsert(dest,'dw.hecho_inscripcion',['id_inscripcion'],dict(
                          id_inscripcion=i['id_inscripcion'],actividad_key=ak[i['id_actividad']],
                          fecha_key=fecha_key(i['created_at']),estado=i['estado'],
                          es_prueba=es_prueba(i['estado']),fecha_inscripcion=i['created_at'],
                          fecha_confirmacion=i['fecha_confirmacion']))
                    for d in detalles:
                        when=d['fecha_confirmacion_financiera']; tipo=d['tipo_concepto']
                        delivered=int(d['cantidad_entregada'] or 0)>=int(d['cantidad'])
                        recognized=when is not None and (tipo!='producto' or delivered)
                        if recognized and d['venta_neta_confirmada'] is None:
                            raise ValueError('Detalle reconocido sin valor financiero, id='+str(d['id_detalle_orden']))
                        dt=when if recognized else next(o['created_at'] for o in ordenes if o['id_orden']==d['id_orden'])
                        add_date(dest,dt)
                        modified+=upsert(dest,'dw.hecho_detalle',['id_detalle_orden'],dict(
                          id_detalle_orden=d['id_detalle_orden'],id_orden=d['id_orden'],
                          actividad_key=ak[act[d['id_orden']]],
                          item_key=ik.get(d['id_item_actividad']) if d['id_item_actividad'] else None,
                          fecha_key=fecha_key(dt),tipo_concepto=tipo,nombre_concepto=d['nombre_concepto'],
                          cantidad=d['cantidad'],cantidad_entregada=d['cantidad_entregada'],
                          neto_pedido=money(Decimal(str(d['subtotal']))-Decimal(str(d['descuento'] or 0))),
                          venta_reconocida=money(d['venta_neta_confirmada']) if recognized else None,
                          costo_reconocido=money(d['costo_total_confirmado'],nullable=True) if recognized else None,
                          ganancia_reconocida=money(d['ganancia_bruta_confirmada'],nullable=True) if recognized else None,
                          fecha_reconocimiento=when if recognized else None,es_prueba=status[d['id_orden']]))
                    # DELETE + recarga por orden cambiada = reversión segura si un abono se rechaza luego.
                    if orderids:
                        dest.execute('DELETE FROM dw.hecho_cobro WHERE id_orden = ANY(%s)',(orderids,))
                    for c in cobros:
                        if c['importe'] is None: raise ValueError('Abono confirmado sin monto')
                        add_date(dest,c['fecha_cobro'])
                        modified+=upsert(dest,'dw.hecho_cobro',['origen','id_movimiento'],dict(
                          origen=c['origen'],id_movimiento=c['id_movimiento'],id_orden=c['id_orden'],
                          actividad_key=ak[act[c['id_orden']]],fecha_key=fecha_key(c['fecha_cobro']),
                          fecha_cobro=c['fecha_cobro'],metodo=c['metodo'],importe=money(c['importe']),
                          es_prueba=status[c['id_orden']]))
                    # Los cierres son 1:1, pueden reclasificarse. No sumar a caja.
                    for c in cierres:
                        add_date(dest,c['created_at'])
                        modified+=upsert(dest,'dw.hecho_cierre',['id_cierre'],dict(
                          id_cierre=c['id_cierre'],id_orden=c['id_orden'],
                          actividad_key=ak[act[c['id_orden']]],fecha_key=fecha_key(c['created_at']),
                          clasificacion=c['clasificacion'],anticipo_sin_entrega=money(c['anticipo_sin_entrega']),
                          fecha_cierre=c['created_at'],es_prueba=status[c['id_orden']]))
                    
                        # Una sincronización individual no debe adelantar
                        # la marca global del ETL incremental.
                        if solo_orden_id is None:
                            dest.execute(
                                """
                                INSERT INTO meta.control(proceso, ultimo_exito)
                                VALUES (%s, %s)
                                ON CONFLICT (proceso)
                                DO UPDATE SET ultimo_exito = EXCLUDED.ultimo_exito
                                """,
                                ('sidan', started)
                            )

                    # Commit automático al salir de conexión destino; la fuente se lee en snapshot.
            log.execute("UPDATE meta.ejecucion SET estado='correcta',fin=clock_timestamp(),filas_extraidas=%s,filas_cargadas=%s WHERE id_ejecucion=%s", (count_extr,modified,run_id))
            print(f'ETL CORRECTA id={run_id}, origen={count_extr}, filas insertadas/actualizadas={modified}')
        except Exception as exc:
            log.execute("UPDATE meta.ejecucion SET estado='fallida',fin=clock_timestamp(),detalle_error=%s WHERE id_ejecucion=%s", (f'{type(exc).__name__}: {str(exc)[:1000]}',run_id))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ETL SIDAN a Data Warehouse'
    )

    parser.add_argument(
        '--full',
        action='store_true',
        help='Extracción completa'
    )

    parser.add_argument(
        '--orden',
        type=int,
        help='Sincronizar solamente una orden por ID'
    )

    args = parser.parse_args()

    if args.full and args.orden is not None:
        parser.error(
            'No se puede combinar --full con --orden'
        )

    if args.orden is not None and args.orden <= 0:
        parser.error(
            'El ID de la orden debe ser positivo'
        )

    run_pipeline(
        full=args.full,
        solo_orden_id=args.orden
    )
