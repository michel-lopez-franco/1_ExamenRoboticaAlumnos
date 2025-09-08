"""
PacMan3.py
----------

Extiende Pac-Man con evasión de enemigos.

==================== Estrategia ====================

- Evasión:
  * Los enemigos se consideran obstáculos dinámicos.
  * También se evita un "margen de seguridad": las celdas vecinas a cada fantasma se marcan como prohibidas.
  * El agente replantea su ruta en tiempo real (cada vez que llega al centro de una celda).

- Limitaciones:
  * No predice movimientos futuros de los enemigos, solo evita sus posiciones actuales y cercanas.
  * Puede darse el caso de que fantasmas bloqueen pellets → en ese caso se reporta como "inaccesible".

- Condiciones de fin:
  * WIN → todos los pellets recogidos y ≥1 vida.
  * LOSE → vidas = 0.
  * Parcial → quedan pellets inaccesibles por enemigos, se informa en consola.

- Consola:
  * Se registran colisiones con enemigos, vidas restantes.
  * Se informa si un pellet fue inaccesible.
  * Al final se informa estado final, ruta encontrada y pellets no alcanzados.

==================== Personalización añadida ====================

- Soporte para múltiples mapas seleccionables con el parámetro --map (1, 2 o 3).
- En la interfaz gráfica se muestra cuántos pellets quedan por recoger.
- Ejemplos con mini mapas en consola: uno exitoso y otro fallido.

Ejemplo de uso:
    python PacMan3.py --map 2
"""

import arcade, heapq, time, random, argparse
from dataclasses import dataclass
from typing import List, Tuple, Dict

# ===================== MAPAS DISPONIBLES =====================
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
SCREEN_TITLE = "PacGPT5 with Enemy Avoidance"
TILE_SIZE = 32
MOVEMENT_SPEED = 4
POWER_TIME = 7.0

RAW_MAP = RAW_MAPS["1"]
ROWS, COLS = len(RAW_MAP), len(RAW_MAP[0])
SCREEN_WIDTH, SCREEN_HEIGHT = COLS * TILE_SIZE, ROWS * TILE_SIZE

# ===================== GRID UTILS =====================
def grid_to_pixel(col: int, row: int) -> Tuple[int, int]:
    return col * TILE_SIZE + TILE_SIZE // 2, (ROWS - row - 1) * TILE_SIZE + TILE_SIZE // 2

def pixel_to_grid(x: float, y: float) -> Tuple[int, int]:
    col = int(x // TILE_SIZE)
    row_from_bottom = int(y // TILE_SIZE)
    return col, ROWS - row_from_bottom - 1

def is_center_of_cell(sprite: arcade.Sprite) -> bool:
    col, row = pixel_to_grid(sprite.center_x, sprite.center_y)
    cx, cy = grid_to_pixel(col, row)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2

# ===================== A* con evasión =====================
def neighbors(cell: Tuple[int,int], walls_grid, forbidden):
    c, r = cell
    for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
        nc, nr = c+dc, r+dr
        if 0 <= nc < COLS and 0 <= nr < ROWS:
            if walls_grid[nr][nc] == 0 and (nc,nr) not in forbidden:
                yield (nc, nr)

def manhattan(a: Tuple[int,int], b: Tuple[int,int]) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def astar(start: Tuple[int,int], goal: Tuple[int,int], walls_grid, forbidden):
    if start == goal: return [start]
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
        for nb in neighbors(cur, walls_grid, forbidden):
            tentative = g[cur] + 1
            if nb not in g or tentative < g[nb]:
                g[nb] = tentative
                f = tentative + manhattan(nb, goal)
                came[nb] = cur
                heapq.heappush(openh, (f, nb))
    return []

# ===================== SPRITES =====================
@dataclass
class GhostState:
    normal_color: Tuple[int,int,int]

class Pacman(arcade.Sprite):
    def __init__(self, col: int, row: int):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = arcade.color.YELLOW
        x, y = grid_to_pixel(col, row)
        self.center_x, self.center_y = x, y
        self.current_dir = (0, 0)
        self.desired_dir = (0, 0)
        self.lives = 3
        self.score = 0
        self.power_timer = 0
        self.invulnerable_timer = 0

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
        if dx == dy == 0: return True
        col, row = pixel_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS): return False
        return walls_grid[nr][nc] == 0

class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, state: GhostState):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(TILE_SIZE, arcade.color.WHITE, 255)
        self.color = state.normal_color
        x, y = grid_to_pixel(col, row)
        self.center_x, self.center_y = x, y
        self.current_dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])

    def update_move(self, walls_grid):
        if is_center_of_cell(self):
            col, row = pixel_to_grid(self.center_x, self.center_y)
            options = [d for d in [(1,0),(-1,0),(0,1),(0,-1)] if self.can_move(d, walls_grid)]
            if self.current_dir in options and len(options) == 2:
                pass
            else:
                back = (-self.current_dir[0], -self.current_dir[1])
                valid = [d for d in options if d != back] or options
                self.current_dir = random.choice(valid)
            self.center_x, self.center_y = grid_to_pixel(col, row)
        self.center_x += self.current_dir[0] * 2
        self.center_y += self.current_dir[1] * 2

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        col, row = pixel_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS): return False
        return walls_grid[nr][nc] == 0

