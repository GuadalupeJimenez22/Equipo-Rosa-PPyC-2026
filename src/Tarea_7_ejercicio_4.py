import urllib.request
from collections import Counter
import re
import threading

libros = [
    ("https://www.gutenberg.org/cache/epub/1342/pg1342.txt", "Orgullo y Prejuicio"),
    ("https://www.gutenberg.org/cache/epub/84/pg84.txt", "Frankenstein"),
    ("https://www.gutenberg.org/cache/epub/11/pg11.txt", "Alicia en el país de las maravillas")
]

contadores_parciales = []
lock = threading.Lock()

def contar_palabras(url):
    try:
        respuesta = urllib.request.urlopen(url, timeout=10)
        texto = respuesta.read().decode('utf-8').lower()
        lista_palabras = re.findall(r'\b\w+\b', texto)
        return Counter(lista_palabras)
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return Counter()

def procesar_libro(url, nombre):
    contador = contar_palabras(url)
    with lock:
        contadores_parciales.append(contador)
    
    print(f"Completado: '{nombre}' ({len(contador)} palabras únicas)")

if __name__ == "__main__":
    hilos = []
    for url, nombre in libros:
        hilo = threading.Thread(target=procesar_libro, args=(url, nombre))
        hilos.append(hilo)
        hilo.start()

    for hilo in hilos:
        hilo.join()

    contador_final = Counter()
    for contador_parcial in contadores_parciales:
        contador_final.update(contador_parcial)
    
    print("\n Top 20 palabras más frecuentes\n")
    for palabra, frecuencia in contador_final.most_common(20):
        print(f"{palabra:20} -> {frecuencia:6} veces")
    
    print(f"\nTotal de palabras únicas: {len(contador_final)}")
    print(f"Total de palabras procesadas: {sum(contador_final.values())}")
