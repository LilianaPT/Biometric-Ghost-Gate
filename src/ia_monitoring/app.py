"""
=========================================================================
 Interfaz Visual de Monitoreo y Entrenamiento en Tiempo Real (Streamlit UI)
-------------------------------------------------------------------------
Descripción: Tablero analítico compacto de una sola pantalla para la 
             visualización de telemetría, entrenamiento del motor IA, 
             evaluación en tiempo real y exportación de binarios VM.
VERSIÓN:     1.3.0
=========================================================================
"""

import os
import glob
import streamlit as st
import plotly.express as px
from zone2.model_isolation import EngineIABGG

# Configuración de página en modo Panoramic / Wide
st.set_page_config(
    page_title="BGG - Command Center", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="collapsed"
)

# Estilos CSS compactos para eliminar espacios muertos y ajustar a 1 sola pantalla
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 0rem; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; }
        h1 { margin-bottom: 0px; font-size: 1.8rem; }
        h3 { margin-top: 5px; margin-bottom: 5px; font-size: 1.2rem; }
        .stButton>button { width: 100%; height: 2.5rem; }
    </style>
""", unsafe_allow_html=True)

# Encabezado Compacto
st.title("🛡️ Biometric Ghost Gate (BGG) — Executive Command Center")

# Inicializar motor analítico
engine = EngineIABGG()

# Auto-entrenamiento silencioso o por botón
if 'entrenado' not in st.session_state:
    st.session_state['df_entrenamiento'] = engine.entrenar_y_guardar()
    st.session_state['entrenado'] = True

df = st.session_state['df_entrenamiento']

# ---------------------------------------------------------
# FILA 1: CONTROL RÁPIDO Y METRICAS KPI (TOP BAR)
# ---------------------------------------------------------
c_ctrl, c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns([2, 2, 2, 2, 2])

with c_ctrl:
    if st.button("🔄 Re-entrenar IA", type="primary"):
        st.session_state['df_entrenamiento'] = engine.entrenar_y_guardar()
        st.toast("¡IA Re-entrenada y binario actualizado!", icon="🚀")
        st.rerun()

total_registros = len(df)
anomalias = len(df[df['es_anomalia'] == -1])
normales = len(df[df['es_anomalia'] == 1])
pct_anomalia = (anomalias / total_registros) * 100 if total_registros > 0 else 0.0

c_kpi1.metric("Telemetría Total", f"{total_registros:,}")
c_kpi2.metric("Tráfico Humano", f"{normales:,}", delta=f"{100-pct_anomalia:.1f}%")
c_kpi3.metric("Bots Detectados", f"{anomalias:,}", delta=f"-{pct_anomalia:.1f}%", delta_color="inverse")

with c_kpi4:
    if os.path.exists(engine.ruta_modelo):
        with open(engine.ruta_modelo, "rb") as f:
            st.download_button(
                label="💾 Descargar .joblib",
                data=f,
                file_name="bgg_isolation_forest.joblib",
                mime="application/octet-stream"
            )

st.divider()

# ---------------------------------------------------------
# FILA 2: DISTRIBUCIÓN PRINCIPAL DE 3 COLUMNAS (GRID COMPACTO)
# ---------------------------------------------------------
col_left, col_center, col_right = st.columns([3.5, 3.5, 3])

# --- COLUMNA IZQUIERDA: Scatter Plot Latencia vs Speed ---
with col_left:
    st.markdown("### 🎯 Frontera de Decisión (Clusters)")
    fig_disp = px.scatter(
        df,
        x="user_speed",
        y="latency",
        color="etiqueta",
        symbol="status_score",
        color_discrete_map={'Humano / Normal': '#10B981', 'Anomalía / Bot': '#EF4444'},
        labels={"user_speed": "Delay Usuario (s)", "latency": "Latencia Servidor (ms)"},
        height=320
    )
    fig_disp.update_layout(margin=dict(l=10, r=10, t=25, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_disp, use_container_width=True)

# --- COLUMNA CENTRO: Histograma Isolation Score ---
with col_center:
    st.markdown("### 📊 Distribución de Isolation Score")
    fig_hist = px.histogram(
        df,
        x="anomaly_score",
        color="etiqueta",
        color_discrete_map={'Humano / Normal': '#10B981', 'Anomalía / Bot': '#EF4444'},
        barmode="overlay",
        height=320
    )
    fig_hist.update_layout(margin=dict(l=10, r=10, t=25, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_hist, use_container_width=True)

# --- COLUMNA DERECHA: Guardián e Inspección en Tiempo Real ---
with col_right:
    st.markdown("### 🛡️ Guardián en Tiempo Real")
    st_code = st.selectbox("Código HTTP", [200, 401, 403, 500], index=0)
    lat_in = st.number_input("Latencia Servidor (ms)", min_value=1.0, max_value=5000.0, value=45.0, step=10.0)
    speed_in = st.number_input("Delay Usuario (s)", min_value=0.0, max_value=30.0, value=0.08, step=0.01)

    if st.button("🔍 Inspeccionar Tráfico"):
        res = engine.evaluar_transaccion(st_code, lat_in, speed_in)
        if res["bloquear"]:
            st.error(f"**HTTP {res['codigo_http']} - BLOQUEADO**")
            st.caption(f"Score: `{res['anomaly_score']:.4f}` | {res['mensaje']}")
            st.toast("🚨 Bot detectado y bloqueado", icon="⛔")
        else:
            st.success(f"**HTTP {res['codigo_http']} - AUTORIZADO**")
            st.caption(f"Score: `{res['anomaly_score']:.4f}` | {res['mensaje']}")
            st.toast("🟢 Acceso humano verificado", icon="✅")

    # Diagnóstico secundario colapsable al pie de la columna derecha
    with st.expander("🔍 Logs de Origen Detectados"):
        archivos = glob.glob(engine.ruta_log)
        st.caption(f"Total: {len(archivos)} archivos log")
        for a in archivos:
            st.text(f"• {os.path.basename(a)}")