import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright


async def extraer_pagina(page):
    # Localiza todas las tarjetas del listado de resultados.
    items = page.locator("//ol[contains(@class,'ui-search-layout')]//li")

    # Espera a que exista al menos una tarjeta visible antes de extraer datos.
    await items.first.wait_for(timeout=15000)

    total = await items.count()
    datos = []

    # Recorre cada tarjeta para extraer sus campos principales.
    for i in range(total):
        item = items.nth(i)

        # Selectores por campo dentro de la tarjeta de producto.
        titulo_loc = item.locator("h3 a").first
        precio_entero_loc = item.locator("span.andes-money-amount__fraction").first
        precio_centavos_loc = item.locator("span.andes-money-amount__cents").first
        cuotas_loc = item.locator(".poly-price__installments").first

        # Lectura segura: primero valida si el elemento existe.
        href = await titulo_loc.get_attribute("href") if await titulo_loc.count() else None
        titulo = (await titulo_loc.inner_text()).strip() if await titulo_loc.count() else "Sin titulo"

        # El precio suele venir separado en entero y centavos.
        entero = (await precio_entero_loc.inner_text()).strip() if await precio_entero_loc.count() else ""
        centavos = (await precio_centavos_loc.inner_text()).strip() if await precio_centavos_loc.count() else "00"
        precio = f"{entero}.{centavos}" if entero else "Sin precio"
        cuotas = (await cuotas_loc.inner_text()).strip() if await cuotas_loc.count() else None

        # Se agrega cada producto a una lista de diccionarios.
        datos.append(
            {
                "titulo": titulo,
                "href": href,
                "precio": precio,
                "cuotas": cuotas,
            }
        )

    return datos


async def play(name):
    # Abre una sesión de Playwright por consulta.
    async with async_playwright() as p:
        # Navegador visible para ver el flujo en tiempo real.
        browser = await p.firefox.launch(headless=False)
        page = await browser.new_page()

        # Flujo de búsqueda inicial en Mercado Libre.
        await page.goto("https://www.mercadolibre.com.mx/")
        await page.get_by_role("combobox", name="Ingresa lo que quieras").fill(name)
        await page.get_by_role("button", name="Buscar").click()

        # Espera robusta: se continúa cuando aparece el listado de resultados.
        await page.locator("//ol[contains(@class,'ui-search-layout')]//li").first.wait_for(timeout=15000)

        pagina = 1
        todos_los_datos = []

        # Pagina todas las secciones de resultados hasta agotar el botón "Siguiente".
        while True:
            print(f"\n=== {name} | Pagina {pagina} ===")

            # Extrae y acumula productos de la página actual.
            datos = await extraer_pagina(page)
            todos_los_datos.extend(datos)

            # Selector del botón "Siguiente" solo cuando está habilitado.
            next_btn = page.locator(
                "li.andes-pagination__button--next:not(.andes-pagination__button--disabled) a"
            )

            # Si no hay botón activo, se termina la paginación.
            if await next_btn.count() == 0:
                break

            # Avanza a la siguiente página y espera resultados antes de continuar.
            await next_btn.first.click()
            await page.locator("//ol[contains(@class,'ui-search-layout')]//li").first.wait_for(timeout=15000)
            pagina += 1

        # Guarda el resultado por consulta para evitar que los archivos se pisen.
        output_dir = Path("data")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"ml_resultados_{name}.json"
        output_file.write_text(
            json.dumps(todos_los_datos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"JSON guardado: {output_file}")

        # Cierra el navegador de esta tarea.
        await browser.close()


async def main():
    # Lista de consultas que se ejecutarán en paralelo.
    items = (
        "LENOVO-IDEAPAD-1-15AD7-15AMN7",
        "LENOVO-IDEAPAD-5-15IIL05-ALC05",
        "HP-PAVILLION-15CW-15CS",
        "HP-PAVILLION-15CX",
        "DELL-INSPIRON-3510-3511-3515-3520-3521",
        "DELL-LATITUDE-E3520-3520",
    )

    # Mide el tiempo total para comparar rendimiento.
    start = time.time()

    # Crea una corrutina por consulta y las ejecuta concurrentemente.
    tareas = [play(item) for item in items]
    resultados = await asyncio.gather(*tareas, return_exceptions=True)

    # Reporta errores por tarea sin detener todo el proceso.
    for item, resultado in zip(items, resultados):
        if isinstance(resultado, Exception):
            print(f"Error en {item}: {resultado}")

    end = time.time()
    print(f"Tiempo total {end - start:.2f} s")


if __name__ == "__main__":
    # Punto de entrada del script asíncrono.
    asyncio.run(main())
