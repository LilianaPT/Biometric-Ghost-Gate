"""
=========================================================================
 Módulo Analítico de Anomaly Detection & Machine Learning (Zona 2)
-------------------------------------------------------------------------
Descripción: Implementación de Isolation Forest para la detección de 
             comportamientos anómalos y ráfagas automatizadas (Bots). 
             Soporta entrenamiento multilog, generación de métricas de 
             evaluación, evaluación en tiempo real con auto-carga de 
             modelos ajustados y exportación de binarios (.joblib).
VERSIÓN:     1.2.2 (Alineación de características y tipos)
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
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        
        # 1. Ruta para localizar los archivos de logs de entrenamiento
        if ruta_log is None:
            ruta_datasets = os.path.join(base_dir, "Biometric-Ghost-Gate", "datasets", "*.log")
            if not glob.glob(ruta_datasets):
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
        
        # Orden estricto de características para entrenamiento e inferencia
        self.features_cols = ["latency", "user_speed", "status_code"]
        
        # Dataset sintético de seguridad en caso de ausencia de logs
        self.respaldo_datos = pd.DataFrame([
            [150.0, 1.5, 200],
            [300.0, 2.0, 200],
            [50.0, 0.01, 401]
        ], columns=self.features_cols)

    def cargar_datos_desde_log(self):
        """
        Parsea los logs de producción extrayendo tuplas limpias y sincronizadas 
        directamente de eventos AUTH_OK y AUTH_FAIL.
        """
        archivos_encontrados = glob.glob(self.ruta_log) if "*" in self.ruta_log else ([self.ruta_log] if os.path.exists(self.ruta_log) else [])

        if not archivos_encontrados:
            return pd.DataFrame({
                'latency': [45.0, 120.0, 350.0, 50.0, 800.0, 12.0],
                'user_speed': [1.2, 2.5, 0.05, 1.8, 0.01, 0.02],
                'status_code': [200, 200, 401, 200, 429, 200]
            })[self.features_cols]

        registros = []
        for ruta_archivo in archivos_encontrados:
            try:
                with open(ruta_archivo, 'r', encoding='utf-8') as f:
                    for linea in f:
                        if "AUTH_OK" in linea or "AUTH_FAIL" in linea or "TRANSACTION" in linea:
                            match_delay = re.search(r"network_delay=([\d\.]+)", linea)
                            match_speed = re.search(r"user_speed=([\d\.]+)", linea)
                            
                            if match_delay and match_speed:
                                network_delay_sec = float(match_delay.group(1))
                                latency_ms = network_delay_sec * 1000.0
                                user_speed_sec = float(match_speed.group(1))
                                status_code = 200 if "AUTH_OK" in linea else 401
                                
                                registros.append({
                                    'latency': latency_ms,
                                    'user_speed': user_speed_sec,
                                    'status_code': status_code
                                })
            except Exception:
                continue

        if not registros:
            return pd.DataFrame({
                'latency': [45.0, 120.0, 50.0],
                'user_speed': [1.2, 2.5, 1.8],
                'status_code': [200, 200, 200]
            })[self.features_cols]

        return pd.DataFrame(registros)[self.features_cols]

    def entrenar_y_guardar(self) -> pd.DataFrame:
        """
        Entrena el modelo con todos los registros acumulados en los logs,
        calcula los scores de anomalía y exporta el binario .joblib para la VM.
        """
        df = self.cargar_datos_desde_log()
        
        # Entrenamiento alineado con features_cols: ['latency', 'user_speed', 'status_code']
        self.model.fit(df[self.features_cols])
        
        # Generar métricas de clasificación para visualización
        df['anomaly_score'] = self.model.decision_function(df[self.features_cols])
        df['es_anomalia'] = self.model.predict(df[self.features_cols])
        df['etiqueta'] = df['es_anomalia'].map({1: 'Humano / Normal', -1: 'Anomalía / Bot'})
        
        # Guardar / Sobrescribir el modelo entrenado (.joblib)
        os.makedirs(os.path.dirname(self.ruta_modelo), exist_ok=True)
        joblib.dump(self.model, self.ruta_modelo)
        
        return df

    def cargar_modelo_exportado(self) -> bool:
        """
        Carga el binario .joblib generado si existe en el almacenamiento.
        """
        if os.path.exists(self.ruta_modelo):
            try:
                self.model = joblib.load(self.ruta_modelo)
                return True
            except Exception:
                return False
        return False

    def evaluar_transaccion(self, status_code: int, latency: float, user_speed: float):
        # Crear DataFrame con el mismo orden exacto de columnas que en el entrenamiento
        features = pd.DataFrame([{
            'latency': float(latency),
            'user_speed': float(user_speed),
            'status_code': int(status_code)
        }])[self.features_cols]

        # Inferencia con la instancia cargada
        prediccion = self.model.predict(features)[0]  # -1 para anomalía, 1 para normal
        score = float(self.model.decision_function(features)[0])

        bloquear = True if prediccion == -1 else False

        return {
            "resultado": "ANOMALIA_DETECTADA_BLOQUEAR" if bloquear else "ACCESO_PERMITIDO",
            "bloquear": bloquear,
            "codigo_http": 403 if bloquear else 200,
            "mensaje": "ALERTA DE SEGURIDAD: Tráfico automatizado / Bot detectado." if bloquear else "Petición legítima.",
            "anomaly_score": score
        }