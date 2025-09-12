"""
Este script implementa un Pac-Man con autopiloto que recorre un laberinto y
recoge todos los pellets usando un algoritmo de búsqueda BFS (Breadth-First Search).
Interfaz del laberinto:
- Representación: lista de strings (RAW_MAP)
- Símbolos:
    '#' : pared
    '.' : pellet
    'o' : power pellet
    'P' : posición inicial de Pac-Man
    'G' : fantasmas (solo visualización)
    ' ' : espacio vacío

Salida:
- En consola se imprime al finalizar:
    1. Ruta encontrada (lista de celdas visitadas)
    2. Número total de pasos
    3. Tiempo de ejecución aproximado (segundos)

La ventana de arcade muestra:
- Paredes azules, pellets blancos, Pac-Man amarillo
- Contador de pellets restantes y pasos actuales

Algoritmo elegido:

- BFS (Breadth-First Search): se utiliza para planificar el camino
  desde la posición actual de Pac-Man hasta el pellet más cercano.
- Motivación:
    * Garantiza encontrar el camino más corto en un grid sin pesos.
    * Es sencillo de implementar y eficiente para mapas pequeños/moderados.
    * Permite simular un autopiloto paso a paso de manera visual.

Despues de la animación del pacman, se imprime:
=== FIN DEL JUEGO ===
Ruta encontrada (total 230 posiciones):
[(20, 8), (19, 8), (18, 8), (17, 8), (17, 7), (17, 6), (18, 6), (18, 5), (18, 4), (18, 3), (18, 2), (18, 1), (17, 1), (16, 1), (15, 1), (14, 1), (13, 1), (12, 1), (11, 1), (11, 2), (11, 3), (11, 4), (10, 4), (9, 4), (8, 4), (8, 3), (8, 2), (8, 1), (7, 1), (6, 1), (5, 1), (4, 1), (3, 1), (2, 1), (1, 1), (1, 2), (1, 3), (1, 4), (2, 4), (3, 4), (4, 4), (4, 3), (4, 2), (4, 3), (4, 4), (5, 4), (6, 4), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (8, 6), (9, 6), (8, 6), (8, 7), (8, 8), (9, 8), (10, 8), (11, 8), (12, 8), (13, 8), (13, 7), (13, 6), (12, 6), (13, 6), (13, 5), (13, 4), (12, 4), (13, 4), (14, 4), (15, 4), (15, 3), (15, 2), (15, 3), (15, 4), (16, 4), (17, 4), (18, 4), (19, 4), (19, 3), (19, 2), (19, 1), (20, 1), (19, 1), (19, 2), (19, 3), (19, 4), (20, 4), (20, 5), (20, 6), (19, 6), (18, 6), (18, 5), (18, 4), (17, 4), (16, 4), (15, 4), (15, 5), (15, 6), (14, 6), (13, 6), (13, 7), (13, 8), (14, 8), (15, 8), (16, 8), (17, 8), (17, 9), (17, 10), (18, 10), (19, 10), (20, 10), (20, 11), (20, 12), (19, 12), (18, 12), (18, 11), (18, 12), (17, 12), (16, 12), (15, 12), (15, 11), (15, 10), (14, 10), (13, 10), (12, 10), (13, 10), (13, 11), (13, 12), (12, 12), (11, 12), (10, 12), (9, 12), (8, 12), (7, 12), (6, 12), (6, 11), (6, 10), (7, 10), (8, 10), (9, 10), (8, 10), (8, 9), (8, 8), (7, 8), (6, 8), (5, 8), (4, 8), (4, 7), (4, 6), (4, 5), (4, 6), (3, 6), (2, 6), (1, 6), (1, 5), (1, 6), (2, 6), (3, 6), (4, 6), (4, 7), (4, 8), (3, 8), (2, 8), (3, 8), (4, 8), (4, 9), (4, 10), (3, 10), (2, 10), (1, 10), (1, 11), (1, 12), (2, 12), (3, 12), (4, 12), (4, 11), (4, 12), (5, 12), (4, 12), (4, 13), (4, 14), (4, 15), (3, 15), (2, 15), (1, 15), (1, 14), (1, 13), (1, 14), (1, 15), (2, 15), (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (8, 14), (8, 13), (8, 12), (9, 12), (10, 12), (11, 12), (11, 13), (11, 14), (11, 15), (12, 15), (13, 15), (14, 15), (15, 15), (15, 14), (15, 13), (15, 12), (14, 12), (15, 12), (16, 12), (17, 12), (18, 12), (18, 13), (19, 13), (19, 14), (18, 14), (18, 15), (17, 15), (16, 15), (17, 15), (18, 15), (19, 15), (20, 15)]
Número total de pasos: 228
Tiempo de ejecución aproximado: 30.76 segundos
"""
import arcade
from collections import deque
import time

# ===================== CONFIG =====================
TILE_SIZE = 32
SCREEN_TITLE = "Pac-Man BFS Autopilot"

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

