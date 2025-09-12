import arcade
import random
from dataclasses import dataclass
from typing import List, Tuple

# ===================== CONFIGURACIÓN GENERAL =====================
SCREEN_TITLE = "PacGPT5"
TILE_SIZE = 32
MOVEMENT_SPEED = 4
POWER_TIME = 7.0

# Mapa: # pared, . punto, o power pellet, P pacman start, ' ' vacío
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


# ===================== FUNCIONES AUXILIARES =====================
def grid_to_pixel(col: int, row: int) -> Tuple[int, int]:
    x = col * TILE_SIZE + TILE_SIZE // 2
    y = (ROWS - row - 1) * TILE_SIZE + TILE_SIZE // 2
    return x, y


def pixel_to_grid(x: float, y: float) -> Tuple[int, int]:
    col = int(x // TILE_SIZE)
    row_from_bottom = int(y // TILE_SIZE)
    row = ROWS - row_from_bottom - 1
    return col, row


def is_center_of_cell(sprite: arcade.Sprite) -> bool:
    col, row = pixel_to_grid(sprite.center_x, sprite.center_y)
    cx, cy = grid_to_pixel(col, row)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2


# ===================== SPRITE PACMAN =====================
class Pacman(arcade.Sprite):
    def __init__(self, col: int, row: int):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(
            TILE_SIZE, arcade.color.WHITE, 255
        )
        self.color = arcade.color.YELLOW
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.current_dir = (0, 0)
        self.desired_dir = (0, 0)
        self.score = 0

    def set_direction(self, dx: int, dy: int):
        self.desired_dir = (dx, dy)

    def update_move(self, walls_grid):
        if is_center_of_cell(self):
            if self.can_move(self.desired_dir, walls_grid):
                self.current_dir = self.desired_dir
            if not self.can_move(self.current_dir, walls_grid):
                self.current_dir = (0, 0)

            col, row = pixel_to_grid(self.center_x, self.center_y)
            cx, cy = grid_to_pixel(col, row)
            self.center_x, self.center_y = cx, cy

        self.center_x += self.current_dir[0] * MOVEMENT_SPEED
        self.center_y += self.current_dir[1] * MOVEMENT_SPEED

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        if dx == 0 and dy == 0:
            return True
        col, row = pixel_to_grid(self.center_x, self.center_y)
        target_col = col + dx
        target_row = row - dy
        if target_col < 0 or target_col >= COLS or target_row < 0 or target_row >= ROWS:
            return False
        return walls_grid[target_row][target_col] == 0


# ===================== JUEGO PRINCIPAL =====================
class PacGPT5(arcade.Window):
    def __init__(self, autopilot=False):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1 / 60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.pacman: Pacman | None = None
        self.walls_grid = []
        self.state = "PLAY"
        self.autopilot = autopilot
        self.autopilot_timer = 0

    def setup(self):
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.state = "PLAY"
        self.walls_grid = [[0] * COLS for _ in range(ROWS)]

        pacman_positions = []

        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_pixel(c, r)
                if ch == "#":
                    wall = arcade.SpriteSolidColor(
                        TILE_SIZE, TILE_SIZE, arcade.color.DARK_BLUE
                    )
                    wall.center_x = x
                    wall.center_y = y
                    self.wall_list.append(wall)
                    self.walls_grid[r][c] = 1
                elif ch == ".":
                    pellet = arcade.SpriteSolidColor(6, 6, arcade.color.WHITE)
                    pellet.center_x = x
                    pellet.center_y = y
                    self.pellet_list.append(pellet)
                elif ch == "o":
                    power = arcade.SpriteSolidColor(14, 14, arcade.color.ORANGE_PEEL)
                    power.center_x = x
                    power.center_y = y
                    self.power_list.append(power)
                elif ch == "P":
                    pacman_positions.append((c, r))

        if pacman_positions:
            col, row = pacman_positions[0]
            self.pacman = Pacman(col, row)
        else:
            self.pacman = Pacman(COLS // 2, ROWS // 2)

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()
        if self.pacman:
            rect_p = arcade.rect.XYWH(
                self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE
            )
            arcade.draw_rect_filled(rect_p, self.pacman.color)

        if self.pacman:
            arcade.draw_text(
                f"Score: {self.pacman.score}",
                10,
                SCREEN_HEIGHT - 22,
                arcade.color.YELLOW,
                14,
            )

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return

        # ===== Autopiloto con BFS =====
        if self.autopilot:
            self.autopilot_timer += delta_time
            if self.autopilot_timer > 0.15:
                self.autopilot_timer = 0
                col, row = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)

                targets = (
                    [pixel_to_grid(p.center_x, p.center_y) for p in self.pellet_list]
                    + [pixel_to_grid(p.center_x, p.center_y) for p in self.power_list]
                )

                if targets:
                    target = min(
                        targets, key=lambda t: abs(t[0] - col) + abs(t[1] - row)
                    )
                    path = self._bfs_path((col, row), target)
                    if len(path) > 1:
                        next_col, next_row = path[1]
                        dx = next_col - col
                        dy = next_row - row
                        self.pacman.set_direction(dx, -dy)

        self.pacman.update_move(self.walls_grid)

        pellets_hit = arcade.check_for_collision_with_list(
            self.pacman, self.pellet_list
        )
        for p in pellets_hit:
            p.remove_from_sprite_lists()
            self.pacman.score += 10

        powers_hit = arcade.check_for_collision_with_list(self.pacman, self.power_list)
        for pw in powers_hit:
            pw.remove_from_sprite_lists()
            self.pacman.score += 50

        if len(self.pellet_list) == 0 and len(self.power_list) == 0:
            self.state = "WIN"

    def _bfs_path(self, start, goal):
        from collections import deque

        queue = deque([(start, [])])
        visited = {start}
        while queue:
            (c, r), path = queue.popleft()
            if (c, r) == goal:
                return path + [(c, r)]
            for dc, dr in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nc, nr = c + dc, r + dr
                if (
                    0 <= nc < COLS
                    and 0 <= nr < ROWS
                    and self.walls_grid[nr][nc] == 0
                    and (nc, nr) not in visited
                ):
                    queue.append(((nc, nr), path + [(c, r)]))
                    visited.add((nc, nr))
        return [start]

    def on_key_press(self, key, modifiers):
        if not self.pacman:
            return
        if key in (arcade.key.UP, arcade.key.W):
            self.pacman.set_direction(0, 1)
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.pacman.set_direction(0, -1)
        elif key in (arcade.key.LEFT, arcade.key.A):
            self.pacman.set_direction(-1, 0)
        elif key in (arcade.key.RIGHT, arcade.key.D):
            self.pacman.set_direction(1, 0)
        elif key == arcade.key.ESCAPE:
            arcade.close_window()


# ===================== CONSOLA MANUAL =====================
def play_console():
    maze = [list(row) for row in RAW_MAP]

    pacman_pos = None
    for r, row in enumerate(maze):
        for c, ch in enumerate(row):
            if ch == "P":
                pacman_pos = [r, c]
                maze[r][c] = " "
                break
        if pacman_pos:
            break

    score = 0

    def print_maze():
        for r, row in enumerate(maze):
            row_str = ""
            for c, ch in enumerate(row):
                if [r, c] == pacman_pos:
                    row_str += "P"
                else:
                    row_str += ch
            print(row_str)
        print(f"Score: {score}")

    print("=== PACMAN CONSOLA ===")
    print("Controles: WASD para moverse | Q o EXIT para salir")
    print_maze()

    while True:
        move = input("Movimiento (WASD o Q/EXIT para salir): ").lower()
        if move in ("q", "exit"):
            print("Juego terminado por el usuario.")
            break

        dr, dc = 0, 0
        if move == "w":
            dr, dc = -1, 0
        elif move == "s":
            dr, dc = 1, 0
        elif move == "a":
            dr, dc = 0, -1
        elif move == "d":
            dr, dc = 0, 1
        else:
            print("Tecla inválida.")
            continue

        nr, nc = pacman_pos[0] + dr, pacman_pos[1] + dc

        if maze[nr][nc] == "#":
            print("¡Choque con pared!")
            continue

        if maze[nr][nc] == ".":
            score += 10
            maze[nr][nc] = " "
        elif maze[nr][nc] == "o":
            score += 50
            maze[nr][nc] = " "

        pacman_pos = [nr, nc]

        print_maze()

        if not any(ch in (".", "o") for row in maze for ch in row):
            print("¡Ganaste! Todos los pellets fueron recogidos.")
            break


# ===================== MENÚ =====================
def menu():
    while True:
        print("\n=== PACMAN MENU ===")
        print("1. Jugar en arcade (autopiloto automático)")
        print("2. Jugar en arcade (manual con flechas o WASD)")
        print("3. Jugar en consola (manual con WASD)")
        print("0. Salir")
        choice = input("Selecciona una opción: ")

        if choice == "1":
            game = PacGPT5(autopilot=True)
            game.setup()
            arcade.run()
        elif choice == "2":
            game = PacGPT5(autopilot=False)
            game.setup()
            arcade.run()
        elif choice == "3":
            play_console()
        elif choice == "0":
            print("Adiós!")
            break
        else:
            print("Opción inválida.")


if __name__ == "__main__":
    menu()
