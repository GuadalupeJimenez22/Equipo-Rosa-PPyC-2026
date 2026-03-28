#Descarga Concurrente de M ́ultiples Archivos

import requests
import time
import threading
 
urls = [
    "https://http2.mlstatic.com/D_Q_NP_609764-MLM108480930454_032026-F-harley-davidson-sportster-48-forty-eight-2014-1200cc-590.webp",
    "https://http2.mlstatic.com/D_Q_NP_680394-MLM105420804172_012026-F-bmw-1250-adventure-gs-rallye-version-limitada-2024.webp",
    "https://http2.mlstatic.com/D_Q_NP_859253-MLM108962047415_032026-F-dodge-attitude-15t-gdi-sxt-at-7dct.webp",
    "https://http2.mlstatic.com/D_NQ_NP_808968-MLM107393140477_022026-F.webp",
    "https://http2.mlstatic.com/D_Q_NP_984897-MLM107320666970_032026-F-a1-sportback-35tfsi-150hp-ego-bpm.webp"
]

nombre_salida = "../data/imagen.png"
def descargar_archivo(url,nombre_salida):
    responese = requests.get(url,stream =True,timeout=20)
    if responese.status_code == 200:
        with open(nombre_salida,"wb") as archivo:
            for chunk in responese.iter_content(chunk_size=1024):
                if chunk:
                    archivo.write(chunk)

if __name__ == "__main__":  

    start = time.time()
    
    #Verisión secuencial
    for i,url in enumerate(urls,start=1):
        ruta_salida = f"../data/imagen_{i}.webp"
        descargar_archivo(url,ruta_salida)
    
    
    print(f"tiempo total descarga secuencial: {time.time()-start}")

    #Versión threading
    
    threads = []
    start1 = time.time()
    for i,url in enumerate(urls,start=1):
        ruta_salida = f"../data/imagen_{i}.webp"
        threads.append(
            threading.Thread(target=descargar_archivo,args=(url,ruta_salida))
        )
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    print(f"tiempo total descarga threading: {time.time()-start1}")