# ===================== UTILIDADES =====================
def grid_to_pixel(col, row):
    x = col * TILE_SIZE + TILE_SIZE//2
    y = (ROWS - row - 1) * TILE_SIZE + TILE_SIZE//2
    return x, y

def pixel_to_grid(x, y):
    col = int(x // TILE_SIZE)
    row_from_bottom = int(y // TILE_SIZE)
    return col, ROWS - row_from_bottom -1

def is_center_of_cell(sprite):
    col, row = pixel_to_grid(sprite.center_x, sprite.center_y)
    cx, cy = grid_to_pixel(col, row)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2

def manhattan(a,b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def bfs_path(start, goal, walls_grid):
    if start == goal:
        return [start]
    q = deque([start])
    visited = {start: None}
    while q:
        cur = q.popleft()
        c, r = cur
        for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
            nc, nr = c+dc, r+dr
            if 0 <= nc < COLS and 0 <= nr < ROWS and walls_grid[nr][nc] == 0:
                if (nc,nr) not in visited:
                    visited[(nc,nr)] = cur
                    q.append((nc,nr))
    if goal not in visited:
        return []
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = visited[cur]
    path.reverse()
    return path

# ===================== SPRITES =====================
class Pacman(arcade.Sprite):
    def __init__(self, col,row):
        super().__init__()
        self.center_x, self.center_y = grid_to_pixel(col,row)
        self.color = arcade.color.YELLOW
        self.current_dir = (0,0)
        self.desired_dir = (0,0)
        self.invulnerable_timer = 0

    def set_direction(self, dx, dy):
        self.desired_dir = (dx,dy)

    def can_move(self, direction, walls_grid):
        dx, dy = direction
        if dx == 0 and dy == 0:
            return True
        col,row = pixel_to_grid(self.center_x, self.center_y)
        nc,nr = col+dx, row-dy
        if not (0<=nc<COLS and 0<=nr<ROWS):
            return False
        return walls_grid[nr][nc]==0

    def update_move(self, walls_grid):
        if is_center_of_cell(self):
            if self.can_move(self.desired_dir, walls_grid):
                self.current_dir = self.desired_dir
            if not self.can_move(self.current_dir, walls_grid):
                self.current_dir = (0,0)
            col,row = pixel_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_pixel(col,row)
        self.center_x += self.current_dir[0]*4
        self.center_y += self.current_dir[1]*4

# ===================== JUEGO =====================
class PacManBFSGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)

        # Estado del juego
        self.show_menu = True
        self.wall_color = arcade.color.DARK_BLUE
        
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.pacman = None
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]

        # autopiloto
        self.autopilot = True
        self.autopilot_path = []
        self.autopilot_index = 0
        self.total_steps = 0
        self.route = []
        self.start_time = None
        
        # Posiciones iniciales para respawn
        self._pacman_start = None

    def setup(self):
        # Limpiar listas
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.walls_grid = [[0]*COLS for _ in range(ROWS)]
        
        pacman_pos = None
        for r,row in enumerate(RAW_MAP):
            for c,ch in enumerate(row):
                x,y = grid_to_pixel(c,r)
                if ch=="#":
                    wall = arcade.SpriteSolidColor(TILE_SIZE,TILE_SIZE,self.wall_color)
                    wall.center_x, wall.center_y = x,y
                    self.wall_list.append(wall)
                    self.walls_grid[r][c]=1
                elif ch in [".","o"]:
                    pellet = arcade.SpriteSolidColor(6,6,arcade.color.WHITE)
                    pellet.center_x, pellet.center_y = x,y
                    self.pellet_list.append(pellet)
                elif ch=="P":
                    pacman_pos = (c,r)

        if pacman_pos:
            self.pacman = Pacman(*pacman_pos)
            self._pacman_start = pacman_pos

        # Reset stats
        self.total_steps = 0
        self.route = []
        self.autopilot_path = []
        self.autopilot_index = 0
        self.start_time = time.time()

    def reset_pacman_position(self):
        """Respawn de Pacman en posición inicial"""
        if self._pacman_start and self.pacman:
            col, row = self._pacman_start
            self.pacman.center_x, self.pacman.center_y = grid_to_pixel(col, row)
            self.pacman.current_dir = (0, 0)
            self.pacman.desired_dir = (0, 0)
            self.pacman.invulnerable_timer = 2.0
            # Reset autopilot
            self.autopilot_path = []
            self.autopilot_index = 0

    def on_draw(self):
        self.clear()
        
        if self.show_menu:
            # Menú inicial
            arcade.draw_text("PAC-MAN BFS AUTOPILOT", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.7,
                           arcade.color.YELLOW, 24, anchor_x="center")
            arcade.draw_text("1 - Iniciar con Autopilot ON", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.5,
                           arcade.color.WHITE, 16, anchor_x="center")
            arcade.draw_text("2 - Iniciar en modo Manual", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.45,
                           arcade.color.WHITE, 16, anchor_x="center")
            arcade.draw_text("3 - Cambiar color de muros", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.4,
                           arcade.color.WHITE, 16, anchor_x="center")
            arcade.draw_text("ESC - Salir", SCREEN_WIDTH/2, SCREEN_HEIGHT*0.35,
                           arcade.color.GRAY, 12, anchor_x="center")
            return

        # Dibujar juego
        self.wall_list.draw()
        self.pellet_list.draw()
        
        if self.pacman:
            # Pacman parpadeante si es invulnerable
            if self.pacman.invulnerable_timer > 0 and int(self.pacman.invulnerable_timer * 10) % 2:
                pass  # No dibujar (parpadeo)
            else:
                arcade.draw_circle_filled(self.pacman.center_x, self.pacman.center_y, 
                                        TILE_SIZE//2, arcade.color.YELLOW)
        
        # HUD
        autopilot_status = "ON" if self.autopilot else "OFF"
        wall_color_name = "Gris" if self.wall_color == arcade.color.GRAY else "Azul"
        
        arcade.draw_text(f"Pellets: {len(self.pellet_list)} | Pasos: {self.total_steps} | Autopilot: {autopilot_status}", 
                        10, SCREEN_HEIGHT-22, arcade.color.CYAN, 14)
        arcade.draw_text(f"Muros: {wall_color_name} | T=Autopilot | C=Color | R=Respawn | WASD/Flechas=Mover", 
                        10, SCREEN_HEIGHT-40, arcade.color.WHITE, 12)

    def on_update(self, delta_time: float):
        if self.show_menu or not self.pacman or len(self.pellet_list)==0:
            return

        # Actualizar timer de invulnerabilidad
        if self.pacman.invulnerable_timer > 0:
            self.pacman.invulnerable_timer -= delta_time

        if self.autopilot:
            # planificar ruta BFS al pellet más cercano
            if is_center_of_cell(self.pacman) and (not self.autopilot_path or self.autopilot_index>=len(self.autopilot_path)):
                start = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
                targets = [(pixel_to_grid(p.center_x,p.center_y)) for p in self.pellet_list]
                if targets:
                    targets.sort(key=lambda t: manhattan(start,t))
                    goal = targets[0]
                    self.autopilot_path = bfs_path(start, goal, self.walls_grid)
                    self.autopilot_index = 1
            # mover paso a paso
            if self.autopilot_path and self.autopilot_index < len(self.autopilot_path):
                cur = pixel_to_grid(self.pacman.center_x,self.pacman.center_y)
                nxt = self.autopilot_path[self.autopilot_index]
                dx = nxt[0]-cur[0]
                dy = cur[1]-nxt[1]
                self.pacman.set_direction(dx,dy)
                if cur==nxt:
                    self.autopilot_index += 1
                    self.total_steps += 1

        self.pacman.update_move(self.walls_grid)

        # Comer solo el pellet exacto de la celda
        pac_col, pac_row = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
        for p in self.pellet_list:
            p_col, p_row = pixel_to_grid(p.center_x, p.center_y)
            if pac_col == p_col and pac_row == p_row:
                p.remove_from_sprite_lists()
                break

        # Guardar ruta
        pos = (pac_col, pac_row)
        if not self.route or self.route[-1]!=pos:
            self.route.append(pos)

        # Fin del juego
        if len(self.pellet_list)==0:
            end_time = time.time()
            elapsed = round(end_time - self.start_time,2)
            print("\n=== FIN DEL JUEGO ===")
            print(f"Ruta encontrada (total {len(self.route)} posiciones):")
            print(self.route)
            print(f"Número total de pasos: {self.total_steps}")
            print(f"Tiempo de ejecución aproximado: {elapsed} segundos")

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
                # Cambiar color de muros
                self.wall_color = arcade.color.GRAY if self.wall_color == arcade.color.DARK_BLUE else arcade.color.DARK_BLUE
                if not self.show_menu:  # Si ya estamos en juego, recrear
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
            self.autopilot_path = []
            self.autopilot_index = 0
            print(f"Autopilot {'activado' if self.autopilot else 'desactivado'}")
        elif key == arcade.key.C:
            # Alternar color de muros (reinicia tablero)
            self.wall_color = arcade.color.GRAY if self.wall_color == arcade.color.DARK_BLUE else arcade.color.DARK_BLUE
            self.setup()
            print(f"Color de muros cambiado a {'Gris' if self.wall_color == arcade.color.GRAY else 'Azul'}")
        elif key == arcade.key.R:
            # Respawn rápido
            self.reset_pacman_position()
            print("Respawn rápido - Invulnerable por 2 segundos")
        
        # Movimiento manual (solo si autopilot está OFF)
        if not self.autopilot and self.pacman:
            if key in (arcade.key.UP, arcade.key.W):
                self.pacman.set_direction(0,1)
            elif key in (arcade.key.DOWN, arcade.key.S):
                self.pacman.set_direction(0,-1)
            elif key in (arcade.key.LEFT, arcade.key.A):
                self.pacman.set_direction(-1,0)
            elif key in (arcade.key.RIGHT, arcade.key.D):
                self.pacman.set_direction(1,0)

# ===================== MAIN =====================
def main():
    game = PacManBFSGame()
    arcade.run()

if __name__=="__main__":
    main()
