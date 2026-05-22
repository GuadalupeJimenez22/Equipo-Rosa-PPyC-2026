# El Juego de la Vida — Guion de demo en vivo

Instrucciones paso a paso para cada integrante del equipo durante la presentación.

---

## Setup inicial (hacer una sola vez antes de empezar)

```bash
# Entrar a la carpeta del proyecto
cd "El juego de la vida"

# Activar el ambiente virtual
source ../venv/bin/activate

# Verificar que funciona
python -c "from juego_vida_optimo import GameOfLifeOptimo; g=GameOfLifeOptimo(); g.load_pattern('glider'); print('OK: juego_vida_optimo listo')"
```

---

## Dos modos de demo

| Modo | Comando | Ventaja |
|---|---|---|
| **Terminal** | `python -c "..."` o `python juego_vida_optimo.py` | Texto preciso, fácil de copiar, no depende de GUI |
| **GUI** | `python juego_vida.py` | Visual, la audiencia ve las células en colores |

**Recomendación:** usar el modo terminal para las demos de patrones individuales.
La GUI puede usarse como cierre o para mostrar varios patrones seguidos.

---

— Introducción (diapositiva 2)

**Patrones:** `blinker`, `block`

**Concepto:** las 4 reglas de Conway producen oscilación y estabilidad.

### Terminal

```bash
python -c "
from juego_vida_optimo import GameOfLifeOptimo
g = GameOfLifeOptimo()

# Blinker: 3 células que oscilan
g.load_pattern('blinker')
print('Blinker Gen 0 (horizontal):', sorted(g.get_cells()))
g.run_logic_step()
print('Blinker Gen 1 (vertical):  ', sorted(g.get_cells()))
g.run_logic_step()
print('Blinker Gen 2 (horizontal):', sorted(g.get_cells()))

# Block: 4 células que nunca cambian
g.clear()
g.load_pattern('block')
print()
print('Block Gen 0:', sorted(g.get_cells()))
g.run_logic_step()
print('Block Gen 1:', sorted(g.get_cells()))
print('(idéntico — nunca cambia)')
"
```

### GUI

```bash
python juego_vida.py
```

- **Tecla 1** → Blinker
- **Tecla Espacio** → ejecutar/pausar
- **Tecla C** → limpiar
- Luego **Click** sobre 4 celdas en cuadrado para armar un Block manualmente

### Guion de voz

1. "El blinker son solo 3 células. Miren cómo oscila entre horizontal y vertical."
2. "El block son 4 células que forman un cuadrado. No cambia nunca."
3. "Estos dos comportamientos —oscilación y estabilidad— salen de las mismas 4 reglas."
4. "Eso es lo fascinante: reglas simples, comportamientos complejos."

---

— Still lifes y osciladores (diapositiva 3)

**Patrones:** `beehive`, `loaf`, `boat`, `toad`, `beacon`

**Concepto:** hay estructuras que persisten sin cambios y otras que alternan entre estados.

### Terminal

```bash
python -c "
from juego_vida_optimo import GameOfLifeOptimo
g = GameOfLifeOptimo()

# Still lifes: todos son estables
for nombre in ['beehive', 'loaf', 'boat']:
    g.clear()
    g.load_pattern(nombre)
    print(f'{nombre} Gen 0:', sorted(g.get_cells()))
    g.run_logic_step()
    print(f'{nombre} Gen 1:', sorted(g.get_cells()))
    print('  -> (sin cambios)')
    print()

# Osciladores: alternan entre 2 estados
for nombre in ['toad', 'beacon']:
    g.clear()
    g.load_pattern(nombre)
    print(f'{nombre} Gen 0:', sorted(g.get_cells()))
    g.run_logic_step()
    print(f'{nombre} Gen 1:', sorted(g.get_cells()))
    g.run_logic_step()
    print(f'{nombre} Gen 2:', sorted(g.get_cells()))
    print('  -> (volvió al estado original)')
    print()
"
```

### GUI

```bash
python juego_vida.py
```

