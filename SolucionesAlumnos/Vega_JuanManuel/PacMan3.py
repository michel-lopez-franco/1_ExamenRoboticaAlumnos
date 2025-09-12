import arcade
import random
from typing import List, Tuple
from collections import deque

# ===================== CONFIGURACIÓN GENERAL =====================
SCREEN_TITLE = "PacGPT5"
TILE_SIZE = 32
MOVEMENT_SPEED = 4
GHOST_SPEED = 2
SCREEN_MARGIN = 32
POWER_TIME = 7.0
EXTRA_LIFE_DURATION = 5.0
EXTRA_LIFE_INTERVAL = 10.0

RAW_MAP = [
    "######################",
    "#........##..........#",
    "#.##.###.##.###.##..#",
    "#o##.###.##.###.##o.#",
    "#....................#",
    "#.##.#.######.#.##.#.#",
    "#....#....##....#....#",
    "####.### #### ###.####",
    "#P.......G  G.......P#",
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
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = arcade.color.YELLOW
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.current_dir = (0, 0)
        self.desired_dir = (0, 0)
        self.score = 0
        self.lives = 3
        self.powered_up = False
        self.power_timer = 0

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


# ===================== SPRITE FANTASMA =====================
class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, color):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.normal_color = color
        self.color = self.normal_color
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.spawn_col = col
        self.spawn_row = row
        self.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.frightened = False

    def update_move(self, pacman, walls_grid):
        if is_center_of_cell(self):
            col, row = pixel_to_grid(self.center_x, self.center_y)
            pcol, prow = pixel_to_grid(pacman.center_x, pacman.center_y)
            dirs = []
            if pcol > col:
                dirs.append((1, 0))
            if pcol < col:
                dirs.append((-1, 0))
            if prow > row:
                dirs.append((0, -1))
            if prow < row:
                dirs.append((0, 1))
            random.shuffle(dirs)
            for d in dirs:
                if self._can_dir(d, walls_grid):
                    self.current_dir = d
                    break
            col, row = pixel_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_pixel(col, row)
        self.center_x += self.current_dir[0] * GHOST_SPEED
        self.center_y += self.current_dir[1] * GHOST_SPEED

    def _can_dir(self, d, walls_grid):
        dx, dy = d
        col, row = pixel_to_grid(self.center_x, self.center_y)
        tcol = col + dx
        trow = row - dy
        if tcol < 0 or tcol >= COLS or trow < 0 or trow >= ROWS:
            return False
        return walls_grid[trow][tcol] == 0

    def reset_position(self):
        x, y = grid_to_pixel(self.spawn_col, self.spawn_row)
        self.center_x = x
        self.center_y = y
        self.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.color = self.normal_color
        self.frightened = False


