
"""SIDAN BI - Panel ejecutivo. Consulta exclusivamente PostgreSQL DW."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

st.set_page_config(
    page_title="SIDAN BI | Panel ejecutivo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st_autorefresh(
    interval=30_000,
    key="sidan_bi_actualizacion_automatica"
)

# ============================================
# ESTILOS ORIGINALES DEL DASHBOARD
# ============================================

st.markdown("""
<style>
:root {
    --navy:#10273f;
    --ink:#162a42;
    --muted:#66788e;
    --teal:#008d9a;
    --line:#dfe8f0;
}
.stApp {
    background:#f3f7fb;
    color:var(--ink);
}
.block-container {
    padding-top:1.35rem;
    padding-bottom:2.8rem;
    max-width:1530px;
}
[data-testid="stHeader"] {
    background:rgba(243,247,251,.88);
}
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#10263d 0%,#15344f 100%);
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
    color:#f2f6fb;
}
[data-testid="stSidebar"] label {
    color:#dfeaf4 !important;
    font-weight:650 !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color:#b5c7d9 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-testid="stDateInput"] [data-baseweb="input"] > div {
    background:#eff5fa !important;
    border:1px solid #bdd0df !important;
    border-radius:10px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color:#18334c !important;
}
[data-testid="stSidebar"] [data-testid="stDateInput"] input {
    color:#18334c !important;
}
[data-testid="stSidebar"] [data-testid="stDateInput"] svg {
    color:#18334c !important;
}
.side-brand {
    padding:8px 2px 15px;
}
.side-brand .brand {
    font-size:1.65rem;
    font-weight:850;
    letter-spacing:.04em;
    color:#fff;
}
.side-brand .sub {
    font-size:.85rem;
    margin-top:3px;
    color:#adc9da;
}
.side-box {
    border:1px solid rgba(255,255,255,.18);
    border-radius:13px;
    padding:12px 14px;
    background:rgba(255,255,255,.055);
    color:#c6d6e5;
    font-size:.83rem;
    line-height:1.6;
}
.side-rule {
    height:1px;
    background:rgba(255,255,255,.16);
    margin:13px 0 18px;
}
.hero {
    background:linear-gradient(115deg,#102b46,#174763 75%,#0e7581);
    color:#fff;
    border-radius:23px;
    padding:27px 33px 25px;
    margin-bottom:15px;
    box-shadow:0 12px 36px rgba(17,49,75,.12);
}
.hero .eyebrow {
    color:#a9dce5;
    font-size:.73rem;
    font-weight:750;
    letter-spacing:.14em;
    text-transform:uppercase;
}
.hero h1 {
    color:#fff !important;
    font-size:clamp(1.55rem,2.4vw,2.15rem);
    margin:.35rem 0 .35rem;
    font-weight:780;
    letter-spacing:-.025em;
}
.hero p {
    color:#d7e8f1;
    font-size:.9rem;
    margin:0;
    max-width:960px;
    line-height:1.65;
}
.kicker {
    color:#0c7485;
    font-weight:750;
    text-transform:uppercase;
    letter-spacing:.10em;
    font-size:.72rem;
    margin-bottom:2px;
}
.section-head {
    margin:1.25rem 0 .75rem;
}
.section-head h2 {
    color:#162a42;
    font-size:1.32rem;
    letter-spacing:-.025em;
    font-weight:760;
    margin:0;
}
.section-head p {
    color:#64778e;
    font-size:.84rem;
    margin:.3rem 0 0;
}
[data-testid="stMetric"] {
    background:#fff;
    padding:17px 18px 18px;
    border:1px solid #e1eaf3;
    border-radius:17px;
    min-height:120px;
    box-shadow:0 5px 23px rgba(19,51,78,.045);
    transition:transform .18s,box-shadow .18s;
}
[data-testid="stMetric"]:hover {
    transform:translateY(-2px);
    box-shadow:0 9px 28px rgba(19,51,78,.095);
}
[data-testid="stMetricLabel"] {
    color:#65778e !important;
    font-weight:700 !important;
}
[data-testid="stMetricLabel"] p {
    font-size:.81rem !important;
}
[data-testid="stMetricValue"] {
    color:#132c46 !important;
    font-size:clamp(1.45rem,1.95vw,2.1rem) !important;
    font-weight:780 !important;
    letter-spacing:-.035em;
}
[data-testid="stMetricDelta"] {
    color:#008d9a !important;
}
button[data-baseweb="tab"] {
    font-weight:700;
    color:#627990;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color:#067d8d !important;
}
[data-testid="stDataFrame"] {
    border:1px solid #e1eaf3;
    border-radius:14px;
    overflow:hidden;
}
[data-testid="stDownloadButton"] button {
    background:#0b7f8c;
    color:white;
    border:0;
    border-radius:11px;
    font-weight:700;
}
[data-testid="stDownloadButton"] button:hover {
    background:#086875;
    color:white;
    border:0;
}
small, .footnote {
    color:#71839a;
    font-size:.79rem;
}
@media(max-width:900px) {
    .hero {
        padding:20px;
        border-radius:17px;
    }
    .block-container {
        padding-left:1rem;
        padding-right:1rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ============================================
# CONEXIÓN DATA WAREHOUSE
# ============================================

DSN = os.getenv("DW_READ_DSN")

if not DSN:
    st.error("Falta DW_READ_DSN en dashboard/.env")
    st.stop()


@st.cache_data(ttl=8, show_spinner=False)
def consulta(sql: str, params=()):
    with psycopg.connect(DSN) as cn:
        with cn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql, params)
            names = [c.name for c in cur.description]
            return pd.DataFrame(
                cur.fetchall(),
                columns=names
            )


# ============================================
# ACTIVIDADES ACTUALES DEL DW
# ============================================

try:
    ultimo = consulta("""
        SELECT id_ejecucion, fin, filas_extraidas
        FROM meta.ejecucion
        WHERE estado = 'correcta'
        ORDER BY id_ejecucion DESC
        LIMIT 1
    """)

    actividades = consulta("""
        SELECT
            actividad_key,
            id_actividad,
            nombre,
            categoria
        FROM mart.actividades_actuales
        ORDER BY nombre
    """)

except Exception as e:
    st.error(
        "No se pudo consultar el Data Warehouse. "
        "Comprobá las vistas y los permisos."
    )
    st.code(type(e).__name__ + ": " + str(e))
    st.stop()


# ============================================
# ENCABEZADO
# ============================================

st.markdown("""
<div class="hero">
    <div class="eyebrow">SIDAN / BUSINESS INTELLIGENCE</div>
    <h1>Panel ejecutivo de SIDAN</h1>
    <p>
        Indicadores financieros y operacionales de actividades,
        órdenes, pagos e inscripciones.
        Información obtenida exclusivamente del
        Data Warehouse PostgreSQL.
    </p>
</div>
""", unsafe_allow_html=True)

if ultimo.empty:
    st.warning(
        "Aún no hay una ejecución ETL exitosa."
    )
    st.stop()


# ============================================
# SIDEBAR: FILTROS CORREGIDOS
# ============================================

with st.sidebar:

    st.markdown("""
        <div class="side-brand">
            <div class="brand">
                SIDAN <span style="color:#5fc6d0">BI</span>
            </div>
            <div class="sub">
                Centro de análisis y decisiones
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="side-rule"></div>',
        unsafe_allow_html=True
    )

    st.markdown("**Filtros del análisis**")

    # ----------------------------------------
    # CATEGORÍAS
    # ----------------------------------------

    categorias = ["Todas"] + sorted(
        actividades["categoria"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if st.session_state.get("filtro_categoria") not in categorias:
        st.session_state.pop("filtro_categoria", None)

    categoria = st.selectbox(
        "Categoría",
        categorias,
        key="filtro_categoria"
    )

    # ----------------------------------------
    # ACTIVIDADES DE LA CATEGORÍA
    # ----------------------------------------

    if categoria == "Todas":
        opciones = actividades.copy()
    else:
        opciones = actividades[
            actividades["categoria"] == categoria
        ].copy()

    opciones = opciones.sort_values(
        ["nombre", "id_actividad"]
    ).reset_index(drop=True)

    # Utilizamos actividad_key para evitar
    # conflictos entre actividades con igual nombre.

    nombres = {
        int(r.actividad_key): f"{r.id_actividad} · {r.nombre}"
        for r in opciones.itertuples(index=False)
    }

    valores = ["Todas las actividades"] + list(nombres.keys())

    # Eliminar selección antigua si desapareció
    # después de una ejecución del ETL.

    if st.session_state.get("filtro_actividad") not in valores:
        st.session_state.pop("filtro_actividad", None)

    seleccion = st.selectbox(
        "Actividad",
        valores,
        format_func=lambda v: nombres.get(v, v),
        key="filtro_actividad"
    )

    # ----------------------------------------
    # CLAVES PARA LOS DIEZ KPI
    # ----------------------------------------

    if seleccion == "Todas las actividades":
        keys = list(nombres)
    else:
        keys = [int(seleccion)]

    # ----------------------------------------
    # FILTROS DE FECHAS
    # ----------------------------------------

    fech = consulta("""
        SELECT
            MIN(fecha) AS minimo,
            MAX(fecha) AS maximo
        FROM dw.dim_fecha
    """)

    mind = fech.iloc[0]["minimo"]
    maxd = fech.iloc[0]["maximo"]

    if mind is None or maxd is None:
        st.info("La dimensión fecha está vacía.")
        st.stop()

    desde = st.date_input(
        "Desde",
        value=mind,
        min_value=mind,
        max_value=maxd,
        key="sidan_desde"
    )

    seguir_fecha = st.checkbox(
        "Incluir automáticamente fechas nuevas",
        value=True,
        key="sidan_hasta_movil"
    )

    hasta_elegido = st.date_input(
        "Hasta",
        value=maxd,
        min_value=mind,
        max_value=maxd,
        disabled=seguir_fecha,
        key="sidan_hasta_manual"
    )

    hasta = maxd if seguir_fecha else hasta_elegido

    if seguir_fecha:
        st.caption(
            f"Hasta la última fecha registrada en DW: "
            f"{maxd:%d/%m/%Y}"
        )

    st.markdown(
        '<div class="side-rule"></div>',
        unsafe_allow_html=True
    )

    st.markdown("""
        <div class="side-box">
            Los movimientos con estado de prueba se excluyen
            del análisis productivo.
            <br><br>
            Los abonos manuales sin marca específica de prueba
            requieren validación local.
        </div>
    """, unsafe_allow_html=True)

    st.caption(
        "Cada proceso utiliza su fecha propia: "
        "emisión, cobro o reconocimiento."
    )

    st.markdown(
        '<div class="side-rule"></div>',
        unsafe_allow_html=True
    )

    st.caption(
        "🔄 Actualización de pantalla cada 30 segundos. "
        "ETL separado y automático."
    )

    st.caption(
        f"Última carga DW: {ultimo.iloc[0]['fin']} · "
        f"Ejecución #{ultimo.iloc[0]['id_ejecucion']}"
    )

    if st.button(
        "↻ Actualizar pantalla ahora",
        use_container_width=True
    ):
        consulta.clear()
        st.rerun()


# ============================================
# VALIDACIÓN DE FILTROS
# ============================================

if desde > hasta:
    st.error(
        "La fecha inicial no puede ser posterior a la final."
    )
    st.stop()

if not keys:
    st.info(
        "No hay actividades disponibles para los filtros."
    )
    st.stop()

a = int(desde.strftime("%Y%m%d"))
b = int(hasta.strftime("%Y%m%d"))
base = (keys, a, b)


# ============================================
# CONSULTAS ORIGINALES DE LOS 10 KPI
# ============================================

cash = consulta("""
    SELECT
        COALESCE(SUM(importe), 0) AS recaudacion,
        COUNT(*) AS movimientos
    FROM dw.hecho_cobro
    WHERE NOT es_prueba
      AND actividad_key = ANY(%s)
      AND fecha_key BETWEEN %s AND %s
""", base).iloc[0]

recognized = consulta("""
    SELECT
        COALESCE(SUM(venta_reconocida), 0) AS venta,
        COALESCE(
            SUM(ganancia_reconocida)
            FILTER (WHERE costo_reconocido IS NOT NULL), 0
        ) AS ganancia,
        COALESCE(
            SUM(venta_reconocida)
            FILTER (WHERE costo_reconocido IS NOT NULL), 0
        ) AS base_margen,
        COUNT(*) AS lineas,
        COUNT(*) FILTER (
            WHERE costo_reconocido IS NOT NULL
        ) AS lineas_costo
    FROM dw.hecho_detalle
    WHERE NOT es_prueba
      AND fecha_key BETWEEN %s AND %s
      AND actividad_key = ANY(%s)
      AND venta_reconocida IS NOT NULL
""", (a, b, keys)).iloc[0]

orders = consulta("""
    SELECT
        COUNT(*) FILTER (
            WHERE estado = 'pagada'
        ) AS pagadas,
        COUNT(*) FILTER (
            WHERE estado IN ('cancelada')
        ) AS bajas,
        COUNT(*) FILTER (
            WHERE estado = 'pendiente_pago'
        ) AS pendientes
    FROM dw.hecho_orden
    WHERE NOT es_prueba
      AND actividad_key = ANY(%s)
      AND fecha_key BETWEEN %s AND %s
""", base).iloc[0]

ins = consulta("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (
            WHERE estado = 'confirmada'
        ) AS confirmadas,
        ROUND(
            AVG(
                EXTRACT(
                    EPOCH FROM fecha_confirmacion - fecha_inscripcion
                ) / 3600
            ) FILTER (
                WHERE estado = 'confirmada'
                  AND fecha_confirmacion >= fecha_inscripcion
            ), 2
        ) AS horas
    FROM dw.hecho_inscripcion
    WHERE NOT es_prueba
      AND actividad_key = ANY(%s)
      AND fecha_key BETWEEN %s AND %s
""", base).iloc[0]

# Cartera cobrable actual de las ordenes emitidas en el periodo seleccionado.
# La vista DW separa vigencia ordinaria y los 30 dias de regularizacion.


portfolio = consulta("""
    WITH cartera AS (
        SELECT
            c.saldo,
            c.total,
            c.recaudado,
            o.estado,
            o.expira_en,
            o.limite_saldo_en,

            (
                o.estado = 'pendiente_pago'
                AND (
                    o.expira_en IS NULL
                    OR (
                        o.expira_en AT TIME ZONE 'UTC'
                    ) > (
                        NOW() AT TIME ZONE
                        'America/El_Salvador'
                    )
                )
                AND (
                    o.limite_saldo_en IS NULL
                    OR (
                        o.limite_saldo_en AT TIME ZONE 'UTC'
                    ) > (
                        NOW() AT TIME ZONE
                        'America/El_Salvador'
                    )
                )
            ) AS activa_sidan

        FROM mart.cartera_orden c

        JOIN dw.hecho_orden o
            ON o.id_orden = c.id_orden

        WHERE c.actividad_key = ANY(%s)
          AND c.fecha_key BETWEEN %s AND %s
    )

    SELECT
        COALESCE(
            SUM(saldo) FILTER (
                WHERE activa_sidan
            ), 0
        ) AS saldo,

        COALESCE(
            SUM(total) FILTER (
                WHERE activa_sidan
            ), 0
        ) AS comprometido,

        COALESCE(
            SUM(recaudado) FILTER (
                WHERE activa_sidan
            ), 0
        ) AS recuperado

    FROM cartera
""", base).iloc[0]



delivery = consulta("""
    SELECT
        COUNT(*) AS pendientes_o_entregadas,
        COUNT(*) FILTER (
            WHERE d.cantidad_entregada >= d.cantidad
        ) AS completas
    FROM dw.hecho_detalle d
    JOIN dw.hecho_orden o USING(id_orden)
    WHERE NOT d.es_prueba
      AND o.estado = 'pagada'
      AND d.tipo_concepto = 'producto'
      AND d.actividad_key = ANY(%s)
      AND o.fecha_key BETWEEN %s AND %s
""", base).iloc[0]


# ============================================
# FUNCIONES DE FORMATO
# ============================================

def numero(v):
    return float(v or 0)


def ratio(num, den):
    return (
        None if not numero(den)
        else numero(num) / numero(den) * 100
    )


def porcentaje(value):
    return "N/D" if value is None else f"{value:,.1f}%"


def dolar(value):
    return f"${numero(value):,.2f}"


# ============================================
# RESUMEN EJECUTIVO
# ============================================

st.markdown(f"""
<div style="color:#63788e;font-size:.83rem;margin:0 0 8px;">
    <strong style="color:#1b425a;">Período seleccionado:</strong>
    {desde:%d/%m/%Y} — {hasta:%d/%m/%Y}
    &nbsp; · &nbsp;
    <strong style="color:#1b425a;">Actividades:</strong> {len(keys)}
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="section-head">
    <div class="kicker">Indicadores principales</div>
    <h2>Resumen ejecutivo</h2>
    <p>
        Diez indicadores calculados directamente sobre hechos analíticos,
        sin sumar órdenes a cobros.
    </p>
</div>
""", unsafe_allow_html=True)

m1 = st.columns(3, gap="medium")

m1[0].metric(
    "Recaudación confirmada",
    dolar(cash["recaudacion"]),
    help="Pagos Wompi confirmados + abonos manuales confirmados."
)
m1[1].metric(
    "Ventas reconocidas",
    dolar(recognized["venta"]),
    help="Registro financiero de detalles; producto requiere entrega completa."
)


m1[2].metric(
    "Saldo de órdenes activas",
    dolar(portfolio["saldo"]),
    help=(
        "Saldo pendiente de órdenes en estado "
        "pendiente_pago, dentro de su plazo de vigencia. "
        "No incluye órdenes vencidas ni canceladas."
    )
)



st.markdown("""
<div class="section-head">
    <div class="kicker">Operación y participación</div>
    <h2>Desempeño de actividades</h2>
    <p>
        Estados de órdenes, inscripciones, entregas
        y recaudo de cartera vigente.
    </p>
</div>
""", unsafe_allow_html=True)

m2 = st.columns(4, gap="medium")

m2[0].metric(
    "Órdenes pagadas / cerradas",
    porcentaje(
        ratio(
            orders["pagadas"],
            numero(orders["pagadas"]) + numero(orders["bajas"])
        )
    ),
    help="Pagada / (pagada + cancelada + vencida)."
)
m2[1].metric(
    "Inscripciones confirmadas",
    porcentaje(ratio(ins["confirmadas"], ins["total"])),
    help="Confirmadas / total de inscripciones no prueba."
)
m2[2].metric(
    "Entrega completa",
    porcentaje(
        ratio(
            delivery["completas"],
            delivery["pendientes_o_entregadas"]
        )
    ),
    help="Líneas completamente entregadas / líneas de producto en órdenes pagadas."
)
m2[3].metric(
    "Recaudo cartera vigente",
    porcentaje(
        ratio(
            portfolio["recuperado"],
            portfolio["comprometido"]
        )
    ),
    help="Cobros acreditados / valor de órdenes aún cobrables, incluidas las vencidas en regularización."
)

st.markdown("""
<div class="section-head">
    <div class="kicker">Calidad y control</div>
    <h2>Salud financiera y operativa</h2>
    <p>
        Cobertura de costos, rentabilidad bruta documentada
        y tiempos de confirmación.
    </p>
</div>
""", unsafe_allow_html=True)

m3 = st.columns(3, gap="medium")

m3[0].metric(
    "Cobertura de costo",
    porcentaje(
        ratio(
            recognized["lineas_costo"],
            recognized["lineas"]
        )
    ),
    help="Líneas reconocidas con costo conocido / todas las reconocidas."
)
m3[1].metric(
    "Margen bruto conocido",
    porcentaje(
        ratio(
            recognized["ganancia"],
            recognized["base_margen"]
        )
    ),
    help="Calculado solo sobre líneas con costo histórico conocido."
)
m3[2].metric(
    "Tiempo confirmación",
    (
        "N/D" if pd.isna(ins["horas"])
        else f"{numero(ins['horas']):,.1f} h"
    ),
    help="Promedio de horas desde inscripción hasta confirmación."
)

st.caption(
    "N/D indica ausencia de denominador u observaciones válidas. "
    "No existen metas institucionales aprobadas en esta versión."
)


# ============================================
# EVOLUCIÓN MENSUAL
# ============================================

cashtrend = consulta("""
    SELECT
        f.anio,
        f.mes,
        COALESCE(SUM(c.importe), 0) AS monto
    FROM dw.hecho_cobro c
    JOIN dw.dim_fecha f USING(fecha_key)
    WHERE NOT c.es_prueba
      AND c.actividad_key = ANY(%s)
      AND c.fecha_key BETWEEN %s AND %s
    GROUP BY 1, 2
    ORDER BY 1, 2
""", base)

salestrend = consulta("""
    SELECT
        f.anio,
        f.mes,
        COALESCE(SUM(d.venta_reconocida), 0) AS monto
    FROM dw.hecho_detalle d
    JOIN dw.dim_fecha f USING(fecha_key)
    WHERE NOT d.es_prueba
      AND d.venta_reconocida IS NOT NULL
      AND d.actividad_key = ANY(%s)
      AND d.fecha_key BETWEEN %s AND %s
    GROUP BY 1, 2
    ORDER BY 1, 2
""", base)

for df, etiqueta in [
    (cashtrend, "Cobros confirmados"),
    (salestrend, "Ventas reconocidas")
]:
    if not df.empty:
        df["periodo"] = (
            df["anio"].astype(str)
            + "-"
            + df["mes"].astype(str).str.zfill(2)
        )
        df["importe"] = df["monto"].astype(float)
        df["serie"] = etiqueta

st.markdown("""
<div class="section-head">
    <div class="kicker">Comportamiento en el tiempo</div>
    <h2>Recaudación y reconocimiento</h2>
    <p>Explorá tendencias y composición de cobros confirmados.</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns([1.62, 1], gap="large")

with c1:
    st.markdown("**Evolución mensual**")

    tendencias = pd.concat(
        [cashtrend, salestrend],
        ignore_index=True
    )

    if tendencias.empty:
        st.info("No hay movimientos en este período.")
    else:
        periodos = sorted(
            tendencias["periodo"].unique().tolist()
        )

        fig = go.Figure()

        for nombre, color in [
            ("Cobros confirmados", "#0794a1"),
            ("Ventas reconocidas", "#f2a340")
        ]:
            serie = (
                tendencias[tendencias["serie"] == nombre]
                .groupby("periodo")["importe"]
                .sum()
                .to_dict()
            )

            valores = [
                float(serie.get(periodo, 0))
                for periodo in periodos
            ]

            if len(periodos) == 1:
                fig.add_trace(go.Bar(
                    x=periodos,
                    y=valores,
                    name=nombre,
                    marker_color=color,
                    hovertemplate=(
                        "%{x}<br>$%{y:,.2f}"
                        "<extra>" + nombre + "</extra>"
                    )
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=periodos,
                    y=valores,
                    mode="lines+markers",
                    name=nombre,
                    line=dict(color=color, width=3),
                    marker=dict(size=9),
                    hovertemplate=(
                        "%{x}<br>$%{y:,.2f}"
                        "<extra>" + nombre + "</extra>"
                    )
                ))

        fig.update_layout(
            template="plotly_white",
            height=330,
            barmode="group",
            margin=dict(l=4, r=12, t=16, b=12),
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                x=0,
                font=dict(size=11)
            ),
            font=dict(
                family="Arial, sans-serif",
                color="#516980"
            ),
            xaxis=dict(
                title=None,
                type="category",
                categoryorder="array",
                categoryarray=periodos,
                showgrid=False
            ),
            yaxis=dict(
                title="Monto (USD)",
                tickprefix="$",
                separatethousands=True,
                gridcolor="#e9eef4",
                zerolinecolor="#e9eef4"
            ),
            hovermode=(
                "x unified" if len(periodos) > 1
                else "closest"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    st.caption(
        "Cobros y ventas corresponden a hechos distintos."
    )


# ============================================
# CANALES DE COBRO
# ============================================

with c2:
    st.markdown("**Canales de cobro**")

    metodos = consulta("""
        SELECT metodo, SUM(importe) AS importe
        FROM dw.hecho_cobro
        WHERE NOT es_prueba
          AND actividad_key = ANY(%s)
          AND fecha_key BETWEEN %s AND %s
        GROUP BY metodo
        ORDER BY importe DESC
    """, base)

    if metodos.empty:
        st.info(
            "Sin cobros confirmados para los filtros actuales."
        )
    else:
        metodos["importe"] = metodos["importe"].astype(float)

        fig = go.Figure(go.Pie(
            labels=metodos["metodo"],
            values=metodos["importe"],
            hole=.70,
            sort=False,
            marker=dict(
                colors=[
                    "#0794a1",
                    "#2f618e",
                    "#f2a340",
                    "#8295aa"
                ]
            ),
            textinfo="percent",
            textfont=dict(size=12, color="white"),
            hovertemplate=(
                "%{label}<br>$%{value:,.2f} "
                "(%{percent})<extra></extra>"
            )
        ))

        fig.update_layout(
            template="plotly_white",
            height=330,
            margin=dict(l=0, r=0, t=8, b=8),
            paper_bgcolor="white",
            annotations=[
                dict(
                    text="COBROS",
                    x=.5,
                    y=.5,
                    font=dict(color="#71879d", size=13),
                    showarrow=False
                )
            ],
            legend=dict(
                orientation="h",
                x=.5,
                xanchor="center",
                y=-.08,
                font=dict(size=11, color="#536a80")
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    st.caption(
        "Distribución sobre importes confirmados, "
        "no sobre cantidad de órdenes."
    )


# ============================================
# COMPARACIÓN POR ACTIVIDADES
# ============================================

st.markdown("""
<div class="section-head">
    <div class="kicker">Detalle por actividad</div>
    <h2>Comparación y exportación</h2>
    <p>
        Concentración de cobros y ventas reconocidas
        por cada actividad de SIDAN.
    </p>
</div>
""", unsafe_allow_html=True)

comparacion = consulta("""
    WITH caja AS (
        SELECT
            actividad_key,
            SUM(importe) AS cobros
        FROM dw.hecho_cobro
        WHERE NOT es_prueba
          AND fecha_key BETWEEN %s AND %s
        GROUP BY actividad_key
    ),
    ventas AS (
        SELECT
            actividad_key,
            SUM(venta_reconocida) AS ventas
        FROM dw.hecho_detalle
        WHERE NOT es_prueba
          AND fecha_key BETWEEN %s AND %s
          AND venta_reconocida IS NOT NULL
        GROUP BY actividad_key
    )
    SELECT
        a.id_actividad,
        a.nombre,
        a.categoria,
        COALESCE(c.cobros, 0) AS recaudacion,
        COALESCE(v.ventas, 0) AS ventas_reconocidas
    FROM dw.dim_actividad a
    LEFT JOIN caja c USING(actividad_key)
    LEFT JOIN ventas v USING(actividad_key)
    WHERE a.actividad_key = ANY(%s)
    ORDER BY recaudacion DESC
""", (a, b, a, b, keys))

col_chart, col_data = st.columns(
    [1.15, 1],
    gap="large"
)

with col_chart:
    st.markdown("**Actividades con importes registrados**")

    if comparacion.empty:
        st.info(
            "No existen actividades para los filtros seleccionados."
        )
    else:
        d = comparacion.copy()

        d["recaudacion"] = pd.to_numeric(
            d["recaudacion"],
            errors="coerce"
        ).fillna(0)

        d["ventas_reconocidas"] = pd.to_numeric(
            d["ventas_reconocidas"],
            errors="coerce"
        ).fillna(0)

        d = d[
            (d["recaudacion"] != 0)
            | (d["ventas_reconocidas"] != 0)
        ].head(8)

        if d.empty:
            st.info(
                "Las actividades seleccionadas no registran importes."
            )
        else:
            d["actividad"] = (
                d["id_actividad"].astype(str)
                + " · "
                + d["nombre"].astype(str).str.slice(0, 28)
            )

            d = d.iloc[::-1]

            df_melt = d.melt(
                id_vars=["actividad"],
                value_vars=[
                    "recaudacion",
                    "ventas_reconocidas"
                ],
                var_name="Concepto",
                value_name="USD"
            )

            df_melt["Concepto"] = df_melt["Concepto"].replace({
                "recaudacion": "Cobros",
                "ventas_reconocidas": "Ventas reconocidas"
            })

            fig = px.bar(
                df_melt,
                x="USD",
                y="actividad",
                orientation="h",
                color="Concepto",
                barmode="group",
                color_discrete_map={
                    "Cobros": "#0794a1",
                    "Ventas reconocidas": "#f2a340"
                },
                labels={
                    "actividad": "",
                    "USD": "USD"
                },
                template="plotly_white"
            )

            fig.update_layout(
                height=max(270, 48 * len(d) + 110),
                margin=dict(l=0, r=8, t=8, b=16),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    x=0
                ),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(color="#516980", size=11)
            )

            fig.update_xaxes(
                tickprefix="$",
                gridcolor="#e9eef4"
            )
            fig.update_yaxes(title=None)

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False}
            )

with col_data:
    st.markdown("**Detalle descargable**")

    st.dataframe(
        comparacion,
        use_container_width=True,
        hide_index=True,
        height=355
    )

    st.download_button(
        "⬇ Descargar comparación CSV",
        comparacion.to_csv(index=False).encode("utf-8-sig"),
        file_name="sidan_bi_comparacion.csv",
        mime="text/csv",
        use_container_width=True
    )


# ============================================
# INTERPRETACIONES
# ============================================

st.markdown("""
<div class="section-head">
    <div class="kicker">Lectura del tablero</div>
    <h2>Interpretación y cautelas</h2>
    <p>
        Hallazgos automáticos que necesitan contexto operacional
        para respaldar decisiones.
    </p>
</div>
""", unsafe_allow_html=True)

if (
    numero(recognized["lineas"])
    and numero(recognized["lineas_costo"])
    < numero(recognized["lineas"])
):
    st.warning(
        "La cobertura de costos no es total: "
        "el margen mostrado no representa toda la operación."
    )

if numero(cash["recaudacion"]) != numero(recognized["venta"]):
    st.info(
        "Recaudación y venta reconocida difieren. "
        "Es esperable por anticipos, entregas pendientes "
        "y momentos de reconocimiento diferentes."
    )

if numero(portfolio["saldo"]) > 0:
    st.info(
        "Hay saldo pendiente cobrable en órdenes emitidas dentro "
        "del período filtrado, incluidas las que siguen en regularización."
    )

st.caption(
    "No se calculan utilidad neta ni asistencia: "
    "los módulos estructurados correspondientes "
    "no se encontraron en el ZIP auditado."
)

st.markdown("""
<div style="text-align:center;font-size:.77rem;color:#8b9caf;padding:28px 0 2px;">
    SIDAN BI · PostgreSQL Data Warehouse · ETL Python · Dashboard Streamlit
</div>
""", unsafe_allow_html=True)
