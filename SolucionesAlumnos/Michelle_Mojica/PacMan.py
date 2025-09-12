import arcade
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import random
import heapq

ColorType = Tuple[int, int, int] | Tuple[int, int, int, int]

# ===================== CONFIGURACIÓN =====================
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

# ===================== UTILIDADES GRID/PIXEL =====================
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

def clamp_to_bounds(sprite: arcade.Sprite):
    half = TILE_SIZE // 2
    sprite.center_x = max(half, min(SCREEN_WIDTH - half, sprite.center_x))
    sprite.center_y = max(half, min(SCREEN_HEIGHT - half, sprite.center_y))

# ===================== A* =====================
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
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return list(reversed(path))
        for nb in neighbors(cur, walls_grid, forbidden):
            ng = g[cur] + 1
            if nb not in g or ng < g[nb]:
                g[nb] = ng
                f = ng + manhattan(nb, goal)
                came[nb] = cur
                heapq.heappush(openh, (f, nb))
    return []

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
        self.center_x, self.center_y = grid_to_pixel(col, row)
        self.current_dir = (0, 0)
        self.desired_dir = (0, 0)
        self.lives = 3
        self.score = 0
        self.power_timer = 0.0

    def set_direction(self, dx: int, dy: int):
        self.desired_dir = (dx, dy)

    def can_move_dir(self, direction, walls_grid) -> bool:
        dx, dy = direction
        col, row = pixel_to_grid(self.center_x, self.center_y)
        tcol = col + dx
        trow = row - dy
        if tcol < 0 or tcol >= COLS or trow < 0 or trow >= ROWS:
            return False
        return walls_grid[trow][tcol] == 0

    def update_move(self, walls_grid):
        if is_center_of_cell(self):
            if self.can_move_dir(self.desired_dir, walls_grid):
                self.current_dir = self.desired_dir
            if not self.can_move_dir(self.current_dir, walls_grid):
                self.current_dir = (0, 0)
            col, row = pixel_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_pixel(col, row)

        self.center_x += self.current_dir[0] * MOVEMENT_SPEED
        self.center_y += self.current_dir[1] * MOVEMENT_SPEED
        clamp_to_bounds(self)

class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, state: GhostState):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = state.normal_color
        self.center_x, self.center_y = grid_to_pixel(col, row)
        self.spawn_col = col
        self.spawn_row = row
        self.state = state
        self.current_dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.frightened = False
        self.dead = False
        self.change_counter = 0.0

    def _can_dir(self, d, walls_grid):
        dx, dy = d
        col, row = pixel_to_grid(self.center_x, self.center_y)
        tcol = col + dx
        trow = row - dy
        if tcol < 0 or tcol >= COLS or trow < 0 or trow >= ROWS:
            return False
        return walls_grid[trow][tcol] == 0

    def _random_dir(self, walls_grid):
        choices = [(1,0),(-1,0),(0,1),(0,-1)]
        random.shuffle(choices)
        for d in choices:
            if self._can_dir(d, walls_grid):
                return d
        return (0,0)

    def _chase_dir(self, pacman, walls_grid):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        pcol, prow = pixel_to_grid(pacman.center_x, pacman.center_y)
        dirs = []
        if pcol > col: dirs.append((1,0))
        if pcol < col: dirs.append((-1,0))
        if prow > row: dirs.append((0,-1))
        if prow < row: dirs.append((0,1))
        random.shuffle(dirs)
        for d in dirs:
            if self._can_dir(d, walls_grid):
                return d
        return self._random_dir(walls_grid)

    def _at_target(self, target_cell):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        return (col, row) == target_cell

    def _move_towards_spawn(self, walls_grid, speed):
        # mover paso a paso sin atravesar paredes
        if is_center_of_cell(self):
            col, row = pixel_to_grid(self.center_x, self.center_y)
            tcol, trow = self.spawn_col, self.spawn_row
            opts = []
            if tcol > col: opts.append((1,0))
            if tcol < col: opts.append((-1,0))
            if trow > row: opts.append((0,-1))
            if trow < row: opts.append((0,1))
            random.shuffle(opts)
            for d in opts:
                if self._can_dir(d, walls_grid):
                    self.current_dir = d
                    break
            else:
                self.current_dir = self._random_dir(walls_grid)

        self.center_x += self.current_dir[0] * speed
        self.center_y += self.current_dir[1] * speed
        clamp_to_bounds(self)

    def update_move(self, walls_grid, pacman, delta_time: float):
        speed = GHOST_SPEED
        self.change_counter += delta_time

        if self.dead:
            target = (self.spawn_col, self.spawn_row)
            if self._at_target(target):
                self.dead = False
                self.frightened = False
                self.color = self.state.normal_color
                self.current_dir = self._random_dir(walls_grid)
            else:
                self._move_towards_spawn(walls_grid, speed)
            return

        if is_center_of_cell(self):
            if self.frightened:
                self.color = self.state.frightened_color
                self.current_dir = self._random_dir(walls_grid)
            else:
                self.color = self.state.normal_color
                if self.change_counter > 0.25:
                    self.current_dir = self._chase_dir(pacman, walls_grid)
                    self.change_counter = 0.0
            if not self._can_dir(self.current_dir, walls_grid):
                self.current_dir = self._random_dir(walls_grid)
            # snap exacto
            col, row = pixel_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_pixel(col, row)

        self.center_x += self.current_dir[0] * speed
        self.center_y += self.current_dir[1] * speed
        clamp_to_bounds(self)

    def eaten(self):
        self.dead = True
        self.frightened = False
        self.color = arcade.color.GRAY

