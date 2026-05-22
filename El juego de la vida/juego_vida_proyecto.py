import pygame
import multiprocessing as mp
import os
from typing import Set, List, Tuple

from patterns import (
    Cell, CATALOG, get_pattern, list_catalog as pattern_list_catalog,
    cells_to_matrix, save_pattern_to_yaml, matrix_to_cells,
    get_patterns_by_type,
)
from automata import PRESETS, PRESET_NAMES, get_rule

ANCHO = 800
ALTO = 800
COLOR_FONDO = (30, 30, 30)
COLOR_CELDA_VIVA = (0, 255, 120)
COLOR_RED = (50, 50, 50)

FILAS_VIRTUALES = 200
COLUMNAS_VIRTUALES = 200

_PATTERN_KEY_MAP = {
    1: "blinker",
    2: "glider",
    3: "lwss",
    4: "pulsar",
    5: "gosper_glider_gun",
    6: "toad",
    7: "beacon",
    8: "r_pentomino",
    9: "diehard",
}


def cells_set_to_grid(cells: Set[Cell], filas: int, cols: int,
                       offset_col: int = 0, offset_row: int = 0) -> List[List[int]]:
    tablero = [[0 for _ in range(cols)] for _ in range(filas)]
    for c, r in cells:
        fc = c + offset_col
        fr = r + offset_row
        if 0 <= fr < filas and 0 <= fc < cols:
            tablero[fr][fc] = 1
    return tablero


def grid_to_cells_set(tablero: List[List[int]],
                       offset_col: int = 0, offset_row: int = 0) -> Set[Cell]:
    cells: Set[Cell] = set()
    for r, row in enumerate(tablero):
        for c, val in enumerate(row):
            if val:
                cells.add((c + offset_col, r + offset_row))
    return cells


def load_pattern_to_grid(name: str, filas: int, cols: int) -> List[List[int]]:
    pattern = get_pattern(name)
    if pattern is None:
        raise ValueError(f"Patrón '{name}' no encontrado.")
    offset_c = (cols - pattern.width) // 2
    offset_r = (filas - pattern.height) // 2
    return cells_set_to_grid(pattern.cells, filas, cols, offset_c, offset_r)


def contar_vecinos(tablero, x, y, filas_tot, cols_tot):
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
    tablero, fila_inicio, fila_fin, filas_tot, cols_tot, born, survive = args
    segmento_nuevo = []
    for fila in range(fila_inicio, fila_fin):
        nueva_fila = []
        for col in range(cols_tot):
            vecinos = contar_vecinos(tablero, col, fila, filas_tot, cols_tot)
            estado_actual = tablero[fila][col]
            if estado_actual == 1 and vecinos not in survive:
                nueva_fila.append(0)
            elif estado_actual == 0 and vecinos in born:
                nueva_fila.append(1)
            else:
                nueva_fila.append(estado_actual)
        segmento_nuevo.append(nueva_fila)
    return fila_inicio, fila_fin, segmento_nuevo


def crear_tablero_vacio():
    return [[0 for _ in range(COLUMNAS_VIRTUALES)] for _ in range(FILAS_VIRTUALES)]


