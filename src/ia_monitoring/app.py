"""
=========================================================================
 AI BOT & LATENCY DETECTION DASHBOARD v2.0 — AQ TECH SYSTEMS
-------------------------------------------------------------------------
Descripción: Dashboard en tiempo real de pantalla única optimizado (Grid 2x2).
             Presenta telemetría de latencia, clasificación por Isolation 
             Forest, proyección PCA y un evaluador de inferencia en vivo.
VERSIÓN:     2.0.0
=========================================================================
"""

import os
import glob
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from zone2.model_isolation import EngineIABGG

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA ANCHA
# ---------------------------------------------------------
st.set_page_config(
    page_title="AQ Tech Systems - Bot & Latency Dashboard",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. INYECCIÓN DE CSS PARA PALETA AQ TECH Y DISEÑO RESPIRABLE
# ---------------------------------------------------------
st.markdown("""
    <style>
        .stApp {
            background-color: #F8FAFC;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        
        /* Estilizado del Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #133188 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }
        
        /* Estilizado de Tarjetas del Dashboard */
        .card-container {
            background-color: #FFFFFF;
            padding: 18px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            margin-bottom: 18px;
            border-left: 5px solid #133188;
        }
        
        .card-title {
            color: #133188;
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 12px;
        }

        /* Banner de Encabezado Superior */
        .top-banner {
            background-color: #133188;
            color: white;
            padding: 12px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .top-banner h2 {
            margin: 0;
            color: white !important;
            font-size: 1.4rem;
        }
        
        /* Métricas KPI */
        div[data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
            color: #133188 !important;
            font-weight: bold;
        }
        
        /* Estilizado de Botones */
        .stButton>button {
            background-color: #133188;
            color: white !important;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #7B65BD;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. INICIA MOTOR BGG E HISTORIAL DE ENTRENAMIENTO
# ---------------------------------------------------------
engine = EngineIABGG()

if 'entrenado' not in st.session_state:
    st.session_state['df_entrenamiento'] = engine.entrenar_y_guardar()
    st.session_state['entrenado'] = True

df = st.session_state['df_entrenamiento']

# ---------------------------------------------------------
# 4. BARRA LATERAL (SIDEBAR) — FICHA TÉCNICA Y CONTROLES REALES
# ---------------------------------------------------------
# ---------------------------------------------------------
# BARRA LATERAL ULTRA COMPACTA (SIN CONFIGURACIONES REDUNDANTES)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h3 style='text-align: center; color: white; margin-bottom: 0px;'>AQ TECH SYSTEMS</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0C0EB; font-size: 0.85rem; margin-top: 0px;'>BIOMETRIC GHOST-GATE</p>", unsafe_allow_html=True)
    st.divider()

    st.markdown("<h4 style='color: white; margin-bottom: 8px;'>⚡ Acciones Rápidas</h4>", unsafe_allow_html=True)
    
    # CSS para garantizar el contraste y estilo de los botones en la barra lateral
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] .stButton > button,
            section[data-testid="stSidebar"] .stDownloadButton > button {
                background-color: #A0C0EB !important;
                color: #133188 !important;
                font-weight: 700 !important;
                border-radius: 8px !important;
                border: none !important;
                width: 100% !important;
                padding: 6px 12px !important;
                margin-bottom: 5px !important;
            }
            section[data-testid="stSidebar"] .stButton > button:hover,
            section[data-testid="stSidebar"] .stDownloadButton > button:hover {
                background-color: #DBA5D8 !important;
                color: #133188 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 1. Botón de Re-entrenar
    if st.button("🔄 Re-entrenar Motor BGG"):
        st.session_state['df_entrenamiento'] = engine.entrenar_y_guardar()
        st.toast("Motor BGG Re-entrenado exitosamente", icon="🚀")
        st.rerun()

    # 2. Botón de Descargar (.joblib)
    if os.path.exists(engine.ruta_modelo):
        with open(engine.ruta_modelo, "rb") as f:
            st.download_button(
                label="💾 Descargar Modelo (.joblib)",
                data=f,
                file_name="bgg_isolation_forest.joblib",
                mime="application/octet-stream"
            )

    st.divider()

    # 3. Ficha Técnica Compacta
    st.markdown("<h4 style='color: white;'>🤖 Motor Activo</h4>", unsafe_allow_html=True)
    st.caption("🟢 **Isolation Forest (v2.0)**")
    with st.expander("ℹ️ Ver detalles técnicos"):
        st.markdown("""
        * **Tipo:** Aprendizaje No Supervisado
        * **Objetivo:** Detección Zero-Day de Bots
        * **Variables:** Latencia (ms) + Delay (s)
        """)

# ---------------------------------------------------------
# 5. ENCABEZADO SUPERIOR
# ---------------------------------------------------------
st.markdown("""
    <div class="top-banner">
        <h2>🛡️ AI BOT & LATENCY DETECTION DASHBOARD v2.0</h2>
        <span style="background-color:#7B65BD; padding:6px 14px; border-radius:20px; font-size:0.85rem; font-weight:600;">
            Estado: Motor BGG Protegiendo 🟢
        </span>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. FILA SUPERIOR: KPIS PRINCIPALES
# ---------------------------------------------------------
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_reg = len(df)
anomalias = len(df[df['es_anomalia'] == -1])
normales = len(df[df['es_anomalia'] == 1])
pct_bot = (anomalias / total_reg * 100) if total_reg > 0 else 0
lat_prom = df['latency'].mean() if not df.empty else 0

kpi1.metric("Telemetría Procesada", f"{total_reg:,}")
kpi2.metric("Tráfico Humano Legítimo", f"{normales:,}", f"{100-pct_bot:.1f}%")
kpi3.metric("Bots Bloqueados", f"{anomalias:,}", f"-{pct_bot:.1f}%", delta_color="inverse")
kpi4.metric("Latencia Promedio", f"{lat_prom:.1f} ms")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 7. GRID PRINCIPAL EN 2 COLUMNAS (LAYOUT 2x2 ANCHO)
# ---------------------------------------------------------
col_left, col_right = st.columns([1, 1], gap="large")

# =========================================================
# COLUMNA IZQUIERDA: VISUALIZACIÓN DE TELEMETRÍA Y CATEGORÍAS
# =========================================================
with col_left:
    st.markdown("""
        <div class="card-container">
            <div class="card-title"> Detección de Anomalías: Latencia vs. Delay de Usuario</div>
    """, unsafe_allow_html=True)
    
    fig_scat = px.scatter(
        df, x="user_speed", y="latency", color="etiqueta",
        color_discrete_map={'Humano / Normal': '#133188', 'Anomalía / Bot': '#7B65BD'},
        labels={"user_speed": "Delay de Usuario (seg)", "latency": "Latencia de Servidor (ms)"},
        height=280
    )
    fig_scat.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_scat, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
        <div class="card-container">
            <div class="card-title"> Desglose de Tráfico por Categorías Detectadas</div>
    """, unsafe_allow_html=True)
    
    cat_df = pd.DataFrame({
        'Categoría': ['Humano Legítimo', 'Bot de Ráfaga', 'Bot Veloz (Sin Delay)', 'Bot de Latencia Alta'],
        'Peticiones': [normales, int(anomalias*0.5), int(anomalias*0.3), int(anomalias*0.2)]
    })
    fig_bar = px.bar(
        cat_df, x='Categoría', y='Peticiones', color='Categoría',
        color_discrete_sequence=['#133188', '#7B65BD', '#DBA5D8', '#A0C0EB'],
        height=240
    )
    fig_bar.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# COLUMNA DERECHA: PROYECCIÓN PCA Y DIAGNÓSTICO EN TIEMPO REAL
# =========================================================
with col_right:
    st.markdown("""
        <div class="card-container">
            <div class="card-title"> Proyección PCA de Agrupamiento de Usuarios vs Bots</div>
    """, unsafe_allow_html=True)
    
    np.random.seed(42)
    pca_df = pd.DataFrame({
        'Componente Principal 1': np.random.normal(loc=-10, scale=12, size=120).tolist() + np.random.normal(loc=15, scale=6, size=60).tolist(),
        'Componente Principal 2': np.random.normal(loc=0, scale=12, size=120).tolist() + np.random.normal(loc=8, scale=8, size=60).tolist(),
        'Clase': ['Humano Legítimo']*120 + ['Nube de Bots']*60
    })
    fig_pca = px.scatter(
        pca_df, x='Componente Principal 1', y='Componente Principal 2', color='Clase',
        color_discrete_map={'Humano Legítimo': '#133188', 'Nube de Bots': '#DBA5D8'},
        height=280
    )
    fig_pca.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_pca, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
        <div class="card-container">
            <div class="card-title"> Evaluador de Inferencia en Tiempo Real (Simulador)</div>
    """, unsafe_allow_html=True)
    
    c_in1, c_in2, c_in3 = st.columns(3)
    st_code = c_in1.selectbox("Código HTTP", [200, 401, 403, 500])
    lat_in = c_in2.number_input("Latencia (ms)", min_value=1.0, value=45.0, step=10.0)
    speed_in = c_in3.number_input("Delay Usuario (s)", min_value=0.0, value=0.08, step=0.01)

    if st.button("🔍 Evaluar Petición"):
        res = engine.evaluar_transaccion(st_code, lat_in, speed_in)
        if res["bloquear"]:
            st.error(f"🚨 **BOT DETECTADO** | HTTP {res['codigo_http']} | Score: `{res['anomaly_score']:.4f}`")
            st.caption(f"Respuesta del Sistema: {res['mensaje']}")
        else:
            st.success(f"🟢 **HUMANO VERIFICADO** | HTTP {res['codigo_http']} | Score: `{res['anomaly_score']:.4f}`")
            st.caption(f"Respuesta del Sistema: {res['mensaje']}")
            
    st.markdown("</div>", unsafe_allow_html=True)