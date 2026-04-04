from playwright.sync_api import sync_playwright

# Este ejemplo usa Playwright en modo síncrono.
# Eso significa que cada instrucción se ejecuta una después de otra,
# sin necesitar `async`, `await` ni un ciclo de eventos de asyncio.
with sync_playwright() as p:
    # Se abre Firefox en modo visible para ver el navegador mientras corre el script.
    browser = p.firefox.launch(headless=False)

    # Se crea una página nueva dentro del navegador.
    page = browser.new_page()

    # Se navega a la página principal de Mercado Libre.
    # En este punto, la ejecución se detiene hasta que la navegación termina.
    page.goto("https://www.mercadolibre.com.mx/")

    # Se toma una captura de pantalla de la página cargada.
    # La ruta relativa `data/test-1.png` guarda la imagen dentro del proyecto.
    page.screenshot(path="data/test-1.png")

    # Se cierra el navegador al terminar.
    browser.close()