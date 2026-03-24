import socket
import threading

paginas = ["scanme.nmap.org", "testphp.vulnweb.com", "example.com", "google.com"]
puertos = [21, 22, 25, 53, 80, 443]

def verificar_puerto(host, puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        if s.connect_ex((host, puerto)) == 0:
            print(f"{host} -> puerto {puerto} abierto")
hilos = []

for host in paginas:
    for puerto in puertos:
        hilo = threading.Thread(
            target=verificar_puerto,
            args=(host, puerto)
        )
        hilo.start()
        hilos.append(hilo)

for hilo in hilos:
    hilo.join()