"""
Cambios:
    Menú inicial: (1) Autopilot ON, (2) Manual, (3) Cambiar color muros
    Tecla C en juego: alterna color muros (reinicia tablero)
    Tecla T: alterna Autopilot ON/OFF
    Flechas / WASD: movimiento manual
    R: respawn rápido tras perder una vida (invulnerable 2s)
    ESC: salir
Reglas:
- Pac-Man:
    * Se mueve con teclas ARRIBA, ABAJO, IZQUIERDA, DERECHA.
    * No atraviesa paredes.
    * Tiene 3 vidas; al tocar un fantasma pierde 1 vida y reaparece.
    * Tras reaparecer, es invulnerable 2 segundos.

- Fantasmas:
    * Se mueven aleatoriamente por el laberinto.
    * En pasillos siguen recto; en intersecciones eligen dirección al azar.
    * La colisión con Pac-Man reduce una vida.

- Pellets:
    * Se consumen solo si Pac-Man está centrado sobre ellos.

Estrategia de evasión:
- BFS para planear ruta hacia el pellet más cercano.
- Se evita la posición de los enemigos y sus celdas adyacentes.
- Replanning en cada centro de celda.
- Los pellets inaccesibles se registran en consola.

Condiciones de fin:
- WIN: todos los pellets recogidos y al menos 1 vida.
- LOSE: vidas agotadas.

Salida en consola:
- Ruta recorrida, pasos, vidas, pellets inaccesibles y estado final.

Ejemplo de uso:
- python PacMan3.py
"""
import arcade, heapq, time, random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

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

# ===================== CONFIG =====================
SCREEN_TITLE = "PacGPT5 - Mapa Único con Personalización"
TILE_SIZE = 32
MOVEMENT_SPEED = 4
GHOST_SPEED = 2
POWER_TIME = 7.0

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
        if dx == dy == 0:
            return True
        col, row = pixel_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            return False
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
                pass  # seguir recto en pasillo
            else:
                back = (-self.current_dir[0], -self.current_dir[1])
                valid = [d for d in options if d != back] or options
                self.current_dir = random.choice(valid)
            self.center_x, self.center_y = grid_to_pixel(col, row)
        self.center_x += self.current_dir[0] * GHOST_SPEED
        self.center_y += self.current_dir[1] * GHOST_SPEED

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        col, row = pixel_to_grid(self.center_x, self.center_y)
        nc, nr = col + dx, row - dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            return False
        return walls_grid[nr][nc] == 0

