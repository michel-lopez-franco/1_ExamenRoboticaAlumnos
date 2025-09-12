"""
README — Procedural Caves with Gem
===================================

Este programa genera cuevas de manera procedural mediante autómatas celulares
y coloca una **gema** en una celda libre. Un agente autónomo busca la ruta más
corta hasta la gema usando **BFS (Breadth-First Search)** y se mueve hasta
encontrarla. 

Durante la ejecución:
- Se muestran en pantalla y en consola los **pasos dados** y el **tiempo total**.
- El tiempo se **detiene al encontrar la gema**.
- Al final aparece un mensaje de victoria con los resultados.

-----------------------------------
CAMBIOS PRINCIPALES
-----------------------------------
✔ Se añade HUD en pantalla (tiempo y pasos en vivo).  
✔ Se guarda el tiempo final al encontrar la gema (no sigue corriendo).  
✔ Se imprime en consola la ruta encontrada, pasos y tiempo.  
✔ Se muestra mensaje final de victoria en pantalla y consola.  

-----------------------------------
EJEMPLO DE EJECUCIÓN
-----------------------------------
Al correr el programa, verás en consola algo como:

Ruta encontrada: [(23, 45), (23, 46), (24, 46), ... , (30, 50)]
Pasos: 58
Tiempo BFS: 0.0021 s
🎉 Gema encontrada en 12.34 s con 58 pasos

En pantalla:
- Arriba a la izquierda: "Tiempo: 12.34 s" y "Pasos: 58".
- Mensaje central: "🎉 Gema encontrada en 12.34 s / Pasos: 58".

-----------------------------------
CASO DE PRUEBA SENCILLO
-----------------------------------
Entrada:  Laberinto procedural generado con `GRID_WIDTH=20`, `GRID_HEIGHT=15`
           Gema colocada en celda libre.
Salida esperada:
           - El agente encuentra la gema en ≤ tiempo finito.
           - Se imprime en consola la ruta encontrada (lista de coordenadas).
           - El HUD muestra pasos > 0 y tiempo > 0.
           - Al tocar la gema se congela el cronómetro.

-----------------------------------
CÓMO EJECUTAR
-----------------------------------
1. Instalar Arcade (si no lo tienes):
   pip install arcade

2. Ejecutar el script desde la terminal:
   python PROCEDURAL.py

3. Espera a que cargue y observa cómo el agente busca y recoge la gema.

-----------------------------------
"""


import random
import arcade
import timeit
from collections import deque

# Sprite scaling
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

# Grid dimensions
GRID_WIDTH = 100
GRID_HEIGHT = 80

# Cellular automata parameters
CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

# Player speed (pixels per frame)
MOVEMENT_SPEED = 3  # más rápido

# Window config
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves with Gem"

# Camera speed
CAMERA_SPEED = 0.1


def create_grid(width, height):
    return [[0 for _x in range(width)] for _y in range(height)]


def initialize_grid(grid):
    height = len(grid)
    width = len(grid[0])
    for row in range(height):
        for column in range(width):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[row][column] = 1


def count_alive_neighbors(grid, x, y):
    height = len(grid)
    width = len(grid[0])
    alive_count = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            neighbor_x = x + i
            neighbor_y = y + j
            if i == 0 and j == 0:
                continue
            elif (
                neighbor_x < 0
                or neighbor_y < 0
                or neighbor_y >= height
                or neighbor_x >= width
            ):
                alive_count += 1
            elif grid[neighbor_y][neighbor_x] == 1:
                alive_count += 1
    return alive_count


def do_simulation_step(old_grid):
    height = len(old_grid)
    width = len(old_grid[0])
    new_grid = create_grid(width, height)
    for x in range(width):
        for y in range(height):
            alive_neighbors = count_alive_neighbors(old_grid, x, y)
            if old_grid[y][x] == 1:
                if alive_neighbors < DEATH_LIMIT:
                    new_grid[y][x] = 0
                else:
                    new_grid[y][x] = 1
            else:
                if alive_neighbors > BIRTH_LIMIT:
                    new_grid[y][x] = 1
                else:
                    new_grid[y][x] = 0
    return new_grid


def find_item(grid, start, item_positions):
    """Encuentra la ruta más corta a la gema más cercana usando BFS."""
    start_time = timeit.default_timer()

    rows, cols = len(grid), len(grid[0])
    visited = [[False] * cols for _ in range(rows)]
    queue = deque([(start, [])])
    visited[start[0]][start[1]] = True

    while queue:
        (r, c), path = queue.popleft()

        if (r, c) in item_positions:
            elapsed = timeit.default_timer() - start_time
            ruta = path + [(r, c)]
            print(f"Ruta encontrada: {ruta}")
            print(f"Pasos: {len(ruta)}")
            print(f"Tiempo BFS: {elapsed:.4f} s")
            return ruta

        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if not visited[nr][nc] and grid[nr][nc] == 0:
                    visited[nr][nc] = True
                    queue.append(((nr, nc), path + [(r, c)]))

    return None


