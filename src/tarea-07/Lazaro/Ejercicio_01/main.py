import time
import requests
import threading

ciudades = [
    {"nombre": "CDMX", "lat": 19.43, "lon": -99.13},
    {"nombre": "Nueva York", "lat": 40.71, "lon": -74.00},
    {"nombre": "Londres", "lat": 51.50, "lon": -0.12},
    {"nombre": "Tokio", "lat": 35.68, "lon": 139.69}
]

def obtener_clima(ciudad):
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": ciudad["lat"],
        "longitude": ciudad["lon"],
        "current_weather": True
    }

    try:
        respuesta = requests.get(base_url, params=params, timeout=10)
        if respuesta.status_code == 200:
            clima = respuesta.json()["current_weather"]
            print(f"{ciudad['nombre']}: {clima}")
            return clima
        else:
            print(f"Error al consultar {ciudad['nombre']}")
            return None
    except Exception as e:
        print(f"Error en {ciudad['nombre']}: {e}")
        return None

def version_secuencial():
    print("\n=== VERSIÓN SECUENCIAL ===")
    inicio = time.time()

    for ciudad in ciudades:
        obtener_clima(ciudad)

    fin = time.time()
    tiempo = fin - inicio
    print(f"Tiempo secuencial: {tiempo:.4f} segundos")
    return tiempo

def version_con_hilos():
    print("\n=== VERSIÓN CON HILOS ===")
    inicio = time.time()

    hilos = []

    for ciudad in ciudades:
        hilo = threading.Thread(target=obtener_clima, args=(ciudad,))
        hilos.append(hilo)
        hilo.start()

    for hilo in hilos:
        hilo.join()

    fin = time.time()
    tiempo = fin - inicio
    print(f"Tiempo con hilos: {tiempo:.4f} segundos")
    return tiempo

if __name__ == "__main__":
    tiempo_secuencial = version_secuencial()
    tiempo_hilos = version_con_hilos()

    print("\n=== COMPARACIÓN FINAL ===")
    print(f"Tiempo secuencial: {tiempo_secuencial:.4f} segundos")
    print(f"Tiempo con hilos: {tiempo_hilos:.4f} segundos")

    if tiempo_hilos < tiempo_secuencial:
        print("La versión con hilos fue más rápida.")
    elif tiempo_hilos > tiempo_secuencial:
        print("La versión secuencial fue más rápida.")
    else:
        print("Ambas tardaron lo mismo.")