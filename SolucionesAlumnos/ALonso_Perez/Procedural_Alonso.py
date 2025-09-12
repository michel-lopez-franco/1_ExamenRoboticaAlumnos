# procedural_arcade3.py (Arcade 3.x)

"""
Ejercicio 6 — Versión para Arcade 3.x (Camera2D)

Objetivo cumplido en este archivo:
- Se añade un nuevo coleccionable: **gema** ("G").
- Se implementa la función pública `find_item(maze, start, item_type='G')` con **BFS**.
- El agente puede ser **autónomo**: tecla `F` activa el autopiloto para ir a la gema más cercana.
- Se respetan paredes y límites.
- Se incluyen docstrings, ejemplo reproducible y prueba sencilla (`--demo`).
- Se reporta ruta, longitud y tiempo aproximado de ejecución.
- **Anti-atasco solicitado**: si el contador de pasos no cambia por ~1s, hace 2 movimientos aleatorios válidos y
  luego vuelve a calcular la ruta.

Comandos de ejecución:
- Juego normal:  `python procedural_arcade3.py`
- Forzar semilla (reproducible): `python procedural_arcade3.py --seed 1234`
- Demo (imprime prueba unitaria y ejemplo de `find_item`): `python procedural_arcade3.py --demo`

Dependencias: `arcade>=3.0.0`

Notas:
- El mapa interno usa 0 = libre, 1 = pared. Para `find_item` generamos una vista textual con `#`, `.` y `G`.
- BFS garantiza camino más corto en grafos no ponderados.
"""

import argparse
import random
import time
from collections import deque
from typing import Iterable, List, Sequence, Tuple, Union, Dict, Any

import arcade

# ===================== Parámetros base (mantenidos del profe, con fixes) =====================
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

GRID_WIDTH = 450
GRID_HEIGHT = 400

CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

MOVEMENT_SPEED = 5
VIEWPORT_MARGIN = 300

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves + Item + BFS (Arcade 3.x)"

CAMERA_SPEED = 0.1

# Nuevo: ítems
GEM_COUNT = 1
GEM_TEXTURE = ":resources:images/items/gemYellow.png"

# ===================== Utilidades de rejilla/CA =====================

def create_grid(width: int, height: int) -> List[List[int]]:
    """Crea una rejilla 2D (height x width) con ceros."""
    return [[0 for _ in range(width)] for _ in range(height)]


def initialize_grid(grid: List[List[int]]) -> None:
    """Inicializa celdas vivas según probabilidad."""
    h = len(grid)
    w = len(grid[0])
    for r in range(h):
        for c in range(w):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[r][c] = 1


def count_alive_neighbors(grid: List[List[int]], x: int, y: int) -> int:
    """Cuenta vecinos vivos (bordes cuentan como vivos para cerrar cuevas)."""
    h = len(grid)
    w = len(grid[0])
    alive = 0
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            nx, ny = x + i, y + j
            if i == 0 and j == 0:
                continue
            if nx < 0 or ny < 0 or ny >= h or nx >= w:
                alive += 1
            elif grid[ny][nx] == 1:
                alive += 1
    return alive


def do_simulation_step(old_grid: List[List[int]]) -> List[List[int]]:
    """Avanza un paso del autómata celular."""
    h = len(old_grid)
    w = len(old_grid[0])
    new_grid = create_grid(w, h)
    for x in range(w):
        for y in range(h):
            alive_neighbors = count_alive_neighbors(old_grid, x, y)
            if old_grid[y][x] == 1:
                new_grid[y][x] = 0 if alive_neighbors < DEATH_LIMIT else 1
            else:
                new_grid[y][x] = 1 if alive_neighbors > BIRTH_LIMIT else 0
    return new_grid

# ===================== BFS / Búsqueda =====================

MazeType = Union[List[str], List[List[int]]]


def _neighbors(r: int, c: int, h: int, w: int) -> Iterable[Tuple[int, int]]:
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < h and 0 <= nc < w:
            yield nr, nc


def _is_wall_char(ch: str) -> bool:
    return ch == '#'


def _is_free_char(ch: str) -> bool:
    return ch == '.' or ch == 'G'


def _build_char_map_from_grid(grid: List[List[int]], items: Iterable[Tuple[int, int]]) -> List[str]:
    h = len(grid)
    w = len(grid[0])
    item_set = set(items)
    rows = []
    for r in range(h):
        chars = []
        for c in range(w):
            if grid[r][c] == 1:
                chars.append('#')
            else:
                chars.append('G' if (r, c) in item_set else '.')
        rows.append(''.join(chars))
    return rows


