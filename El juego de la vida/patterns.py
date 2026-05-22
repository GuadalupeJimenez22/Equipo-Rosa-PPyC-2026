from dataclasses import dataclass, field
from typing import Set, Tuple, List, Dict, Optional
import yaml

Cell = Tuple[int, int]


@dataclass
class Pattern:
    name: str
    type: str
    cells: Set[Cell]
    period: Optional[int] = None
    description: str = ""
    author: str = ""

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        cols = [c for c, _ in self.cells]
        rows = [r for _, r in self.cells]
        return min(cols), min(rows), max(cols), max(rows)

    @property
    def width(self) -> int:
        min_c, _, max_c, _ = self.bounds
        return max_c - min_c + 1

    @property
    def height(self) -> int:
        _, min_r, _, max_r = self.bounds
        return max_r - min_r + 1

    def to_matrix(self) -> List[List[int]]:
        min_c, min_r, max_c, max_r = self.bounds
        w = max_c - min_c + 1
        h = max_r - min_r + 1
        matrix = [[0] * w for _ in range(h)]
        for c, r in self.cells:
            matrix[r - min_r][c - min_c] = 1
        return matrix

    def centered(self, n_cols: int, n_rows: int) -> Set[Cell]:
        min_c, min_r, _, _ = self.bounds
        offset_c = (n_cols - self.width) // 2 - min_c
        offset_r = (n_rows - self.height) // 2 - min_r
        return {(c + offset_c, r + offset_r) for c, r in self.cells}


CATALOG: Dict[str, Pattern] = {}

def _p(name: str, type_: str, cells: Set[Cell], period: Optional[int] = None,
       description: str = "", author: str = "") -> Pattern:
    p = Pattern(name, type_, cells, period, description, author)
    CATALOG[name] = p
    return p


# Still lifes
_p("block", "still_life",
  {(0, 0), (1, 0), (0, 1), (1, 1)},
  period=1, description="El oscilador más simple (estático).")
