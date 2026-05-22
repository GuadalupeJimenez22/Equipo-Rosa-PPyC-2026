import random
import os
import time
from typing import NewType, Any, List, Tuple, Set, Dict

import yaml
import pygame
import numpy as np

from automata import AutomataRule, PRESETS, PRESET_NAMES, get_rule
from patterns import (
    Cell, Pattern, CATALOG, get_pattern, list_catalog as pattern_list_catalog,
    cells_to_matrix, save_pattern_to_yaml,
)


class GameOfLife:
    """
    Implementación del Juego de la Vida de Conway en Pygame.

    Características:
    - Cálculos optimizados y preparados para paralelismo
    - Métodos puros (_count_living_neighbors, _should_cell_survive, _should_cell_reproduce)
    - Patrones configurables (0-9) desde catálogo y seed_patterns.yml
    - Soporte para grillas finitas e infinitas (con wrapping)
    - Pausa, paso manual y edición en tiempo real
    - Guardar patrones (tecla S) y cambiar reglas de autómata (tecla R)
    """

    _PATTERN_KEY_MAP: Dict[int, str] = {
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

    def __init__(self) -> None:
        self._config = self._get_config()
        if self._config['random_seed'] is not None:
            random.seed(self._config['random_seed'])
        self._n_cols = self._config['width'] // self._config['cell_size']
        self._n_rows = self._config['height'] // self._config['cell_size']
        self._n_cells = self._n_rows * self._n_cols
        pygame.init()
        self._screen = pygame.display.set_mode(
            (self._config['width'], self._config['height'])
        )
        self.clock = pygame.time.Clock()
        self._living_cells: Set[Cell] = set()
        self._is_paused = True
        self._run_next_step = False
        self._current_pattern = None
        rule_str = self._config.get('rule_string', 'B3/S23')
        self._rule = get_rule(rule_str)
        self._rule_index = 0
        self._update_caption()

    def _update_caption(self) -> None:
        pat = self._current_pattern or 'None'
        paused = 'paused' if self._is_paused else 'running'
        rule = self._rule.rule_string
        caption = f"Life [{pat}] ({paused}) [{rule}]"
        pygame.display.set_caption(caption)

    @staticmethod
    def _get_config() -> Dict[str, Any]:
        this_file_path = os.path.abspath(__file__)
        project_path = '/'.join(this_file_path.split('/')[:-1])
        config_path = project_path + '/config.yml'
        with open(config_path, 'r') as yml_file:
            config = yaml.safe_load(yml_file)[0]['config']
        return config

    def _generate_random_init_grid(self) -> Set[Cell]:
        self._current_pattern = 'Rand'
        pct_living_cells = random.randrange(
            start=self._config['gen_min_pct_living_cells'],
            stop=self._config['gen_max_pct_living_cells']
        )
        n_cells_to_gen = (self._n_cells * pct_living_cells) // 100
        new_living_cells = {
            (random.randrange(self._n_cols), random.randrange(self._n_rows))
            for _ in range(n_cells_to_gen)
        }
        return new_living_cells

    def _generate_pattern_from_catalog(self, id_: int) -> Set[Cell]:
        name = self._PATTERN_KEY_MAP.get(id_)
        if name is None:
            return self._generate_random_init_grid()
        pattern = get_pattern(name)
        if pattern is None:
            return self._generate_random_init_grid()
        self._current_pattern = name
        return pattern.centered(self._n_cols, self._n_rows)

    def _save_current_pattern(self) -> None:
        if not self._living_cells:
            print("[SAVE] No hay células vivas para guardar.")
            return
        this_file_path = os.path.abspath(__file__)
        project_path = '/'.join(this_file_path.split('/')[:-1])
        filepath = project_path + '/saved_patterns.yml'
        try:
            save_pattern_to_yaml(self._living_cells, "user_pattern", filepath)
            print(f"[SAVE] Patrón guardado en {filepath}")
        except Exception as e:
            print(f"[SAVE] Error al guardar: {e}")

    def _cycle_rule(self) -> None:
        self._rule_index = (self._rule_index + 1) % len(PRESET_NAMES)
        preset_name = PRESET_NAMES[self._rule_index]
        self._rule = PRESETS[preset_name]
        print(f"[RULE] Cambiado a: {self._rule}")

    def process_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                col = x // self._config['cell_size']
                row = y // self._config['cell_size']
                cell = (col, row)
                if cell in self._living_cells:
                    self._living_cells.remove(cell)
                else:
                    self._living_cells.add(cell)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self._is_paused = not self._is_paused
                elif event.key == pygame.K_RIGHT and self._is_paused:
                    self._run_next_step = True
                elif event.key == pygame.K_c:
                    self._living_cells.clear()
                    self._is_paused = True
                    self._current_pattern = None
                elif event.key == pygame.K_g:
                    self._living_cells = self._generate_random_init_grid()
                    self._is_paused = True
                elif event.key == pygame.K_s:
                    self._save_current_pattern()
                elif event.key == pygame.K_r:
                    self._cycle_rule()
                elif event.key == pygame.K_p:
                    self._print_catalog()
                elif pygame.K_0 <= event.key <= pygame.K_9:
                    pattern_id = event.key - pygame.K_0
                    if pattern_id == 0:
                        self._living_cells = self._generate_random_init_grid()
                        self._current_pattern = 'Rand'
                    else:
                        self._living_cells = self._generate_pattern_from_catalog(id_=pattern_id)
                    self._is_paused = True
            self._update_caption()
        return True

    def _print_catalog(self) -> None:
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
        for name, rule in PRESETS.items():
            print(f"  {name:<15s}  {rule.rule_string}  {rule.name}")
        print("=" * 50 + "\n")

    def _count_living_neighbors(self, cell: Cell) -> int:
        neighbors = self._get_neighbors(cell)
        return sum(1 for neighbor in neighbors if neighbor in self._living_cells)

    def _should_cell_survive(self, living_neighbors: int) -> bool:
        return self._rule.should_survive(living_neighbors)

    def _should_cell_reproduce(self, living_neighbors: int) -> bool:
        return self._rule.should_reproduce(living_neighbors)

    def run_logic(self) -> None:
        if self._is_paused and not self._run_next_step:
            return
        if self._config['sleep'] is not None:
            time.sleep(self._config['sleep'])
        new_living_cells: Set[Cell] = set()
        all_neighbors: Set[Cell] = set()
        for cell in self._living_cells:
            living_neighbors = self._count_living_neighbors(cell)
            if self._should_cell_survive(living_neighbors):
                new_living_cells.add(cell)
            all_neighbors.update(self._get_neighbors(cell))
        for cell in all_neighbors:
            if cell not in self._living_cells:
                living_neighbors = self._count_living_neighbors(cell)
                if self._should_cell_reproduce(living_neighbors):
                    new_living_cells.add(cell)
        self._living_cells = new_living_cells
        self._run_next_step = False

    def _get_neighbors(self, cell: Cell) -> List[Cell]:
        col, row = cell
        grid_is_infinite = self._config['grid_is_infinite']
        neighbors = []
        for delta_col in [-1, 0, 1]:
            for delta_row in [-1, 0, 1]:
                if delta_col == 0 and delta_row == 0:
                    continue
                new_col = col + delta_col
                new_row = row + delta_row
                if grid_is_infinite:
                    new_col = new_col % self._n_cols
                    new_row = new_row % self._n_rows
                elif not (0 <= new_col < self._n_cols and 0 <= new_row < self._n_rows):
                    continue
                neighbors.append((new_col, new_row))
        return neighbors

    def draw(self) -> None:
        self._screen.fill(self._config['dead_cell_color'])
        cell_size = self._config['cell_size']
        for col, row in self._living_cells:
            pygame.draw.rect(
                surface=self._screen,
                color=self._config['living_cell_color'],
                rect=(col * cell_size, row * cell_size, cell_size, cell_size)
            )
        for row in range(self._n_rows):
            pygame.draw.line(
                surface=self._screen,
                color=self._config['grid_line_color'],
                start_pos=(0, row * cell_size),
                end_pos=(self._config['width'], row * cell_size)
            )
        for col in range(self._n_cols):
            pygame.draw.line(
                surface=self._screen,
                color=self._config['grid_line_color'],
                start_pos=(col * cell_size, 0),
                end_pos=(col * cell_size, self._config['height'])
            )
        pygame.display.update()


if __name__ == '__main__':
    print("Controles:")
    print("  ESPACIO  = Pausar/Reanudar")
    print("  DERECHA  = Avanzar un paso (en pausa)")
    print("  C        = Limpiar grilla")
    print("  G/0      = Grilla aleatoria")
    print("  1-9      = Cargar patrón precargado")
    print("  P        = Imprimir catálogo de patrones y reglas")
    print("  S        = Guardar patrón actual como YAML")
    print("  R        = Cambiar regla de autómata")
    print("  CLICK    = Pintar/borrar células\n")

    simulation = GameOfLife()
    running = True
    while running:
        running = simulation.process_events()
        simulation.run_logic()
        simulation.draw()
        simulation.clock.tick()
    pygame.quit()