def _reconstruct_path(parents: Dict[Tuple[int, int], Tuple[int, int]], end: Tuple[int, int]) -> List[Tuple[int, int]]:
    path: List[Tuple[int, int]] = []
    cur = end
    while cur in parents:
        path.append(cur)
        cur = parents[cur]
    path.reverse()
    return path


def _positions_to_udlr(path: Sequence[Tuple[int, int]], start: Tuple[int, int]) -> str:
    out = []
    r, c = start
    for nr, nc in path:
        if nr == r and nc == c + 1:
            out.append('R')
        elif nr == r and nc == c - 1:
            out.append('L')
        elif nr == r + 1 and nc == c:
            out.append('D')
        elif nr == r - 1 and nc == c:
            out.append('U')
        r, c = nr, nc
    return ''.join(out)


def find_item(maze: MazeType, start: Tuple[int, int], item_type: str = 'G') -> Dict[str, Any]:
    """
    Encuentra un item en un laberinto usando BFS (camino más corto).

    Parámetros
    ----------
    maze : list[str] | list[list[int]]
        - **Formato textual** (recomendado para pruebas): lista de strings con:
          '#' = pared, '.' = libre, 'G' = gema (o `item_type`).
        - **Formato numérico**: lista de listas con 0 = libre, 1 = pared. Para este
          formato, esta función asume que los ítems han sido "impresos" en una vista
          textual previa (ver `build_char_map` en el juego) y por tanto use el formato
          textual para la llamada final.
    start : (row, col)
        Posición inicial en coordenadas de celda.
    item_type : str
        Carácter del ítem a buscar, por defecto 'G'.

    Retorna
    -------
    dict con las claves:
        - found : bool
        - positions : list[(row, col)]  (de start+1 hasta el ítem)
        - path_udlr : str  (secuencia U/D/L/R)
        - steps : int
        - elapsed : float (segundos)
        - goal : (row, col) o None

    Justificación
    -------------
    - BFS (anchura) garantiza el **camino más corto** en grafos no ponderados; el mapa
      se modela como cuadrícula 4-conexa.
    """
    t0 = time.perf_counter()

    # Normalizamos el laberinto a formato textual para facilitar la búsqueda.
    if isinstance(maze, list) and maze and isinstance(maze[0], str):
        grid_txt = maze
    else:
        raise ValueError(
            "Para formato numérico usa primero una vista textual (ver build_char_map)."
        )

    h = len(grid_txt)
    w = len(grid_txt[0]) if h else 0

    sr, sc = start
    if not (0 <= sr < h and 0 <= sc < w):
        raise ValueError("start fuera de rango")
    if _is_wall_char(grid_txt[sr][sc]):
        return {"found": False, "positions": [], "path_udlr": "", "steps": 0, "elapsed": 0.0, "goal": None}

    # Pre-localizamos todas las metas (celdas con item_type)
    goals = {(r, c) for r in range(h) for c in range(w) if grid_txt[r][c] == item_type}
    if not goals:
        elapsed = time.perf_counter() - t0
        return {"found": False, "positions": [], "path_udlr": "", "steps": 0, "elapsed": elapsed, "goal": None}

    q = deque([start])
    seen = {start}
    parents: Dict[Tuple[int, int], Tuple[int, int]] = {}
    goal_reached = None

    while q:
        r, c = q.popleft()
        if (r, c) in goals:
            goal_reached = (r, c)
            break
        for nr, nc in _neighbors(r, c, h, w):
            if (nr, nc) in seen:
                continue
            ch = grid_txt[nr][nc]
            if _is_free_char(ch):
                seen.add((nr, nc))
                parents[(nr, nc)] = (r, c)
                q.append((nr, nc))

    elapsed = time.perf_counter() - t0

    if goal_reached is None:
        return {"found": False, "positions": [], "path_udlr": "", "steps": 0, "elapsed": elapsed, "goal": None}

    path = _reconstruct_path(parents, goal_reached)
    udlr = _positions_to_udlr(path, start)
    return {"found": True, "positions": path, "path_udlr": udlr, "steps": len(path), "elapsed": elapsed, "goal": goal_reached}

# ===================== Vistas =====================

