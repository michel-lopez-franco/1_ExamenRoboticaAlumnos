"""
procedural.py — Ejercicio 6
===========================

Extiende el ejemplo de Arcade de cuevas (autómata celular) para añadir un nuevo
elemento coleccionable y un algoritmo que lo localice y recoja.

NUEVO ELEMENTO
--------------
- Tipo: "gema" (item_type="GEM")
- Representación en mapa lógico: carácter 'G' sobre una celda transitable (grid[y][x]==0)
- Representación visual: sprite (diamante) usando un recurso de Arcade

FUNCIÓN PÚBLICA
---------------
find_item(maze, start, item_type, return_moves=False)
    - Algoritmo: BFS (anchura). Justificación: garantiza la ruta más corta en
      grafos no ponderados y es simple de implementar; adecuado en grids con
      coste uniforme por paso.
    - Parámetros:
        maze: lista de strings o lista de listas (0/1) donde 1=pared, 0=piso
        start: tupla (row, col) origen
        item_type: str (por ahora "GEM")
        return_moves: bool, si True devuelve movimientos 'U','D','L','R';
                      si False devuelve lista de posiciones [(r,c), ...]
    - Devuelve:
        path, info  donde
         * path: lista de posiciones o lista de movimientos según return_moves
                 (None si inaccesible)
         * info: dict con {"steps": int, "time_s": float, "reachable": bool}
    - Reglas:
        Respeta paredes (celdas con 1); movimientos en 4 direcciones.

FORMATO DEL MAPA
----------------
- Internamente, el mapa base es una matriz de 0/1 (0=transitable, 1=pared).
- El elemento 'G' se ubica en una celda con valor 0. En la capa visual se dibuja
  además un sprite de gema.

EJEMPLO RÁPIDO (CLI)
--------------------
$ python procedural.py --example
Imprime una ruta mínima en un mini-mapa de prueba y el tiempo de ejecución.

JUEGO (ARCADE)
--------------
$ python procedural.py
Teclas: ↑ ↓ ← → (manual), F (ruta a la gema), F1 (regenerar mapa), ESC (salir).
En el overlay se muestran: tiempos, pasos y estado del ítem.

"""

import argparse
import random
import timeit
from collections import deque
from typing import List, Tuple, Optional, Union, Dict

import arcade

print(arcade.__version__)  # debería ser 3.x

# =======================
# Escalado y ventana
# =======================
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

GRID_WIDTH = 120   # tamaño moderado para rendimiento/legibilidad
GRID_HEIGHT = 90

CHANCE_TO_START_ALIVE = 0.40
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

MOVEMENT_SPEED = 5
VIEWPORT_MARGIN = 300

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves + Item (BFS)"

CAMERA_SPEED = 0.1

# =======================
# Ítems: catálogo simple
# =======================
ITEM_TYPES = {
    "GEM": {
        "char": "G",
        "texture": ":resources:images/items/gemBlue.png",
    }
}

# ----------------------------------------------------------------------
# Utilidades de grid
# ----------------------------------------------------------------------
def create_grid(width: int, height: int) -> List[List[int]]:
    """Crea una grilla 2D de 0 (piso) inicializada a 0."""
    return [[0 for _ in range(width)] for _ in range(height)]


def initialize_grid(grid: List[List[int]]) -> None:
    """Inicializa aleatoriamente celdas "vivas" (1 = pared) según probabilidad."""
    height = len(grid)
    width = len(grid[0])
    for r in range(height):
        for c in range(width):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[r][c] = 1


def count_alive_neighbors(grid: List[List[int]], x: int, y: int) -> int:
    """Cuenta vecinos "vivos" (pared=1). Los bordes cuentan como vivos para cerrar mapa."""
    h = len(grid)
    w = len(grid[0])
    alive = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            nx = x + i
            ny = y + j
            if i == 0 and j == 0:
                continue
            if nx < 0 or ny < 0 or ny >= h or nx >= w:
                alive += 1
            elif grid[ny][nx] == 1:
                alive += 1
    return alive


