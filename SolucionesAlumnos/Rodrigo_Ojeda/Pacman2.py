
"""
PacMan2.py - Ejercicio 3 del examen

Este archivo implementa una versión de Pac-Man extendida con **enemigos (fantasmas)**,
vidas limitadas y un modo **autopiloto** que recoge pellets automáticamente usando
**BFS (Breadth-First Search) con estrategia greedy** (elige siempre el pellet más cercano).

=====================
Interfaz:
- El laberinto se define como una **lista de strings rectangular** en la variable RAW_MAP.
- Cada carácter representa un elemento del mapa:
  * '#' = pared
  * '.' = pellet (punto)
  * 'o' = power pellet (sin efecto en esta versión)
  * 'P' = posición inicial de Pac-Man
  * 'G' = posición inicial de un fantasma
  * ' ' = espacio vacío

=====================
Salida:
- En pantalla:
  * Puntuación (Score)
  * Vidas (Lives)
  * Estado del juego: "WIN" o "GAME OVER"
  * Estado del autopiloto (si está activado)
- En consola:
  * Colisiones con fantasmas
  * Vidas restantes
  * Ruta seguida (número de pasos)
  * Tiempo total de ejecución

=====================
Algoritmo:
- Pac-Man se mueve en modo **autopiloto** usando BFS para encontrar el camino más corto
  hasta el pellet más cercano en cada momento (estrategia greedy).
- Motivación:
  * BFS garantiza encontrar el camino más corto en un grid no ponderado.
  * Elegir siempre el pellet más cercano simplifica el problema (no resuelve el óptimo global tipo TSP,
    pero es suficiente para laberintos pequeños/medianos).
  * Es eficiente, fácil de implementar y cumple los requisitos del examen.

=====================
Ejemplo de uso:
$ python PacMan2.py
- Presiona la tecla SPACE para iniciar el juego.
- Pac-Man empezará en modo autopiloto y recogerá los pellets automáticamente.
- El juego termina cuando recoge todos los pellets (WIN) o pierde todas las vidas (GAME OVER).

=====================
Caso de prueba sencillo:
Entrada (RAW_MAP reducido):
[
    "#####",
    "#P..#",
    "#...#",
    "#####"
]

- Pac-Man empieza en la celda 'P'.
- Hay 4 pellets en el mapa.
- Autopiloto recorrerá todas las celdas accesibles recogiendo los pellets.
- Salida esperada:
  Score final = 40 (4 pellets * 10 puntos cada uno)
  Estado final = WIN
  Número de pasos = longitud mínima de la ruta que conecta los pellets
"""


# Código implementado:

import arcade
import time
import random
from collections import deque
from typing import List, Tuple

# ===================== CONFIGURACIÓN GENERAL =====================
SCREEN_TITLE = "PacMan BFS Autopilot con Enemigos"
TILE_SIZE = 32
HUD_MARGIN_TOP = 60  # espacio para HUD superior
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
    "#P.......G......G..P#",
    "####.### #### ###.####",
    "#....#....##....#....#",
    "#.##.#.######.#.##.#.#",
    "#........G...........#",
    "#o##.###.##.###.##o.#",
    "#.##.###.##.###.##..#",
    "#........##..........#",
    "######################",
]

ROWS = len(RAW_MAP)
COLS = len(RAW_MAP[0])
SCREEN_WIDTH = COLS * TILE_SIZE
SCREEN_HEIGHT = ROWS * TILE_SIZE + HUD_MARGIN_TOP

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

    path = []
    node = goal
    while node in parent:
        path.append(node)
        node = parent[node]
    path.append(start)
    path.reverse()
    return path

def find_closest_pellet(pacman_pos, pellet_list, walls_grid):
    """Encuentra el pellet más cercano a Pac-Man"""
    shortest = None
    best_path = None
    for pellet in pellet_list:
        goal = pixel_to_grid(pellet.center_x, pellet.center_y)
        path = bfs_path(pacman_pos, goal, walls_grid)
        if path and (shortest is None or len(path) < shortest):
            shortest = len(path)
            best_path = path
    return best_path

# ===================== CLASES =====================
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
        self.speed = 4  # 🔹 píxeles por frame
        self.target = None

    def move_to(self, x, y):
        """Define un objetivo de movimiento en píxeles"""
        self.target = (x, y)

    def update(self):
        if self.target:
            dx = self.target[0] - self.center_x
            dy = self.target[1] - self.center_y
            dist = (dx**2 + dy**2) ** 0.5
            if dist < self.speed:
                self.center_x, self.center_y = self.target
                self.target = None
            else:
                self.center_x += self.speed * dx / dist
                self.center_y += self.speed * dy / dist

