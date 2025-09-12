"""
PacMan3_mod.py
--------------

Versión con inicio por SPACE, HUD arriba a la derecha y esquema de colores pedido:
- Fantasmas: rosa
- Laberinto y pellets: beige

Mantiene la evasión básica (zonas prohibidas alrededor de los fantasmas).
"""

import arcade, heapq, time, random, argparse
from dataclasses import dataclass
from typing import List, Tuple, Dict

# ===================== MAPAS =====================
RAW_MAPS = {
    "1": [
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
    ],
    "2": [
        "######################",
        "#........##..........#",
        "#.##.###.##.###.##..#",
        "#o##.............##o.#",
        "#....................#",
        "#.##.#.######.#.##.#.#",
        "#....#....##....#....#",
        "####.### #### ###.####",
        "#P.......G  G.......P#",
        "####.### #### ###.####",
        "#....#....##....#....#",
        "#.##.#.######.#.##.#.#",
        "#....................#",
        "#o##.............##o.#",
        "#.##.###.##.###.##..#",
        "#........##..........#",
        "######################",
    ],
    "3": [
        "######################",
        "#....................#",
        "#.####.########.####.#",
        "#o####.########.####o#",
        "#....................#",
        "####.####.##.####.####",
        "####.####.##.####.####",
        "#....................#",
        "#P....### GG ###....P#",
        "#....................#",
        "####.####.##.####.####",
        "####.####.##.####.####",
        "#....................#",
        "#o####.########.####o#",
        "#.####.########.####.#",
        "#....................#",
        "######################",
    ],
}

# ===================== CONFIG =====================
TILE = 32
SPEED = 4
GHOST_SPEED = 2
POWER_TIME = 7.0
TITLE = "Maze Run (mod)"

# Colores solicitados
COLOR_WALL = arcade.color.BEIGE
COLOR_PELLET = arcade.color.BEIGE
COLOR_POWER = arcade.color.BEIGE
COLOR_GHOST = arcade.color.PINK
COLOR_PAC = arcade.color.YELLOW

RAW_MAP = RAW_MAPS["1"]
ROWS, COLS = len(RAW_MAP), len(RAW_MAP[0])
WIDTH, HEIGHT = COLS * TILE, ROWS * TILE

# ===================== GRID UTILS =====================
def grid_to_px(c: int, r: int) -> Tuple[int, int]:
    return c * TILE + TILE // 2, (ROWS - r - 1) * TILE + TILE // 2

