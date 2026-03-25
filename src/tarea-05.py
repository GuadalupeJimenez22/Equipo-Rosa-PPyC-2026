import socket
import time
import threading
import queue
import multiprocessing

pages= ["scanme.nmap.org", "testphp.vulnweb.com","example.com","google.com"]

def nmap(page: str, cola_puertos: queue.Queue, puertos_abiertos: list[int], lock: threading.Lock) -> None:
    while True:
        try:
            port = cola_puertos.get_nowait()
        except queue.Empty:
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((page, port)) == 0:
                    with lock:
                        puertos_abiertos.append(port)
        finally:
            cola_puertos.task_done()
        


def proceso(page:str)->None:
    cola_puertos = queue.Queue()
    for port in range(1, 1000):
        cola_puertos.put(port)

    puertos_abiertos: list[int] = []
    lock = threading.Lock()

    threads = [] 
    num_threads = min(100, cola_puertos.qsize())
    for _ in range(num_threads):
        t = threading.Thread(target=nmap, args=(page, cola_puertos, puertos_abiertos, lock))
        threads.append(t)
        t.start()

    cola_puertos.join()
    for thread in threads:
        thread.join()

    puertos_abiertos.sort()
    print(f"puertos abiertos: {puertos_abiertos} en {page}")


if __name__ == "__main__":   
    start = time.time()
    procesos = []
    for page in pages:
        procesos.append(
            multiprocessing.Process(target=proceso,args=(page,))
        )
    for procces in procesos:
        procces.start()

    for procces in procesos:
        procces.join()

    end = time.time()

    print(f"Tiempo total {end-start}")