import streamlit as st
import time
import os
import sys

# TRUCO MÁGICO: Le decimos a Python que busque desde la raíz del proyecto
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

# importación limpia 
from src.ia_monitoring.zone2.model_isolation import EngineIABGG

# Configuración del título de la página
st.set_page_config(page_title="BGG - Panel de Monitoreo IA", layout="wide")

# Configuración del título de la página
st.set_page_config(page_title="BGG - Panel de Monitoreo IA", layout="wide")

st.title("🛡️ Biometric Ghost Gate (BGG)")
st.subheader("Zona 2: El Búnker - Motor de IA Analítico en Tiempo Real")

# Inicializar el motor de IA
engine = EngineIABGG()

# Crear un botón en la interfaz para entrenar la IA en vivo
if st.button("🔄 Sincronizar Logs y Re-entrenar IA"):
    with st.spinner("Analizando telemetría del simulador bancario..."):
        # Llamamos a las funciones de tu otro archivo
        df_datos = engine.entrenar_modelo()
        time.sleep(1)
        st.success(f"¡IA entrenada exitosamente con {len(df_datos)} registros del log operativo!")
        
        # Mostramos los datos en una tabla bonita en la pantalla
        st.write("### Últimos datos de telemetría analizados:")
        st.dataframe(df_datos.tail(10))
        
        # Dibujamos una gráfica simple de las latencias
        st.write("### Gráfica de Latencia de Red (ms):")
        st.line_chart(df_datos["latency"])
else:
    st.info("Presiona el botón de arriba para leer el archivo de logs actual y poner a trabajar la IA.")