if __name__ == '__main__':
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Conway - Motor Paralelo [B3/S23]")
    reloj = pygame.time.Clock()

    num_procesos = max(1, os.cpu_count() - 1)
    pool_trabajadores = mp.Pool(processes=num_procesos)

    tablero = crear_tablero_vacio()
    jugando = False
    corriendo = True

    tamano_celda = 10
    camara_x = (COLUMNAS_VIRTUALES // 2 * tamano_celda) - (ANCHO // 2)
    camara_y = (FILAS_VIRTUALES // 2 * tamano_celda) - (ALTO // 2)

    rule = get_rule("B3/S23")
    rule_index = 0

    print("Controles:")
    print("  ESPACIO  = Pausar/Reanudar")
    print("  C        = Limpiar grilla")
    print("  1-9      = Cargar patrón precargado")
    print("  P        = Imprimir catálogo de patrones y reglas")
    print("  S        = Guardar patrón actual como YAML")
    print("  R        = Cambiar regla de autómata")
    print("  W/A/S/D  = Mover cámara")
    print("  Rueda    = Zoom")
    print("  CLICK    = Pintar/borrar células (en pausa)\n")

    while corriendo:
        reloj.tick(15)
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
                if evento.key == pygame.K_r:
                    rule_index = (rule_index + 1) % len(PRESET_NAMES)
                    rule = PRESETS[PRESET_NAMES[rule_index]]
                    caption = f"Conway - Motor Paralelo [{rule.rule_string}]"
                    pygame.display.set_caption(caption)
                    print(f"[RULE] Cambiado a: {rule}")
                if evento.key == pygame.K_s:
                    cells = grid_to_cells_set(tablero)
                    this_file_path = os.path.abspath(__file__)
                    project_path = '/'.join(this_file_path.split('/')[:-1])
                    filepath = project_path + '/saved_patterns_paralelo.yml'
                    try:
                        save_pattern_to_yaml(cells, "user_pattern_paralelo", filepath)
                        print(f"[SAVE] Patrón guardado en {filepath}")
                    except Exception as e:
                        print(f"[SAVE] Error: {e}")
                if evento.key == pygame.K_p:
                    print("\n" + "=" * 50)
                    print("CATÁLOGO DE PATRONES DISPONIBLES")
                    print("=" * 50)
                    for ptype in ["still_life", "oscillator", "spaceship", "gun", "methuselah"]:
                        patterns = [p for p in CATALOG.values() if p.type == ptype]
                        if not patterns:
                            continue
                        print(f"\n--- {ptype.upper()} ---")
                        for p in patterns:
                            print(f"  {p.name:<20s}  {p.width}x{p.height}  {p.description}")
                    print(f"\n--- REGLAS DE AUTÓMATA ---")
                    for name, r in PRESETS.items():
                        print(f"  {name:<15s}  {r.rule_string}  {r.name}")
                    print("=" * 50 + "\n")
                if pygame.K_0 <= evento.key <= pygame.K_9:
                    pattern_id = evento.key - pygame.K_0
                    if pattern_id == 0:
                        tablero = crear_tablero_vacio()
                    else:
                        name = _PATTERN_KEY_MAP.get(pattern_id)
                        if name:
                            try:
                                tablero = load_pattern_to_grid(name, FILAS_VIRTUALES, COLUMNAS_VIRTUALES)
                                print(f"[LOAD] Patrón cargado: {name}")
                            except ValueError as e:
                                print(f"[LOAD] {e}")
                    jugando = False

        teclas = pygame.key.get_pressed()
        velocidad_camara = 20
        if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
            camara_x -= velocidad_camara
        if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
            camara_x += velocidad_camara
        if teclas[pygame.K_UP] or teclas[pygame.K_w]:
            camara_y -= velocidad_camara
        if teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
            camara_y += velocidad_camara

        botones = pygame.mouse.get_pressed()
        if not jugando and (botones[0] or botones[2]):
            pos_x, pos_y = pygame.mouse.get_pos()
            columna = (pos_x + camara_x) // tamano_celda
            fila = (pos_y + camara_y) // tamano_celda
            if 0 <= fila < FILAS_VIRTUALES and 0 <= columna < COLUMNAS_VIRTUALES:
                if botones[0]:
                    tablero[fila][columna] = 1
                elif botones[2]:
                    tablero[fila][columna] = 0

        if jugando:
            filas_por_proceso = FILAS_VIRTUALES // num_procesos
            tareas = []
            for i in range(num_procesos):
                fila_inicio = i * filas_por_proceso
                fila_fin = FILAS_VIRTUALES if i == num_procesos - 1 else (i + 1) * filas_por_proceso
                tareas.append((
                    tablero, fila_inicio, fila_fin,
                    FILAS_VIRTUALES, COLUMNAS_VIRTUALES,
                    rule.born, rule.survive,
                ))
            resultados = pool_trabajadores.map(calcular_segmento, tareas)
            nuevo_tablero = crear_tablero_vacio()
            for inicio, fin, segmento in resultados:
                nuevo_tablero[inicio:fin] = segmento
            tablero = nuevo_tablero

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
                    pygame.draw.rect(pantalla, COLOR_CELDA_VIVA,
                                     (x_pantalla, y_pantalla, tamano_celda, tamano_celda))
                if tamano_celda > 5:
                    pygame.draw.rect(pantalla, COLOR_RED,
                                     (x_pantalla, y_pantalla, tamano_celda, tamano_celda), 1)
        pygame.display.flip()

    pool_trabajadores.close()
    pool_trabajadores.join()
    pygame.quit()
