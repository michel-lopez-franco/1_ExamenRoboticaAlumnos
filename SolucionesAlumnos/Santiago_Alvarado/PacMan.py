import arcade
from dataclasses import dataclass
from typing import List, Tuple
import random
from collections import deque

# ===================== CONFIGURACIÓN GENERAL =====================
SCREEN_TITLE = "PacGPT5"
TILE_SIZE = 32
MOVEMENT_SPEED = 4
GHOST_SPEED = 2
POWER_TIME = 7.0

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


# ===================== FUNCIONES =====================
def grid_to_pixel(col: int, row: int) -> Tuple[int, int]:
    return col * TILE_SIZE + TILE_SIZE // 2, (ROWS - row - 1) * TILE_SIZE + TILE_SIZE // 2


def pixel_to_grid(x: float, y: float) -> Tuple[int, int]:
    return int(x // TILE_SIZE), ROWS - int(y // TILE_SIZE) - 1


def is_center_of_cell(sprite: arcade.Sprite) -> bool:
    col, row = pixel_to_grid(sprite.center_x, sprite.center_y)
    cx, cy = grid_to_pixel(col, row)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2


@dataclass
class GhostState:
    normal_color: Tuple[int, int, int]
    frightened_color: Tuple[int, int, int] = arcade.color.BLUE


# ===================== SPRITES =====================
class Pacman(arcade.Sprite):
    def __init__(self, col: int, row: int):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = arcade.color.YELLOW
        self.center_x, self.center_y = grid_to_pixel(col, row)
        self.current_dir = (0, 0)
        self.desired_dir = (0, 0)
        self.lives = 3
        self.score = 0
        self.power_timer = 0.0

    def set_direction(self, dx: int, dy: int):
        self.desired_dir = (dx, dy)

    def update_move(self, walls_grid):
        if is_center_of_cell(self):
            if self.can_move(self.desired_dir, walls_grid):
                self.current_dir = self.desired_dir
            if not self.can_move(self.current_dir, walls_grid):
                self.current_dir = (0, 0)
            col, row = pixel_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_pixel(col, row)
        self.center_x += self.current_dir[0] * MOVEMENT_SPEED
        self.center_y += self.current_dir[1] * MOVEMENT_SPEED

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        col, row = pixel_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        return (0 <= nc < COLS and 0 <= nr < ROWS and walls_grid[nr][nc] == 0)


class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, state: GhostState):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = state.normal_color
        self.center_x, self.center_y = grid_to_pixel(col, row)
        self.spawn_col, self.spawn_row = col, row
        self.state = state
        self.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.frightened = False
        self.dead = False

    def update_move(self, walls_grid, pacman: Pacman, delta_time: float):
        speed = GHOST_SPEED
        if is_center_of_cell(self):
            col, row = pixel_to_grid(self.center_x, self.center_y)

            if self.dead:
                target = (self.spawn_col, self.spawn_row)
                if (col, row) == target:
                    self.dead = False
                    self.frightened = False
                    self.color = self.state.normal_color
                else:
                    self.current_dir = self._step_towards(target, walls_grid)

            elif self.frightened:
                self.color = self.state.frightened_color
                self.current_dir = self._random_dir(walls_grid)

            else:
                self.color = self.state.normal_color
                self.current_dir = self._chase_dir(pacman, walls_grid)

            self.center_x, self.center_y = grid_to_pixel(col, row)

        self.center_x += self.current_dir[0] * speed
        self.center_y += self.current_dir[1] * speed

    def _step_towards(self, target_cell, walls_grid):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        tcol, trow = target_cell
        options = []
        if tcol > col: options.append((1, 0))
        if tcol < col: options.append((-1, 0))
        if trow > row: options.append((0, -1))
        if trow < row: options.append((0, 1))
        random.shuffle(options)
        for d in options:
            if self._can_dir(d, walls_grid):
                return d
        return self._random_dir(walls_grid)

    def _chase_dir(self, pacman: Pacman, walls_grid):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        pcol, prow = pixel_to_grid(pacman.center_x, pacman.center_y)
        dirs = []
        if pcol > col: dirs.append((1, 0))
        if pcol < col: dirs.append((-1, 0))
        if prow > row: dirs.append((0, -1))
        if prow < row: dirs.append((0, 1))
        random.shuffle(dirs)
        for d in dirs:
            if self._can_dir(d, walls_grid):
                return d
        return self._random_dir(walls_grid)

    def _random_dir(self, walls_grid):
        choices = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(choices)
        for d in choices:
            if self._can_dir(d, walls_grid):
                return d
        return (0, 0)

    def _can_dir(self, d, walls_grid):
        dx, dy = d
        col, row = pixel_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        return (0 <= nc < COLS and 0 <= nr < ROWS and walls_grid[nr][nc] == 0)

    def eaten(self):
        self.dead = True
        self.frightened = False
        self.color = arcade.color.GRAY