class InstructionView(arcade.View):
    def on_show_view(self):
        self.window.background_color = random.choice(
            [arcade.color.DARK_RED, arcade.color.DARK_SLATE_BLUE, arcade.color.DARK_GREEN]
        )
        self.window.default_camera.use()

    def on_draw(self):
        self.clear()
        arcade.draw_text(
            "Loading...",
            self.window.width // 2,
            self.window.height // 2,
            arcade.color.WHITE,
            font_size=50,
            anchor_x="center",
        )

    def on_update(self, dt):
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.grid = None
        self.wall_list = None
        self.player_sprite = None
        self.player_list = None
        self.gem_list = None
        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()
        self.path = []
        self.gem_positions = []

        # Cronómetro y pasos
        self.start_time = None
        self.final_time = None   # 👈 se guarda el tiempo al encontrar la gema
        self.steps = 0

        # Estado de victoria
        self.victory = False

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.gem_list = arcade.SpriteList()

        # Crear mapa
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for step in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.BasicSprite(texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # Player
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING,
        )
        self.player_list.append(self.player_sprite)

        placed = False
        while not placed:
            max_x = int(GRID_WIDTH * SPRITE_SIZE)
            max_y = int(GRID_HEIGHT * SPRITE_SIZE)
            self.player_sprite.center_x = random.randint(0, max_x)
            self.player_sprite.center_y = random.randint(0, max_y)
            if not arcade.check_for_collision_with_list(self.player_sprite, self.wall_list):
                placed = True

        # Gema
        placed = False
        while not placed:
            col = random.randrange(GRID_WIDTH)
            row = random.randrange(GRID_HEIGHT)
            if self.grid[row][col] == 0:
                gem = arcade.Sprite(
                    ":resources:images/items/gemYellow.png", scale=SPRITE_SCALING
                )
                gem.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                gem.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                self.gem_list.append(gem)
                self.gem_positions.append((row, col))
                placed = True

        # Iniciar cronómetro y pasos
        self.start_time = timeit.default_timer()
        self.steps = 0

        # Calcular primera ruta
        self.calculate_new_path()

        # Cámara en el jugador desde inicio
        self.scroll_to_player(1.0)

    def calculate_new_path(self):
        if not self.gem_positions:
            return

        start_row = int(self.player_sprite.center_y // SPRITE_SIZE)
        start_col = int(self.player_sprite.center_x // SPRITE_SIZE)
        path = find_item(self.grid, (start_row, start_col), self.gem_positions)
        if path:
            self.path = path[1:]  # quitar la posición inicial

    def on_draw(self):
        self.clear()

        # Dibujar mundo
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.gem_list.draw()
        self.player_list.draw()

        # HUD fijo
        self.camera_gui.use()
        total_time = self.final_time if self.final_time is not None else timeit.default_timer() - self.start_time

        arcade.draw_text(
            f"Tiempo: {total_time:.2f} s",
            20,
            self.window.height - 40,
            arcade.color.WHITE,
            font_size=16,
        )
        arcade.draw_text(
            f"Pasos: {self.steps}",
            20,
            self.window.height - 70,
            arcade.color.WHITE,
            font_size=16,
        )

        # Mensaje final
        if self.victory:
            arcade.draw_text(
                f"🎉 Gema encontrada en {total_time:.2f} s\nPasos: {self.steps}",
                self.window.width // 2,
                self.window.height // 2,
                arcade.color.YELLOW,
                font_size=30,
                anchor_x="center",
            )

    def on_update(self, delta_time):
        if self.victory:
            return

        # Movimiento paso a paso
        if self.path:
            next_row, next_col = self.path[0]
            target_x = next_col * SPRITE_SIZE + SPRITE_SIZE / 2
            target_y = next_row * SPRITE_SIZE + SPRITE_SIZE / 2

            dx = target_x - self.player_sprite.center_x
            dy = target_y - self.player_sprite.center_y

            if abs(dx) < MOVEMENT_SPEED and abs(dy) < MOVEMENT_SPEED:
                self.player_sprite.center_x = target_x
                self.player_sprite.center_y = target_y
                self.path.pop(0)
                self.steps += 1
            else:
                if dx > 0:
                    self.player_sprite.center_x += MOVEMENT_SPEED
                elif dx < 0:
                    self.player_sprite.center_x -= MOVEMENT_SPEED
                if dy > 0:
                    self.player_sprite.center_y += MOVEMENT_SPEED
                elif dy < 0:
                    self.player_sprite.center_y -= MOVEMENT_SPEED

        # Colisión con gema
        hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.gem_list)
        if hit_list:
            for gem in hit_list:
                gem.remove_from_sprite_lists()
            self.victory = True
            self.final_time = timeit.default_timer() - self.start_time  # ⏱ guardar tiempo final
            print(f"🎉 Gema encontrada en {self.final_time:.2f} s con {self.steps} pasos")

        # Scroll cámara
        self.scroll_to_player(CAMERA_SPEED)

    def scroll_to_player(self, camera_speed):
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(
            self.camera_sprites.position,
            position,
            camera_speed,
        )


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = InstructionView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
