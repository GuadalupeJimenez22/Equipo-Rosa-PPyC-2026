import socket
import threading

paginas = ["scanme.nmap.org", "testphp.vulnweb.com", "example.com", "google.com"]
puertos = [80, 443, 21, 22, 25, 53, 110, 143, 8080]

lock = threading.Lock()

def verificar_puerto(host, puerto):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, puerto)) == 0:
                with lock:
                    print(f"{host} -> puerto {puerto} ABIERTO")
    except Exception:
        pass

hilos = []

for pagina in paginas:
    for puerto in puertos:
        hilo = threading.Thread(target=verificar_puerto, args=(pagina, puerto))
        hilos.append(hilo)
        hilo.start()

for hilo in hilos:
    hilo.join()

print("Verificación finalizada.")