import streamlit as st
import time
import os
import sys
import glob

# Forzar la ruta raíz del proyecto
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

from src.ia_monitoring.zone2.model_isolation import EngineIABGG

st.set_page_config(page_title="Biometric Ghost Gate (BGG)", layout="wide")
st.title("🛡️ Biometric Ghost Gate (BGG)")
st.subheader("Zona 2: El Búnker - Motor de IA Analítico en Tiempo Real")

# Instanciamos el motor
engine = EngineIABGG()

if st.button("🔄 Sincronizar Logs y Re-entrenar IA"):
    with st.spinner("Analizando telemetría..."):
        time.sleep(0.5)
        df = engine.entrenar_modelo()
        
        # --- BLOQUE DE DIAGNÓSTICO EN PANTALLA ---
        st.info("🔍 **Diagnóstico de la carpeta Datasets:**")
        archivos = glob.glob(engine.ruta_log)
        st.write(f"• **Ruta buscada por Python:** `{engine.ruta_log}`")
        st.write(f"• **Archivos `.log` encontrados:** {len(archivos)}")
        if archivos:
            for arc in archivos:
                st.write(f"  - Archivo detectado: `{os.path.basename(arc)}`")
        else:
            st.warning("⚠️ ¡Python no encontró ningún archivo en esa ruta física!")
        # ------------------------------------------

        st.success(f"¡IA entrenada exitosamente con {len(df)} registros del log operativo!")
        
        st.subheader("Últimos datos de telemetría analizados:")
        st.dataframe(df)