import time
import random
import requests
import threading
from bs4 import BeautifulSoup
import queue
from sqlalchemy import create_engine,text

user="postgres"
password="postgres"
host="localhost"  # Desde host local hacia contenedor publicado
port="5450"
database="ppyc_db"

cola_procesos = queue.Queue()
acciones = {}

def get_connection(user,password,host,port,database):
    return create_engine(
        url="postgresql+psycopg2://{0}:{1}@{2}:{3}/{4}".format(
            user,password,host,port,database
        )
    )

def obtener_precio_stock():
    while not cola_procesos.empty():
        try:
            symbol = cola_procesos.get_nowait()
        except queue.Empty:
            break
        
        url = f"https://finance.yahoo.com/quote/{symbol}"

        header = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://finance.yahoo.com"
            }
        
        time.sleep(8 * random.random())
        response = requests.get(url, headers=header)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            valor = soup.find("span", {"data-testid": "qsp-price"})
            precio = None

            if valor:
                try:
                    precio = float(valor.text.strip().replace(",", ""))
                except ValueError:
                    precio = None

            acciones[symbol] = precio

            if precio is not None:
                with get_connection(user, password, host, port, database).begin() as connector:
                    try:
                        connector.execute(
                            text("INSERT INTO acciones (nombre, valor) VALUES (:nombre, :valor)"),
                            {"nombre": symbol, "valor": precio},
                        )
                    except Exception as error:
                        print("INSERT done unsuccessfully", error)

        cola_procesos.task_done()
    

if __name__ == "__main__":
    with open("data/lista_sp500.txt","r") as f:
        lista_symbolos = eval(f.read())

    threads = []
    for symbol in lista_symbolos:
        cola_procesos.put(symbol)

    for _ in range(8):
        threads.append(
            threading.Thread(target = obtener_precio_stock)
        )
        
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()
        
    """with get_connection(user, password, host, port, database).begin() as connector:
        try:
            for nombre, valor in acciones.items():
                connector.execute(
                    text("INSERT INTO acciones (nombre, valor) VALUES (:nombre, :valor)"),
                    {"nombre": nombre, "valor": valor},
                )
            peticion = connector.execute(text("SELECT * FROM acciones"))
            print(peticion.fetchall())
            
        except Exception as error:
            print("INSERTS done unsuccessfully", error)"""


