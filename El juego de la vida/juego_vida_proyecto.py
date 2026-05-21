import pygame
import multiprocessing as mp
import os

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
ANCHO = 800
ALTO = 800
COLOR_FONDO = (30, 30, 30)
COLOR_CELDA_VIVA = (0, 255, 120)
COLOR_RED = (50, 50, 50)

# Para la programación paralela, los tableros grandes muestran el verdadero poder
FILAS_VIRTUALES = 200
COLUMNAS_VIRTUALES = 200

# --- 2. FUNCIONES PURAS (Para los procesos trabajadores) ---
# Estas funciones deben estar a nivel global para que Python pueda enviarlas a otros núcleos

def contar_vecinos(tablero, x, y, filas_tot, cols_tot):
    """Lógica aislada para contar vecinos respetando los bordes infinitos."""
    vecinos_vivos = 0
    for i in [-1, 0, 1]:
        for j in [-1, 0, 1]:
            if i == 0 and j == 0:
                continue
            
            fila_vecino = (y + i) % filas_tot
            columna_vecino = (x + j) % cols_tot
            vecinos_vivos += tablero[fila_vecino][columna_vecino]
    return vecinos_vivos

def calcular_segmento(args):
    """
    Esta es la función que ejecuta CADA NÚCLEO de forma independiente.
    Recibe un paquete de argumentos (args) con su porción de trabajo.
    """
    tablero, fila_inicio, fila_fin, filas_tot, cols_tot = args
    segmento_nuevo = []
    
    # El trabajador solo procesa las filas que le fueron asignadas
    for fila in range(fila_inicio, fila_fin):
        nueva_fila = []
        for col in range(cols_tot):
            vecinos = contar_vecinos(tablero, col, fila, filas_tot, cols_tot)
            estado_actual = tablero[fila][col]
            
            # Reglas de Conway
            if estado_actual == 1 and (vecinos < 2 or vecinos > 3):
                nueva_fila.append(0)
            elif estado_actual == 0 and vecinos == 3:
                nueva_fila.append(1)
            else:
                nueva_fila.append(estado_actual)
                
        segmento_nuevo.append(nueva_fila)
        
    # Devuelve dónde empieza, dónde termina y el resultado procesado
    return fila_inicio, fila_fin, segmento_nuevo

def crear_tablero_vacio():
    return [[0 for _ in range(COLUMNAS_VIRTUALES)] for _ in range(FILAS_VIRTUALES)]

# --- 3. BUCLE PRINCIPAL Y PROCESO MAESTRO ---
if __name__ == '__main__':
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Conway - Motor Paralelo")
    reloj = pygame.time.Clock()

    # Configuración de Procesos Paralelos
    # Usamos la cantidad de núcleos disponibles en tu PC (dejando 1 libre por estabilidad)
    num_procesos = max(1, os.cpu_count() - 1) 
    pool_trabajadores = mp.Pool(processes=num_procesos)

    tablero = crear_tablero_vacio()
    jugando = False
    corriendo = True

    tamano_celda = 10
    camara_x = (COLUMNAS_VIRTUALES // 2 * tamano_celda) - (ANCHO // 2)
    camara_y = (FILAS_VIRTUALES // 2 * tamano_celda) - (ALTO // 2)

    while corriendo:
        reloj.tick(15) 
        
        # --- GESTIÓN DE EVENTOS ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            
            if evento.type == pygame.MOUSEWHEEL:
                if evento.y > 0:
                    tamano_celda = min(tamano_celda + 2, 60)
                elif evento.y < 0:
                    tamano_celda = max(tamano_celda - 2, 4)
                    
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_SPACE:
                    jugando = not jugando
                if evento.key == pygame.K_c:
                    tablero = crear_tablero_vacio()
                    jugando = False

        # --- MOVER CÁMARA ---
        teclas = pygame.key.get_pressed()
        velocidad_camara = 20
        if teclas[pygame.K_LEFT] or teclas[pygame.K_a]: camara_x -= velocidad_camara
        if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]: camara_x += velocidad_camara
        if teclas[pygame.K_UP] or teclas[pygame.K_w]: camara_y -= velocidad_camara
        if teclas[pygame.K_DOWN] or teclas[pygame.K_s]: camara_y += velocidad_camara

        # --- PINTAR CON EL RATÓN ---
        botones = pygame.mouse.get_pressed()
        if not jugando and (botones[0] or botones[2]):
            pos_x, pos_y = pygame.mouse.get_pos()
            columna = (pos_x + camara_x) // tamano_celda
            fila = (pos_y + camara_y) // tamano_celda
            
            if 0 <= fila < FILAS_VIRTUALES and 0 <= columna < COLUMNAS_VIRTUALES:
                if botones[0]: tablero[fila][columna] = 1
                elif botones[2]: tablero[fila][columna] = 0

        # --- LÓGICA DE CONWAY (PARALELIZADA) ---
        if jugando:
            # 1. Calcular cuántas filas le tocan a cada proceso
            filas_por_proceso = FILAS_VIRTUALES // num_procesos
            tareas = []
            
            # 2. Empaquetar el trabajo (Crear los 'args' para cada trabajador)
            for i in range(num_procesos):
                fila_inicio = i * filas_por_proceso
                # El último proceso se lleva cualquier fila sobrante si la división no es exacta
                fila_fin = FILAS_VIRTUALES if i == num_procesos - 1 else (i + 1) * filas_por_proceso
                tareas.append((tablero, fila_inicio, fila_fin, FILAS_VIRTUALES, COLUMNAS_VIRTUALES))
            
            # 3. EJECUCIÓN PARALELA: El Pool reparte las tareas y espera los resultados
            resultados = pool_trabajadores.map(calcular_segmento, tareas)
            
            # 4. Sincronización: Juntar las piezas devueltas en el tablero original
            nuevo_tablero = crear_tablero_vacio()
            for inicio, fin, segmento in resultados:
                nuevo_tablero[inicio:fin] = segmento
                
            tablero = nuevo_tablero

        # --- DIBUJAR PANTALLA ---
        pantalla.fill(COLOR_FONDO)
        
        inicio_col = max(0, camara_x // tamano_celda)
        fin_col = min(COLUMNAS_VIRTUALES, (camara_x + ANCHO) // tamano_celda + 1)
        inicio_fila = max(0, camara_y // tamano_celda)
        fin_fila = min(FILAS_VIRTUALES, (camara_y + ALTO) // tamano_celda + 1)

        for fila in range(inicio_fila, fin_fila):
            for col in range(inicio_col, fin_col):
                x_pantalla = (col * tamano_celda) - camara_x
                y_pantalla = (fila * tamano_celda) - camara_y
                
                if tablero[fila][col] == 1:
                    pygame.draw.rect(pantalla, COLOR_CELDA_VIVA, (x_pantalla, y_pantalla, tamano_celda, tamano_celda))
                
                # Desactivamos el dibujo de la cuadrícula si está muy lejos para mejorar el rendimiento
                if tamano_celda > 5:
                    pygame.draw.rect(pantalla, COLOR_RED, (x_pantalla, y_pantalla, tamano_celda, tamano_celda), 1)
                
        pygame.display.flip()

    # Cerrar los procesos paralelos limpiamente al salir
    pool_trabajadores.close()
    pool_trabajadores.join()
    pygame.quit()