class InstructionView(arcade.View):
    """Pantalla de carga/instrucciones."""

    def __init__(self):
        super().__init__()
        self.frame_count = 0

    def on_show_view(self):
        self.window.background_color = arcade.csscolor.DARK_SLATE_BLUE
        self.window.default_camera.use()

    def on_draw(self):
        self.clear()
        arcade.draw_text(
            "Loading...",
            self.window.width // 2,
            self.window.height // 2,
            arcade.color.BLACK,
            font_size=50,
            anchor_x="center",
        )

    def on_update(self, dt: float):
        if self.frame_count == 0:
            self.frame_count += 1
            return
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    """Juego principal con ítem y BFS/autopiloto."""

    def __init__(self):
        super().__init__()

        self.grid: List[List[int]] = []
        self.wall_list: arcade.SpriteList | None = None
        self.player_list: arcade.SpriteList | None = None
        self.player_sprite: arcade.Sprite | None = None
        self.gem_list: arcade.SpriteList | None = None

        self.draw_time = 0.0
        self.processing_time = 0.0

        self.physics_engine: arcade.PhysicsEngineSimple | None = None

        # Entrada
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        # UI
        self.sprite_count_text: arcade.Text | None = None
        self.draw_time_text: arcade.Text | None = None
        self.processing_time_text: arcade.Text | None = None
        self.bfs_info_text: arcade.Text | None = None

        # Cámaras
        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()

        self.window.background_color = arcade.color.BLACK

        # Autopiloto
        self.autopilot_active = False
        self.autopilot_path: List[Tuple[int, int]] = []
        self.autopilot_target_px: Tuple[float, float] | None = None
        self.last_bfs_result: Dict[str, Any] | None = None

        # ---- Anti-atasco por steps detenidos ----
        self.prev_steps_left: int | None = None
        self.no_progress_timer: float = 0.0

        # Para convertir entre mundo y celda
        self.grid_h = GRID_HEIGHT
        self.grid_w = GRID_WIDTH

    # --------- Helpers de coordenadas
    def world_to_cell(self, x: float, y: float) -> Tuple[int, int]:
        return int(y // SPRITE_SIZE), int(x // SPRITE_SIZE)

    def cell_center_world(self, r: int, c: int) -> Tuple[float, float]:
        return c * SPRITE_SIZE + SPRITE_SIZE / 2, r * SPRITE_SIZE + SPRITE_SIZE / 2

    def build_char_map(self) -> List[str]:
        # Construye mapa textual con paredes y gemas
        gems = []
        if self.gem_list:
            for s in self.gem_list:
                gr, gc = self.world_to_cell(s.center_x, s.center_y)
                gems.append((gr, gc))
        return _build_char_map_from_grid(self.grid, gems)

    # Pequeño “desatorador”: dos pasos aleatorios válidos
    def _nudge_random_two_moves(self):
        r, c = self.world_to_cell(self.player_sprite.center_x, self.player_sprite.center_y)
        for _ in range(2):  # dos movimientos
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            random.shuffle(dirs)
            moved = False
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < GRID_HEIGHT and 0 <= nc < GRID_WIDTH and self.grid[nr][nc] == 0:
                    nx, ny = self.cell_center_world(nr, nc)
                    self.player_sprite.center_x, self.player_sprite.center_y = nx, ny
                    r, c = nr, nc
                    moved = True
                    break
            if not moved:
                break  # no hay movimiento posible desde aquí

    # --------- Setup
    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.gem_list = arcade.SpriteList()

        # Cueva aleatoria
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for _ in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for r in range(GRID_HEIGHT):
            for c in range(GRID_WIDTH):
                if self.grid[r][c] == 1:
                    wall = arcade.BasicSprite(texture, scale=SPRITE_SCALING)
                    wall.center_x = c * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = r * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # Jugador
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING,
        )
        self.player_list.append(self.player_sprite)

        # Colocar jugador aleatoriamente en celda libre
        placed = False
        max_x = int(GRID_WIDTH * SPRITE_SIZE)
        max_y = int(GRID_HEIGHT * SPRITE_SIZE)
        while not placed:
            self.player_sprite.center_x = random.randrange(max_x)
            self.player_sprite.center_y = random.randrange(max_y)
            if len(arcade.check_for_collision_with_list(self.player_sprite, self.wall_list)) == 0:
                placed = True

        # Colocar gemas en celdas libres (intentamos que haya al menos una alcanzable)
        floor_cells: List[Tuple[int, int]] = [
            (r, c)
            for r in range(GRID_HEIGHT)
            for c in range(GRID_WIDTH)
            if self.grid[r][c] == 0
        ]
        random.shuffle(floor_cells)

        gems_placed = 0
        tries = 0
        while gems_placed < GEM_COUNT and tries < 5000:
            tries += 1
            r, c = random.choice(floor_cells)
            gx, gy = self.cell_center_world(r, c)
            gem = arcade.Sprite(GEM_TEXTURE, scale=SPRITE_SCALING)
            gem.center_x, gem.center_y = gx, gy
            # Asegurar que no está sobre pared
            if arcade.check_for_collision_with_list(gem, self.wall_list):
                continue
            # Opcional: intentar que sea alcanzable desde la posición actual
            start_cell = self.world_to_cell(self.player_sprite.center_x, self.player_sprite.center_y)
            char_map = _build_char_map_from_grid(self.grid, [(r, c)])
            res = find_item(char_map, start_cell, item_type='G')
            if res["found"]:
                self.gem_list.append(gem)
                gems_placed += 1

        # UI text
        sprite_count = len(self.wall_list)
        self.sprite_count_text = arcade.Text(
            f"Sprite Count: {sprite_count:,}", 20, self.window.height - 20, arcade.color.WHITE, 16
        )
        self.draw_time_text = arcade.Text("Drawing time:", 20, self.window.height - 40, arcade.color.WHITE, 16)
        self.processing_time_text = arcade.Text("Processing time:", 20, self.window.height - 60, arcade.color.WHITE, 16)
        self.bfs_info_text = arcade.Text("BFS: -", 20, self.window.height - 80, arcade.color.WHITE, 16)

        self.physics_engine = arcade.PhysicsEngineSimple(self.player_sprite, self.wall_list)
        self.scroll_to_player(1.0)

    # --------- Dibujo
    def on_draw(self):
        t0 = time.perf_counter()
        self.clear()
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.gem_list.draw()
        self.player_list.draw()
        self.camera_gui.use()
        self.sprite_count_text.draw()
        self.draw_time_text.text = f"Drawing time: {self.draw_time:.3f}"
        self.draw_time_text.draw()
        self.processing_time_text.text = f"Processing time: {self.processing_time:.3f}"
        self.processing_time_text.draw()
        self.bfs_info_text.draw()
        self.draw_time = time.perf_counter() - t0

    # --------- Movimiento manual
    def update_player_speed(self):
        if self.autopilot_active:
            # Autopiloto gestiona velocidades
            return
        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0
        if self.up_pressed and not self.down_pressed:
            self.player_sprite.change_y = MOVEMENT_SPEED
        elif self.down_pressed and not self.up_pressed:
            self.player_sprite.change_y = -MOVEMENT_SPEED
        if self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = -MOVEMENT_SPEED
        elif self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = MOVEMENT_SPEED

    def on_key_press(self, key, modifiers):
        if key == arcade.key.UP:
            self.up_pressed = True
        elif key == arcade.key.DOWN:
            self.down_pressed = True
        elif key == arcade.key.LEFT:
            self.left_pressed = True
        elif key == arcade.key.RIGHT:
            self.right_pressed = True
        elif key == arcade.key.F:
            self.start_autopilot_to_nearest_gem()

    def on_key_release(self, key, modifiers):
        if key == arcade.key.UP:
            self.up_pressed = False
        elif key == arcade.key.DOWN:
            self.down_pressed = False
        elif key == arcade.key.LEFT:
            self.left_pressed = False
        elif key == arcade.key.RIGHT:
            self.right_pressed = False

    # --------- Cámara/resize
    def scroll_to_player(self, camera_speed: float):
        pos = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(self.camera_sprites.position, pos, camera_speed)

    def on_resize(self, width: int, height: int):
        super().on_resize(width, height)
        self.camera_sprites.match_window()
        self.camera_gui.match_window()

    # --------- Update
    def on_update(self, delta_time: float):
        t0 = time.perf_counter()

        if self.autopilot_active:
            self.step_autopilot()
        else:
            self.update_player_speed()
        self.physics_engine.update()

        # -------- Anti-atasco por steps detenidos (1s) --------
        if self.autopilot_active:
            steps_left = len(self.autopilot_path) + (1 if self.autopilot_target_px is not None else 0)
            if self.prev_steps_left is None:
                self.prev_steps_left = steps_left
                self.no_progress_timer = 0.0
            else:
                if steps_left == self.prev_steps_left:
                    self.no_progress_timer += delta_time
                else:
                    self.no_progress_timer = 0.0
                    self.prev_steps_left = steps_left

            if self.no_progress_timer > 1.0:
                print("[Anti-Stuck] Steps no cambian en 1.0s -> 2 movimientos aleatorios + recalcular ruta")
                self.no_progress_timer = 0.0
                self.prev_steps_left = None
                # Dos movimientos aleatorios válidos
                self._nudge_random_two_moves()
                # Recalcular ruta desde la nueva celda
                self.start_autopilot_to_nearest_gem()

        # Pickup de gemas
        hits = arcade.check_for_collision_with_list(self.player_sprite, self.gem_list)
        for gem in hits:
            gem.remove_from_sprite_lists()
            self.autopilot_active = False
            self.autopilot_path.clear()
            self.autopilot_target_px = None
            self.prev_steps_left = None
            self.no_progress_timer = 0.0
            self.bfs_info_text.text = "BFS: Gem collected"

        self.scroll_to_player(CAMERA_SPEED)
        self.processing_time = time.perf_counter() - t0

    # --------- Autopiloto
    def start_autopilot_to_nearest_gem(self):
        if not self.gem_list or len(self.gem_list) == 0:
            self.bfs_info_text.text = "BFS: No gems available"
            return
        start_cell = self.world_to_cell(self.player_sprite.center_x, self.player_sprite.center_y)
        # Todas las gemas como metas; BFS devuelve la primera alcanzada (más cercana en capas)
        gems_cells = [self.world_to_cell(g.center_x, g.center_y) for g in self.gem_list]
        char_map = _build_char_map_from_grid(self.grid, gems_cells)
        res = find_item(char_map, start_cell, item_type='G')
        self.last_bfs_result = res
        if not res["found"]:
            self.autopilot_active = False
            self.autopilot_path = []
            self.autopilot_target_px = None
            self.prev_steps_left = None
            self.no_progress_timer = 0.0
            self.bfs_info_text.text = "BFS: Gem unreachable"
            print("[BFS] No reachable gem. Steps=0, time=%.3f s" % res["elapsed"])
            return
        self.autopilot_path = res["positions"][:]  # copia
        self.autopilot_active = True
        self.prev_steps_left = len(self.autopilot_path) + 1  # incluye la celda target actual
        self.no_progress_timer = 0.0
        self.bfs_info_text.text = f"BFS: found steps={res['steps']} time={res['elapsed']*1000:.1f} ms"
        print("[BFS] Found path: steps=%d, time=%.3f s, UDLR=%s" % (res["steps"], res["elapsed"], res["path_udlr"]))
        self.set_next_autopilot_target()

    def set_next_autopilot_target(self):
        if not self.autopilot_path:
            self.autopilot_target_px = None
            self.autopilot_active = False
            return
        r, c = self.autopilot_path.pop(0)
        self.autopilot_target_px = self.cell_center_world(r, c)

    def step_autopilot(self):
        if self.autopilot_target_px is None:
            self.autopilot_active = False
            return
        tx, ty = self.autopilot_target_px
        px, py = self.player_sprite.center_x, self.player_sprite.center_y
        dx, dy = tx - px, ty - py
        # Normalizamos a movimiento Manhattan por celdas
        if abs(dx) > 2:
            self.player_sprite.change_x = MOVEMENT_SPEED if dx > 0 else -MOVEMENT_SPEED
            self.player_sprite.change_y = 0
        elif abs(dy) > 2:
            self.player_sprite.change_y = MOVEMENT_SPEED if dy > 0 else -MOVEMENT_SPEED
            self.player_sprite.change_x = 0
        else:
            # Llegó a la celda objetivo
            self.player_sprite.center_x, self.player_sprite.center_y = tx, ty
            self.set_next_autopilot_target()

# ===================== Demo / pruebas =====================

def _demo_find_item() -> None:
    print("\n[DEMO] Prueba unitaria de find_item en mapa pequeño:")
    maze = [
        "#######",
        "#....G#",
        "#.###.#",
        "#.....#",
        "#######",
    ]
    start = (1, 1)  # fila 1, col 1
    res = find_item(maze, start, item_type='G')
    print("found=", res["found"], "steps=", res["steps"], "elapsed=%.4f s" % res["elapsed"])
    print("path UDLR:", res["path_udlr"])  # esperado: RRRR
    print("positions:", res["positions"])  # 4 posiciones hasta la G


def main(seed: int | None = None, demo: bool = False) -> None:
    if seed is not None:
        random.seed(seed)
    if demo:
        _demo_find_item()

    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    view = InstructionView()
    window.show_view(view)
    arcade.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None, help="Semilla RNG para reproducibilidad")
    parser.add_argument("--demo", action="store_true", help="Ejecuta una demo/prueba de find_item y continúa al juego")
    args = parser.parse_args()
    main(seed=args.seed, demo=args.demo)
