"""
=========================================================================
 Módulo Analítico de Anomaly Detection & Machine Learning (Zona 2)
-------------------------------------------------------------------------
Descripción: Implementación de Isolation Forest para la detección de 
             comportamientos anómalos y ráfagas automatizadas (Bots). 
             Soporta entrenamiento multilog, generación de métricas de 
             evaluación, evaluación en tiempo real con auto-carga de 
             modelos ajustados y exportación de binarios (.joblib).
VERSIÓN:     1.4.0 (Umbral biométrico alineado con scripts/bots < 0.15s)
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

        # Hiperparámetros calibrados de Isolation Forest (contaminación ajustada)
        self.model = IsolationForest(contamination=0.20, random_state=42)
        
        # Orden estricto de características para entrenamiento e inferencia
        self.features_cols = ["latency", "user_speed", "status_code"]
        
        # Dataset sintético de respaldo calibrado con perfiles humanos y bots
        self.respaldo_datos = pd.DataFrame([
            [150.0, 1.50, 200],  # Humano
            [300.0, 2.10, 200],  # Humano
            [120.0, 1.20, 200],  # Humano
            [250.0, 0.85, 401],  # Humano (Fallo de clave)
            [15.0,  0.01, 401],  # Bot (Ataque rápido)
            [10.0,  0.001, 401], # Bot (Ataque ultra rápido)
            [5.0,   0.02, 401]   # Bot (Ataque script)
        ], columns=self.features_cols)

    def cargar_datos_desde_log(self):
        """
        Parsea los logs de producción extrayendo tuplas limpias y sincronizadas 
        directamente de eventos AUTH_OK y AUTH_FAIL.
        """
        archivos_encontrados = glob.glob(self.ruta_log) if "*" in self.ruta_log else ([self.ruta_log] if os.path.exists(self.ruta_log) else [])

        if not archivos_encontrados:
            return self.respaldo_datos[self.features_cols]

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
            return self.respaldo_datos[self.features_cols]

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
        """
        Evalúa una petición combinando la inferencia del Isolation Forest 
        con reglas de umbral biométrico estricto.
        """
        # Intentar cargar el modelo actualizado si existe
        self.cargar_modelo_exportado()

        features = pd.DataFrame([{
            'latency': float(latency),
            'user_speed': float(user_speed),
            'status_code': int(status_code)
        }])[self.features_cols]

        # Inferencia del modelo ML
        prediccion = self.model.predict(features)[0]  # -1 para anomalía, 1 para normal
        score = float(self.model.decision_function(features)[0])

        # Regla de seguridad biométrica ajustada: 
        # Si la velocidad es menor a 0.15s (rango de bot de 0.01s a 0.30s), se considera inhumana/bot.
        es_velocidad_bot = float(user_speed) < 0.15
        es_rafaga_fallos = (int(status_code) == 401) and (float(latency) < 25.0)

        bloquear = True if (prediccion == -1 or es_velocidad_bot or es_rafaga_fallos) else False

        return {
            "resultado": "ANOMALIA_DETECTADA_BLOQUEAR" if bloquear else "ACCESO_PERMITIDO",
            "bloquear": bloquear,
            "codigo_http": 403 if bloquear else 200,
            "mensaje": "ALERTA DE SEGURIDAD: Tráfico automatizado / Bot detectado por BGG." if bloquear else "Petición legítima.",
            "anomaly_score": score
        }