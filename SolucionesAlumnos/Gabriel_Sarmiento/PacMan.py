import arcade
from dataclasses import dataclass
from typing import List, Tuple, Deque, Dict, Optional
import random
from collections import deque
import heapq

ColorType = Tuple[int, int, int] | Tuple[int, int, int, int]

# ===================== CONFIGURACIÓN GENERAL =====================
SCREEN_TITLE = "PacGPT5"
TILE_SIZE = 32
SCALE = 1
MOVEMENT_SPEED = 4      # píxeles por frame (divide TILE_SIZE)
GHOST_SPEED = 2
POWER_TIME = 7.0
SCREEN_MARGIN = 32

# Mapa: # pared, . punto, o power pellet, P pacman start, G ghost start, ' ' vacío
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

# ===================== UTILIDADES GRID <-> PIXEL =====================
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

# ===================== A* PATHFINDING =====================
def neighbors(cell: Tuple[int,int], walls_grid, forbidden: set[Tuple[int,int]]):
    c, r = cell
    for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
        nc, nr = c+dc, r+dr
        if 0 <= nc < COLS and 0 <= nr < ROWS and walls_grid[nr][nc] == 0 and (nc,nr) not in forbidden:
            yield (nc, nr)

def manhattan(a: Tuple[int,int], b: Tuple[int,int]) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def astar(start: Tuple[int,int], goal: Tuple[int,int], walls_grid, forbidden: set[Tuple[int,int]]):
    if start == goal:
        return [start]
    openh = []
    heapq.heappush(openh, (0, start))
    came: Dict[Tuple[int,int], Tuple[int,int]] = {}
    g: Dict[Tuple[int,int], int] = {start: 0}
    while openh:
        _, cur = heapq.heappop(openh)
        if cur == goal:
            # reconstruir
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            path.reverse()
            return path
        for nb in neighbors(cur, walls_grid, forbidden):
            tentative = g[cur] + 1
            if nb not in g or tentative < g[nb]:
                g[nb] = tentative
                f = tentative + manhattan(nb, goal)
                came[nb] = cur
                heapq.heappush(openh, (f, nb))
    return []  # sin camino

# ===================== SPRITES =====================
@dataclass
class GhostState:
    normal_color: ColorType
    frightened_color: ColorType = arcade.color.BLUE

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
        if dx == 0 and dy == 0:
            return True
        col, row = pixel_to_grid(self.center_x, self.center_y)
        target_col = col + dx
        target_row = row - dy
        if target_col < 0 or target_col >= COLS or target_row < 0 or target_row >= ROWS:
            return False
        return walls_grid[target_row][target_col] == 0

class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, state: GhostState):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = state.normal_color
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.spawn_col = col
        self.spawn_row = row
        self.state = state
        self.current_dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.frightened = False
        self.dead = False
        self.change_counter = 0.0

    def update_move(self, walls_grid, pacman: Pacman, delta_time: float):
        speed = GHOST_SPEED
        self.change_counter += delta_time

        if self.dead:
            target = (self.spawn_col, self.spawn_row)
            if self._at_target(target):
                self.dead = False
                self.frightened = False
                self.color = self.state.normal_color
            else:
                self._move_towards(target, walls_grid, speed)
            # --- Corrección de posición ---
            self._clamp_position()
            return

        if self.frightened:
            self.color = self.state.frightened_color
            if self.change_counter > 0.4:
                self.current_dir = self._random_dir(walls_grid)
                self.change_counter = 0
        else:
            self.color = self.state.normal_color
            if self.change_counter > 0.3:
                self.current_dir = self._chase_dir(pacman, walls_grid)
                self.change_counter = 0

        if is_center_of_cell(self):
            if not self._can_dir(self.current_dir, walls_grid):
                self.current_dir = self._random_dir(walls_grid)
            col, row = pixel_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_pixel(col, row)

        self.center_x += self.current_dir[0] * speed
        self.center_y += self.current_dir[1] * speed

        # --- Corrección de posición ---
        self._clamp_position()

    def _clamp_position(self):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        # Solo corrige si está fuera del mapa
        if col < 0 or col >= COLS or row < 0 or row >= ROWS:
            col = max(0, min(COLS - 1, col))
            row = max(0, min(ROWS - 1, row))
            self.center_x, self.center_y = grid_to_pixel(col, row)

    def _at_target(self, target_cell):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        return (col, row) == target_cell

    def _move_towards(self, target_cell, walls_grid, speed):
        if is_center_of_cell(self):
            col, row = pixel_to_grid(self.center_x, self.center_y)
            tcol, trow = target_cell
            options = []
            if tcol > col: options.append((1,0))
            if tcol < col: options.append((-1,0))
            if trow > row: options.append((0,-1))
            if trow < row: options.append((0,1))
            random.shuffle(options)
            for d in options:
                if self._can_dir(d, walls_grid):
                    self.current_dir = d
                    break
            else:
                self.current_dir = self._random_dir(walls_grid)
        self.center_x += self.current_dir[0] * speed
        self.center_y += self.current_dir[1] * speed

    def _chase_dir(self, pacman: Pacman, walls_grid):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        pcol, prow = pixel_to_grid(pacman.center_x, pacman.center_y)
        path = astar((col, row), (pcol, prow), walls_grid, set())
        if len(path) >= 2:
            next_cell = path[1]
            dc = next_cell[0] - col
            dr = next_cell[1] - row
            # dr es en coordenadas de grid, convertir a dirección de pantalla
            return (dc, -dr)
        # Si no hay camino, moverse aleatoriamente
        return self._random_dir(walls_grid)

    def _random_dir(self, walls_grid):
        choices = [(1,0),(-1,0),(0,1),(0,-1)]
        random.shuffle(choices)
        for d in choices:
            if self._can_dir(d, walls_grid):
                return d
        return (0,0)

    def _can_dir(self, d, walls_grid):
        dx, dy = d
        col, row = pixel_to_grid(self.center_x, self.center_y)
        tcol = col + dx
        trow = row - dy
        if tcol < 0 or tcol >= COLS or trow < 0 or trow >= ROWS:
            return False
        return walls_grid[trow][tcol] == 0

    def eaten(self):
        self.dead = True
        self.frightened = False
        self.color = arcade.color.GRAY

