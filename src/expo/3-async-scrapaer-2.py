import asyncio
import json
from playwright.async_api import async_playwright

async def scraper(page):
    # Selector principal del listado de resultados de Mercado Libre.
    items = page.locator("//ol[contains(@class,'ui-search-layout')]//li")

    # Se espera el primer elemento antes de leer cualquier dato.
    # Esto evita fallos si la página todavía no terminó de renderizar el listado.
    await items.first.wait_for(timeout=40000)

    total = await items.count()
    datos = []

    # Se recorren todos los productos visibles en la página actual.
    for i in range(total):
        item = items.nth(i)

        # Selectores básicos de cada tarjeta.
        titulo_loc = item.locator("h3 a").first
        precio_entero_loc = item.locator("span.andes-money-amount__fraction").first
        precio_centavos_loc = item.locator("span.andes-money-amount__cents").first
        cuotas_loc = item.locator(".poly-price__installments").first

        # El atributo `href` normalmente lleva el enlace al detalle del producto.
        href = await titulo_loc.get_attribute("href") if await titulo_loc.count() else None
    
        # El título se extrae como texto visible.
        titulo = (await titulo_loc.inner_text()).strip() if await titulo_loc.count() else "Sin titulo"

        # El precio está dividido en dos partes: entero y centavos.
        entero = (await precio_entero_loc.inner_text()).strip() if await precio_entero_loc.count() else ""
        centavos = (await precio_centavos_loc.inner_text()).strip() if await precio_centavos_loc.count() else "00"
        precio = f"{entero}.{centavos}" if entero else "Sin precio"
        
        # Las cuotas aparecen solo si el producto ofrece financiamiento.
        cuotas = (await cuotas_loc.inner_text()).strip() if await cuotas_loc.count() else None

        # Se guarda cada producto como un diccionario para luego exportarlo a JSON.
        datos.append({
            "titulo": titulo,
            "href": href,
            "precio": precio,
            "cuotas": cuotas,
        })

    return datos

async def play(query):
    # `async with` abre y cierra automáticamente la sesión asíncrona de Playwright.
    async with async_playwright() as p:
        # Navegador visible para observar el proceso paso a paso.
        browser = await p.firefox.launch(headless=False)

        # Página nueva donde se hace la navegación y la búsqueda.
        page = await browser.new_page()

        # Se entra a la portada del sitio.
        await page.goto("https://www.mercadolibre.com.mx/")

        # Se llena el campo de búsqueda con el texto ingresado por el usuario.
        await page.get_by_role("combobox", name="Ingresa lo que quieras").fill(query)

        # Se presiona el botón de buscar.
        await page.get_by_role("button", name="Buscar").click()

        # Se espera a que el primer resultado exista, en lugar de usar `networkidle`.
        await page.locator("//ol[contains(@class,'ui-search-layout')]//li").first.wait_for(timeout=40000)

        pagina = 1
        todos_los_datos = []

        # Bucle para recorrer todas las páginas de resultados.
        while True:
            print(f"\n=== Pagina {pagina} ===")

            # Se extraen los productos de la página actual.
            datos = await scraper(page)
            todos_los_datos.extend(datos)

            # Botón "Siguiente" del paginador.
            next_btn = page.locator(
                "li.andes-pagination__button--next:not(.andes-pagination__button--disabled) a"
            )

            # Si no existe, ya no hay más páginas.
            if await next_btn.count() == 0:
                break

            # Se avanza a la siguiente página y se vuelve a esperar el listado.
            await next_btn.first.click()
            await page.locator("//ol[contains(@class,'ui-search-layout')]//li").first.wait_for(timeout=40000)
            pagina += 1

        # Se guarda toda la información recopilada en un archivo JSON.
        with open("data/ml_resultados.json", "w", encoding="utf-8") as f:
            json.dump(todos_los_datos, f, ensure_ascii=False, indent=2)

        # Cierre limpio del navegador.
        await browser.close()

if __name__ == "__main__":
    # Entrada por consola para definir el término de búsqueda.
    query = input("Item: ")

    # Punto de entrada de la corrutina principal.
    asyncio.run(play(query))