# ===================== JUEGO =====================
class PacGPT5(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1 / 60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts: List[Ghost] = []
        self.pacman: Pacman | None = None
        self.walls_grid = []
        self.state = "PLAY"
        self.autopilot = False
        self.autopilot_path: List[Tuple[int, int]] = []

    def setup(self):
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts = []
        self.state = "PLAY"
        self.walls_grid = [[0] * COLS for _ in range(ROWS)]
        self.autopilot_path.clear()
        pacman_positions, ghost_positions = [], []

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
                elif ch == "o":
                    power = arcade.SpriteSolidColor(14, 14, arcade.color.ORANGE_PEEL)
                    power.center_x, power.center_y = x, y
                    self.power_list.append(power)
                elif ch == "P":
                    pacman_positions.append((c, r))
                elif ch == "G":
                    ghost_positions.append((c, r))

        if pacman_positions:
            col, row = pacman_positions[0]
            self.pacman = Pacman(col, row)
        else:
            self.pacman = Pacman(COLS // 2, ROWS // 2)

        colors = [arcade.color.RED, arcade.color.GREEN, arcade.color.PURPLE, arcade.color.PINK]
        for idx, pos in enumerate(ghost_positions):
            col, row = pos
            ghost = Ghost(col, row, GhostState(colors[idx % len(colors)]))
            self.ghosts.append(ghost)

    # ===================== ZONAS DE PELIGRO =====================
    def get_danger_zones(self, radius: int = 2) -> set[Tuple[int, int]]:
        danger = set()
        for g in self.ghosts:
            if not g.dead and not g.frightened:
                col, row = pixel_to_grid(g.center_x, g.center_y)
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        nc, nr = col + dx, row + dy
                        if 0 <= nc < COLS and 0 <= nr < ROWS:
                            danger.add((nc, nr))
        return danger

    # ===================== AUTOPILOTO =====================
      # ===================== AUTOPILOTO =====================
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        danger = set()
        if self.pacman and self.pacman.power_timer <= 0:
            danger = self.get_danger_zones(radius=2)

        queue = deque([start])
        came_from = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            col, row = current
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nc, nr = col + dx, row + dy
                if (0 <= nc < COLS and 0 <= nr < ROWS and
                    self.walls_grid[nr][nc] == 0 and
                    (nc, nr) not in came_from and
                    (nc, nr) not in danger):
                    queue.append((nc, nr))
                    came_from[(nc, nr)] = current

        if goal not in came_from:
            # ⚠️ Plan B: ignorar zonas de peligro para no quedarse atorado
            return self.find_path_ignore_danger(start, goal)

        path = []
        cur = goal
        while cur != start:
            path.append(cur)
            cur = came_from[cur]
        path.reverse()
        return path

    def find_path_ignore_danger(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """BFS normal sin considerar zonas de peligro"""
        queue = deque([start])
        came_from = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            col, row = current
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nc, nr = col + dx, row + dy
                if (0 <= nc < COLS and 0 <= nr < ROWS and
                    self.walls_grid[nr][nc] == 0 and
                    (nc, nr) not in came_from):
                    queue.append((nc, nr))
                    came_from[(nc, nr)] = current

        if goal not in came_from:
            return []

        path = []
        cur = goal
        while cur != start:
            path.append(cur)
            cur = came_from[cur]
        path.reverse()
        return path


    def choose_next_target(self):
        if not self.pacman or (len(self.pellet_list) == 0 and len(self.power_list) == 0):
            return

        col, row = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)

        # Lista de objetivos: pellets normales + power pellets
        targets = [pixel_to_grid(p.center_x, p.center_y) for p in self.pellet_list] + \
                  [pixel_to_grid(pw.center_x, pw.center_y) for pw in self.power_list]

        best_path = []
        for target in targets:
            path = self.find_path((col, row), target)
            if path and (not best_path or len(path) < len(best_path)):
                best_path = path

        # ⚠️ Si no se encontró camino seguro, usar plan B (ignora peligros)
        if not best_path:
            for target in targets:
                path = self.find_path_ignore_danger((col, row), target)
                if path and (not best_path or len(path) < len(best_path)):
                    best_path = path

        self.autopilot_path = best_path

    # ===================== RESET =====================
    def _reset_positions(self):
        if not self.pacman:
            return
        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                if ch == "P":
                    x, y = grid_to_pixel(c, r)
                    self.pacman.center_x = x
                    self.pacman.center_y = y
                    self.pacman.current_dir = (0, 0)
                    self.pacman.desired_dir = (0, 0)
                    self.pacman.power_timer = 0.0
                    break
            else:
                continue
            break
        for g in self.ghosts:
            x, y = grid_to_pixel(g.spawn_col, g.spawn_row)
            g.center_x, g.center_y = x, y
            g.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            g.frightened = False
            g.dead = False
            g.color = g.state.normal_color

    # ===================== CICLO =====================
    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()
        if self.pacman:
            rect_p = arcade.rect.XYWH(self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_p, arcade.color.YELLOW)
        for g in self.ghosts:
            rect_g = arcade.rect.XYWH(g.center_x, g.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_g, g.color)
        if self.pacman:
            arcade.draw_text(f"Score: {self.pacman.score}", 10, SCREEN_HEIGHT - 22, arcade.color.YELLOW, 14)
            arcade.draw_text(f"Lives: {self.pacman.lives}", 10, SCREEN_HEIGHT - 40, arcade.color.RED, 14)
            if self.pacman.power_timer > 0:
                arcade.draw_text(f"Poder: {self.pacman.power_timer:0.1f}s", 10, SCREEN_HEIGHT - 58, arcade.color.ORANGE, 14)
        if self.state == "WIN":
            arcade.draw_text("Congratulations!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.RED, 40, anchor_x="center")
        arcade.draw_text(f"Autopiloto: {'ON' if self.autopilot else 'OFF'} (tecla A)",
                         SCREEN_WIDTH-10, 10, arcade.color.WHITE, 12, anchor_x="right")

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return
        if self.pacman.power_timer > 0:
            self.pacman.power_timer -= delta_time
            if self.pacman.power_timer <= 0:
                for g in self.ghosts:
                    if not g.dead:
                        g.frightened = False
                        g.color = g.state.normal_color
        self.pacman.update_move(self.walls_grid)
        for g in self.ghosts:
            g.update_move(self.walls_grid, self.pacman, delta_time)
        pellets_hit = arcade.check_for_collision_with_list(self.pacman, self.pellet_list)
        for p in pellets_hit:
            p.remove_from_sprite_lists()
            self.pacman.score += 10
        powers_hit = arcade.check_for_collision_with_list(self.pacman, self.power_list)
        if powers_hit:
            for pw in powers_hit:
                pw.remove_from_sprite_lists()
            self.pacman.power_timer = POWER_TIME
            for g in self.ghosts:
                if not g.dead:
                    g.frightened = True
                    g.color = g.state.frightened_color
        if len(self.pellet_list) == 0 and len(self.power_list) == 0:
            self.state = "WIN"
            return
        for g in self.ghosts:
            if arcade.check_for_collision(self.pacman, g):
                if g.frightened and not g.dead:
                    g.eaten()
                    self.pacman.score += 200
                elif not g.dead:
                    self.pacman.lives -= 1
                    if self.pacman.lives <= 0:
                        self.state = "LOSE"
                    else:
                        self._reset_positions()
                    return
        if self.autopilot and is_center_of_cell(self.pacman):
            if not self.autopilot_path:
                self.choose_next_target()
            if self.autopilot_path:
                next_col, next_row = self.autopilot_path.pop(0)
                pcol, prow = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
                dx = next_col - pcol
                dy = prow - next_row
                self.pacman.set_direction(dx, dy)

    def on_key_press(self, key, modifiers):
        if not self.pacman:
            return
        if key == arcade.key.UP: 
            self.pacman.set_direction(0, 1)
        elif key == arcade.key.DOWN: 
            self.pacman.set_direction(0, -1)
        elif key == arcade.key.LEFT: 
            self.pacman.set_direction(-1, 0)
        elif key == arcade.key.RIGHT: 
            self.pacman.set_direction(1, 0)
        elif key == arcade.key.A:
            self.autopilot = not self.autopilot
            self.autopilot_path.clear()
        elif key == arcade.key.N:        # 👈 Nueva tecla
            self.setup()                 # Reinicia el juego completo
        elif key == arcade.key.ESCAPE: 
            arcade.close_window()


def main():
    game = PacGPT5()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()
