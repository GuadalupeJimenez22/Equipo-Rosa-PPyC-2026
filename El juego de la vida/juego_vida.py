import random
import os
import time
from typing import NewType, Any, List, Tuple, Set, Dict

import yaml
import pygame
import numpy as np


Cell = NewType('Cell', Tuple[int, int])

class GameOfLife:

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
    
        self._current_pattern = 'Rand'
        pct_living_cells = random.randrange(
            start=self._config['gen_min_pct_living_cells'],
            stop=self._config['gen_max_pct_living_cells']
        )
        new_living_cells = set()  
        n_cells_to_gen = (self._n_cells * pct_living_cells) // 100
        for _ in range(n_cells_to_gen):
            row = random.randrange(start=0, stop=self._n_rows)
            col = random.randrange(start=0, stop=self._n_cols)
            new_living_cells.add(Cell((col, row)))
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

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                return False  

            if event.type == pygame.MOUSEBUTTONDOWN:  # TODO:
                x, y = pygame.mouse.get_pos()
                col = x // self._config['cell_size']
                row = y // self._config['cell_size']
                cell = Cell((col, row))
                if cell in self._living_cells: 
                    self._living_cells.remove(cell)  # TODO:
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
                    self._is_paused, self._current_pattern = True, 'Rand'
                elif event.key == pygame.K_1:  # pattern 1 (seed_patterns.yml)
                    self._living_cells = self._generate_seed_pattern(id_=1)
                    self._is_paused, self._current_pattern = True, '1'
                elif event.key == pygame.K_2:  # pattern 2 (seed_patterns.yml)
                    self._living_cells = self._generate_seed_pattern(id_=2)
                    self._is_paused, self._current_pattern = True, '2'
                elif event.key == pygame.K_3:  # pattern 3 (seed_patterns.yml)
                    self._living_cells = self._generate_seed_pattern(id_=3)
                    self._is_paused, self._current_pattern = True, '3'
                elif event.key == pygame.K_4:  # pattern 4 (seed_patterns.yml)
                    self._living_cells = self._generate_seed_pattern(id_=4)
                    self._is_paused, self._current_pattern = True, '4'
                elif event.key == pygame.K_5:  
                    self._living_cells = self._generate_seed_pattern(id_=5)
                    self._is_paused, self._current_pattern = True, '5'
                elif event.key == pygame.K_6:  
                    self._living_cells = self._generate_seed_pattern(id_=6)
                    self._is_paused, self._current_pattern = True, '6'
                elif event.key == pygame.K_7:  
                    self._living_cells = self._generate_seed_pattern(id_=7)
                    self._is_paused, self._current_pattern = True, '7'
                elif event.key == pygame.K_8:  
                    self._living_cells = self._generate_seed_pattern(id_=8)
                    self._is_paused, self._current_pattern = True, '8'
                elif event.key == pygame.K_9: 
                    self._living_cells = self._generate_seed_pattern(id_=9)
                    self._is_paused, self._current_pattern = True, '9'
        return True 


    def run_logic(self) -> None:
        
        pygame.display.set_caption(
            self._config['screen_caption'].format(
                pat=self._current_pattern,
                paused='paused' if self._is_paused else 'running')
        )

        if self._is_paused and not self._run_next_step:
                return  

        if self._config['sleep'] is not None:  
            time.sleep(self._config['sleep'])

        all_neighbors = set()
        new_living_cells = set()

        for cell in self._living_cells:
            cell_neighbors = self._get_neighbors(cell=cell)
            all_neighbors.update(cell_neighbors)
            cell_living_neighbors = list(
                filter(
                    lambda cell_: cell_ in self._living_cells, cell_neighbors
                )
            )
            if (self._config['underpopulation'] <=
                    len(cell_living_neighbors) <=
                    self._config['overpopulation']):
                new_living_cells.add(cell)

        for cell in all_neighbors:
            cell_neighbors = self._get_neighbors(cell=cell)
            cell_living_neighbors = list(
                filter(
                    lambda cell_: cell_ in self._living_cells, cell_neighbors
                )
            )
            if len(cell_living_neighbors) == self._config['reproduction']:
                new_living_cells.add(cell)
        self._living_cells = new_living_cells
        self._run_next_step = False  


    def _get_neighbors(self, cell: Cell) -> List[Cell]:
        
        col, row = cell
        grid_is_infinite = self._config['grid_is_infinite']
        delta_row_vals, delta_col_vals = [-1, 0, 1], [-1, 0, 1]

        if row == self._n_rows-1:  
            if grid_is_infinite: 
                delta_row_vals[-1] = - self._n_rows + 1
            else:  
                delta_row_vals.pop()  

        elif row == 0:  
            if grid_is_infinite: 
                delta_row_vals[0] = self._n_rows - 1
            else:  
                delta_row_vals.pop(0)  

        if col == self._n_cols-1:  
            if grid_is_infinite: 
                delta_col_vals[-1] = - self._n_cols + 1
            else:  
                delta_col_vals.pop()  
        elif col == 0: 
            if grid_is_infinite:  
                delta_col_vals[0] = self._n_cols - 1
            else:  
                delta_col_vals.pop(0)  

        neighbors = []  
        for delta_col in delta_col_vals:
            for delta_row in delta_row_vals:
                if delta_col == 0 and delta_row == 0:
                    continue  # this iteration is the given 'cell' itself
                neighbors.append(Cell((col+delta_col, row+delta_row)))
        return neighbors


    def draw(self) -> None:
        
        self._screen.fill(self._config['dead_cell_color'])  
        cell_size = self._config['cell_size']

        for col, row in self._living_cells:
            pygame.draw.rect(
                surface=self._screen,
                color=self._config['living_cell_color'],
                rect=(col*cell_size, row*cell_size, cell_size, cell_size)
            )

        for row in range(self._n_rows):
            pygame.draw.line(
                surface=self._screen,
                color=self._config['grid_line_color'],
                start_pos=(0, row*cell_size),
                end_pos=(self._config['width'], row*cell_size)
            )

        # Draw the vertical lines of the grid
        for col in range(self._n_cols):
            pygame.draw.line(
                surface=self._screen,
                color=self._config['grid_line_color'],
                start_pos=(col*cell_size, 0),
                end_pos=(col*cell_size, self._config['height'])
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