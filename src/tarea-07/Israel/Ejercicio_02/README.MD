# Simulación de Venta de Boletos 
**hilos (threads)** en Python puede generar condiciones de carrera al modificar una variable compartida, y cómo solucionarlo utilizando un **Lock**.

## Descripción
El programa simula la venta de boletos:
- **Versión sin lock(sin.py):** múltiples hilos acceden y modifican la variable `boletos_disponibles` sin sincronización, lo que provoca resultados inconsistentes.
- **Versión con lock(con.py):** se utiliza `threading.Lock()` para asegurar que solo un hilo modifique la variable a la vez, evitando condiciones de carrera.

**EJECUCION**
1. Clona este repositorio o copia los archivos en tu máquina.
2. Asegúrate de tener Python instalado (versión 3.8 o superior recomendada).
3. Ejecuta el archivo principal:

```bash
python main.py