# ===================== JUEGO PRINCIPAL =====================
class PacGPT5(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts: List[Ghost] = []
        self.pacman: Pacman | None = None
        self.walls_grid = []  # 1 pared, 0 libre
        self.state = "PLAY"   # PLAY, WIN, LOSE
        # Autonomía basada en A*
        self.auto_path: List[Tuple[int,int]] = []   # celdas por visitar
        self.auto_step_index = 0

    def setup(self):
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts = []
        self.state = "PLAY"
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]
        self.auto_path.clear()
        self.auto_step_index = 0

        pacman_positions = []
        ghost_positions = []

        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_pixel(c, r)
                if ch == "#":
                    wall = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, arcade.color.DARK_BLUE)
                    wall.center_x = x; wall.center_y = y
                    self.wall_list.append(wall)
                    self.walls_grid[r][c] = 1
                elif ch == ".":
                    pellet = arcade.SpriteSolidColor(6, 6, arcade.color.WHITE)
                    pellet.center_x = x; pellet.center_y = y
                    self.pellet_list.append(pellet)
                elif ch == "o":
                    power = arcade.SpriteSolidColor(14, 14, arcade.color.ORANGE_PEEL)
                    power.center_x = x; power.center_y = y
                    self.power_list.append(power)
                elif ch == "P":
                    pacman_positions.append((c, r))
                elif ch == "G":
                    ghost_positions.append((c, r))

        if pacman_positions:
            col, row = pacman_positions[0]
            self.pacman = Pacman(col, row)
            # otras P a pellets
            for extra in pacman_positions[1:]:
                c, r = extra
                px, py = grid_to_pixel(c, r)
                pellet = arcade.SpriteSolidColor(6, 6, arcade.color.WHITE)
                pellet.center_x = px; pellet.center_y = py
                self.pellet_list.append(pellet)
        else:
            self.pacman = Pacman(COLS//2, ROWS//2)

        colors = [arcade.color.RED, arcade.color.GREEN, arcade.color.PURPLE, arcade.color.PINK]
        for idx, pos in enumerate(ghost_positions):
            col, row = pos
            ghost = Ghost(col, row, GhostState(colors[idx % len(colors)]))
            self.ghosts.append(ghost)

    # ===================== RENDER =====================
    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()

        if self.pacman:
            rect_p = arcade.rect.XYWH(self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_p, getattr(self.pacman, "color", arcade.color.YELLOW))
        for g in self.ghosts:
            rect_g = arcade.rect.XYWH(g.center_x, g.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_g, getattr(g, "color", arcade.color.RED))

        if self.pacman:
            arcade.draw_text(f"Score: {self.pacman.score}", 10, SCREEN_HEIGHT-22, arcade.color.YELLOW, 14)
            arcade.draw_text(f"Vidas: {self.pacman.lives}", 10, SCREEN_HEIGHT-40, arcade.color.YELLOW, 14)
            if self.pacman.power_timer > 0:
                arcade.draw_text(f"Poder: {self.pacman.power_timer:0.1f}", 10, SCREEN_HEIGHT-58, arcade.color.ORANGE_PEEL, 14)

        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.RED, 40, anchor_x="center")

    # ===================== GAME LOOP =====================
    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return

        # Timers de poder
        if self.pacman.power_timer > 0:
            self.pacman.power_timer -= delta_time
            if self.pacman.power_timer <= 0:
                for g in self.ghosts:
                    if not g.dead:
                        g.frightened = False

        # ----- Autonomía Pac-Man: decidir camino con A* -----
        self._autopilot_update()

        # Mover Pac-Man
        self.pacman.update_move(self.walls_grid)

        # Mover fantasmas
        for g in self.ghosts:
            g.update_move(self.walls_grid, self.pacman, delta_time)

        # Comer pellets
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

        # Colisiones con fantasmas
        for g in self.ghosts:
            if arcade.check_for_collision(self.pacman, g):
                if self.pacman.power_timer > 0 and not g.dead:
                    g.eaten()
                    self.pacman.score += 200
                elif not g.dead:
                    # pierde vida
                    self.pacman.lives -= 1
                    if self.pacman.lives <= 0:
                        self.state = "LOSE"
                    self._reset_positions()
                    return

        # Victoria
        if len(self.pellet_list) == 0 and len(self.power_list) == 0:
            self.state = "WIN"

    # ---------- Autopiloto basado en A* ----------
    def _autopilot_update(self):
        """Elige objetivo más cercano y sigue el camino; replanifica si se acaba o si hay fantasma cercano."""
        if not self.pacman:
            return
        # Solo decidir paso cuando está centrado
        if not is_center_of_cell(self.pacman):
            return

        pcol, prow = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)

        # Si no hay camino o ya consumido el objetivo, replanificar
        need_plan = (not self.auto_path) or (self.auto_step_index >= len(self.auto_path))

        # Replanificar también si un fantasma está a 1 celda
        forbidden = set()
        for g in self.ghosts:
            gc, gr = pixel_to_grid(g.center_x, g.center_y)
            for dc, dr in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                nc, nr = gc+dc, gr+dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    forbidden.add((nc, nr))

        if (pcol, prow) in forbidden:
            need_plan = True

        if need_plan:
            target = self._nearest_food_cell((pcol, prow), forbidden)
            if target is None:
                self.auto_path = []
                self.pacman.set_direction(0, 0)
                return
            path = astar((pcol, prow), target, self.walls_grid, forbidden)
            if len(path) <= 1:
                self.auto_path = []
                self.pacman.set_direction(0, 0)
                return
            self.auto_path = path
            self.auto_step_index = 1  # el 0 es la celda actual

        # Siguiente celda del camino → dirección
        if self.auto_step_index < len(self.auto_path):
            nextc, nextr = self.auto_path[self.auto_step_index]
            dc = nextc - pcol
            dr = nextr - prow
            # convertir dr a dirección de pantalla (y arriba = dy positivo)
            self.pacman.set_direction(dc, -dr)
            self.auto_step_index += 1

    def _nearest_food_cell(self, start: Tuple[int,int], forbidden: set[Tuple[int,int]]):
        """Devuelve la celda (col,row) del pellet/power más cercano en pasos A* evitando 'forbidden'."""
        # Listado de celdas de comida
        targets: List[Tuple[int,int]] = []
        for s in self.pellet_list:
            targets.append(pixel_to_grid(s.center_x, s.center_y))
        for s in self.power_list:
            targets.append(pixel_to_grid(s.center_x, s.center_y))
        if not targets:
            return None

        best = None
        best_len = 10**9
        # Heurística: probar por distancia Manhattan primero para podar
        targets.sort(key=lambda t: manhattan(start, t))
        for t in targets[:200]:  # suficiente en este mapa
            path = astar(start, t, self.walls_grid, forbidden)
            if path:
                if len(path) < best_len:
                    best = t
                    best_len = len(path)
        return best

    def _reset_positions(self):
        if not self.pacman:
            return
        # Pacman a su spawn (primera P)
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
        # Fantasmas
        for g in self.ghosts:
            x, y = grid_to_pixel(g.spawn_col, g.spawn_row)
            g.center_x = x; g.center_y = y
            g.dead = False
            g.frightened = False
            g.current_dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            g.color = g.state.normal_color
        # Reset plan
        self.auto_path.clear()
        self.auto_step_index = 0

    # ===================== INPUT OPCIONAL =====================
    def on_key_press(self, key, modifiers):
        if key == arcade.key.R and self.state != "PLAY":
            self.setup()
        elif key == arcade.key.ESCAPE:
            arcade.close_window()

# ===================== MAIN =====================
def main():
    game = PacGPT5()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()