- **Tecla G** → grilla aleatoria y buscar estas estructuras que aparecen naturalmente
- Explicar que el caos inicial produce beehives y boats espontáneamente

### Guion de voz

1. "Beehive, loaf y boat: 3 still lifes. Cada célula tiene exactamente 2 o 3 vecinos. No se mueven."
2. "Toad y beacon: osciladores de período 2. Van y vuelven entre dos formas."
3. "Lo interesante: estas estructuras aparecen solas del caos. Emergen."
4. "Son los ladrillos y relojes del mundo de Conway."

---

— Naves espaciales (diapositiva 4)

**Patrones:** `glider`, `lwss`, `mwss`, `hwss`

**Concepto:** patrones que se desplazan por la grilla, transmiten información.

### Terminal

```bash
python -c "
from juego_vida_optimo import GameOfLifeOptimo
g = GameOfLifeOptimo()

# Glider: la nave más pequeña (diagonal, c/4)
g.load_pattern('glider')
for i in range(5):
    print(f'Glider Gen {i}:', sorted(g.get_cells()))
    g.run_logic_step()

print()

# LWSS: nave ortogonal más pequeña (c/2)
g.clear()
g.load_pattern('lwss')
for i in range(5):
    print(f'LWSS Gen {i}:', sorted(g.get_cells()))
    g.run_logic_step()

# Puedes repetir con mwss y hwss
"
```

### GUI

```bash
python juego_vida.py
```

- **Tecla 2** → Glider
- **Tecla 3** → LWSS
- **Tecla Espacio** → ver cómo se mueven

### Guion de voz

1. "El glider: 5 células, se mueve en diagonal. La nave más pequeña posible."
2. "LWSS, MWSS, HWSS: naves ortogonales. Más grandes, más rápidas."
3. "Pregunta: ¿para qué sirve una nave? Para transmitir información a distancia."
4. "El Gosper Glider Gun que verá Jorge dispara gliders como mensajeros."

---

— Osciladores complejos y cañones (diapositiva 5)

**Patrones:** `pulsar`, `pentadecathlon`, `gosper_glider_gun`

**Concepto:** periodicidad, generación infinita, el poder de los cañones.

### Terminal

```bash
python -c "
from juego_vida_optimo import GameOfLifeOptimo
g = GameOfLifeOptimo()

# Pulsar: período 3, 48 células, simetría
g.load_pattern('pulsar')
for i in range(4):
    print(f'Pulsar Gen {i}: {len(g.get_cells())} celulas vivas')
    g.run_logic_step()
print('  -> Período 3: cada 3 generaciones vuelve al inicio')

print()

# Gosper Glider Gun: produce un glider cada 30 pasos
g.clear()
g.load_pattern('gosper_glider_gun')
print('Gosper Glider Gun — observa cómo suelta gliders:')
for i in range(0, 91, 30):
    for _ in range(30 if i > 0 else 0):
        g.run_logic_step()
    print(f'  Gen {i}: {len(g.get_cells())} celulas')
print('  -> Ya soltó 3 gliders')
"
```

### GUI

```bash
python juego_vida.py
```

- **Tecla 4** → Pulsar
- **Tecla 5** → Gosper Glider Gun (dale play y mira cómo dispara)

### Guion de voz

1. "El pulsar tiene 48 células y período 3. Es simétrico, casi hipnótico."
2. "El Gosper Glider Gun fue descubierto en 1970 por Bill Gosper."
3. "Cada 30 generaciones suelta un glider nuevo. Crecimiento infinito."
4. "Esto demostró que el Juego de la Vida es Turing-completo. Puede computar cualquier cosa."

---

— Matusalenes y paralelismo (diapositiva 6)

**Patrones:** `r_pentomino`, `diehard`, `acorn`

**Concepto:** patrones pequeños que evolucionan por miles de generaciones.
El paralelismo con `multiprocessing` acelera estas simulaciones largas.

### Terminal (demo de matusalenes)

