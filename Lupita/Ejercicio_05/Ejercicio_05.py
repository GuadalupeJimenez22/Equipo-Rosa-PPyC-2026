import requests
import queue
import threading
import time


cola = queue.Queue(maxsize=20)
MAX_CHISTES = 50
SEGUNDOS_MAXIMOS = 5

def productor(cola, stop_event):
    endpoint = "https://api.chucknorris.io/jokes/random"
    
    while not stop_event.is_set():
        try:
            r = requests.get(endpoint, timeout=2)
            chiste = r.json()['value']
            cola.put(chiste, timeout=0.5)  # mete a la cola
        except:
            pass

def consumidor(cola, stop_event, contador, contador_lock):
    with open("chistes.txt", "a", encoding="utf-8") as f:
        while not stop_event.is_set() or not cola.empty():
            try:
                chiste = cola.get(timeout=1)
                with contador_lock:
                    if contador["valor"] >= MAX_CHISTES:
                        stop_event.set()
                        cola.task_done()
                        continue

                    f.write(chiste + "\n")
                    contador["valor"] += 1

                    if contador["valor"] >= MAX_CHISTES:
                        stop_event.set()

                cola.task_done()
            except:
                pass

stop_event = threading.Event()
contador = {"valor": 0}
contador_lock = threading.Lock()

def temporizador(stop_event):
    time.sleep(SEGUNDOS_MAXIMOS)
    stop_event.set()

# Crear hilos
productores = [threading.Thread(target=productor, args=(cola, stop_event)) for _ in range(2)]
consumidores = [
    threading.Thread(target=consumidor, args=(cola, stop_event, contador, contador_lock))
    for _ in range(3)
]

timer = threading.Thread(target=temporizador, args=(stop_event,))

inicio = time.time()

for p in productores:
    p.start()

for c in consumidores:
    c.start()

timer.start()

for p in productores:
    p.join()

for c in consumidores:
    c.join()

timer.join()

duracion = time.time() - inicio
print(f"Chistes guardados: {contador['valor']} | Tiempo total: {duracion:.2f}s")