_p("beehive", "still_life",
  {(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (2, 2)},
  period=1, description="Estructura estática común que surge del caos.")
_p("loaf", "still_life",
  {(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (3, 2), (2, 3)},
  period=1, description="Estático de 7 células, común en sopas aleatorias.")
_p("boat", "still_life",
  {(0, 0), (1, 0), (0, 1), (2, 1), (1, 2)},
  period=1, description="Estático de 5 células.")
_p("tub", "still_life",
  {(1, 0), (0, 1), (2, 1), (1, 2)},
  period=1, description="Estático de 4 células con forma de tina.")
_p("ship", "still_life",
  {(0, 0), (1, 0), (0, 1), (2, 1), (1, 2), (2, 2)},
  period=1, description="Estático de 6 células.")
_p("pond", "still_life",
  {(0, 0), (1, 0), (2, 1), (3, 1), (0, 2), (1, 2), (2, 3), (3, 3)},
  period=1, description="Estático de 8 células con forma de estanque.")

# Oscillators
_p("blinker", "oscillator",
  {(0, 1), (1, 1), (2, 1)},
  period=2, description="El oscilador más pequeño (horizontal / vertical).")
_p("toad", "oscillator",
  {(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1)},
  period=2, description="Oscilador de período 2.")
_p("beacon", "oscillator",
  {(0, 0), (1, 0), (0, 1), (3, 2), (2, 3), (3, 3)},
  period=2, description="Dos bloques que parpadean alternadamente.")
_p("pulsar", "oscillator",
  {(2, 0), (3, 0), (4, 0), (8, 0), (9, 0), (10, 0),
   (0, 2), (5, 2), (7, 2), (12, 2),
   (0, 3), (5, 3), (7, 3), (12, 3),
   (0, 4), (5, 4), (7, 4), (12, 4),
   (2, 5), (3, 5), (4, 5), (8, 5), (9, 5), (10, 5),
   (2, 7), (3, 7), (4, 7), (8, 7), (9, 7), (10, 7),
   (0, 8), (5, 8), (7, 8), (12, 8),
   (0, 9), (5, 9), (7, 9), (12, 9),
   (0, 10), (5, 10), (7, 10), (12, 10),
   (2, 12), (3, 12), (4, 12), (8, 12), (9, 12), (10, 12)},
  period=3, description="Oscilador de período 3, uno de los más icónicos.")
_p("pentadecathlon", "oscillator",
  {(0, 2), (7, 2),
   (1, 1), (6, 1),
   (1, 0), (3, 0), (4, 0), (6, 0),
   (1, 3), (3, 3), (4, 3), (6, 3),
   (2, 1), (5, 1), (2, 2), (5, 2)},
  period=15, description="Oscilador de período 15 con 12 células vivas.")

# Spaceships
_p("glider", "spaceship",
  {(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)},
  period=4, description="La nave más pequeña. Se mueve en diagonal a c/4.")
_p("lwss", "spaceship",
  {(1, 0), (2, 0), (3, 0), (4, 0),
   (0, 1), (4, 1),
   (4, 2),
   (0, 3), (3, 3)},
  period=4, description="Lightweight Spaceship. Nave más pequeña ortogonal (c/2).")
_p("mwss", "spaceship",
  {(1, 0), (2, 0), (3, 0), (4, 0), (5, 0),
   (0, 1), (5, 1),
   (5, 2),
   (0, 3), (4, 3)},
  period=4, description="Middleweight Spaceship (c/2).")
_p("hwss", "spaceship",
  {(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0),
   (0, 1), (6, 1),
   (6, 2),
   (0, 3), (5, 3)},
  period=4, description="Heavyweight Spaceship (c/2).")

# Guns
_p("gosper_glider_gun", "gun",
  {(24, 0),
   (22, 1), (24, 1),
   (12, 2), (13, 2), (20, 2), (21, 2), (34, 2), (35, 2),
   (11, 3), (15, 3), (20, 3), (21, 3), (34, 3), (35, 3),
   (0, 4), (1, 4), (10, 4), (16, 4), (20, 4), (21, 4),
   (0, 5), (1, 5), (10, 5), (14, 5), (16, 5), (17, 5), (22, 5), (24, 5),
   (10, 6), (16, 6), (24, 6),
   (11, 7), (15, 7),
   (12, 8), (13, 8)},
  period=30, description="El primer cañón de gliders descubierto (Gosper, 1970). Produce un glider cada 30 generaciones.",
  author="Bill Gosper")

# Methuselahs
_p("r_pentomino", "methuselah",
  {(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)},
  description="Matusalén de 5 células. Estabiliza tras 1103 generaciones con 116 células.",
  author="John Conway")
_p("diehard", "methuselah",
  {(0, 0), (1, 0), (1, 1), (5, 1), (6, 1), (7, 1), (6, 2)},
  description="Matusalén que desaparece tras 130 generaciones.")
_p("acorn", "methuselah",
  {(0, 0), (1, 0), (4, 1), (5, 1), (6, 1), (3, 2), (5, 3)},
  description="Matusalén de 7 células. Estabiliza tras 5206 generaciones.",
  author="Charles Corderman")
_p("b_heptomino", "methuselah",
  {(0, 0), (1, 0), (2, 0), (0, 1), (1, 2), (2, 2)},
  description="Matusalén de 6 células con comportamiento complejo.")

# Puffers / others
_p("queen_bee", "oscillator",
  {(0, 0), (0, 1), (0, 3), (0, 4), (0, 5), (0, 6), (0, 8), (0, 9),
   (2, 0), (2, 1),
   (4, 1), (5, 1),
   (4, 3), (5, 3),
   (4, 6), (5, 6),
   (5, 9),
   (7, 0), (7, 2), (7, 3), (7, 4), (7, 5), (7, 7), (8, 8), (8, 9),
   (9, 1), (9, 8),
   (10, 2), (10, 3), (10, 6), (10, 7),
   (10, 0), (11, 1), (11, 8), (12, 2), (12, 6),
   (12, 3), (12, 7), (13, 3), (13, 4), (13, 5), (13, 7), (14, 3), (14, 7)},
  period=30, description="Queen Bee Shuttle. Oscilador que produce una 'abeja' que rebota.",
  author="Bill Gosper")


def matrix_to_cells(matrix: List[List[int]], offset_col: int = 0, offset_row: int = 0) -> Set[Cell]:
    cells: Set[Cell] = set()
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if val:
                cells.add((c + offset_col, r + offset_row))
    return cells


def cells_to_matrix(cells: Set[Cell], normalize: bool = True) -> List[List[int]]:
    if not cells:
        return [[]]
    min_c = min(c for c, _ in cells)
    min_r = min(r for _, r in cells)
    max_c = max(c for c, _ in cells)
    max_r = max(r for _, r in cells)
    w = max_c - min_c + 1
    h = max_r - min_r + 1
    matrix = [[0] * w for _ in range(h)]
    for c, r in cells:
        dr = r - min_r if normalize else r
        dc = c - min_c if normalize else c
        if 0 <= dr < h and 0 <= dc < w:
            matrix[dr][dc] = 1
    return matrix


def cells_to_yaml_dict(cells: Set[Cell]) -> List[List[int]]:
    return cells_to_matrix(cells, normalize=True)


def save_pattern_to_yaml(cells: Set[Cell], name: str, filepath: str) -> None:
    matrix = cells_to_matrix(cells, normalize=True)
    data: Dict = {}
    try:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if 'patterns' not in data or not isinstance(data.get('patterns'), dict):
        data['patterns'] = {}
    existing = {k for k, _ in data.get('patterns', {}).items() if isinstance(k, int)}
    next_id = 1
    while next_id in existing:
        next_id += 1
    data['patterns'][next_id] = {'name': name, 'matrix': matrix}
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_patterns_from_yaml(filepath: str) -> Dict[str, Set[Cell]]:
    try:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return {}
    if not data or not isinstance(data, dict):
        return {}
    patterns = data.get('patterns', {})
    result: Dict[str, Set[Cell]] = {}
    for key, val in patterns.items():
        name = val.get('name', str(key)) if isinstance(val, dict) else str(key)
        matrix = val.get('matrix', val) if isinstance(val, dict) else val
        result[name] = matrix_to_cells(matrix)
    return result


def get_patterns_by_type(pattern_type: str) -> List[Pattern]:
    return [p for p in CATALOG.values() if p.type == pattern_type]


def list_catalog() -> List[str]:
    return list(CATALOG.keys())


def get_pattern(name: str) -> Optional[Pattern]:
    return CATALOG.get(name)