# ===================== JUEGO =====================
class PacGPT5(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts: List[Ghost] = []
        self.pacman: Optional[Pacman] = None
        self.walls_grid = []
        self.state = "PLAY"
        self.auto_path: List[Tuple[int,int]] = []
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
            c0, r0 = pacman_positions[0]
            self.pacman = Pacman(c0, r0)
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
            self.ghosts.append(Ghost(col, row, GhostState(colors[idx % len(colors)])))

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()

        if self.pacman:
            rect_p = arcade.rect.XYWH(self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_p, self.pacman.color)
        for g in self.ghosts:
            rect_g = arcade.rect.XYWH(g.center_x, g.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_g, g.color)

        if self.pacman:
            arcade.draw_text(f"Score: {self.pacman.score}", 10, SCREEN_HEIGHT-22, arcade.color.YELLOW, 14)
            arcade.draw_text(f"Vidas: {self.pacman.lives}", 10, SCREEN_HEIGHT-40, arcade.color.YELLOW, 14)
            if self.pacman.power_timer > 0:
                arcade.draw_text(f"Poder: {self.pacman.power_timer:0.1f}", 10, SCREEN_HEIGHT-58, arcade.color.ORANGE_PEEL, 14)

        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.RED, 40, anchor_x="center")

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return

        if self.pacman.power_timer > 0:
            self.pacman.power_timer -= delta_time
            if self.pacman.power_timer <= 0:
                for g in self.ghosts:
                    if not g.dead:
                        g.frightened = False

        self._autopilot_update()
        self.pacman.update_move(self.walls_grid)

        for g in self.ghosts:
            g.update_move(self.walls_grid, self.pacman, delta_time)

        for p in arcade.check_for_collision_with_list(self.pacman, self.pellet_list):
            p.remove_from_sprite_lists()
            self.pacman.score += 10

        if arcade.check_for_collision_with_list(self.pacman, self.power_list):
            for pw in arcade.check_for_collision_with_list(self.pacman, self.power_list):
                pw.remove_from_sprite_lists()
            self.pacman.power_timer = POWER_TIME
            for g in self.ghosts:
                if not g.dead:
                    g.frightened = True

        for g in self.ghosts:
            if arcade.check_for_collision(self.pacman, g):
                if self.pacman.power_timer > 0 and not g.dead:
                    g.eaten()
                    self.pacman.score += 200
                elif not g.dead:
                    self.pacman.lives -= 1
                    if self.pacman.lives <= 0:
                        self.state = "LOSE"
                    self._reset_positions()
                    return

        if len(self.pellet_list) == 0 and len(self.power_list) == 0:
            self.state = "WIN"

    # ---------- Autopiloto A* ----------
    def _autopilot_update(self):
        if not self.pacman or not is_center_of_cell(self.pacman):
            return
        pcol, prow = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)

        forbidden = set()
        for g in self.ghosts:
            gc, gr = pixel_to_grid(g.center_x, g.center_y)
            for dc, dr in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                nc, nr = gc+dc, gr+dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    forbidden.add((nc, nr))

        if not self.auto_path or self.auto_step_index >= len(self.auto_path) or (pcol, prow) in forbidden:
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
            self.auto_step_index = 1

        nextc, nextr = self.auto_path[self.auto_step_index]
        dc = nextc - pcol
        dr = nextr - prow
        self.pacman.set_direction(dc, -dr)
        self.auto_step_index += 1

    def _nearest_food_cell(self, start: Tuple[int,int], forbidden: set[Tuple[int,int]]):
        targets: List[Tuple[int,int]] = []
        for s in self.pellet_list:
            targets.append(pixel_to_grid(s.center_x, s.center_y))
        for s in self.power_list:
            targets.append(pixel_to_grid(s.center_x, s.center_y))
        if not targets:
            return None
        targets.sort(key=lambda t: manhattan(start, t))
        best = None; best_len = 10**9
        for t in targets[:200]:
            path = astar(start, t, self.walls_grid, forbidden)
            if path and len(path) < best_len:
                best, best_len = t, len(path)
        return best

    def _reset_positions(self):
        if not self.pacman:
            return
        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                if ch == "P":
                    self.pacman.center_x, self.pacman.center_y = grid_to_pixel(c, r)
                    self.pacman.current_dir = (0, 0)
                    self.pacman.desired_dir = (0, 0)
                    self.pacman.power_timer = 0.0
                    break
            else:
                continue
            break
        for g in self.ghosts:
            g.center_x, g.center_y = grid_to_pixel(g.spawn_col, g.spawn_row)
            g.dead = False
            g.frightened = False
            g.current_dir = g._random_dir(self.walls_grid)
            g.color = g.state.normal_color
        self.auto_path.clear()
        self.auto_step_index = 0

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
