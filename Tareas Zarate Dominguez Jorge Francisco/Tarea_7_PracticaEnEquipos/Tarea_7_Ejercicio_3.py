import requests
from PIL import Image
import numpy as np
import io
import threading
import time

url_img = "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0?w=1080"
response = requests.get(url_img)
img = Image.open(io.BytesIO(response.content))
matriz = np.array(img)

def procesar_segmento(matriz, inicio, fin):
    for i in range(inicio, fin):
        for j in range(matriz.shape[1]):
            r, g, b = matriz[i, j]
            gris = int(0.299*r + 0.587*g + 0.114*b)
            matriz[i, j] = [gris, gris, gris]

def escala_grises_paralela(matriz, num_hilos):
    alto = matriz.shape[0]
    hilos = []

    segmento = alto // num_hilos

    for i in range(num_hilos):
        inicio = i * segmento

        if i == num_hilos - 1:
            fin = alto
        else:
            fin = (i + 1) * segmento

        hilo = threading.Thread(target=procesar_segmento, args=(matriz, inicio, fin))
        hilos.append(hilo)
        hilo.start()

    for hilo in hilos:
        hilo.join()

    return matriz

inicio_tiempo = time.time()

resultado = escala_grises_paralela(matriz, 8)

fin_tiempo = time.time()

print(f"Tiempo de ejecución: {fin_tiempo - inicio_tiempo:.4f} segundos")