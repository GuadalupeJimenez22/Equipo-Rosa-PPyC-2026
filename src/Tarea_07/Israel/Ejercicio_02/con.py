import threading
import time

boletos_disponibles = 1000
lock = threading.Lock()

def vender_boletos(cantidad):
    global boletos_disponibles
    time.sleep(0.0001)
    with lock:
        boletos_disponibles -= cantidad

hilos = []
for _ in range(100):
    t = threading.Thread(target=vender_boletos, args=(1,))
    hilos.append(t)
    t.start()

for t in hilos:
    t.join()

print("Boletos restantes (con lock):", boletos_disponibles)
