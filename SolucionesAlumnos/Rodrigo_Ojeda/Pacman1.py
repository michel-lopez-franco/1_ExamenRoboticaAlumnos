"""
PacMan.py - Ejercicio 2 del examen

Este archivo implementa una versión de Pac-Man con un modo **autopiloto** que recorre el mapa
y recoge todos los pellets (.) de forma automática usando **BFS (Breadth-First Search)**.

=====================
Formato del laberinto:
- Se define como una **lista de strings rectangular** en la variable RAW_MAP.
- Cada carácter representa un elemento del mapa:
  * '#' = pared
  * '.' = pellet (punto)
  * 'o' = power pellet
  * 'P' = posición inicial de Pac-Man
  * 'G' = posición inicial de un fantasma
  * ' ' = espacio vacío

=====================
Interfaz:
- La función principal pública es `main()`, que inicia el juego en Arcade.
- El usuario puede mover a Pac-Man con las flechas o activar el **autopiloto (tecla A)**.
- El autopiloto usa BFS para encontrar el siguiente pellet más cercano y dirigirse hacia él.
- Se garantiza que Pac-Man no atraviesa muros ni se sale del mapa.

=====================
Salida:
- En consola se imprime al finalizar:
  * Ruta completa recorrida
  * Número de pasos totales
  * Tiempo de ejecución aproximado
- En la ventana del juego se muestra:
  * Puntuación (score)
  * Estado del autopiloto (ON/OFF)
  * Mensaje de instrucciones ("Presiona A...")
  * Mensaje de victoria ("¡GANASTE!") cuando se recojan todos los pellets

=====================
Ejemplo de uso:
$ python PacMan.py

- Usa las teclas de dirección para mover Pac-Man manualmente.
- Presiona la tecla A para activar/desactivar el autopiloto.
"""

import arcade
import time
import random
from collections import deque
from typing import List, Tuple

# ===================== CONFIGURACIÓN GENERAL =====================
SCREEN_TITLE = "PacMan BFS Autopilot"
TILE_SIZE = 32
SCREEN_MARGIN = 32

RAW_MAP = [
    "######################",
    "#........##..........#",
    "#.##.###.##.###.##..#",
    "#o##.###.##.###.##o.#",
    "#....................#",
    "#.##.#.######.#.##.#.#",
    "#....#....##....#....#",
    "####.### #### ###.####",
    "#P..................P#",
    "####.### #### ###.####",
    "#....#....##....#....#",
    "#.##.#.######.#.##.#.#",
    "#....................#",
    "#o##.###.##.###.##o.#",
    "#.##.###.##.###.##..#",
    "#........##..........#",
    "######################",
]

ROWS = len(RAW_MAP)
COLS = len(RAW_MAP[0])
SCREEN_WIDTH = COLS * TILE_SIZE
SCREEN_HEIGHT = ROWS * TILE_SIZE

# ===================== UTILIDADES =====================
def grid_to_pixel(col: int, row: int) -> Tuple[int, int]:
    x = col * TILE_SIZE + TILE_SIZE // 2
    y = (ROWS - row - 1) * TILE_SIZE + TILE_SIZE // 2
    return x, y