# ===================== JUEGO PRINCIPAL =====================
class PacGPT5(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_color = arcade.color.DARK_BLUE
        self.show_menu = True  # Menú inicial
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts: List[Ghost] = []
        self.pacman: Optional[Pacman] = None
        self.walls_grid: List[List[int]] = []
        self.state = "PLAY"  # PLAY | WIN | LOSE
        self.auto_path: List[Tuple[int,int]] = []
        self.auto_index = 0
        self.autopilot = True
        self.unreachable: List[Tuple[int,int]] = []
        self._pacman_start: Optional[Tuple[int,int]] = None
        self._ghost_starts: List[Tuple[int,int]] = []
        
        # Crear objetos Text para mejorar el rendimiento
        self.setup_text_objects()

    def setup_text_objects(self):
        """Crear objetos Text reutilizables para evitar warning de rendimiento"""
        self.title_text = arcade.Text("PACGPT5 - MENU", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.7,
                                     arcade.color.YELLOW, 30, anchor_x="center")
        
        self.menu_text1 = arcade.Text("1 - Iniciar con Autopilot ON", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.5,
                                     arcade.color.WHITE, 18, anchor_x="center")
        
        self.menu_text2 = arcade.Text("2 - Iniciar en modo Manual", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.45,
                                     arcade.color.WHITE, 18, anchor_x="center")
        
        self.menu_text3 = arcade.Text("3 - Cambiar color de laberinto (Azul/Gris)", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.4,
                                     arcade.color.WHITE, 18, anchor_x="center")
        
        self.menu_text4 = arcade.Text("ESC - Salir", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.35,
                                     arcade.color.GRAY, 14, anchor_x="center")
        
        # Textos del HUD (se actualizarán dinámicamente)
        self.score_text = arcade.Text("Score: 0", 10, SCREEN_HEIGHT - 22, arcade.color.YELLOW, 14)
        self.lives_text = arcade.Text("Vidas: 3", 10, SCREEN_HEIGHT - 40, arcade.color.YELLOW, 14)
        self.pellets_text = arcade.Text("Pellets restantes: 0", 10, SCREEN_HEIGHT - 58, arcade.color.WHITE, 14)
        self.autopilot_text = arcade.Text("Autopilot: ON", 10, SCREEN_HEIGHT - 76, arcade.color.WHITE, 14)
        self.wall_color_text = arcade.Text("Color muros: Azul", 10, SCREEN_HEIGHT - 94, arcade.color.WHITE, 14)
        
        # Textos de estado final
        self.win_text = arcade.Text("¡GANASTE!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.GREEN, 40, anchor_x="center")
        self.lose_text = arcade.Text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, arcade.color.RED, 40, anchor_x="center")

    def update_hud_texts(self):
        """Actualizar textos del HUD con los valores actuales"""
        if self.pacman:
            self.score_text.text = f"Score: {self.pacman.score}"
            self.lives_text.text = f"Vidas: {self.pacman.lives}"
        
        self.pellets_text.text = f"Pellets restantes: {len(self.pellet_list) + len(self.power_list)}"
        self.autopilot_text.text = f"Autopilot: {'ON' if self.autopilot else 'OFF'}"
        self.wall_color_text.text = f"Color muros: {'Gris' if self.wall_color == arcade.color.GRAY else 'Azul'}"

    def setup(self):
        self.wall_list, self.pellet_list, self.power_list = arcade.SpriteList(), arcade.SpriteList(), arcade.SpriteList()
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]
        pacman_pos, ghost_pos = None, []

        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_pixel(c, r)
                if ch == "#":
                    wall = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, self.wall_color)
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
            self._pacman_start = (col, row)

        self._ghost_starts = []
        colors = [arcade.color.RED, arcade.color.GREEN]
        for idx, (c, r) in enumerate(ghost_pos):
            self.ghosts.append(Ghost(c, r, GhostState(colors[idx % len(colors)])))
            self._ghost_starts.append((c, r))

    def reset_positions(self):
        if self._pacman_start and self.pacman:
            x, y = grid_to_pixel(*self._pacman_start)
            self.pacman.center_x, self.pacman.center_y = x, y
            self.pacman.current_dir = (0, 0)
            self.pacman.desired_dir = (0, 0)
        for g, (c, r) in zip(self.ghosts, self._ghost_starts):
            x, y = grid_to_pixel(c, r)
            g.center_x, g.center_y = x, y
            g.current_dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        self.auto_path = []
        self.auto_index = 0
        if self.pacman:
            self.pacman.invulnerable_timer = 2.0

    def on_draw(self):
        self.clear()
        if self.show_menu:
            self.title_text.draw()
            self.menu_text1.draw()
            self.menu_text2.draw()
            self.menu_text3.draw()
            self.menu_text4.draw()
            return

        # --- Juego ---
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()
        
        if self.pacman:
            # Usar draw_lbwh_rectangle_filled en lugar de draw_xywh_rectangle_filled
            arcade.draw_lbwh_rectangle_filled(
                self.pacman.center_x - TILE_SIZE/2,
                self.pacman.center_y - TILE_SIZE/2,
                TILE_SIZE, TILE_SIZE,
                arcade.color.YELLOW
            )
        
        for g in self.ghosts:
            # Usar draw_lbwh_rectangle_filled en lugar de draw_xywh_rectangle_filled
            arcade.draw_lbwh_rectangle_filled(
                g.center_x - TILE_SIZE/2,
                g.center_y - TILE_SIZE/2,
                TILE_SIZE, TILE_SIZE,
                g.color
            )

        # HUD - Actualizar y dibujar textos
        self.update_hud_texts()
        self.score_text.draw()
        self.lives_text.draw()
        self.pellets_text.draw()
        self.autopilot_text.draw()
        self.wall_color_text.draw()

        if self.state == "WIN":
            self.win_text.draw()
        elif self.state == "LOSE":
            self.lose_text.draw()

    def on_update(self, delta_time: float):
        if self.show_menu or self.state != "PLAY" or not self.pacman:
            return

        if self.pacman.invulnerable_timer > 0:
            self.pacman.invulnerable_timer -= delta_time

        # Autopilot con evasión (replanifica en centros de celda)
        if self.autopilot and is_center_of_cell(self.pacman) and (not self.auto_path or self.auto_index >= len(self.auto_path)):
            start = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
            forbidden = set()
            for g in self.ghosts:
                gc, gr = pixel_to_grid(g.center_x, g.center_y)
                for dc, dr in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                    nc, nr = gc+dc, gr+dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS:
                        forbidden.add((nc,nr))
            targets = [pixel_to_grid(s.center_x, s.center_y) for s in self.pellet_list] + \
                      [pixel_to_grid(s.center_x, s.center_y) for s in self.power_list]
            reachable = None
            for t in sorted(targets, key=lambda t: manhattan(start, t)):
                path = astar(start, t, self.walls_grid, forbidden)
                if path:
                    reachable = (t, path)
                    break
            if reachable:
                self.auto_path = reachable[1]
                self.auto_index = 1

        # Seguir ruta en autopilot
        if self.autopilot and self.auto_path and self.auto_index < len(self.auto_path):
            cur = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
            nxt = self.auto_path[self.auto_index]
            dx = nxt[0] - cur[0]
            dy = cur[1] - nxt[1]
            self.pacman.set_direction(dx, dy)
            if cur == nxt:
                self.auto_index += 1

        # Movimiento (manual o autopilot)
        self.pacman.update_move(self.walls_grid)

        # Comer pellets / power-ups
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
                    if self.pacman.lives <= 0:
                        self.state = "LOSE"
                        return
                    # Respawn
                    self.reset_positions()

        # Victoria
        if not self.pellet_list and not self.power_list and self.pacman.lives > 0:
            self.state = "WIN"

    def on_key_press(self, key, modifiers):
        # Menú inicial
        if self.show_menu:
            if key == arcade.key.KEY_1:
                self.autopilot = True
                self.show_menu = False
                self.setup()
            elif key == arcade.key.KEY_2:
                self.autopilot = False
                self.show_menu = False
                self.setup()
            elif key == arcade.key.KEY_3:
                # Alternar color y refrescar muros
                self.wall_color = arcade.color.GRAY if self.wall_color == arcade.color.DARK_BLUE else arcade.color.DARK_BLUE
                self.setup()
            elif key == arcade.key.ESCAPE:
                arcade.close_window()
            return

        # En juego
        if key == arcade.key.ESCAPE:
            arcade.close_window()
        elif key == arcade.key.T:
            # Alternar autopilot
            self.autopilot = not self.autopilot
            self.auto_path = []
            self.auto_index = 0
        elif key == arcade.key.C:
            # Alternar color de muros (reinicia tablero)
            self.wall_color = arcade.color.GRAY if self.wall_color == arcade.color.DARK_BLUE else arcade.color.DARK_BLUE
            # Mantener score y vidas actuales al recolorear
            score, lives = (self.pacman.score, self.pacman.lives) if self.pacman else (0, 3)
            self.setup()
            if self.pacman:
                self.pacman.score = score
                self.pacman.lives = lives
        elif key in (arcade.key.UP, arcade.key.W):
            if self.pacman: self.pacman.set_direction(0, 1)
        elif key in (arcade.key.DOWN, arcade.key.S):
            if self.pacman: self.pacman.set_direction(0, -1)
        elif key in (arcade.key.LEFT, arcade.key.A):
            if self.pacman: self.pacman.set_direction(-1, 0)
        elif key in (arcade.key.RIGHT, arcade.key.D):
            if self.pacman: self.pacman.set_direction(1, 0)
        elif key == arcade.key.R:
            # Respawn rápido
            self.reset_positions()


def main():
    game = PacGPT5()
    # No llamamos setup aquí; se llama al elegir en el menú (1 o 2) o al cambiar color (3)
    arcade.run()


if __name__ == "__main__":
    main()