# ===================== solve() auxiliar =====================
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
                    heapq.heappush(openh,(ng+manhattan((nr,nc),goal), (nr,nc)))
        return []

    positions=[start]; moves=[]; current=start; rem=pellets[:]
    while rem:
        target=min(rem,key=lambda p: manhattan(current,p))
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
        self.walls_grid = []
        self.state = "PLAY"
        self.auto_path: List[Tuple[int,int]] = []
        self.auto_index = 0
        self.autopilot = True
        self.unreachable = []

    def setup(self):
        self.wall_list, self.pellet_list, self.power_list = arcade.SpriteList(), arcade.SpriteList(), arcade.SpriteList()
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]
        pacman_pos, ghost_pos = None, []

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
                    power = arcade.SpriteSolidColor(14, 14, arcade.color.ORANGE)
                    power.center_x, power.center_y = x, y
                    self.power_list.append(power)
                elif ch == "P":
                    pacman_pos = (c, r)
                elif ch == "G":
                    ghost_pos.append((c, r))

        if pacman_pos:
            col, row = pacman_pos
            self.pacman = Pacman(col, row)

        colors = [arcade.color.RED, arcade.color.GREEN]
        for idx, (c, r) in enumerate(ghost_pos):
            self.ghosts.append(Ghost(c, r, GhostState(colors[idx % len(colors)])))

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

        arcade.draw_text(f"Score: {self.pacman.score}", 10, SCREEN_HEIGHT - 22, arcade.color.YELLOW, 14)
        arcade.draw_text(f"Vidas: {self.pacman.lives}", 10, SCREEN_HEIGHT - 40, arcade.color.YELLOW, 14)
        arcade.draw_text(f"Pellets restantes: {len(self.pellet_list) + len(self.power_list)}",
                         10, SCREEN_HEIGHT - 58, arcade.color.WHITE, 14)
        arcade.draw_text(f"Autopilot: {'ON' if self.autopilot else 'OFF'}",
                         SCREEN_WIDTH-10, 10, arcade.color.WHITE, 12, anchor_x="right")

        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.RED, 40, anchor_x="center")

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman: return

        if self.pacman.invulnerable_timer > 0:
            self.pacman.invulnerable_timer -= delta_time

        # Autopilot con evasión
        if is_center_of_cell(self.pacman) and (not self.auto_path or self.auto_index >= len(self.auto_path)):
            start = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)

            # calcular forbidden = enemigos + vecinos
            forbidden = set()
            for g in self.ghosts:
                gc, gr = pixel_to_grid(g.center_x, g.center_y)
                for dc, dr in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                    nc, nr = gc+dc, gr+dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS:
                        forbidden.add((nc,nr))

            # buscar pellet más cercano alcanzable
            targets = [pixel_to_grid(s.center_x, s.center_y) for s in self.pellet_list] + \
                      [pixel_to_grid(s.center_x, s.center_y) for s in self.power_list]
            reachable = None
            for t in sorted(targets, key=lambda t: manhattan(start, t)):
                path = astar(start, t, self.walls_grid, forbidden)
                if path:
                    reachable = (t, path)
                    break
                else:
                    if t not in self.unreachable:
                        self.unreachable.append(t)
                        print(f"No se pudo alcanzar el pellet en {t} debido a enemigos")

            if reachable:
                self.auto_path = reachable[1]
                self.auto_index = 1

        if self.auto_path and self.auto_index < len(self.auto_path):
            cur = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
            nxt = self.auto_path[self.auto_index]
            dx = nxt[0] - cur[0]
            dy = cur[1] - nxt[1]
            self.pacman.set_direction(dx, dy)
            if cur == nxt:
                self.auto_index += 1

        self.pacman.update_move(self.walls_grid)

        # Comer pellets
        for p in arcade.check_for_collision_with_list(self.pacman, self.pellet_list):
            p.remove_from_sprite_lists()
            self.pacman.score += 10
        for pw in arcade.check_for_collision_with_list(self.pacman, self.power_list):
            pw.remove_from_sprite_lists()
            self.pacman.score += 50
            self.pacman.power_timer = POWER_TIME

        # Mover enemigos
        for g in self.ghosts:
            g.update_move(self.walls_grid)

        # Colisiones con enemigos
        for g in self.ghosts:
            if arcade.check_for_collision(self.pacman, g):
                if self.pacman.invulnerable_timer <= 0:
                    self.pacman.lives -= 1
                    print(f"Colisión con enemigo, vidas restantes: {self.pacman.lives}")
                    if self.pacman.lives <= 0:
                        self.state = "LOSE"
                        print("GAME OVER")
                        result = solve(RAW_MAP)
                        print(f"Ruta tentativa con {result['steps']} pasos en {result['time']}s")
                        print("Movimientos:", result["moves"])
                        return
                    # Respawn
                    for r, row in enumerate(RAW_MAP):
                        for c, ch in enumerate(row):
                            if ch == "P":
                                x, y = grid_to_pixel(c, r)
                                self.pacman.center_x, self.pacman.center_y = x, y
                    self.pacman.invulnerable_timer = 2.0

        # Condición de victoria
        if not self.pellet_list and not self.power_list and self.pacman.lives > 0:
            if self.unreachable:
                print(f"No se pudieron recoger todos los pellets: {self.unreachable}")
            else:
                print(f"GANASTE con {self.pacman.lives} vidas restantes")
            self.state = "WIN"
            result = solve(RAW_MAP)
            print(f"Ruta encontrada con {result['steps']} pasos en {result['time']}s")
            print("Movimientos:", result["moves"])

