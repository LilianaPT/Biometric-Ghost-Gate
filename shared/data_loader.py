import os
import re
import glob
import numpy as np

def cargar_ultimo_dataset_log(directorio_datasets="datasets"):
    """
    Busca el archivo de log más reciente en la carpeta 'datasets'
    y extrae las características para el entrenamiento de la IA.
    """
    # Buscar todos los archivos .log en la ruta provista por el equipo
    archivos = glob.glob(os.path.join(directorio_datasets, "bgg_*.log"))
    if not archivos:
        print("⚠️ No se encontraron archivos de log en la carpeta 'datasets'.")
        return None
    
    # Obtener el archivo más reciente por fecha de modificación
    ultimo_archivo = max(archivos, key=os.path.getmtime)
    print(f"📦 Procesando dataset operativo: {ultimo_archivo}")
    
    caracteristicas = []
    
    # Expresión regular para capturar: status y latency
    pattern = re.compile(r"status=(\d+)\s+latency=([\d\.]+)ms")
    
    with open(ultimo_archivo, "r", encoding="utf-8") as f:
        for linea in f:
            if "endpoint=/api/v1/auth/login" in linea:
                match = pattern.search(linea)
                if match:
                    status = int(match.group(1))
                    latencia = float(match.group(2))
                    
                    # Transformación de características:
                    # Como Isolation Forest requiere entradas numéricas, mapeamos el status:
                    # Un login exitoso (200) se considera comportamiento basal normal (1)
                    # Un login fallido (401) incrementa la sospecha de anomalía (0)
                    status_score = 1.0 if status == 200 else 0.0
                    
                    # Creamos el vector de entrenamiento: [status_score, latencia]
                    caracteristicas.append([status_score, latencia])
                    
    return np.array(caracteristicas)