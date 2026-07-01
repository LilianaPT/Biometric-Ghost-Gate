import os
import time
import random
from datetime import datetime

def generar_log_bot(num_peticiones=150):
    """
    Simula un bot de fuerza bruta/credential stuffing atacando el Ghost Gate.
    Genera patrones de tiempo ultra-rápidos y múltiples códigos de error.
    """
    # Definimos la ruta absoluta exacta para evitar que dependa de dónde ejecutas el script
    datasets_dir = r"D:\bggIA_2\datasets"
    
    # Verificación de respaldo por si cambió la letra de la unidad o la carpeta base
    if not os.path.exists(datasets_dir):
        # Si no existe la ruta absoluta, intentamos la ruta relativa combinada
        base_dir = os.path.abspath(os.path.dirname(__file__))
        datasets_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "Biometric-Ghost-Gate", "datasets"))

    # Asegura que la carpeta exista físicamente
    os.makedirs(datasets_dir, exist_ok=True)
        
    # Si por alguna razón no existe la carpeta, la crea automáticamente
    os.makedirs(datasets_dir, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"bgg_bot_attack_{timestamp_str}.log"
    ruta_log = os.path.join(datasets_dir, nombre_archivo)

    print(f"🤖 Iniciando simulación de Bot Atacante...")
    print(f"📂 Escribiendo anomalías en: {ruta_log}")

    with open(ruta_log, "w", encoding="utf-8") as f:
        for i in range(num_peticiones):
            # 1. Simular la velocidad del usuario (network_delay) de un script automatizado
            # Un bot no tiene retrasos humanos (los humanos varían entre 0.3s y varios segundos)
            # El bot ataca con delays fijos y ultra cortos (ej. 0.001s a 0.02s)
            bot_delay = random.choice([0.001, 0.005, 0.012])
            f.write(f"2026-06-17 {datetime.now().time()} [AUTH] - User sequence initiated - network_delay={bot_delay}s\n")
            
            # 2. Simular la respuesta del servidor (REQUEST)
            # La mayoría de los intentos de un bot de fuerza bruta serán fallidos (401 o 403)
            # Además, las ráfagas rápidas tienden a elevar la latencia del servidor o ser sospechosamente idénticas
            es_exitoso = random.choices([200, 401, 403], weights=[10, 70, 20])[0]
            
            if es_exitoso == 200:
                latency = random.uniform(10.0, 45.0) # Petición normal ocasional
            else:
                # El servidor procesando bloqueos o errores de autenticación bajo ataque
                latency = random.uniform(350.0, 600.0) 
            
            f.write(f"2026-06-17 {datetime.now().time()} [REQUEST] - POST /api/v1/auth/login - status={es_exitoso} latency={latency:.2f}ms\n")
            
            # El script del bot se ejecuta casi instantáneamente sin pausas reales
            time.sleep(0.005)

    print(f"✅ Simulación completada. Se inyectaron {num_peticiones} registros anómalos de bot.")

if __name__ == "__main__":
    generar_log_bot()