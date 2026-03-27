import time
import random
import requests
import threading
from bs4 import BeautifulSoup
import queue
from sqlalchemy import create_engine, text

user = "postgres"
password = "postgres"
host = "localhost"
port = "5450"
database = "ppyc_db"

engine = create_engine(
    f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
)

cola_procesos = queue.Queue()
cola_inserts = queue.Queue()
resultados = []
lock_resultados = threading.Lock()


def obtener_precio(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    while True:
        try:
            time.sleep(1 * random.random())
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                valor = soup.find("span", {"data-testid": "qsp-price"})

                if valor:
                    precio_texto = valor.text.strip().replace(",", "")
                    try:
                        precio = float(precio_texto)
                        return precio
                    except ValueError:
                        return None
                else:
                    return None
            else:
                continue
        except Exception:
            continue


def insertar_en_bd(symbol, precio):
    if precio is None:
        return

    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO acciones (nombre, valor) VALUES (:nombre, :valor)"),
            {"nombre": symbol, "valor": precio}
        )
        conn.commit()


# =========================
# Alternativa 1:
# obtener e insertar en el mismo hilo
# =========================
def worker_alternativa_1():
    while not cola_procesos.empty():
        try:
            symbol = cola_procesos.get_nowait()
        except queue.Empty:
            break

        precio = obtener_precio(symbol)

        if precio is not None:
            print(f"[ALT 1] {symbol}: {precio}")
            insertar_en_bd(symbol, precio)

        cola_procesos.task_done()


def worker_obtener():
    while not cola_procesos.empty():
        try:
            symbol = cola_procesos.get_nowait()
        except queue.Empty:
            break

        precio = obtener_precio(symbol)

        if precio is not None:
            print(f"[OBTENIDO] {symbol}: {precio}")
            with lock_resultados:
                resultados.append((symbol, precio))
                cola_inserts.put((symbol, precio))

        cola_procesos.task_done()


if __name__ == "__main__":
    with open("lista_sp500.txt", "r") as f:
        lista_symbolos = eval(f.read())

    lista_symbolos = lista_symbolos[:10]

    print("Obtener e insertar en el mismo flujo paralelo\n")

    for symbol in lista_symbolos:
        cola_procesos.put(symbol)

    threads = []
    for _ in range(5):
        t = threading.Thread(target=worker_alternativa_1)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("Obtener primero todos los precios y luego insertar en paralelo\n")

    # Volver a llenar cola
    for symbol in lista_symbolos:
        cola_procesos.put(symbol)

    threads = []
    for _ in range(5):
        t = threading.Thread(target=worker_obtener)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    insert_threads = []
    for _ in range(5):
        t = threading.Thread(target=worker_insertar)
        insert_threads.append(t)
        t.start()

    for t in insert_threads:
        t.join()

    print("\nProceso finalizado.")