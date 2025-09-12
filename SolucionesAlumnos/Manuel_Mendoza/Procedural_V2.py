"""
procedural.py — Ejercicio 6 (multigema)
=======================================

Extiende el ejemplo de Arcade de cuevas (autómata celular) para añadir
múltiples elementos coleccionables (gemas) y un algoritmo que las localice
y recoja en orden de la más cercana a la más lejana (heurística codiciosa
por distancia BFS). Se traza en pantalla la polilínea del recorrido.

ELEMENTOS
---------
- Tipo: "gema" (item_type="GEM")
- Representación lógica: carácter 'G' sobre celda transitable (grid[y][x]==0)
- Representación visual: sprite ":resources:images/items/gemBlue.png"

API PÚBLICA
-----------
find_item(maze, start, item_type, return_moves=False)
    - Igual que antes: BFS hasta la primera 'G' encontrada en un mapa textual.
    - Útil como ejemplo/compatibilidad; internamente el juego usa _bfs_path().

FORMATO DEL MAPA
----------------
- Matriz de 0/1 (0=transitable, 1=pared). Las gemas se guardan como (r,c) y se
  dibujan con sprites.

PLANEACIÓN MULTI-OBJETIVO
-------------------------
- Desde la celda actual, calcula para cada gema accesible la distancia/ruta BFS.
- Selecciona la gema con ruta mínima, concatena esa ruta al plan, actualiza el
  origen y repite hasta recolectar todas las gemas (o las accesibles).
- Traza la polilínea del plan completo y segmentos por objetivo.

JUEGO (ARCADE)
--------------
$ python procedural.py
Teclas:
  - ↑ ↓ ← →  : control manual (si no hay waypoints)
  - F        : recalcular plan hacia todas las gemas restantes
  - F1       : regenerar mapa y gemas
  - G        : resembrar gemas (manteniendo el mapa)
  - ESC      : salir

EJEMPLO CLI
-----------
$ python procedural.py --example
Mapa de prueba con dos gemas; imprime ruta total (pasos) y tiempo.

"""

import argparse
import random
import timeit
from collections import deque
from typing import List, Tuple, Optional, Union, Dict

import arcade

# =======================
# Configuración general
# =======================
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

GRID_WIDTH = 60
GRID_HEIGHT = 60

CHANCE_TO_START_ALIVE = 0.40
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

MOVEMENT_SPEED = 5
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves + Multi-Gem (BFS Greedy)"
CAMERA_SPEED = 0.1

# Número de gemas a colocar
NUM_GEMS = 6

# Catálogo de ítems
ITEM_TYPES = {
    "GEM": {
        "char": "G",
        "texture": ":resources:images/items/gemBlue.png",
    }
}

# ----------------------------------------------------------------------
# Utilidades de grid / autómata celular
# ----------------------------------------------------------------------
def create_grid(width: int, height: int) -> List[List[int]]:
    return [[0 for _ in range(width)] for _ in range(height)]


def initialize_grid(grid: List[List[int]]) -> None:
    h, w = len(grid), len(grid[0])
    for r in range(h):
        for c in range(w):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[r][c] = 1


def count_alive_neighbors(grid: List[List[int]], x: int, y: int) -> int:
    h, w = len(grid), len(grid[0])
    alive = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            nx, ny = x + i, y + j
            if i == 0 and j == 0:
                continue
            if nx < 0 or ny < 0 or ny >= h or nx >= w:
                alive += 1
            elif grid[ny][nx] == 1:
                alive += 1
    return alive


def do_simulation_step(old_grid: List[List[int]]) -> List[List[int]]:
    h, w = len(old_grid), len(old_grid[0])
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
# BFS helpers (interno del juego)
# ----------------------------------------------------------------------
def _neighbors_4(r: int, c: int) -> List[Tuple[int, int]]:
    return [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]