```bash
python -c "
from juego_vida_optimo import GameOfLifeOptimo
g = GameOfLifeOptimo()

print('=== R-pentomino: 5 celulas -> 1103 generaciones -> 116 celulas ===')
g.load_pattern('r_pentomino')
for i in [0, 50, 100, 200, 500, 1103]:
    g.clear()
    g.load_pattern('r_pentomino')
    g.run_n_steps(i)
    print(f'  Gen {i}: {len(g.get_cells())} celulas vivas')

print()
print('=== Acorn: 7 celulas -> 5206 generaciones ===')
g.clear()
g.load_pattern('acorn')
print(f'  Gen 0: {len(g.get_cells())} celulas')
g.run_n_steps(100)
print(f'  Gen 100: {len(g.get_cells())} celulas')
g.run_n_steps(500)
print(f'  Gen 600: {len(g.get_cells())} celulas — ¡ya explotó!')
"
```

### Demo del motor paralelo

```bash
python juego_vida_proyecto.py
```

- Dibuja un r\_pentomino con el mouse (o presiona **8**)
- **Espacio** para ejecutar
- **R** para cambiar reglas en caliente
- Explica: "Cada núcleo del CPU calcula una franja de filas"

### Guion de voz

1. "Un matusalén es un patrón chiquito que tarda MILES de generaciones en estabilizarse."
2. "R-pentomino: 5 células. 1103 generaciones. Termina con 116 células."
3. "Acorn: 7 células. 5206 generaciones. Explota en un montón de estructuras."
4. "Para simular esto rápido usamos multiprocessing: dividimos el tablero entre todos los núcleos."
5. "Cada núcleo calcula su parte sin comunicarse con los demás. Al final juntamos todo."

---

— Reglas alternativas (diapositiva 7)

**Patrones:** mismo glider con `highlife`, `seeds`, `daynight`

**Concepto:** cambiar las reglas de nacimiento/supervivencia produce universos completamente distintos.

### Terminal

```bash
python -c "
from juego_vida_optimo import GameOfLifeOptimo
g = GameOfLifeOptimo()

# Mismo patrón, 4 reglas distintas
for regla, nombre in [('B3/S23', 'Conway'), ('B36/S23', 'HighLife'), ('B2/S', 'Seeds'), ('B3678/S34678', 'Day & Night')]:
    g.set_rule(regla)
    g.load_pattern('glider')
    print(f'=== {nombre} ({regla}) ===')
    for i in range(4):
        print(f'  Gen {i}:', sorted(g.get_cells()))
        g.run_logic_step()
    print()
"
```

### GUI

```bash
python juego_vida.py
```

- **Tecla 2** → cargar Glider
- **Tecla R** → ciclar entre reglas (Conway → HighLife → Seeds → Maze → ...)
- Cada vez que presionas R mira cómo cambia el comportamiento del mismo glider

### Guion de voz

1. "Todo lo que vimos hasta ahora usa las reglas de Conway: B3/S23."
2. "¿Qué pasa si cambiamos las reglas? Veamos el mismo glider con otras leyes."
3. "HighLife: muy parecido a Conway, pero tiene un replicador natural."
4. "Seeds: todo es caótico, el glider muere en 2 pasos."
5. "Day & Night: es simétrico. Si intercambias vivo por muerto se comporta igual."
6. "El mismo patrón, pero vive en universos distintos. Y tenemos 11 para explorar."

---

## Tips para la presentación

| Situación | Qué hacer |
|---|---|
| **El comando falla** | Verificar que el venv está activado: `which python` debe mostrar `.../venv/bin/python` |
| **No encuentra los módulos** | Ejecutar desde la carpeta `El juego de la vida/`: `cd "El juego de la vida"` |
| **Quieres mostrar más rápido** | Usa `g.run_n_steps(50)` en vez de `g.run_logic_step()` en bucle |
| **Quieres limpiar entre demos** | Usa `g.clear()` antes de `g.load_pattern(...)` |
| **La GUI va muy lenta** | Baja el `sleep` en `config.yml` a `0.05` o menos |
| **Modo paralelo no muestra nada** | Dibuja con el mouse (click izquierdo) un patrón antes de darle play |

---

