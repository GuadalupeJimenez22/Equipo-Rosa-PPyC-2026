import time, random, requests, threading
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from datetime import datetime

user = "postgres"
password = "supersecret"
host = "localhost"
port = "5432"
database = "postgres"

semaforo = threading.Semaphore(8)

def get_connection(user, password, host, port, database):
    return create_engine(url="postgresql+psycopg2://{0}:{1}@{2}:{3}/{4}".format(user, password, host, port, database))

def obtener_precio_y_guardar(symbol):
    with semaforo:
        url = f"https://finance.yahoo.com/quote/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            time.sleep(2 * random.random())
            r = requests.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            tag = soup.find("span", {"data-testid": "qsp-price"})
            if tag:
                precio = float(tag.text.replace(',', ''))
                with get_connection(user, password, host, port, database).connect() as connector:
                    connector.execute(text("INSERT INTO inversiones (SYMBOL, PRICE, REGISTER_DATE) VALUES (:s, :p, :d)"), 
                                     {"s": symbol, "p": precio, "d": datetime.now()})
                    connector.commit()
        except:
            pass

if __name__ == "__main__":
    with open("C:/Users/mtorr/OneDrive/Escritorio/8vo Semestre/PPyC/Tareas/lista_sp500.txt", "r") as f:
        lista = eval(f.read())

    threads = [threading.Thread(target=obtener_precio_y_guardar, args=(s,)) for s in lista]
    for t in threads: 
        t.start()
    for t in threads: 
        t.join()

    print("Proceso terminado c: ")