def _bfs_path(grid01: List[List[int]], start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """
    Ruta BFS mínima entre start y goal (incluye ambos extremos).
    Retorna None si no hay camino.
    """
    h, w = len(grid01), len(grid01[0])
    sr, sc = start
    gr, gc = goal
    if not (0 <= sr < h and 0 <= sc < w) or not (0 <= gr < h and 0 <= gc < w):
        return None
    if grid01[sr][sc] == 1 or grid01[gr][gc] == 1:
        return None

    q = deque([(sr, sc)])
    parent = {(sr, sc): None}
    while q:
        r, c = q.popleft()
        if (r, c) == (gr, gc):
            break
        for nr, nc in _neighbors_4(r, c):
            if 0 <= nr < h and 0 <= nc < w and grid01[nr][nc] == 0 and (nr, nc) not in parent:
                parent[(nr, nc)] = (r, c)
                q.append((nr, nc))

    if (gr, gc) not in parent:
        return None

    path = []
    cur = (gr, gc)
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path


def _bfs_multi_target_plan(grid01: List[List[int]], start: Tuple[int, int], targets: List[Tuple[int, int]]) -> Tuple[List[Tuple[int, int]], List[List[Tuple[int, int]]], List[Tuple[int, int]]]:
    """
    Planea ruta completa para visitar múltiples objetivos en orden codicioso:
    siempre el objetivo accesible con ruta BFS mínima desde el punto actual.

    Retorna:
      - full_path: lista concatenada de celdas (incluye start una sola vez)
      - segments:  lista de rutas por cada objetivo elegido (para colorear)
      - order:     lista de objetivos en el orden visitado
    Si algún objetivo no es accesible, simplemente no aparece en `order`.
    """
    remaining = targets[:]
    cur = start
    full_path: List[Tuple[int, int]] = [cur]
    segments: List[List[Tuple[int, int]]] = []
    order: List[Tuple[int, int]] = []

    while remaining:
        best = None
        best_path = None
        best_len = None
        # evalúa todas las rutas desde cur a cada candidato
        for t in remaining:
            p = _bfs_path(grid01, cur, t)
            if p is None:
                continue
            steps = len(p) - 1
            if best_len is None or steps < best_len:
                best = t
                best_path = p
                best_len = steps
        if best is None:
            # no quedan accesibles
            break
        # concatena (evita duplicar la primera celda)
        seg = best_path
        if full_path and seg and seg[0] == full_path[-1]:
            full_path.extend(seg[1:])
        else:
            full_path.extend(seg)
        segments.append(seg)
        order.append(best)
        cur = best
        remaining.remove(best)

    return full_path, segments, order


# ----------------------------------------------------------------------
# API pública (para los requisitos del ejercicio)
# ----------------------------------------------------------------------
def _coerce_maze(maze: Union[List[str], List[List[int]]]) -> List[List[int]]:
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
                    # '0', '.', 'G' u otros se asumen piso
                    o.append(0)
            out.append(o)
        return out
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
    Encuentra una ruta mínima desde `start` hasta el primer ítem `item_type` en un
    mapa textual. Implementado con BFS. Útil para ejemplo/compatibilidad.
    """
    if item_type not in ITEM_TYPES:
        raise ValueError(f"item_type desconocido: {item_type}")

    t0 = timeit.default_timer()

    goal: Optional[Tuple[int, int]] = None
    maze_grid = _coerce_maze(maze)

    if maze and isinstance(maze[0], str):
        goal = _find_first_char(maze, ITEM_TYPES[item_type]["char"])

    if goal is None:
        t1 = timeit.default_timer()
        return None, {"steps": 0, "time_s": t1 - t0, "reachable": False, "item": item_type}

    path = _bfs_path(maze_grid, start, goal)
    t1 = timeit.default_timer()
    if path is None:
        return None, {"steps": 0, "time_s": t1 - t0, "reachable": False, "item": item_type}

    steps = len(path) - 1
    if not return_moves:
        return path, {"steps": steps, "time_s": t1 - t0, "reachable": True, "item": item_type}

    # movimientos
    moves: List[str] = []
    dir_map = {(-1, 0): "U", (1, 0): "D", (0, -1): "L", (0, 1): "R"}
    for (r1, c1), (r2, c2) in zip(path[:-1], path[1:]):
        dr, dc = (r2 - r1, c2 - c1)
        moves.append(dir_map[(dr, dc)])
    return moves, {"steps": steps, "time_s": t1 - t0, "reachable": True, "item": item_type}


# ----------------------------------------------------------------------
# Vistas de Arcade (multi-gema)
# ----------------------------------------------------------------------
class InstructionView(arcade.View):
    def __init__(self):
        super().__init__()
        self.frame_count = 0
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
    Juego principal. Recolecta varias gemas en orden de cercanía (BFS codicioso).
    Teclas:
      F  - recalcular plan desde la posición actual hacia las gemas restantes
      F1 - regenerar mapa y resembrar gemas
      G  - resembrar gemas (mismo mapa)
      ESC- salir
    """

    def __init__(self):
        super().__init__()
        self.grid: Optional[List[List[int]]] = None
        self.wall_list: Optional[arcade.SpriteList] = None
        self.player_list: Optional[arcade.SpriteList] = None
        self.player_sprite: Optional[arcade.Sprite] = None

        # Ítems
        self.item_list: Optional[arcade.SpriteList] = None
        self.item_rcs: List[Tuple[int, int]] = []   # todas las gemas (r,c) restantes

        self.draw_time = 0.0
        self.processing_time = 0.0
        self.physics_engine: Optional[arcade.PhysicsEngineSimple] = None

        # HUD
        self.sprite_count_text: Optional[arcade.Text] = None
        self.draw_time_text: Optional[arcade.Text] = None
        self.processing_time_text: Optional[arcade.Text] = None
        self.path_info_text: Optional[arcade.Text] = None
        self.item_state_text: Optional[arcade.Text] = None

        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()
        self.window.background_color = arcade.color.BLACK

        # Navegación
        self.waypoints: deque[Tuple[float, float]] = deque()
        self.plan_segments_world: List[List[Tuple[float, float]]] = []  # para dibujar por tramo
        self.total_planned_steps: int = 0
        self.last_plan_time: float = 0.0

    # --- conversión de coordenadas ---
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
        h, w = len(self.grid), len(self.grid[0])
        while True:
            r = random.randrange(h)
            c = random.randrange(w)
            if self.grid[r][c] == 0:
                return (r, c)

    def _nearest_free_cell(self, r: int, c: int) -> Tuple[int, int]:
        """Si (r,c) cae en pared, devuelve la celda libre más cercana (BFS)."""
        assert self.grid is not None
        if self.grid[r][c] == 0:
            return r, c
        h, w = len(self.grid), len(self.grid[0])
        q = deque([(r, c)])
        seen = {(r, c)}
        while q:
            rr, cc = q.popleft()
            for nr, nc in _neighbors_4(rr, cc):
                if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen:
                    if self.grid[nr][nc] == 0:
                        return nr, nc
                    seen.add((nr, nc))
                    q.append((nr, nc))
        return r, c

    # --- gemas ---
    def _clear_gems(self):
        if self.item_list:
            for s in list(self.item_list):
                s.remove_from_sprite_lists()
        self.item_rcs.clear()

    def _spawn_gems(self, n: int):
        """Coloca n gemas en celdas libres distintas. Evita duplicados/colisiones."""
        assert self.item_list is not None and self.grid is not None
        placed = set()
        tries = 0
        while len(placed) < n and tries < n * 100:
            tries += 1
            rc = self._place_random_free_cell()
            if rc in placed:
                continue
            r, c = rc
            x, y = self._grid_to_world(r, c)
            gem = arcade.Sprite(ITEM_TYPES["GEM"]["texture"], scale=SPRITE_SCALING)
            gem.center_x = x
            gem.center_y = y
            self.item_list.append(gem)
            placed.add(rc)
        self.item_rcs = list(placed)

    # --- setup y dibujo ---
    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.item_list = arcade.SpriteList()

        # Generar cueva
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

        # Posición inicial libre
        placed = False
        max_x = int(GRID_WIDTH * SPRITE_SIZE)
        max_y = int(GRID_HEIGHT * SPRITE_SIZE)
        while not placed:
            self.player_sprite.center_x = random.randrange(max_x)
            self.player_sprite.center_y = random.randrange(max_y)
            walls_hit = arcade.check_for_collision_with_list(self.player_sprite, self.wall_list)
            if len(walls_hit) == 0:
                placed = True

        # Gemas
        self._clear_gems()
        self._spawn_gems(NUM_GEMS)

        # HUD
        sprite_count = len(self.wall_list)
        self.sprite_count_text = arcade.Text(f"Sprite Count: {sprite_count:,}", 20, self.window.height - 20, arcade.color.WHITE, 16)
        self.draw_time_text = arcade.Text("Drawing time:", 20, self.window.height - 40, arcade.color.WHITE, 16)
        self.processing_time_text = arcade.Text("Processing time:", 20, self.window.height - 60, arcade.color.WHITE, 16)
        self.path_info_text = arcade.Text("Route: -", 20, self.window.height - 80, arcade.color.WHITE, 16)
        self.item_state_text = arcade.Text("Gems: -", 20, self.window.height - 100, arcade.color.WHITE, 16)

        self.physics_engine = arcade.PhysicsEngineSimple(self.player_sprite, self.wall_list)
        self.scroll_to_player(1.0)

        # Plan automático al iniciar
        self._plan_and_follow_all_gems()

    def on_draw(self):
        draw_start = timeit.default_timer()
        self.clear()

        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        if self.item_list and len(self.item_list) > 0:
            self.item_list.draw(pixelated=True)
        self.player_list.draw()

        # Dibujo del camino planificado (polilínea)
        if self.plan_segments_world:
            # dibuja cada segmento con líneas
            for seg in self.plan_segments_world:
                if len(seg) < 2:
                    continue
                for (x1, y1), (x2, y2) in zip(seg[:-1], seg[1:]):
                    arcade.draw_line(x1, y1, x2, y2, arcade.color.CYAN, line_width=2)

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

    # --- movimiento ---
    def _update_player_speed_keys(self):
        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0
        # si hay waypoints, no usamos flechas
        if self.waypoints:
            return
        # manual
        if arcade.key.UP in self.window.keyboard.modifiers:  # no usado; solo ejemplo
            pass
        # En realidad usamos flags por on_key_press/release:
        # mantengo la lógica para input manual estándar
        # (se conservaron flags en versión anterior)
        # Aquí, por simplicidad, dejamos el movimiento guiado por waypoints.

    def _follow_waypoints(self):
        if not self.waypoints or self.player_sprite is None:
            return
        tx, ty = self.waypoints[0]
        px, py = self.player_sprite.center_x, self.player_sprite.center_y
        dx = tx - px
        dy = ty - py
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= MOVEMENT_SPEED:
            self.player_sprite.center_x = tx
            self.player_sprite.center_y = ty
            self.waypoints.popleft()
        else:
            self.player_sprite.center_x += MOVEMENT_SPEED * dx / dist
            self.player_sprite.center_y += MOVEMENT_SPEED * dy / dist

    def on_update(self, delta_time: float):
        start_t = timeit.default_timer()

        # Seguir plan si existe
        self._follow_waypoints()

        self.physics_engine.update()
        self.scroll_to_player(CAMERA_SPEED)

        # Recolección: eliminar sprites de gemas colisionadas
        if self.item_list and len(self.item_list) > 0:
            hits = arcade.check_for_collision_with_list(self.player_sprite, self.item_list)
            if hits:
                for s in hits:
                    s.remove_from_sprite_lists()
                # quitar de la lista lógica
                px, py = self.player_sprite.center_x, self.player_sprite.center_y
                pr, pc = self._world_to_grid(px, py)
                # borrar cualquier gema cuya celda coincida
                self.item_rcs = [(r, c) for (r, c) in self.item_rcs if (r, c) != (pr, pc)]
                self.item_state_text.text = f"Gems left: {len(self.item_rcs)}"
                # si ya no hay gems, limpiar waypoints
                if not self.item_rcs:
                    self.waypoints.clear()
                    self.plan_segments_world.clear()

        self.processing_time = timeit.default_timer() - start_t

    # --- cámara y resize ---
    def scroll_to_player(self, camera_speed: float):
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(self.camera_sprites.position, position, camera_speed)

    def on_resize(self, width: int, height: int):
        super().on_resize(width, height)
        self.camera_sprites.match_window()
        self.camera_gui.match_window()

    # --- entrada de teclado ---
    def on_key_press(self, key, modifiers):
        if key == arcade.key.F:
            self._plan_and_follow_all_gems()
        elif key == arcade.key.F1:
            self.setup()
        elif key == arcade.key.G:
            # resembrar gemas (mismo mapa)
            self._clear_gems()
            self._spawn_gems(NUM_GEMS)
            self._plan_and_follow_all_gems()
        elif key == arcade.key.ESCAPE:
            arcade.exit()

    # --- planeación multi-gema ---
    def _plan_and_follow_all_gems(self):
        """Planifica ruta a todas las gemas restantes y genera waypoints."""
        if self.grid is None or self.player_sprite is None:
            return
        t0 = timeit.default_timer()

        # origen (asegura celda libre)
        pr, pc = self._world_to_grid(self.player_sprite.center_x, self.player_sprite.center_y)
        pr, pc = self._nearest_free_cell(pr, pc)

        # si no hay gemas, limpiar
        if not self.item_rcs:
            self.waypoints.clear()
            self.plan_segments_world.clear()
            self.total_planned_steps = 0
            self.last_plan_time = 0.0
            self.path_info_text.text = "Route: (no gems)"
            self.item_state_text.text = "Gems left: 0"
            return

        # plan codicioso BFS
        full_path, segments, order = _bfs_multi_target_plan(self.grid, (pr, pc), self.item_rcs)

        # Si no alcanzó ninguna, informar
        if len(order) == 0:
            t1 = timeit.default_timer()
            self.waypoints.clear()
            self.plan_segments_world.clear()
            self.total_planned_steps = 0
            self.last_plan_time = t1 - t0
            self.path_info_text.text = f"Route: none reachable (t={self.last_plan_time:.4f}s)"
            self.item_state_text.text = f"Gems left: {len(self.item_rcs)}"
            return

        # Generar waypoints (omitiendo la celda actual)
        self.waypoints.clear()
        self.plan_segments_world.clear()
        total_steps = 0
        for seg in segments:
            if not seg:
                continue
            total_steps += (len(seg) - 1)
            seg_world: List[Tuple[float, float]] = [self._grid_to_world(r, c) for (r, c) in seg]
            self.plan_segments_world.append(seg_world)
            # no repetir el primer punto si coincide con la posición actual/ruta previa
            for idx, (r, c) in enumerate(seg[1:], start=1):
                self.waypoints.append(self._grid_to_world(r, c))

        t1 = timeit.default_timer()
        self.total_planned_steps = total_steps
        self.last_plan_time = t1 - t0
        self.path_info_text.text = f"Route: steps={total_steps}  plan_time={self.last_plan_time:.4f}s"
        self.item_state_text.text = f"Gems left: {len(self.item_rcs)}"


# ----------------------------------------------------------------------
# Ejemplo CLI reproducible
# ----------------------------------------------------------------------
def _example_cli():
    """
    Ejemplo reproducible (sin Arcade). Dos gemas; planea en orden de cercanía.
    """
    # 0=piso, 1=pared
    grid = [
        [1,1,1,1,1,1,1],
        [1,0,0,0,0,0,1],
        [1,0,1,1,1,0,1],
        [1,0,0,0,0,0,1],
        [1,1,1,1,1,1,1],
    ]
    start = (3, 1)
    gems = [(1,3), (1,5)]

    t0 = timeit.default_timer()
    full_path, segments, order = _bfs_multi_target_plan(grid, start, gems)
    t1 = timeit.default_timer()

    steps = max(0, len(full_path)-1)
    print("=== EJEMPLO CLI MULTI-GEMA ===")
    print("Start:", start)
    print("Gems :", gems)
    print("Order:", order)
    print("Total steps:", steps)
    print("Plan time (s):", round(t1 - t0, 6))
    # Caso simple: debe visitar ambas gemas en orden (1,3) luego (1,5)
    assert order and order[0] == (1,3)
    print("✔ Caso de prueba OK")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Procedural caves + multi-gem BFS greedy")
    parser.add_argument("--example", action="store_true", help="Ejecuta ejemplo/PRUEBA en consola")
    args = parser.parse_args()

    if args.example:
        _example_cli()
        return

    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = InstructionView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
