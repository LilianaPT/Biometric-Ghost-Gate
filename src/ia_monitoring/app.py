"""
=========================================================================
 Interfaz Visual de Monitoreo y Entrenamiento en Tiempo Real (Streamlit UI)
-------------------------------------------------------------------------
Descripción: Tablero analítico para la visualización de telemetría de red,
             sincronización dinámica de logs operativos, proyección de 
             clusters en 2D, simulación de respuestas del Guardián IA y 
             exportación del modelo para entornos VM.
VERSIÓN:     1.2.0
=========================================================================
"""

import os
import glob
import streamlit as st
import plotly.express as px
from zone2.model_isolation import EngineIABGG

# Configuración de página
st.set_page_config(
    page_title="BGG - Motor IA Analítico", 
    layout="wide", 
    page_icon="🛡️"
)

st.title("🛡️ Biometric Ghost Gate (BGG)")
st.subheader("Zona 2: El Búnker - Panel de Entrenamiento e Inspección en Tiempo Real")

# Inicializar motor analítico
engine = EngineIABGG()

# --- SECCIÓN DE ACCIÓN PRINCIPAL ---
col_action, col_info = st.columns([1, 3])

with col_action:
    if st.button("🔄 Sincronizar Logs y Entrenar IA", type="primary"):
        df_entrenamiento = engine.entrenar_y_guardar()
        st.session_state['df_entrenamiento'] = df_entrenamiento
        st.session_state['entrenado'] = True
        st.success("¡Modelo entrenado y guardado en binario .joblib!")

with col_info:
    st.info(
        "Presiona el botón para procesar todos los archivos `.log`  cargados, "
        "recalibrar la frontera de decisión con Isolation Forest y actualizar el "
        "binario de despliegue para la Máquina Virtual."
    )

# --- SECCIÓN DE DIAGNÓSTICO DE ARCHIVOS LOG ---
st.markdown("---")
with st.expander("🔍 Diagnóstico de Datasets e Inspección de Archivos .log", expanded=False):
    archivos_encontrados = glob.glob(engine.ruta_log)
    st.write(f"**Patrón / Ruta de Búsqueda:** `{engine.ruta_log}`")
    st.write(f"**Total de archivos `.log` detectados:** `{len(archivos_encontrados)}`")
    
    if archivos_encontrados:
        for idx, archivo in enumerate(archivos_encontrados, 1):
            nombre_archivo = os.path.basename(archivo)
            st.code(f"[{idx}] {nombre_archivo}", language="text")
    else:
        st.warning("⚠️ No se encontraron archivos .log en la ruta especificada.")

# --- MÉTRICAS Y GRÁFICAS DE ENTRENAMIENTO ---
if 'entrenado' in st.session_state and st.session_state['entrenado']:
    df = st.session_state['df_entrenamiento']
    
    st.markdown("---")
    st.markdown("### 📊 Métricas de Evaluación de Entrenamiento")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    total_registros = len(df)
    anomalias = len(df[df['es_anomalia'] == -1])
    normales = len(df[df['es_anomalia'] == 1])
    pct_anomalia = (anomalias / total_registros) * 100 if total_registros > 0 else 0.0

    kpi1.metric("Total Telemetría", f"{total_registros:,}")
    kpi2.metric("Patrones Humanos (Normal)", f"{normales:,}", delta=f"{100-pct_anomalia:.1f}%")
    kpi3.metric("Ataques / Bots Detectados", f"{anomalias:,}", delta=f"-{pct_anomalia:.1f}%", delta_color="inverse")
    kpi4.metric("Estado del Binario", "EXPORTADO (.joblib)", help=f"Ubicado en: {engine.ruta_modelo}")

    st.markdown("---")
    st.markdown("### 🎯 Frontera de Decisión: Humanos vs. Bots")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_disp = px.scatter(
            df,
            x="user_speed",
            y="latency",
            color="etiqueta",
            symbol="status_score",
            color_discrete_map={'Humano / Normal': '#00CC96', 'Anomalía / Bot': '#EF553B'},
            title="Separación por Latencia y Velocidad de Interacción",
            labels={"user_speed": "Velocidad Usuario / Network Delay (s)", "latency": "Latencia del Servidor (ms)"},
            hover_data=["status_score", "anomaly_score"]
        )
        st.plotly_chart(fig_disp, use_container_width=True)

    with col_chart2:
        fig_hist = px.histogram(
            df,
            x="anomaly_score",
            color="etiqueta",
            color_discrete_map={'Humano / Normal': '#00CC96', 'Anomalía / Bot': '#EF553B'},
            title="Distribución del Puntaje de Aislamiento (Isolation Score)",
            barmode="overlay"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # --- SIMULADOR EN TIEMPO REAL (GUARDIÁN BGG) ---
    st.markdown("---")
    st.markdown("### 🚨 Evaluador de Tráfico en Tiempo Real (Simulador del Guardián)")
    st.caption("Prueba la respuesta del modelo ante peticiones entrantes similes a las que procesará la VM.")

    col_in1, col_in2, col_in3 = st.columns(3)
    
    with col_in1:
        st_code = st.selectbox("Código de Respuesta HTTP", [200, 401, 403, 500], index=0)
    with col_in2:
        lat_in = st.number_input("Latencia del Servidor (ms)", min_value=1.0, max_value=5000.0, value=45.0, step=5.0)
    with col_in3:
        speed_in = st.number_input("Velocidad de Usuario / Delay (s)", min_value=0.0, max_value=30.0, value=0.08, step=0.01)

    if st.button("🛡️ Evaluar Transacción con IA"):
        res = engine.evaluar_transaccion(st_code, lat_in, speed_in)
        
        if res["bloquear"]:
            st.error(f"**HTTP {res['codigo_http']} - {res['resultado']}**")
            st.error(res["mensaje"])
            st.caption(f"Score de Anomalía: `{res['anomaly_score']:.4f}`")
            st.toast("🚨 ACCIÓN DETENIDA: Intento de Bot bloqueado por BGG.", icon="⛔")
        else:
            st.success(f"**HTTP {res['codigo_http']} - {res['resultado']}**")
            st.success(res["mensaje"])
            st.caption(f"Score de Anomalía: `{res['anomaly_score']:.4f}`")
            st.toast("🟢 Acceso Autorizado: Tráfico legítimo.", icon="✅")

    # --- ENTREGABLE PARA DESPLIEGUE EN VM ---
    st.markdown("---")
    st.markdown("### 📦 Entregable para Despliegue en VM")
    st.code(f"Ruta física del binario: {engine.ruta_modelo}", language="text")
    
    if os.path.exists(engine.ruta_modelo):
        with open(engine.ruta_modelo, "rb") as f:
            st.download_button(
                label="💾 Descargar bgg_isolation_forest.joblib para VM",
                data=f,
                file_name="bgg_isolation_forest.joblib",
                mime="application/octet-stream"
            )