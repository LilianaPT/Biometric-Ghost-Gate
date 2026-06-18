import os
import re
import pandas as pd
from sklearn.ensemble import IsolationForest

class EngineIABGG:
    def __init__(self, ruta_log="logs/active/bgg_operativo.log"):
        self.ruta_log = ruta_log
        # Configuramos la IA para que detecte un 5% de actividad sospechosa (bots)
        self.model = IsolationForest(contamination=0.05, random_state=42)
        
        # Datos de respaldo por si el archivo del simulador está vacío
        self.respaldo_datos = pd.DataFrame([
            [1.0, 150.0, 5.0],  # Acceso normal: Buena respuesta, velocidad humana
            [1.0, 300.0, 12.0], # Acceso normal: Red lenta, velocidad humana
            [0.0, 50.0, 0.1]    # Bloqueo: Contraseña mal, velocidad absurdamente rápida (Bot)
        ], columns=["status_score", "latency", "user_speed"])

    def cargar_datos_desde_log(self) -> pd.DataFrame:
        """
        Esta función lee el cuaderno de notas (log) del simulador
        y extrae los números de latencia y velocidad del usuario.
        """
        X = []
        
        # Si el archivo todavía no existe, usamos los datos de respaldo
        if not os.path.exists(self.ruta_log):
            return self.respaldo_datos

        # Herramientas para buscar las palabras clave en el texto del log
        regex_auth = r"status=(?P<status>\d+).*latency=\s*(?P<latency>[\d.]+)ms"
        regex_speed = r"user_speed=(?P<user_speed>[\d.]+)s"
        
        with open(self.ruta_log, "r", encoding="utf-8") as f:
            for linea in f:
                match_auth = re.search(regex_auth, linea)
                match_speed = re.search(regex_speed, linea)
                
                # Si la línea tiene los datos completos, los guardamos
                if match_auth and match_speed:
                    status_code = int(match_auth.group("status"))
                    latency = float(match_auth.group("latency"))
                    user_speed = float(match_speed.group("user_speed"))
                    
                    # Convertimos el estatus a un número (1 si entró, 0 si falló)
                    status_score = 1.0 if status_code == 200 else 0.0
                    X.append([status_score, latency, user_speed])
                    
        if len(X) == 0:
            return self.respaldo_datos
            
        return pd.DataFrame(X, columns=["status_score", "latency", "user_speed"])

    def entrenar_modelo(self):
        """
        Esta función hace que la IA analice los datos y aprenda
        a distinguir entre un humano y un bot.
        """
        df = self.cargar_datos_desde_log()
        
        # Entrenamos la IA con las 3 variables: estatus, latencia y velocidad
        self.model.fit(df[["status_score", "latency", "user_speed"]])
        return df

    def evaluar_transaccion(self, status_code, latency, user_speed) -> str:
        """
        Revisa un intento de login en tiempo real y decide si bloquea o no.
        """
        status_score = 1.0 if status_code == 200 else 0.0
        
        # La IA predice: 1 es comportamiento normal, -1 es sospechoso (bot)
        prediccion = self.model.predict([[status_score, latency, user_speed]])[0]
        
        # Regla inteligente: Si la IA duda, pero la contraseña es correcta y la velocidad
        # es humana, no lo bloqueamos (evitamos un falso positivo por culpa del internet).
        if prediccion == -1 and status_code == 200 and user_speed >= 2.0:
            return "APROBADO_CON_ALTA_LATENCIA"
        elif prediccion == -1:
            return "ANOMALIA_DETECTADA_BLOQUEAR"
        
        return "ACCESO_NORMAL_VALIDADO"