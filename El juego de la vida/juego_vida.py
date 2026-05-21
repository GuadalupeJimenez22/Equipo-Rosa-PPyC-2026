import random
import os
import time
from typing import NewType, Any, List, Tuple, Set, Dict

import yaml
import pygame
import numpy as np


Cell = NewType('Cell', Tuple[int, int])

class GameOfLife:
    """
    Implementación del Juego de la Vida de Conway en Pygame.
    
    Características:
    - Cálculos optimizados y preparados para paralelismo
    - Métodos puros (_count_living_neighbors, _should_cell_survive, _should_cell_reproduce)
    - Patrones configurables (0-9)
    - Soporte para grillas finitas e infinitas (con wrapping)
    - Pausa, paso manual y edición en tiempo real
    """

    def __init__(self) -> None:
        """Inicializa la simulación del Juego de la Vida."""
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
        pygame.display.set_caption(
            self._config['screen_caption'].format(pat='None', paused='paused')
        )
        self.clock = pygame.time.Clock()

        self._living_cells = set()
        self._is_paused = True
        self._run_next_step = False
        self._current_pattern = None 


    @staticmethod
    def _get_config() -> Dict[str, Any]:

        this_file_path = os.path.abspath(__file__)
        project_path = '/'.join(this_file_path.split('/')[:-1])
        config_path = project_path + '/config.yml'

        with open(config_path, 'r') as yml_file:
            config = yaml.safe_load(yml_file)[0]['config']
        return config


    def _generate_random_init_grid(self) -> Set[Cell]:
        """Genera una grilla inicial aleatoria de células vivas."""
        self._current_pattern = 'Rand'
        pct_living_cells = random.randrange(
            start=self._config['gen_min_pct_living_cells'],
            stop=self._config['gen_max_pct_living_cells']
        )
        n_cells_to_gen = (self._n_cells * pct_living_cells) // 100
        new_living_cells = {
            Cell((random.randrange(self._n_cols), random.randrange(self._n_rows)))
            for _ in range(n_cells_to_gen)
        }
        return new_living_cells


    def _generate_seed_pattern(self, id_: int) -> Set[Cell]:

        if not (1 <= id_ <= 9):
            raise ValueError("the given pattern 'id_' must be between 1 and 9")

        this_file_path = os.path.abspath(__file__)
        project_path = '/'.join(this_file_path.split('/')[:-1])
        seed_patterns_path = project_path + '/seed_patterns.yml'

        with open(seed_patterns_path, 'r') as yml_file:
            binary_pattern = yaml.safe_load(yml_file)[0]['patterns'][id_]
        binary_pattern = np.array(binary_pattern)
        top_left_col = (self._n_cols - len(binary_pattern[0])) // 2
        top_left_row = (self._n_rows - len(binary_pattern)) // 2

        seed_pattern_living_cells = zip(*np.where(binary_pattern))
        pattern_living_cells = set()
        for row, col in seed_pattern_living_cells:
            pattern_living_cells.add(
                Cell((col+top_left_col, row+top_left_row))
            )
        return pattern_living_cells


    def process_events(self) -> bool:
        """Procesa eventos de entrada del usuario. Retorna False si debe cerrarse."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  

            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                col = x // self._config['cell_size']
                row = y // self._config['cell_size']
                cell = Cell((col, row))
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
                elif event.key == pygame.K_g:
                    self._living_cells = self._generate_random_init_grid()
                    self._is_paused = True
                elif pygame.K_0 <= event.key <= pygame.K_9:
                    # Manejo unificado de patrones 0-9
                    pattern_id = event.key - pygame.K_0
                    if pattern_id == 0:
                        self._living_cells = self._generate_random_init_grid()
                    else:
                        self._living_cells = self._generate_seed_pattern(id_=pattern_id)
                    self._current_pattern = str(pattern_id)
                    self._is_paused = True
        return True 


    def _count_living_neighbors(self, cell: Cell) -> int:
        """Cuenta el número de vecinos vivos de una célula. Método puro para paralelismo."""
        neighbors = self._get_neighbors(cell)
        return sum(1 for neighbor in neighbors if neighbor in self._living_cells)

    def _should_cell_survive(self, living_neighbors: int) -> bool:
        """Determina si una célula viva debe sobrevivir."""
        return self._config['underpopulation'] <= living_neighbors <= self._config['overpopulation']

    def _should_cell_reproduce(self, living_neighbors: int) -> bool:
        """Determina si una célula muerta debe nacer."""
        return living_neighbors == self._config['reproduction']

    def run_logic(self) -> None:
        """Ejecuta un paso de la simulación."""
        pygame.display.set_caption(
            self._config['screen_caption'].format(
                pat=self._current_pattern,
                paused='paused' if self._is_paused else 'running')
        )

        if self._is_paused and not self._run_next_step:
            return  

        if self._config['sleep'] is not None:  
            time.sleep(self._config['sleep'])

        new_living_cells = set()
        all_neighbors = set()

        # Verificar células vivas y sus vecinos
        for cell in self._living_cells:
            living_neighbors = self._count_living_neighbors(cell)
            if self._should_cell_survive(living_neighbors):
                new_living_cells.add(cell)
            all_neighbors.update(self._get_neighbors(cell))

        # Verificar células muertas vecinas a células vivas (reproducción)
        for cell in all_neighbors:
            if cell not in self._living_cells:  # Solo células muertas
                living_neighbors = self._count_living_neighbors(cell)
                if self._should_cell_reproduce(living_neighbors):
                    new_living_cells.add(cell)

        self._living_cells = new_living_cells
        self._run_next_step = False  


    def _get_neighbors(self, cell: Cell) -> List[Cell]:
        """Retorna los 8 vecinos de una célula, con wrapping si es necesario."""
        col, row = cell
        grid_is_infinite = self._config['grid_is_infinite']
        neighbors = []
        
        for delta_col in [-1, 0, 1]:
            for delta_row in [-1, 0, 1]:
                if delta_col == 0 and delta_row == 0:
                    continue
                
                new_col = col + delta_col
                new_row = row + delta_row
                
                # Aplicar wrapping si la grilla es infinita
                if grid_is_infinite:
                    new_col = new_col % self._n_cols
                    new_row = new_row % self._n_rows
                # Ignorar si está fuera de límites
                elif not (0 <= new_col < self._n_cols and 0 <= new_row < self._n_rows):
                    continue
                
                neighbors.append((new_col, new_row))
        
        return neighbors


    def draw(self) -> None:
        """Dibuja el estado actual de la simulación."""
        self._screen.fill(self._config['dead_cell_color'])  
        cell_size = self._config['cell_size']

        # Dibujar células vivas
        for col, row in self._living_cells:
            pygame.draw.rect(
                surface=self._screen,
                color=self._config['living_cell_color'],
                rect=(col * cell_size, row * cell_size, cell_size, cell_size)
            )

        # Dibujar grid (líneas horizontales)
        for row in range(self._n_rows):
            pygame.draw.line(
                surface=self._screen,
                color=self._config['grid_line_color'],
                start_pos=(0, row * cell_size),
                end_pos=(self._config['width'], row * cell_size)
            )

        # Dibujar grid (líneas verticales)
        for col in range(self._n_cols):
            pygame.draw.line(
                surface=self._screen,
                color=self._config['grid_line_color'],
                start_pos=(col * cell_size, 0),
                end_pos=(col * cell_size, self._config['height'])
            )
        pygame.display.update()  


if __name__ == '__main__':
    simulation = GameOfLife()

    running = True
    while running:
        running = simulation.process_events()
        simulation.run_logic()
        simulation.draw()
        simulation.clock.tick()

    pygame.quit()