def px_to_grid(x: float, y: float) -> Tuple[int, int]:
    col = int(x // TILE)
    row_from_bottom = int(y // TILE)
    return col, ROWS - row_from_bottom - 1

def at_cell_center(sprite: arcade.Sprite) -> bool:
    col, row = px_to_grid(sprite.center_x, sprite.center_y)
    cx, cy = grid_to_px(col, row)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2

# ===================== A* con evasión =====================
def manhattan(a: Tuple[int,int], b: Tuple[int,int]) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def _neighbors(cell: Tuple[int,int], walls_grid, forbidden):
    c, r = cell
    for dc, dr in ((1,0),(-1,0),(0,1),(0,-1)):
        nc, nr = c+dc, r+dr
        if 0 <= nc < COLS and 0 <= nr < ROWS:
            if walls_grid[nr][nc] == 0 and (nc,nr) not in forbidden:
                yield (nc, nr)

def astar(start: Tuple[int,int], goal: Tuple[int,int], walls_grid, forbidden):
    if start == goal:
        return [start]
    openh = [(0, start)]
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
        for nb in _neighbors(cur, walls_grid, forbidden):
            tentative = g[cur] + 1
            if nb not in g or tentative < g[nb]:
                g[nb] = tentative
                f = tentative + manhattan(nb, goal)
                came[nb] = cur
                heapq.heappush(openh, (f, nb))
    return []

# ===================== SPRITES =====================
@dataclass
class GhostSkin:
    color: Tuple[int,int,int]

class Player(arcade.Sprite):
    def __init__(self, col: int, row: int):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE, arcade.color.WHITE, 255)
        self.color = COLOR_PAC
        x, y = grid_to_px(col, row)
        self.center_x, self.center_y = x, y
        self.dir_now = (0, 0)
        self.dir_want = (0, 0)
        self.lives = 3
        self.score = 0
        self.power_timer = 0
        self.invuln = 0

    def set_dir(self, dx: int, dy: int):
        self.dir_want = (dx, dy)

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        if dx == dy == 0:
            return True
        col, row = px_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            return False
        return walls_grid[nr][nc] == 0

    def step(self, walls_grid):
        if at_cell_center(self):
            if self.can_move(self.dir_want, walls_grid):
                self.dir_now = self.dir_want
            if not self.can_move(self.dir_now, walls_grid):
                self.dir_now = (0, 0)
            col, row = px_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_px(col, row)
        self.center_x += self.dir_now[0] * SPEED
        self.center_y += self.dir_now[1] * SPEED

class Chaser(arcade.Sprite):
    def __init__(self, col: int, row: int, skin: GhostSkin):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE, arcade.color.WHITE, 255)
        self.color = skin.color
        x, y = grid_to_px(col, row)
        self.center_x, self.center_y = x, y
        self.dir_now = random.choice([(1,0),(-1,0),(0,1),(0,-1)])

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        col, row = px_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            return False
        return walls_grid[nr][nc] == 0

    def step(self, walls_grid):
        if at_cell_center(self):
            col, row = px_to_grid(self.center_x, self.center_y)
            opts = [d for d in [(1,0),(-1,0),(0,1),(0,-1)] if self.can_move(d, walls_grid)]
            if self.dir_now in opts and len(opts) == 2:
                pass
            else:
                back = (-self.dir_now[0], -self.dir_now[1])
                valid = [d for d in opts if d != back] or opts
                self.dir_now = random.choice(valid)
            self.center_x, self.center_y = grid_to_px(col, row)
        self.center_x += self.dir_now[0] * GHOST_SPEED
        self.center_y += self.dir_now[1] * GHOST_SPEED

# ===================== solve() auxiliar (no gráfico) =====================
def solve(maze: List[str]) -> dict:
    start_time = time.time()
    rows, cols = len(maze), len(maze[0])
    walls = {(r,c) for r,row in enumerate(maze) for c,ch in enumerate(row) if ch == "#"}
    start = next(((r,c) for r,row in enumerate(maze) for c,ch in enumerate(row) if ch == "P"), None)
    pellets = [(r,c) for r,row in enumerate(maze) for c,ch in enumerate(row) if ch in ".o"]

    def astar_local(start, goal):
        openh=[(0,start)]; came={}; g={start:0}
        while openh:
            _,cur=heapq.heappop(openh)
            if cur==goal:
                path=[cur]
                while cur in came: cur=came[cur]; path.append(cur)
                return list(reversed(path))
            r,c=cur
            for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr,nc=r+dr,c+dc
                if not(0<=nr<rows and 0<=nc<cols): continue
                if (nr,nc) in walls: continue
                ng=g[cur]+1
                if (nr,nc) not in g or ng<g[(nr,nc)]:
                    g[(nr,nc)]=ng; came[(nr,nc)]=cur
                    heapq.heappush(openh,(ng+abs(nr-goal[0])+abs(nc-goal[1]), (nr,nc)))
        return []

    positions=[start]; moves=[]; current=start; rem=pellets[:]
    while rem:
        target=min(rem,key=lambda p: abs(current[0]-p[0])+abs(current[1]-p[1]))
        path=astar_local(current,target)
        if not path: break
        for i in range(1,len(path)):
            r0,c0=path[i-1]; r1,c1=path[i]
            dr,dc=r1-r0,c1-c0
            if dr==-1: moves.append("UP")
            elif dr==1: moves.append("DOWN")
            elif dc==-1: moves.append("LEFT")
            elif dc==1: moves.append("RIGHT")
        positions+=path[1:]; current=target; rem.remove(target)
    end_time=time.time()
    return {
        "positions":positions,
        "moves":moves,
        "steps":len(moves),
        "time":round(end_time-start_time,4)
    }

