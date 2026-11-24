import sqlite3
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "test.db"

# Configuración de la página
st.set_page_config(
    page_title="Garage & Telemetría",
    page_icon="🏎️",
    layout="wide",
)

# --- ESTILO ---
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem;}
    div[data-testid="stMetric"] {
        background: rgba(255, 75, 75, 0.08);
        border: 1px solid rgba(255, 75, 75, 0.25);
        border-radius: 12px;
        padding: 14px 18px;
    }
    .hero {
        background: linear-gradient(90deg, #ff4b4b 0%, #8b1e3f 100%);
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 18px;
        color: white;
    }
    .hero h1 {margin: 0; font-size: 2rem; color: white;}
    .hero p {margin: 4px 0 0 0; opacity: .9;}
    </style>
    <div class="hero">
        <h1>🏎️ Garage & Telemetría</h1>
        <p>Compara coches, simula curvas de potencia y consulta la base de datos SQLite.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- BASE DE DATOS (SQLite) ---
# SQLite no necesita un servidor: es un motor embebido que lee test.db directamente
# al abrir la conexión.
def ejecutar_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Ejecuta una consulta parametrizada sobre test.db y devuelve un DataFrame."""
    with sqlite3.connect(DB_PATH) as conexion:
        return pd.read_sql_query(sql, conexion, params=params)


QUERY_VENTAS = """
SELECT SUM(su.quantity) as 'Total vendidas', su.product_id as 'id_producto'
FROM sales_uuid su
GROUP by su.product_id;
"""


@st.cache_data(ttl=60, show_spinner="Consultando test.db...")
def cargar_ventas() -> pd.DataFrame:
    return ejecutar_query(QUERY_VENTAS)


# --- DATASET DE COCHES ---
datos_coches = pd.DataFrame({
    "Modelo": [
        "Audi RS3 Sportback",
        "BMW M2 (G87)",
        "Ford Focus RS Mk3",
        "Porsche 911 GT3 (992)",
        "Toyota GR Yaris",
        "VW Golf 5 1.9 TDI",
        "VW Golf 7 GTI",
        "Honda Civic Type R (FK8)",
        "Mercedes-AMG A 45 S",
        "Renault Mégane RS Trophy",
        "Seat León Cupra 300"
    ],
    "Categoría": ["Compacto Deportivo", "Coupé", "Compacto Deportivo", "Superdeportivo", "Hot Hatch", "Compacto",
                  "Hot Hatch", "Compacto Deportivo", "Compacto Deportivo", "Hot Hatch", "Compacto Deportivo"],
    "Potencia (CV)": [400, 460, 350, 510, 280, 105, 230, 320, 421, 300, 300],
    "Par Motor (Nm)": [500, 550, 440, 470, 390, 250, 350, 400, 500, 420, 400],
    "0-100 km/h (s)": [3.8, 4.1, 4.7, 3.4, 5.2, 11.3, 6.4, 5.7, 3.9, 5.7, 5.7],
    "Peso (kg)": [1570, 1725, 1599, 1435, 1280, 1300, 1330, 1380, 1635, 1450, 1395],
    "Tracción": ["Total (Quattro)", "Trasera (RWD)", "Total (AWD)", "Trasera (RWD)", "Total (GR-Four)", "Delantera (FWD)",
                 "Delantera (FWD)", "Delantera (FWD)", "Total (4MATIC+)", "Delantera (FWD)", "Delantera (FWD)"]
})

# Calculamos relación peso/potencia
datos_coches["Peso/Potencia (kg/CV)"] = (datos_coches["Peso (kg)"] / datos_coches["Potencia (CV)"]).round(2)

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔧 Configuración de Garage")

traccion_sel = st.sidebar.multiselect(
    "Filtrar por tipo de tracción:",
    options=datos_coches["Tracción"].unique(),
    default=datos_coches["Tracción"].unique()
)

df_filtrado = datos_coches[datos_coches["Tracción"].isin(traccion_sel)]

if df_filtrado.empty:
    st.sidebar.warning("Selecciona al menos una tracción.")
    coche_opciones = datos_coches["Modelo"]
else:
    coche_opciones = df_filtrado["Modelo"]

coche_principal = st.sidebar.selectbox(
    "Selecciona vehículo para telemetría:",
    options=coche_opciones
)

st.sidebar.divider()
modo_sport = st.sidebar.toggle("Activar Repro Stage 1 (+15% CV)", value=False)

tab_garage, tab_comparar, tab_db = st.tabs(["🏁 Telemetría", "⚔️ Comparador", "🗄️ Base de datos (SQL)"])

# =====================================================================
# TAB 1: TELEMETRÍA
# =====================================================================
with tab_garage:
    info_coche = datos_coches[datos_coches["Modelo"] == coche_principal].iloc[0]

    cv_final = int(info_coche["Potencia (CV)"] * (1.15 if modo_sport else 1.0))
    par_final = int(info_coche["Par Motor (Nm)"] * (1.18 if modo_sport else 1.0))
    acel_final = round(info_coche["0-100 km/h (s)"] - (0.3 if modo_sport else 0.0), 2)

    st.subheader(f"📊 Ficha Técnica: {coche_principal} {'🔥 (Stage 1)' if modo_sport else ''}")
    st.caption(f"{info_coche['Categoría']} · {info_coche['Tracción']} · {info_coche['Peso (kg)']} kg")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Potencia", f"{cv_final} CV", f"+{cv_final - info_coche['Potencia (CV)']} CV" if modo_sport else None)
    col2.metric("Par Motor", f"{par_final} Nm", f"+{par_final - info_coche['Par Motor (Nm)']} Nm" if modo_sport else None)
    col3.metric("0-100 km/h", f"{acel_final} s", "-0.3 s" if modo_sport else None, delta_color="inverse")
    col4.metric("Relación Peso/Potencia", f"{round(info_coche['Peso (kg)'] / cv_final, 2)} kg/CV")

    st.divider()

    col_izq, col_der = st.columns([1.3, 1])

    with col_izq:
        st.subheader("📈 Curva de Potencia Simulada (RPM)")
        rpm = np.arange(1500, 7500, 500)
        factor_curva = np.sin(np.linspace(0.3, 2.5, len(rpm)))
        curva_cv = (factor_curva / factor_curva.max()) * cv_final

        df_telemetria = pd.DataFrame({
            "RPM": rpm,
            "Potencia (CV)": curva_cv.round(1)
        }).set_index("RPM")

        st.area_chart(df_telemetria, color="#FF4B4B")

    with col_der:
        st.subheader("🏁 Comparativa del Garage")
        st.dataframe(
            df_filtrado[["Modelo", "Potencia (CV)", "0-100 km/h (s)", "Peso/Potencia (kg/CV)"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Potencia (CV)": st.column_config.ProgressColumn(
                    "Potencia (CV)", min_value=0, max_value=int(datos_coches["Potencia (CV)"].max()), format="%d"
                ),
            },
        )

    st.subheader("⚡ Comparativa de Caballos (CV) por Modelo")
    st.bar_chart(df_filtrado.set_index("Modelo")["Potencia (CV)"], color="#FF4B4B")

# =====================================================================
# TAB 2: COMPARADOR DE DOS COCHES
# =====================================================================
with tab_comparar:
    st.subheader("⚔️ Cara a cara")
    c1, c2 = st.columns(2)
    modelos = datos_coches["Modelo"].tolist()
    coche_a = c1.selectbox("Coche A", modelos, index=0, key="coche_a")
    coche_b = c2.selectbox("Coche B", modelos, index=5, key="coche_b")

    a = datos_coches[datos_coches["Modelo"] == coche_a].iloc[0]
    b = datos_coches[datos_coches["Modelo"] == coche_b].iloc[0]

    # (columna, "mayor es mejor")
    campos = [
        ("Potencia (CV)", True),
        ("Par Motor (Nm)", True),
        ("0-100 km/h (s)", False),
        ("Peso (kg)", False),
        ("Peso/Potencia (kg/CV)", False),
    ]
    filas = []
    for campo, mayor_mejor in campos:
        va, vb = a[campo], b[campo]
        if va == vb:
            ganador = "Empate"
        else:
            gana_a = (va > vb) == mayor_mejor
            ganador = coche_a if gana_a else coche_b
        filas.append({"Dato": campo, coche_a: va, coche_b: vb, "Mejor": ganador})

    st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

# =====================================================================
# TAB 3: CONSULTA SQL SOBRE test.db
# =====================================================================
with tab_db:
    st.subheader("🗄️ Unidades vendidas por producto (test.db)")

    if not DB_PATH.exists():
        st.error(f"No se encuentra la base de datos en `{DB_PATH}`.")
    else:
        try:
            ventas = cargar_ventas()
        except sqlite3.Error as e:
            st.error(f"Error al consultar la base de datos: {e}")
            ventas = None

        if ventas is not None:
            if ventas.empty:
                st.info("La consulta no devolvió resultados.")
            else:
                min_u = st.slider(
                    "Mostrar productos con al menos X unidades vendidas",
                    0, int(ventas["Total vendidas"].max()), 0,
                )
                filtrado = ventas[ventas["Total vendidas"] >= min_u].sort_values(
                    "Total vendidas", ascending=False
                )

                m1, m2, m3 = st.columns(3)
                m1.metric("Productos distintos", f"{len(filtrado)}")
                m2.metric("Unidades vendidas", f"{int(filtrado['Total vendidas'].sum())}")
                if not filtrado.empty:
                    m3.metric("Producto más vendido", f"{int(filtrado['Total vendidas'].max())} uds")

                st.markdown("**Top 15 productos por unidades vendidas**")
                top = filtrado.head(15)
                st.altair_chart(
                    alt.Chart(top).mark_bar(color="#FF4B4B").encode(
                        x=alt.X("Total vendidas:Q", title="Unidades"),
                        y=alt.Y("id_producto:N", sort="-x", title=None),
                        tooltip=["id_producto", "Total vendidas"],
                    ),
                    use_container_width=True,
                )

                st.dataframe(filtrado, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇️ Descargar resultados (CSV)",
                    filtrado.to_csv(index=False).encode("utf-8"),
                    file_name="ventas_por_producto.csv",
                    mime="text/csv",
                )

            with st.expander("Ver consulta SQL ejecutada"):
                st.code(QUERY_VENTAS.strip(), language="sql")

            if st.button("🔄 Recargar datos de test.db"):
                cargar_ventas.clear()
                st.rerun()