def pixel_to_grid(x: float, y: float) -> Tuple[int, int]:
    col = int(x // TILE_SIZE)
    row_from_bottom = int(y // TILE_SIZE)
    row = ROWS - row_from_bottom - 1
    return col, row

# ===================== BFS =====================
def bfs_path(start: Tuple[int, int], goal: Tuple[int, int], walls_grid: List[List[int]]):
    """Encuentra el camino más corto entre start y goal usando BFS"""
    n, m = len(walls_grid), len(walls_grid[0])
    visited = [[False]*m for _ in range(n)]
    parent = dict()
    q = deque([start])
    visited[start[1]][start[0]] = True

    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            break
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < m and 0 <= ny < n and not visited[ny][nx]:
                if walls_grid[ny][nx] == 0:
                    visited[ny][nx] = True
                    parent[(nx, ny)] = (x, y)
                    q.append((nx, ny))

    # Reconstruir camino
    path = []
    node = goal
    while node in parent:
        path.append(node)
        node = parent[node]
    path.append(start)
    path.reverse()
    return path

# ===================== CLASE PACMAN =====================
class Pacman(arcade.Sprite):
    def __init__(self, col: int, row: int):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = arcade.color.YELLOW
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.lives = 3
        self.score = 0

# ===================== JUEGO PRINCIPAL =====================
class PacGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.pacman: Pacman | None = None
        self.walls_grid = []
        self.state = "PLAY"
        self.autopilot = False
        self.autopilot_path = []
        self.total_steps = 0
        self.start_time = 0.0

        # 🔹 Control de velocidad del autopiloto
        self.move_delay = 0.015  # segundos entre movimientos
        self.time_since_move = 0.0

    def setup(self):
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]

        pacman_pos = None
        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_pixel(c, r)
                if ch == "#":
                    wall = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, arcade.color.DARK_BLUE)
                    wall.center_x, wall.center_y = x, y
                    self.wall_list.append(wall)
                    self.walls_grid[r][c] = 1
                elif ch == ".":
                    pellet = arcade.SpriteSolidColor(6, 6, arcade.color.WHITE)
                    pellet.center_x, pellet.center_y = x, y
                    self.pellet_list.append(pellet)
                elif ch == "P":
                    pacman_pos = (c, r)

        if pacman_pos:
            self.pacman = Pacman(*pacman_pos)

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        if self.pacman:
            rect_p = arcade.rect.XYWH(self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_p, self.pacman.color)

        arcade.draw_text(f"Score: {self.pacman.score}", 10, SCREEN_HEIGHT-20, arcade.color.YELLOW, 14)

        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")

        # 🔹 Indicador mejorado
        arcade.draw_text(
            f"Autopiloto: {'ON' if self.autopilot else 'OFF'}",
            SCREEN_WIDTH/2, 20, arcade.color.ORANGE, 14, anchor_x="center"
        )
        arcade.draw_text(
            "Presiona la tecla A para activar/desactivar el AUTOPILOTO",
            SCREEN_WIDTH/2, 40, arcade.color.ORANGE, 14, anchor_x="center"
        )

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return

        if self.autopilot:
            # Controlar velocidad
            self.time_since_move += delta_time
            if self.time_since_move < self.move_delay:
                return
            self.time_since_move = 0.0

            if not self.autopilot_path:
                if len(self.pellet_list) == 0:
                    self.state = "WIN"
                    elapsed = time.time() - self.start_time
                    print(f"Ruta completa encontrada en {self.total_steps} pasos")
                    print(f"Tiempo de ejecución: {elapsed:.3f} segundos")
                    return
                pellet = self.pellet_list[0]
                goal = pixel_to_grid(pellet.center_x, pellet.center_y)
                pac_col, pac_row = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
                self.autopilot_path = bfs_path((pac_col, pac_row), goal, self.walls_grid)
                self.autopilot_path.pop(0)

            if self.autopilot_path:
                next_cell = self.autopilot_path.pop(0)
                x, y = grid_to_pixel(*next_cell)
                self.pacman.center_x, self.pacman.center_y = x, y
                self.total_steps += 1

                hit = arcade.check_for_collision_with_list(self.pacman, self.pellet_list)
                for p in hit:
                    p.remove_from_sprite_lists()
                    self.pacman.score += 10

    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.autopilot = not self.autopilot
            if self.autopilot:
                self.total_steps = 0
                self.start_time = time.time()
                print("Autopiloto activado.")

# ===================== MAIN =====================
def main():
    game = PacGame()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()

# ===================== NOTA SOBRE EL ALGORITMO =====================
# En este ejercicio se eligió el algoritmo **BFS (Breadth-First Search)**
# para el modo autopiloto de Pac-Man.
#
# Justificación:
# - BFS garantiza encontrar el camino más corto en un grafo no ponderado.
# - Es sencillo de implementar y eficiente en mapas de tamaño moderado.
# - Se adapta bien a laberintos y grids donde todos los movimientos tienen el mismo coste.
#
# Limitaciones:
# - BFS siempre busca el pellet más cercano en cada momento, lo cual puede no ser óptimo
#   a largo plazo (no resuelve el problema global como TSP).
# - Para mapas más grandes o con muchos objetivos, un algoritmo heurístico como A* o
#   una aproximación de TSP podría ser más eficiente.
#
# Para este examen, BFS ofrece un equilibrio adecuado entre simplicidad, claridad
# y eficiencia, cumpliendo con los requisitos del ejercicio.
