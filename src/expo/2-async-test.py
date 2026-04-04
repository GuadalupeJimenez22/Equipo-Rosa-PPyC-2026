import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def guardar_html_pagina(page, query: str, pagina: int):
    # Se obtiene y se guarda el HTML tal cual viene de la pagina.
    html = await page.content()

    output_dir = Path("data") / "html_guardado"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"pagina_{pagina}.html"
    output_file.write_text(html, encoding="utf-8")

    print(f"HTML guardado: {output_file}")


async def play(name):
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://www.mercadolibre.com.mx/")
        await page.get_by_role("combobox", name="Ingresa lo que quieras").fill(name)
        await page.get_by_role("button", name="Buscar").click()

        # Espera robusta: presencia de resultados visibles en la pagina.
        await page.locator("//ol[contains(@class,'ui-search-layout')]//li").first.wait_for(timeout=15000)

        pagina = 1

        # Se recorren paginas y se guarda su HTML, sin extraer productos.
        while True:
            print(f"\n=== Pagina {pagina} ===")

            await guardar_html_pagina(page, name, pagina)

            next_btn = page.locator(
                "li.andes-pagination__button--next:not(.andes-pagination__button--disabled) a"
            )

            if await next_btn.count() == 0:
                break

            await next_btn.first.click()
            await page.locator("//ol[contains(@class,'ui-search-layout')]//li").first.wait_for(timeout=15000)
            pagina += 1

        await browser.close()

if __name__ == "__main__":
    query = input("Item: ")
    asyncio.run(play(query))