def do_simulation_step(old_grid: List[List[int]]) -> List[List[int]]:
    """Aplica una iteración del autómata celular."""
    h = len(old_grid)
    w = len(old_grid[0])
    new_grid = create_grid(w, h)
    for x in range(w):
        for y in range(h):
            neighbors = count_alive_neighbors(old_grid, x, y)
            if old_grid[y][x] == 1:
                new_grid[y][x] = 0 if neighbors < DEATH_LIMIT else 1
            else:
                new_grid[y][x] = 1 if neighbors > BIRTH_LIMIT else 0
    return new_grid


# ----------------------------------------------------------------------
# Búsqueda del ítem (API pública)
# ----------------------------------------------------------------------
def _neighbors_4(r: int, c: int) -> List[Tuple[int, int]]:
    return [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]


def _coerce_maze(maze: Union[List[str], List[List[int]]]) -> List[List[int]]:
    """
    Convierte a matriz 0/1 si entra una lista de strings.
    Supone que '1'/'#' son paredes; '0'/'.' son piso; 'G' se ignora como piso.
    """
    if not maze:
        return []
    if isinstance(maze[0], str):
        out = []
        for row in maze:
            o = []
            for ch in row:
                if ch in ("1", "#"):
                    o.append(1)
                else:
                    # '0', '.', 'G', etc. se tratan como piso
                    o.append(0)
            out.append(o)
        return out
    # ya parece ser lista de listas de ints
    return maze  # type: ignore


def _find_first_char(maze_str: List[str], target: str) -> Optional[Tuple[int, int]]:
    for r, row in enumerate(maze_str):
        c = row.find(target)
        if c != -1:
            return (r, c)
    return None


def find_item(
    maze: Union[List[str], List[List[int]]],
    start: Tuple[int, int],
    item_type: str,
    return_moves: bool = False,
) -> Tuple[Optional[List[Tuple[int, int]]], Dict[str, Union[int, float, bool, str]]]:
    """
    Encuentra una ruta mínima desde `start` hasta el primer ítem de tipo `item_type`.

    Parámetros
    ----------
    maze : List[str] | List[List[int]]
        Mapa en forma de:
          - lista de strings (p. ej. '1' o '#' = pared; '0' o '.' = piso; 'G' = gema), o
          - lista de listas de enteros (1=pared, 0=piso).
    start : (int, int)
        Coordenadas lógicas (row, col) de inicio.
    item_type : str
        Tipo de ítem a buscar, por ahora soporta "GEM".
    return_moves : bool
        Si True, devuelve movimientos ['U','D','L','R'] en lugar de posiciones (r,c).

    Retorna
    -------
    path : list[(int,int)] | list[str] | None
        La ruta mínima como lista de posiciones (r,c) incluyendo origen y destino,
        o una lista de movimientos si return_moves=True. None si inaccesible.
    info : dict
        {"steps": int, "time_s": float, "reachable": bool, "item": str}

    Notas
    -----
    - Algoritmo: BFS (anchura), que garantiza óptimo en grafos no ponderados.
    - Respeta paredes (1/#) y límites; movimientos en 4 direcciones.
    """
    if item_type not in ITEM_TYPES:
        raise ValueError(f"item_type desconocido: {item_type}")

    t0 = timeit.default_timer()

    # Si el mapa viene como strings, localizamos la primera 'G' (gema).
    goal: Optional[Tuple[int, int]] = None
    maze_grid = _coerce_maze(maze)

    if maze and isinstance(maze[0], str):
        goal = _find_first_char(maze, ITEM_TYPES[item_type]["char"])
    # Si no está en strings, no podemos inferir posición del char; el llamador
    # podría marcarla aparte. En ese caso se considera inaccesible si no se pasa.

    if goal is None:
        # sin objetivo (no existe o no marcado)
        t1 = timeit.default_timer()
        return None, {
            "steps": 0,
            "time_s": t1 - t0,
            "reachable": False,
            "item": item_type,
        }

    h = len(maze_grid)
    w = len(maze_grid[0]) if h else 0

    sr, sc = start
    if not (0 <= sr < h and 0 <= sc < w) or maze_grid[sr][sc] == 1:
        t1 = timeit.default_timer()
        return None, {
            "steps": 0,
            "time_s": t1 - t0,
            "reachable": False,
            "item": item_type,
        }

    gr, gc = goal

    # BFS
    q = deque([(sr, sc)])
    parent = {(sr, sc): None}
    seen = {(sr, sc)}

    while q:
        r, c = q.popleft()
        if (r, c) == (gr, gc):
            break
        for nr, nc in _neighbors_4(r, c):
            if 0 <= nr < h and 0 <= nc < w and maze_grid[nr][nc] == 0 and (nr, nc) not in seen:
                seen.add((nr, nc))
                parent[(nr, nc)] = (r, c)
                q.append((nr, nc))

    # reconstrucción
    if (gr, gc) not in parent:
        t1 = timeit.default_timer()
        return None, {
            "steps": 0,
            "time_s": t1 - t0,
            "reachable": False,
            "item": item_type,
        }

    path_pos: List[Tuple[int, int]] = []
    cur = (gr, gc)
    while cur is not None:
        path_pos.append(cur)
        cur = parent[cur]
    path_pos.reverse()

    t1 = timeit.default_timer()
    steps = max(0, len(path_pos) - 1)

    if not return_moves:
        return path_pos, {
            "steps": steps,
            "time_s": t1 - t0,
            "reachable": True,
            "item": item_type,
        }

    # Convertir a movimientos
    moves: List[str] = []
    dir_map = {(-1, 0): "U", (1, 0): "D", (0, -1): "L", (0, 1): "R"}
    for (r1, c1), (r2, c2) in zip(path_pos[:-1], path_pos[1:]):
        dr, dc = (r2 - r1, c2 - c1)
        moves.append(dir_map[(dr, dc)])
    return moves, {
        "steps": steps,
        "time_s": t1 - t0,
        "reachable": True,
        "item": item_type,
    }