class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, walls_grid):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = arcade.color.RED
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.walls_grid = walls_grid
        self.direction = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.speed = 3
        self.target = None
        self.change_timer = 0

    def update(self):
        if self.target:
            dx = self.target[0] - self.center_x
            dy = self.target[1] - self.center_y
            dist = (dx**2 + dy**2) ** 0.5
            if dist < self.speed:
                self.center_x, self.center_y = self.target
                self.target = None
            else:
                self.center_x += self.speed * dx / dist
                self.center_y += self.speed * dy / dist

        # Movimiento aleatorio cada cierto tiempo
        self.change_timer += 1
        if self.change_timer > 30 and not self.target:  # cada 30 frames
            col, row = pixel_to_grid(self.center_x, self.center_y)
            dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            nx, ny = col + dx, row + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and self.walls_grid[ny][nx] == 0:
                self.target = grid_to_pixel(nx, ny)
            self.change_timer = 0

# ===================== JUEGO PRINCIPAL =====================
class PacGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.ghost_list = arcade.SpriteList()
        self.pacman: Pacman | None = None
        self.walls_grid = []
        self.state = "PLAY"
        self.autopilot = False
        self.autopilot_path = []
        self.total_steps = 0
        self.start_time = 0.0
        self.start_pos = None
        self.running = False

    def setup(self):
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.ghost_list = arcade.SpriteList()
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]

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
                    self.start_pos = (c, r)
                elif ch == "G":
                    ghost = Ghost(c, r, self.walls_grid)
                    self.ghost_list.append(ghost)

        if self.start_pos:
            self.pacman = Pacman(*self.start_pos)

    def on_draw(self):
        self.clear()
        arcade.draw_text(f"Score: {self.pacman.score}", 10, SCREEN_HEIGHT - 30, arcade.color.YELLOW, 16)
        arcade.draw_text(f"Lives: {self.pacman.lives}", SCREEN_WIDTH - 100, SCREEN_HEIGHT - 30, arcade.color.RED, 16)

        self.wall_list.draw()
        self.pellet_list.draw()
        self.ghost_list.draw()
        if self.pacman:
            rect_p = arcade.rect.XYWH(self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_p, self.pacman.color)

        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "GAME_OVER":
            arcade.draw_text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.RED, 40, anchor_x="center")

        if not self.running and self.state == "PLAY":
            arcade.draw_text("Presiona SPACE para empezar", SCREEN_WIDTH/2, SCREEN_HEIGHT - 60,
                             arcade.color.ORANGE, 20, anchor_x="center")

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman or not self.running:
            return

        self.pacman.update()
        for ghost in self.ghost_list:
            ghost.update()

        # Autopiloto: calcular siguiente pellet más cercano
        if not self.pacman.target:
            if len(self.pellet_list) == 0:
                self.state = "WIN"
                elapsed = time.time() - self.start_time
                print(f"Ruta completa encontrada en {self.total_steps} pasos")
                print(f"Tiempo de ejecución: {elapsed:.3f} segundos")
                return
            pac_col, pac_row = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
            self.autopilot_path = find_closest_pellet((pac_col, pac_row), self.pellet_list, self.walls_grid)
            if self.autopilot_path:
                self.autopilot_path.pop(0)  # quitar inicio
                if self.autopilot_path:
                    next_cell = self.autopilot_path.pop(0)
                    self.pacman.move_to(*grid_to_pixel(*next_cell))
                    self.total_steps += 1

        # Comer pellets
        hit = arcade.check_for_collision_with_list(self.pacman, self.pellet_list)
        for p in hit:
            p.remove_from_sprite_lists()
            self.pacman.score += 10

        # Colisión con fantasmas
        hit_ghosts = arcade.check_for_collision_with_list(self.pacman, self.ghost_list)
        if hit_ghosts:
            self.pacman.lives -= 1
            print(f"⚠️ Colisión con fantasma. Vidas restantes: {self.pacman.lives}")
            if self.pacman.lives <= 0:
                self.state = "GAME_OVER"
                print("Pac-Man ha perdido todas las vidas. GAME OVER.")
            else:
                x, y = grid_to_pixel(*self.start_pos)
                self.pacman.center_x, self.pacman.center_y = x, y
                self.pacman.target = None

    def on_key_press(self, key, modifiers):
        if key == arcade.key.SPACE:
            self.running = True
            self.start_time = time.time()
            print("▶️ Juego iniciado.")

# ===================== MAIN =====================
def main():
    game = PacGame()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
