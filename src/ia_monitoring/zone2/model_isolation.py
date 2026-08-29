"""
=========================================================================
 Módulo Analítico de Anomaly Detection & Machine Learning (Zona 2)
-------------------------------------------------------------------------
Descripción: Implementación de Isolation Forest para la detección de 
             comportamientos anómalos y ráfagas automatizadas (Bots). 
             Soporta entrenamiento multilog, generación de métricas de 
             evaluación, evaluación en tiempo real y exportación de 
             binarios portátiles (.joblib).
VERSIÓN:     1.2.0
=========================================================================
"""

import os
import re
import glob
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

class EngineIABGG:
    def __init__(self, ruta_log=None, ruta_modelo=None):
        """
        Inicializa las rutas base, el modelo Isolation Forest y los datos de respaldo.
        """
        # Calcular la raíz principal del proyecto
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        
        # 1. Ruta para localizar los archivos de logs de entrenamiento
        if ruta_log is None:
            # Intenta buscar en la carpeta de datasets del repositorio
            ruta_datasets = os.path.join(base_dir, "Biometric-Ghost-Gate", "datasets", "*.log")
            if not glob.glob(ruta_datasets):
                # Ruta alternativa si los datasets están en la raíz directa
                ruta_datasets = os.path.join(base_dir, "datasets", "*.log")
            self.ruta_log = ruta_datasets
        else:
            self.ruta_log = ruta_log

        # 2. Ruta física para guardar/cargar el binario .joblib para la VM
        if ruta_modelo is None:
            self.ruta_modelo = os.path.join(base_dir, "src", "ia_monitoring", "zone2", "bgg_isolation_forest.joblib")
        else:
            self.ruta_modelo = ruta_modelo

        # Hiperparámetros calibrados de Isolation Forest
        self.model = IsolationForest(contamination=0.15, random_state=42)
        
        # Dataset sintético de seguridad en caso de no disponer de logs
        self.respaldo_datos = pd.DataFrame([
            [1.0, 150.0, 5.0],
            [1.0, 300.0, 12.0],
            [0.0, 50.0, 0.1]
        ], columns=["status_score", "latency", "user_speed"])

    def cargar_datos_desde_log(self) -> pd.DataFrame:
        """
        Analiza los archivos .log reales extrayendo latencias de servidor (REQUEST)
        y retrasos de red/interacción humana (AUTH).
        """
        X = []
        archivos_encontrados = glob.glob(self.ruta_log)
        
        if not archivos_encontrados:
            return self.respaldo_datos

        # Expresiones regulares para la extracción de métricas
        regex_request = r"status=(?P<status>\d+).*latency=\s*(?P<latency>[\d.]+)(?P<unidad>ms|s)"
        regex_auth = r"network_delay=(?P<delay>[\d.]+)s"
        
        for ruta_archivo in archivos_encontrados:
            ultimo_delay = 0.5  # Valor por defecto inicial
            
            try:
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    for linea in f:
                        # 1. Extraer retraso del usuario (delays de autenticación)
                        match_auth = re.search(regex_auth, linea)
                        if match_auth:
                            ultimo_delay = float(match_auth.group("delay"))
                            continue
                        
                        # 2. Extraer respuesta HTTP y latencia de servidor
                        match_req = re.search(regex_request, linea)
                        if match_req:
                            status_code = int(match_req.group("status"))
                            latency_val = float(match_req.group("latency"))
                            unidad = match_req.group("unidad")
                            
                            # Normalizar latencias expresadas en segundos a milisegundos
                            if unidad == "s":
                                latency_val = latency_val * 1000.0
                                
                            status_score = 1.0 if status_code == 200 else 0.0
                            
                            # Registro: [estado_http, latencia_ms, velocidad_usuario_s]
                            X.append([status_score, latency_val, ultimo_delay])
            except Exception:
                continue
                        
        if len(X) == 0:
            return self.respaldo_datos
            
        return pd.DataFrame(X, columns=["status_score", "latency", "user_speed"])

    def entrenar_y_guardar(self) -> pd.DataFrame:
        """
        Entrena el modelo con todos los registros acumulados en los logs,
        calcula los score de anomalía y exporta el binario .joblib para la VM.
        """
        df = self.cargar_datos_desde_log()
        
        # Entrenamiento sobre las características extraídas
        self.model.fit(df[["status_score", "latency", "user_speed"]])
        
        # Generar métricas de clasificación para visualización
        df['anomaly_score'] = self.model.decision_function(df[["status_score", "latency", "user_speed"]])
        df['es_anomalia'] = self.model.predict(df[["status_score", "latency", "user_speed"]])
        df['etiqueta'] = df['es_anomalia'].map({1: 'Humano / Normal', -1: 'Anomalía / Bot'})
        
        # Guardar / Sobrescribir el modelo entrenado (.joblib)
        os.makedirs(os.path.dirname(self.ruta_modelo), exist_ok=True)
        joblib.dump(self.model, self.ruta_modelo)
        
        return df

    def cargar_modelo_exportado(self) -> bool:
        """
        Carga el binario .joblib generado si existe en disco duro.
        """
        if os.path.exists(self.ruta_modelo):
            self.model = joblib.load(self.ruta_modelo)
            return True
        return False

    def evaluar_transaccion(self, status_code: int, latency: float, user_speed: float) -> dict:
        """
        Inspecciona una transacción individual en tiempo real para determinar si debe
        bloquearse por comportamiento de Bot o autorizarse como tráfico humano.
        """
        status_score = 1.0 if status_code == 200 else 0.0
        features = np.array([[status_score, latency, user_speed]])
        
        # Inferencia con Isolation Forest
        prediccion = self.model.predict(features)[0]
        anomaly_score = float(self.model.decision_function(features)[0])
        
        # Regla de decisión y detección de ráfagas automatizadas
        if prediccion == -1 or user_speed < 0.15:
            return {
                "resultado": "ANOMALIA_DETECTADA_BLOQUEAR",
                "bloquear": True,
                "codigo_http": 403,
                "mensaje": "⚠️ ALERTA DE SEGURIDAD: Tráfico automatizado / Bot detectado. Acceso denegado.",
                "anomaly_score": anomaly_score
            }
        
        if status_code == 200 and latency > 1000.0 and user_speed >= 2.0:
            return {
                "resultado": "APROBADO_CON_ALTA_LATENCIA",
                "bloquear": False,
                "codigo_http": 200,
                "mensaje": "🟡 Tráfico legítimo verificado con alta latencia de respuesta.",
                "anomaly_score": anomaly_score
            }

        return {
            "resultado": "ACCESO_NORMAL_VALIDADO",
            "bloquear": False,
            "codigo_http": 200,
            "mensaje": "🟢 Acceso normal verificado con éxito.",
            "anomaly_score": anomaly_score
        }