# ===================== VENTANA =====================
class Game(arcade.Window):
    def __init__(self):
        super().__init__(WIDTH, HEIGHT, TITLE, update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts: List[Chaser] = []
        self.player: Player | None = None
        self.walls_grid: List[List[int]] = []
        # Estados: "WAIT", "PLAY", "WIN", "LOSE"
        self.state = "WAIT"
        self.path: List[Tuple[int,int]] = []
        self.path_i = 0
        self.unreachable: List[Tuple[int,int]] = []

    def setup(self):
        # limpiar
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts = []
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]
        self.path, self.path_i, self.unreachable = [], 0, []
        pac_pos, ghost_pos = None, []

        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_px(c, r)
                if ch == "#":
                    wall = arcade.SpriteSolidColor(TILE, TILE, COLOR_WALL)
                    wall.center_x, wall.center_y = x, y
                    self.wall_list.append(wall)
                    self.walls_grid[r][c] = 1
                elif ch == ".":
                    pellet = arcade.SpriteSolidColor(6, 6, COLOR_PELLET)
                    pellet.center_x, pellet.center_y = x, y
                    self.pellet_list.append(pellet)
                elif ch == "o":
                    power = arcade.SpriteSolidColor(14, 14, COLOR_POWER)
                    power.center_x, power.center_y = x, y
                    self.power_list.append(power)
                elif ch == "P":
                    pac_pos = (c, r)
                elif ch == "G":
                    ghost_pos.append((c, r))

        if pac_pos:
            col, row = pac_pos
            self.player = Player(col, row)

        for (c, r) in ghost_pos:
            self.ghosts.append(Chaser(c, r, GhostSkin(COLOR_GHOST)))

        self.state = "WAIT"  # esperar SPACE

    # ---- Controles ----
    def on_key_press(self, symbol: int, modifiers: int):
        if not self.player:
            return
        if symbol == arcade.key.SPACE:
            if self.state in ("WAIT",):
                self.state = "PLAY"
            elif self.state in ("WIN", "LOSE"):
                self.setup()
                self.state = "PLAY"
        # Flechas (opcional, si quieres forzar dirección manual)
        if symbol == arcade.key.UP:
            self.player.set_dir(0, 1)
        elif symbol == arcade.key.DOWN:
            self.player.set_dir(0, -1)
        elif symbol == arcade.key.LEFT:
            self.player.set_dir(-1, 0)
        elif symbol == arcade.key.RIGHT:
            self.player.set_dir(1, 0)

    # ---- Dibujo ----
    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()

        # Jugador (dibujo circular para que se vea distinto)
        if self.player:
            arcade.draw_circle_filled(self.player.center_x, self.player.center_y, TILE//2 - 2, COLOR_PAC)

        # Fantasmas
        for g in self.ghosts:
            rect_g = arcade.rect.XYWH(g.center_x, g.center_y, TILE, TILE)
            arcade.draw_rect_filled(rect_g, g.color)

        # HUD arriba a la derecha
        if self.player:
            hud_x = WIDTH - 12
            y0 = HEIGHT - 16
            arcade.draw_text(f"Score: {self.player.score}", hud_x, y0, arcade.color.WHITE, 14, anchor_x="right")
            arcade.draw_text(f"Vidas: {self.player.lives}", hud_x, y0 - 20, arcade.color.WHITE, 14, anchor_x="right")

        # Mensajes de estado
        if self.state == "WAIT":
            arcade.draw_text("Presiona ESPACIO para iniciar", WIDTH/2, HEIGHT*0.55,
                             arcade.color.BEIGE, 24, anchor_x="center")
        elif self.state == "WIN":
            arcade.draw_text("¡GANASTE!", WIDTH/2, HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", WIDTH/2, HEIGHT/2, arcade.color.RED, 40, anchor_x="center")

    # ---- Lógica ----
    def on_update(self, dt: float):
        if self.state != "PLAY" or not self.player:
            return

        if self.player.invuln > 0:
            self.player.invuln -= dt

        # Construir zonas prohibidas (fantasmas y vecinos)
        if at_cell_center(self.player) and (not self.path or self.path_i >= len(self.path)):
            start = px_to_grid(self.player.center_x, self.player.center_y)
            forbidden = set()
            for g in self.ghosts:
                gc, gr = px_to_grid(g.center_x, g.center_y)
                for dc, dr in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                    nc, nr = gc+dc, gr+dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS:
                        forbidden.add((nc,nr))

            targets = [px_to_grid(s.center_x, s.center_y) for s in self.pellet_list] + \
                      [px_to_grid(s.center_x, s.center_y) for s in self.power_list]
            reachable = None
            for t in sorted(targets, key=lambda t: manhattan(start, t)):
                path = astar(start, t, self.walls_grid, forbidden)
                if path:
                    reachable = (t, path)
                    break
                else:
                    if t not in self.unreachable:
                        self.unreachable.append(t)
                        print(f"Pellet inaccesible (enemigos): {t}")

            if reachable:
                self.path = reachable[1]
                self.path_i = 1

        # Seguir camino
        if self.path and self.path_i < len(self.path):
            cur = px_to_grid(self.player.center_x, self.player.center_y)
            nxt = self.path[self.path_i]
            dx = nxt[0] - cur[0]
            dy = cur[1] - nxt[1]
            self.player.set_dir(dx, dy)
            if cur == nxt:
                self.path_i += 1

        # Movimiento
        self.player.step(self.walls_grid)

        # Comer pellets
        for p in arcade.check_for_collision_with_list(self.player, self.pellet_list):
            p.remove_from_sprite_lists()
            self.player.score += 10
        for pw in arcade.check_for_collision_with_list(self.player, self.power_list):
            pw.remove_from_sprite_lists()
            self.player.score += 50
            self.player.power_timer = POWER_TIME

        # Mover fantasmas
        for g in self.ghosts:
            g.step(self.walls_grid)

        # Colisiones con fantasmas
        for g in self.ghosts:
            if arcade.check_for_collision(self.player, g):
                if self.player.invuln <= 0:
                    self.player.lives -= 1
                    print(f"Colisión. Vidas: {self.player.lives}")
                    if self.player.lives <= 0:
                        self.state = "LOSE"
                        print("GAME OVER")
                        return
                    # Respawn en 'P'
                    for r, row in enumerate(RAW_MAP):
                        for c, ch in enumerate(row):
                            if ch == "P":
                                x, y = grid_to_px(c, r)
                                self.player.center_x, self.player.center_y = x, y
                    self.player.invuln = 2.0

        # Victoria
        if not self.pellet_list and not self.power_list and self.player.lives > 0:
            if self.unreachable:
                print(f"Quedaron pellets inaccesibles: {self.unreachable}")
            self.state = "WIN"

# ===================== MAIN =====================
def main():
    global RAW_MAP, ROWS, COLS, WIDTH, HEIGHT
    parser = argparse.ArgumentParser(description="Maze Run mod (inicia con SPACE)")
    parser.add_argument("--map", default="1", choices=RAW_MAPS.keys(),
                        help="Selecciona el mapa (1, 2 o 3)")
    args = parser.parse_args()

    RAW_MAP = RAW_MAPS[args.map]
    ROWS, COLS = len(RAW_MAP), len(RAW_MAP[0])
    # actualizar dimensiones
    global TILE
    WIDTH, HEIGHT = COLS * TILE, ROWS * TILE

    game = Game()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