# ===================== MAIN =====================
def main():
    global RAW_MAP, ROWS, COLS, SCREEN_WIDTH, SCREEN_HEIGHT
    parser = argparse.ArgumentParser(description="PacGPT5 evasión de enemigos con mapas")
    parser.add_argument("--map", default="1", choices=RAW_MAPS.keys(),
                        help="Selecciona el mapa (1, 2 o 3)")
    args = parser.parse_args()

    # === Ejemplo 1: caso exitoso con mini mapa ===
    MINI_MAP_SUCCESS = [
        "#####",
        "#P..#",
        "# # #",
        "#  .#",
        "#####",
    ]
    print("\n=== Caso exitoso con MINI_MAP_SUCCESS ===")
    result = solve(MINI_MAP_SUCCESS)
    print(f"Ruta encontrada con {result['steps']} pasos en {result['time']}s")
    print("Movimientos:", result["moves"], "\n")

    # === Ejemplo 2: caso fallido con mini mapa ===
    MINI_MAP_FAIL = [
        "#####",
        "#P.G#",
        "# # #",
        "#  .#",
        "#####",
    ]
    print("=== Caso fallido con MINI_MAP_FAIL ===")
    result_fail = solve(MINI_MAP_FAIL)
    if result_fail["steps"] == 0:
        print("No se pudo completar: pellet inaccesible debido al fantasma\n")
    else:
        print(f"Ruta parcial con {result_fail['steps']} pasos en {result_fail['time']}s")
        print("Movimientos:", result_fail["moves"], "\n")

    # === Juego arcade con mapa seleccionado ===
    RAW_MAP = RAW_MAPS[args.map]
    ROWS, COLS = len(RAW_MAP), len(RAW_MAP[0])
    SCREEN_WIDTH, SCREEN_HEIGHT = COLS * TILE_SIZE, ROWS * TILE_SIZE

    game = PacGPT5()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