# ===================== JUEGO PRINCIPAL =====================
class PacGPT5(arcade.Window):
    def __init__(self, autopilot=True):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1 / 60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.extra_life: arcade.Sprite | None = None
        self.extra_life_timer = 0
        self.extra_life_spawn_timer = EXTRA_LIFE_INTERVAL
        self.pacman: Pacman | None = None
        self.ghosts: List[Ghost] = []
        self.walls_grid = []
        self.state = "PLAY"
        self.autopilot = autopilot
        self.start_pos = None
        self.evasion_timer = 3.0  # tiempo inicial de evasión

    def setup(self):
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.extra_life = None
        self.extra_life_timer = 0
        self.extra_life_spawn_timer = EXTRA_LIFE_INTERVAL
        self.ghosts = []
        self.state = "PLAY"
        self.walls_grid = [[0] * COLS for _ in range(ROWS)]

        pacman_positions = []
        ghost_positions = []

        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_pixel(c, r)
                if ch == "#":
                    wall = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, arcade.color.DARK_BLUE)
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
                elif ch == "G":
                    ghost_positions.append((c, r))

        if pacman_positions:
            col, row = pacman_positions[0]
            self.pacman = Pacman(col, row)
            self.start_pos = (col, row)

        colors = [arcade.color.RED, arcade.color.GREEN, arcade.color.PINK, arcade.color.ORANGE]
        for idx, (c, r) in enumerate(ghost_positions):
            ghost = Ghost(c, r, colors[idx % len(colors)])
            self.ghosts.append(ghost)

    # ===================== AUTOPILOT BFS PENALIZADO =====================
    def _bfs_path_penalized(self, start, goal, ghost_positions):
        queue = deque([(start, [], 0)])
        visited = {start}
        while queue:
            (c, r), path, danger_score = queue.popleft()
            if (c, r) == goal:
                return path + [(c, r)], danger_score
            for dc, dr in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS and self.walls_grid[nr][nc] == 0 and (nc, nr) not in visited:
                    extra_danger = 0
                    for gx, gy in ghost_positions:
                        dist = abs(gx - nc) + abs(gy - nr)
                        if dist <= 2:
                            extra_danger += (3 - dist) * 10
                    queue.append(((nc, nr), path + [(c, r)], danger_score + extra_danger))
                    visited.add((nc, nr))
        return [start], float("inf")

    # ===================== CICLO =====================
    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return

        # Timer de powerup
        if self.pacman.powered_up:
            self.pacman.power_timer -= delta_time
            if self.pacman.power_timer <= 0:
                self.pacman.powered_up = False
                for g in self.ghosts:
                    g.frightened = False
                    g.color = g.normal_color

        # Vidas extra
        self.extra_life_spawn_timer -= delta_time
        if self.extra_life_spawn_timer <= 0:
            self._spawn_extra_life()
            self.extra_life_spawn_timer = EXTRA_LIFE_INTERVAL
        if self.extra_life:
            self.extra_life_timer -= delta_time
            if self.extra_life_timer <= 0:
                self.extra_life = None

        # Autopilot
        if self.autopilot and is_center_of_cell(self.pacman):
            col, row = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
            ghost_positions = [pixel_to_grid(g.center_x, g.center_y) for g in self.ghosts]
            targets = [pixel_to_grid(p.center_x, p.center_y) for p in self.pellet_list] + \
                      [pixel_to_grid(p.center_x, p.center_y) for p in self.power_list]
            best_path, best_score = None, float("inf")
            for t in targets:
                path, score = self._bfs_path_penalized((col, row), t, ghost_positions)
                if len(path) > 1 and score < best_score:
                    best_score, best_path = score, path
            if best_path:
                next_col, next_row = best_path[1]
                dx = next_col - col
                dy = next_row - row
                self.pacman.set_direction(dx, -dy)

        # Movimiento
        self.pacman.update_move(self.walls_grid)
        for g in self.ghosts:
            g.update_move(self.pacman, self.walls_grid)

        # Colisiones
        if self.extra_life and arcade.check_for_collision(self.pacman, self.extra_life):
            self.pacman.lives += 1
            self.extra_life = None

        for p in arcade.check_for_collision_with_list(self.pacman, self.pellet_list):
            p.remove_from_sprite_lists()
            self.pacman.score += 10
        for pw in arcade.check_for_collision_with_list(self.pacman, self.power_list):
            pw.remove_from_sprite_lists()
            self.pacman.score += 50
            self.pacman.powered_up = True
            self.pacman.power_timer = POWER_TIME
            for g in self.ghosts:
                g.frightened = True
                g.color = arcade.color.BLUE

        for g in self.ghosts:
            if arcade.check_for_collision(self.pacman, g):
                if g.frightened:
                    g.reset_position()
                    self.pacman.score += 200
                else:
                    self.pacman.lives -= 1
                    if self.pacman.lives <= 0:
                        self.state = "LOSE"
                    else:
                        self._reset_positions()
                break

        if len(self.pellet_list) == 0 and len(self.power_list) == 0:
            self.state = "WIN"

    def _spawn_extra_life(self):
        if self.extra_life is not None:
            return
        while True:
            c, r = random.randint(0, COLS - 1), random.randint(0, ROWS - 1)
            if self.walls_grid[r][c] == 0:
                x, y = grid_to_pixel(c, r)
                self.extra_life = arcade.SpriteSolidColor(18, 18, arcade.color.GREEN)
                self.extra_life.center_x, self.extra_life.center_y = x, y
                self.extra_life_timer = EXTRA_LIFE_DURATION
                break

    def _reset_positions(self):
        if self.pacman and self.start_pos:
            col, row = self.start_pos
            self.pacman.center_x, self.pacman.center_y = grid_to_pixel(col, row)
            self.pacman.current_dir = (0, 0)
            self.pacman.desired_dir = (0, 0)
            self.pacman.powered_up = False
            self.pacman.power_timer = 0
        for g in self.ghosts:
            g.reset_position()

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()
        if self.extra_life:
            rect_life = arcade.rect.XYWH(self.extra_life.center_x, self.extra_life.center_y, 18, 18)
            arcade.draw_rect_filled(rect_life, arcade.color.GREEN)
        if self.pacman:
            rect_p = arcade.rect.XYWH(self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_p, self.pacman.color)
        for g in self.ghosts:
            rect_g = arcade.rect.XYWH(g.center_x, g.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_g, g.color)
        if self.pacman:
            arcade.draw_text(f"Score: {self.pacman.score}", 10, SCREEN_HEIGHT - 22, arcade.color.YELLOW, 14)
            arcade.draw_text(f"Vidas: {self.pacman.lives}", 10, SCREEN_HEIGHT - 40, arcade.color.YELLOW, 14)
        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, arcade.color.RED, 40, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if not self.pacman:
            return
        if not self.autopilot:
            if key in (arcade.key.UP, arcade.key.W):
                self.pacman.set_direction(0, 1)
            elif key in (arcade.key.DOWN, arcade.key.S):
                self.pacman.set_direction(0, -1)
            elif key in (arcade.key.LEFT, arcade.key.A):
                self.pacman.set_direction(-1, 0)
            elif key in (arcade.key.RIGHT, arcade.key.D):
                self.pacman.set_direction(1, 0)
        if key == arcade.key.ESCAPE:
            arcade.close_window()


# ===================== MENÚ =====================
def menu():
    while True:
        print("\n=== PACMAN MENU ===")
        print("1. Jugar en arcade (autopiloto)")
        print("2. Jugar en arcade (manual)")
        print("0. Salir")
        choice = input("Selecciona una opción: ")
        if choice == "1":
            game = PacGPT5(autopilot=True); game.setup(); arcade.run()
        elif choice == "2":
            game = PacGPT5(autopilot=False); game.setup(); arcade.run()
        elif choice == "0":
            print("Adiós!"); break
        else:
            print("Opción inválida.")


# ===================== MAIN =====================
if __name__ == "__main__":
    menu()
