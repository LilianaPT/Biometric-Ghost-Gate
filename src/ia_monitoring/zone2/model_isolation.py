import os
import re
import glob
import pandas as pd
from sklearn.ensemble import IsolationForest

class EngineIABGG:
    def __init__(self, ruta_log=None):
        if ruta_log is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            self.ruta_log = os.path.join(base_dir, "datasets", "*.log")
        else:
            self.ruta_log = ruta_log
            
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.respaldo_datos = pd.DataFrame([
            [1.0, 150.0, 5.0],
            [1.0, 300.0, 12.0],
            [0.0, 50.0, 0.1]
        ], columns=["status_score", "latency", "user_speed"])

    def cargar_datos_desde_log(self) -> pd.DataFrame:
        """
        Analiza los logs reales extrayendo latencias de REQUEST 
        y retrasos de red de los bloques de AUTH.
        """
        X = []
        archivos_encontrados = glob.glob(self.ruta_log)
        
        if not archivos_encontrados:
            return self.respaldo_datos

        # Expresiones regulares adaptadas al formato real de tus archivos
        # Con \s* soportamos cualquier cantidad de espacios o tabulaciones intermedias
        regex_request = r"status=(?P<status>\d+).*latency=\s*(?P<latency>[\d.]+)(?P<unidad>ms|s)"
        regex_auth = r"network_delay=(?P<delay>[\d.]+)s"
        
        for ruta_archivo in archivos_encontrados:
            # Mantendremos un registro del último delay de red detectado
            ultimo_delay = 0.5  # Valor por defecto si no ha habido login previo
            
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                for linea in f:
                    # 1. Si es línea de AUTH, guardamos el delay del usuario
                    match_auth = re.search(regex_auth, linea)
                    if match_auth:
                        ultimo_delay = float(match_auth.group("delay"))
                        continue
                    
                    # 2. Si es línea de REQUEST, extraemos los datos y armamos el registro
                    match_req = re.search(regex_request, linea)
                    if match_req:
                        status_code = int(match_req.group("status"))
                        latency_val = float(match_req.group("latency"))
                        unidad = match_req.group("unidad")
                        
                        # Si por alguna razón viene en segundos, normalizamos a milisegundos
                        if unidad == "s":
                            latency_val = latency_val * 1000.0
                            
                        status_score = 1.0 if status_code == 200 else 0.0
                        
                        # Guardamos: [status, latencia_ms, velocidad_usuario_en_segundos]
                        X.append([status_score, latency_val, ultimo_delay])
                        
        if len(X) == 0:
            return self.respaldo_datos
            
        return pd.DataFrame(X, columns=["status_score", "latency", "user_speed"])

    def entrenar_modelo(self):
        df = self.cargar_datos_desde_log()
        self.model.fit(df[["status_score", "latency", "user_speed"]])
        return df

    def evaluar_transaccion(self, status_code, latency, user_speed) -> str:
        status_score = 1.0 if status_code == 200 else 0.0
        prediccion = self.model.predict([[status_score, latency, user_speed]])[0]
        
        if prediccion == -1 and status_code == 200 and user_speed >= 2.0:
            return "APROBADO_CON_ALTA_LATENCIA"
        elif prediccion == -1:
            return "ANOMALIA_DETECTADA_BLOQUEAR"
        
        return "ACCESO_NORMAL_VALIDADO"