# ----------------------------------------------------------------------
# Vistas de Arcade con ítem y auto-navegación
# ----------------------------------------------------------------------
class InstructionView(arcade.View):
    def __init__(self):
        super().__init__()
        self.frame_count = 0
        # Usar Text object (evita PerformanceWarning de draw_text)
        self.loading_text = arcade.Text(
            "Loading...",
            0, 0,
            arcade.color.BLACK,
            50,
            anchor_x="center",
            anchor_y="center"
        )

    def on_show_view(self):
        self.window.background_color = arcade.csscolor.DARK_SLATE_BLUE
        self.window.default_camera.use()

    def on_draw(self):
        self.clear()
        # Centrar el texto
        self.loading_text.x = self.window.width // 2
        self.loading_text.y = self.window.height // 2
        self.loading_text.draw()

    def on_update(self, dt: float):
        if self.frame_count == 0:
            self.frame_count += 1
            return
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    """
    Juego principal. Presiona F para que el agente calcule la ruta BFS y se mueva a la gema.
    """

    def __init__(self):
        super().__init__()
        self.grid: Optional[List[List[int]]] = None
        self.wall_list: Optional[arcade.SpriteList] = None
        self.player_list: Optional[arcade.SpriteList] = None
        self.player_sprite: Optional[arcade.Sprite] = None

        # Ítem como SpriteList (Arcade 3.x dibuja sprites desde listas)
        self.item_list: Optional[arcade.SpriteList] = None
        self.item_sprite: Optional[arcade.Sprite] = None
        self.item_rc: Optional[Tuple[int, int]] = None  # (row, col) en grid

        self.draw_time = 0.0
        self.processing_time = 0.0
        self.physics_engine: Optional[arcade.PhysicsEngineSimple] = None

        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        self.sprite_count_text: Optional[arcade.Text] = None
        self.draw_time_text: Optional[arcade.Text] = None
        self.processing_time_text: Optional[arcade.Text] = None
        self.path_info_text: Optional[arcade.Text] = None
        self.item_state_text: Optional[arcade.Text] = None

        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()
        self.window.background_color = arcade.color.BLACK

        # Ruta planificada (en celdas)
        self.planned_path: List[Tuple[int, int]] = []
        # Cola de objetivos (centros de celda) para moverse
        self.waypoints: deque[Tuple[float, float]] = deque()
        self.item_collected: bool = False
        self.last_route_length: int = 0
        self.last_route_time: float = 0.0

    def _grid_to_world(self, r: int, c: int) -> Tuple[float, float]:
        x = c * SPRITE_SIZE + SPRITE_SIZE / 2
        y = r * SPRITE_SIZE + SPRITE_SIZE / 2
        return (x, y)

    def _world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        c = int(x // SPRITE_SIZE)
        r = int(y // SPRITE_SIZE)
        return (r, c)

    def _place_random_free_cell(self) -> Tuple[int, int]:
        assert self.grid is not None
        h = len(self.grid)
        w = len(self.grid[0])
        while True:
            r = random.randrange(h)
            c = random.randrange(w)
            if self.grid[r][c] == 0:
                return (r, c)

    def _spawn_item(self) -> None:
        # Coloca una gema 'G' en una celda libre
        self.item_rc = self._place_random_free_cell()
        ir, ic = self.item_rc
        x, y = self._grid_to_world(ir, ic)

        # Crear listas/sprite del ítem
        assert self.item_list is not None
        self.item_sprite = arcade.Sprite(ITEM_TYPES["GEM"]["texture"], scale=SPRITE_SCALING)
        self.item_sprite.center_x = x
        self.item_sprite.center_y = y
        self.item_list.append(self.item_sprite)

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.item_list = arcade.SpriteList()   # Lista para la gema

        # Genera la cueva
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for _ in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        # Paredes
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

        # Posicionar jugador en celda libre
        placed = False
        max_x = int(GRID_WIDTH * SPRITE_SIZE)
        max_y = int(GRID_HEIGHT * SPRITE_SIZE)
        while not placed:
            self.player_sprite.center_x = random.randrange(max_x)
            self.player_sprite.center_y = random.randrange(max_y)
            walls_hit = arcade.check_for_collision_with_list(self.player_sprite, self.wall_list)
            if len(walls_hit) == 0:
                placed = True

        # Item (gema)
        self._spawn_item()

        # Textos
        sprite_count = len(self.wall_list)
        self.sprite_count_text = arcade.Text(f"Sprite Count: {sprite_count:,}", 20, self.window.height - 20, arcade.color.WHITE, 16)
        self.draw_time_text = arcade.Text("Drawing time:", 20, self.window.height - 40, arcade.color.WHITE, 16)
        self.processing_time_text = arcade.Text("Processing time:", 20, self.window.height - 60, arcade.color.WHITE, 16)
        self.path_info_text = arcade.Text("Route: -", 20, self.window.height - 80, arcade.color.WHITE, 16)
        self.item_state_text = arcade.Text("Item: not collected", 20, self.window.height - 100, arcade.color.WHITE, 16)

        self.physics_engine = arcade.PhysicsEngineSimple(self.player_sprite, self.wall_list)
        self.scroll_to_player(1.0)

    def on_draw(self):
        draw_start = timeit.default_timer()
        self.clear()

        self.camera_sprites.use()
        assert self.wall_list is not None and self.player_list is not None

        self.wall_list.draw(pixelated=True)
        if self.item_list and not self.item_collected:
            self.item_list.draw(pixelated=True)
        self.player_list.draw()

        # GUI
        self.camera_gui.use()
        self.sprite_count_text.draw()
        self.draw_time_text.text = f"Drawing time: {self.draw_time:.3f}"
        self.draw_time_text.draw()
        self.processing_time_text.text = f"Processing time: {self.processing_time:.3f}"
        self.processing_time_text.draw()
        self.path_info_text.draw()
        self.item_state_text.draw()

        self.draw_time = timeit.default_timer() - draw_start

    def _update_player_speed_keys(self):
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

    def _follow_waypoints(self):
        """Mueve al jugador hacia el próximo waypoint (centro de celda)."""
        if not self.waypoints or self.player_sprite is None:
            return
        tx, ty = self.waypoints[0]
        px, py = self.player_sprite.center_x, self.player_sprite.center_y
        dx = tx - px
        dy = ty - py
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= MOVEMENT_SPEED:
            # alcanza el waypoint
            self.player_sprite.center_x = tx
            self.player_sprite.center_y = ty
            self.waypoints.popleft()
        else:
            # normaliza y avanza
            self.player_sprite.center_x += MOVEMENT_SPEED * dx / dist
            self.player_sprite.center_y += MOVEMENT_SPEED * dy / dist

    def on_update(self, delta_time: float):
        start_t = timeit.default_timer()

        # Si hay ruta planificada, ignora input de flechas y sigue la ruta
        if self.waypoints:
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0
            self._follow_waypoints()
        else:
            self._update_player_speed_keys()

        self.physics_engine.update()
        self.scroll_to_player(CAMERA_SPEED)

        # ¿colisiona con ítem?
        if self.item_list and not self.item_collected:
            hits = arcade.check_for_collision_with_list(self.player_sprite, self.item_list)
            if hits:
                self.item_collected = True
                self.item_state_text.text = "Item: collected ✔"
                for s in hits:
                    s.remove_from_sprite_lists()
                self.item_sprite = None

        self.processing_time = timeit.default_timer() - start_t

    def scroll_to_player(self, camera_speed: float):
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(self.camera_sprites.position, position, camera_speed)

    def on_resize(self, width: int, height: int):
        super().on_resize(width, height)
        self.camera_sprites.match_window()
        self.camera_gui.match_window()

    # ----------------------------
    # Entrada de teclado
    # ----------------------------
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
            # Calcular y seguir ruta hasta la gema
            self._plan_and_follow_route_to_item()
        elif key == arcade.key.F1:
            # Regenerar mapa + reubicar item
            self.setup()
        elif key == arcade.key.ESCAPE:
            arcade.exit()

    def on_key_release(self, key, modifiers):
        if key == arcade.key.UP:
            self.up_pressed = False
        elif key == arcade.key.DOWN:
            self.down_pressed = False
        elif key == arcade.key.LEFT:
            self.left_pressed = False
        elif key == arcade.key.RIGHT:
            self.right_pressed = False

    def _plan_and_follow_route_to_item(self):
        """Calcula ruta BFS desde la posición actual a la gema y prepara waypoints."""
        if self.grid is None or self.item_rc is None or self.player_sprite is None:
            return

        # Construir un "maze" como lista de strings para reutilizar find_item y marcar 'G'
        rows: List[str] = []
        h = len(self.grid)
        w = len(self.grid[0])
        for r in range(h):
            chars = []
            for c in range(w):
                if self.grid[r][c] == 1:
                    chars.append("#")
                else:
                    chars.append(".")
            rows.append("".join(chars))
        # Marca la gema
        ir, ic = self.item_rc
        row_list = list(rows[ir])
        row_list[ic] = ITEM_TYPES["GEM"]["char"]
        rows[ir] = "".join(row_list)

        # Origen (grid)
        pr, pc = self._world_to_grid(self.player_sprite.center_x, self.player_sprite.center_y)

        path, info = find_item(rows, (pr, pc), "GEM", return_moves=False)
        if path is None:
            self.path_info_text.text = f"Route: not reachable (t={info['time_s']:.4f}s)"
            print("[INFO] Item GEM no accesible. Tiempo: %.4fs" % info["time_s"])
            return

        # Muestra y almacena
        self.last_route_length = int(info["steps"])
        self.last_route_time = float(info["time_s"])
        self.path_info_text.text = f"Route: steps={self.last_route_length}  time={self.last_route_time:.4f}s"
        print("[ROUTE] steps=%d time=%.4fs" % (self.last_route_length, self.last_route_time))
        print("[ROUTE] path (r,c):", path)

        # Construye waypoints (centro de celda para cada paso)
        self.waypoints.clear()
        for r, c in path[1:]:  # omite celda actual
            self.waypoints.append(self._grid_to_world(r, c))


# ----------------------------------------------------------------------
# Entrada principal (CLI)
# ----------------------------------------------------------------------
def _example_cli():
    """
    Ejemplo reproducible y caso de prueba sencillo (sin Arcade).
    Construye un mini-laberinto y busca la 'G' con BFS.
    """
    mini = [
        "#######",
        "#..G..#",
        "#.###.#",
        "#.....#",
        "#######",
    ]
    start = (3, 1)  # (row, col)
    path, info = find_item(mini, start, "GEM", return_moves=True)
    print("=== EJEMPLO CLI ===")
    print("Mapa:")
    for row in mini:
        print(row)
    print(f"Start: {start}")
    print("Path (moves):", path)
    print("Info:", info)
    # Caso de prueba esperado: ruta existente, pasos mínimos y reachable=True
    assert info["reachable"] is True
    assert isinstance(path, list) and len(path) == info["steps"]
    print("✔ Caso de prueba: OK")


def main():
    parser = argparse.ArgumentParser(description="Procedural caves + item & BFS")
    parser.add_argument("--example", action="store_true", help="Ejecuta ejemplo/PRUEBA en consola")
    args = parser.parse_args()

    if args.example:
        _example_cli()
        return

    # Arcade
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = InstructionView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
