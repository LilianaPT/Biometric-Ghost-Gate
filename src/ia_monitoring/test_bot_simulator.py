import requests
import time

# ── Configuración de Entorno ──────────────────────────────────────────
# Cambia 'localhost:8000' por la IP o dominio de la VM de tu compañera
API_BASE = "http://localhost:8000" 

# Credenciales de prueba tomadas de la BD del proyecto
BOT_CREDENTIALS = {
    "username": "cliente_001",
    "password": "Banco$ecure#2024",
    "destination": "MX-9012-3344",
    "amount": 5000.00
}

def execute_bot_attack():
    session = requests.Session()
    print("🤖 [BOT] Iniciando simulación de ataque y login...")

    # --- PASO 1: LOGIN ---
    login_payload = {
        "username": BOT_CREDENTIALS["username"],
        "password": BOT_CREDENTIALS["password"],
        "user_speed": 0.03  # 30ms -> Inyección sobrehumana
    }

    start_time = time.time()
    try:
        res_login = session.post(
            f"{API_BASE}/api/v1/auth/login",
            json=login_payload,
            headers={"Content-Type": "application/json"}
        )

        if res_login.status_code != 200:
            print(f"❌ Falló el inicio de sesión ({res_login.status_code}):", res_login.json())
            return

        user_data = res_login.json()
        account_id = user_data.get("account_id", "MX-4821-0001")
        full_name = user_data.get("full_name", "Cliente")
        print(f"✅ Login Exitoso | Usuario: {full_name} | Cuenta: {account_id}")

        # --- PASO 2: TRANSACCIÓN INMEDIATA ---
        txn_payload = {
            "account_id": account_id,
            "destination_account": BOT_CREDENTIALS["destination"],
            "amount": BOT_CREDENTIALS["amount"],
            "user_speed": 0.01  # 10ms -> Llenado automatizado
        }

        res_txn = session.post(
            f"{API_BASE}/api/v1/transactions/transfer",
            json=txn_payload,
            headers={"Content-Type": "application/json"}
        )

        elapsed = time.time() - start_time
        print(f"⏱️ Tiempo total de ejecución del Bot: {elapsed:.3f}s")
        print(f"📊 Status Code Transacción: {res_txn.status_code}")
        print(f"📩 Respuesta del Backend (VM):", res_txn.json())

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión al backend en {API_BASE}: {e}")

if __name__ == "__main__":
    execute_bot_attack()