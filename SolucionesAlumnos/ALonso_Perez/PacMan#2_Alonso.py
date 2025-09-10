#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PacMan_Alonso.py — Ejercicio 4 (autónomo + evasión de enemigos + compat Arcade 2.x/3.x)

Basado en tu archivo original del Ejercicio 2. Se mantiene la lógica base de
render, sprites, mapa y ejecución; solo se **añade** una capa de planificación
segura en tiempo real para **evitar fantasmas** y **completar la recolección**.

Cambios mínimos:
- Se agrega un planificador A* en espacio-tiempo con horizonte limitado y
  "mapa de amenaza" dinámico por fantasmas.
- Replanning frecuente (cada N ticks) y margen de seguridad.
- Con poder activo, se reduce el peso de la amenaza para permitir pasar/comer.
- Reporte al final si quedan pellets no alcanzados y causa estimada.

Cómo corre (igual que tu base):
  python PacMan_Alonso.py

Parámetros de la IA (ajustables en el código):
  AI_HORIZON = 12        # profundidad temporal
  AI_SAFETY  = 1         # radio de seguridad en celdas
  AI_REPLAN_EVERY = 1    # replantear cada N frames
  AI_POWER_THREAT_SCALE = 0.15  # factor de amenaza cuando hay poder

"""

import time
import random
from dataclasses import dataclass
from collections import deque
from typing import List, Tuple, Iterable, Optional, Set, Dict

import arcade

# =================== SKIN / INTERFAZ ===================
PACMAN_COLOR = arcade.color.YELLOW
WALL_COLOR   = arcade.color.DARK_BLUE
PELLET_COLOR = arcade.color.LIGHT_YELLOW
GHOST_COLORS = [
    arcade.color.RED,
    arcade.color.SPRING_GREEN,
    arcade.color.PURPLE,
    arcade.color.PINK,
]
# =======================================================

# =================== CONFIG GENERAL ====================
SCREEN_TITLE = "PacGPT5 (Auto)"
TILE_SIZE = 28
MOVEMENT_SPEED = 4   # px/frame
GHOST_SPEED = 2
POWER_TIME = 7.0
FPS = 60

# Parámetros de IA (puedes ajustarlos)
AI_HORIZON = 12
AI_SAFETY = 1
AI_REPLAN_EVERY = 1
AI_POWER_THREAT_SCALE = 0.15
AI_DIAG = False  # en este juego solo 4 direcciones
# Anti-oscilación
AI_LOOP_PENALTY = 0.6   # costo extra por re-visitar celdas recientes (sube si aún se cicla)
AI_LOOP_MEMORY = 6      # cuántos estados recordar para evitar bucles cortos
AI_OSC_SAFETY_BOOST = 1 # +celdas de seguridad temporales si se detecta bucle
# =======================================================

# =================== COMPAT DIBUJO (Arcade 2.x / 3.x) ===================
def _rect_filled(x: float, y: float, w: float, h: float, color):
    """Dibuja un rectángulo lleno sin depender de la versión de Arcade."""
    if hasattr(arcade, "draw_rectangle_filled"):
        arcade.draw_rectangle_filled(x, y, w, h, color)
    else:
        # Arcade 3.x
        arcade.draw_rect_filled(arcade.rect.XYWH(x, y, w, h), color)


def _circle_filled(x: float, y: float, r: float, color):
    if hasattr(arcade, "draw_circle_filled"):
        arcade.draw_circle_filled(x, y, r, color)
    else:
        # Fallback simple con elipse
        arcade.draw_ellipse_filled(x, y, 2*r, 2*r, color)


def _arc_filled(x: float, y: float, w: float, h: float, color, start_angle: float, end_angle: float):
    if hasattr(arcade, "draw_arc_filled"):
        arcade.draw_arc_filled(x, y, w, h, color, start_angle, end_angle)
    else:
        # Si no está disponible, omitimos la boca (no es crítica)
        _rect_filled(x, y, w, h, color)
# ========================================================================

# =================== MAPA DEMO =========================
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
# =======================================================


# ================ GRID <-> PANTALLA ====================
def grid_to_pixel(col: int, row: int, rows: int, tile: int) -> Tuple[int, int]:
    x = col * tile + tile // 2
    y = (rows - row - 1) * tile + tile // 2
    return x, y


def pixel_to_grid(x: float, y: float, rows: int, tile: int) -> Tuple[int, int]:
    col = int(x // tile)
    row_from_bottom = int(y // tile)
    row = rows - row_from_bottom - 1
    return col, row


def is_center_of_cell(sprite: arcade.Sprite, rows: int, tile: int) -> bool:
    col, row = pixel_to_grid(sprite.center_x, sprite.center_y, rows, tile)
    cx, cy = grid_to_pixel(col, row, rows, tile)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2


# =================== PARSER DE MAPA =====================
def parse_maze(
    lines: List[str],
    wall: str = '#',
    empty: str = ' ',
    pellet: str = '.',
    start: str = 'P',
    ghost: str = 'G',
):
    """Asegura rectángulo (acolchona filas cortas con pared) y devuelve grid y entidades."""
    grid = [list(r.rstrip('')) for r in lines]
    maxC = max((len(r) for r in grid), default=0)
    for row in grid:
        if len(row) < maxC:
            row.extend(list(wall * (maxC - len(row))))
    R, C = len(grid), maxC

    start_pos = None
    pellets: Set[Tuple[int, int]] = set()
    ghosts: List[Tuple[int, int]] = []

    for r in range(R):
        for c in range(C):
            ch = grid[r][c]
            if ch == start:
                if start_pos is None:
                    start_pos = (r, c)
                    grid[r][c] = empty
                else:
                    pellets.add((r, c))
                    grid[r][c] = pellet
            elif ch == pellet:
                pellets.add((r, c))
            elif ch == ghost:
                ghosts.append((r, c))
                grid[r][c] = empty
            elif ch in (wall, empty, 'o'):
                pass
            else:
                grid[r][c] = empty

    if start_pos is None:
        raise ValueError("Falta posición inicial 'P'.")

    return grid, start_pos, pellets, ghosts, (R, C)


# ================ SOLVER (BFS REPETIDA) =================
def neighbors(r: int, c: int) -> Iterable[Tuple[int, int, str]]:
    return (
        (r - 1, c, 'U'),
        (r + 1, c, 'D'),
        (r, c - 1, 'L'),
        (r, c + 1, 'R'),
    )


def in_bounds(r: int, c: int, R: int, C: int) -> bool:
    return 0 <= r < R and 0 <= c < C


def bfs_to_nearest_pellet(
    grid: List[List[str]],
    start: Tuple[int, int],
    wall_char: str,
    pellet_char: str = '.',
) -> Optional[Tuple[List[str], List[Tuple[int, int]], Tuple[int, int]]]:
    R, C = len(grid), len(grid[0]) if grid else 0
    q = deque([start])
    prev: dict[Tuple[int, int], Tuple[Optional[Tuple[int, int]], Optional[str]]] = {
        start: (None, None)
    }
    target: Optional[Tuple[int, int]] = None

    while q:
        cur = q.popleft()
        if grid[cur[0]][cur[1]] == pellet_char:
            target = cur
            break
        r, c = cur
        for nr, nc, mv in neighbors(r, c):
            if not in_bounds(nr, nc, R, C): continue
            if grid[nr][nc] == wall_char:   continue
            if (nr, nc) in prev:            continue
            prev[(nr, nc)] = (cur, mv)
            q.append((nr, nc))

    if target is None:
        return None

    # reconstrucción
    moves: List[str] = []
    path: List[Tuple[int, int]] = []
    cur = target
    while True:
        path.append(cur)
        p, mv = prev[cur]
        if p is None: break
        moves.append(mv)  # type: ignore
        cur = p
    moves.reverse()
    path.reverse()
    return moves, path, target


def solve(
    maze_lines: List[str],
    start_symbol: str = 'P',
    wall_symbol: str = '#',
    empty_symbol: str = ' ',
    pellet_symbol: str = '.',
    ghost_symbol: str = 'G',
):
    """
    Devuelve: (path[UDLR], visited[(r,c)], steps, elapsed_s, pellets_restantes)
    (Se mantiene para compatibilidad, aunque ahora el autopiloto se replantea en tiempo real.)
    """
    t0 = time.perf_counter()
    grid, start, _pellets, _ghosts, (R, C) = parse_maze(
        maze_lines, wall=wall_symbol, empty=empty_symbol,
        pellet=pellet_symbol, start=start_symbol, ghost=ghost_symbol
    )

    pos = start
    total_moves: List[str] = []
    visited: List[Tuple[int, int]] = [pos]

    def pellets_remaining() -> int:
        return sum(row.count(pellet_symbol) for row in ("".join(r) for r in grid))

    while pellets_remaining() > 0:
        res = bfs_to_nearest_pellet(grid, pos, wall_char=wall_symbol, pellet_char=pellet_symbol)
        if res is None:
            break  # pellets inaccesibles
        moves, coords, end_pos = res

        er, ec = end_pos
        if grid[er][ec] == pellet_symbol:
            grid[er][ec] = empty_symbol

        total_moves.extend(moves)
        if coords and coords[0] == visited[-1]:
            visited.extend(coords[1:])
        else:
            visited.extend(coords)
        pos = end_pos

    elapsed = time.perf_counter() - t0
    remaining = pellets_remaining()
    return total_moves, visited, len(total_moves), elapsed, remaining


# =================== SPRITES ============================
@dataclass
class GhostState:
    normal_color: Tuple[int, int, int]
    frightened_color: Tuple[int, int, int] = arcade.color.BLUE


class Pacman(arcade.Sprite):
    def __init__(self, col: int, row: int, rows: int, tile: int, color=(255, 255, 0)):
        super().__init__()
        # textura base (aunque dibujamos manual, dejamos textura por compatibilidad)
        self.texture = arcade.make_soft_square_texture(tile, arcade.color.WHITE, 255)
        self.color = color
        self.center_x, self.center_y = grid_to_pixel(col, row, rows, tile)
        self.rows = rows
        self.tile = tile
        self.current_dir = (0, 0)
        self.desired_dir = (0, 0)
        self.lives = 3
        self.score = 0
        self.power_timer = 0.0

    def set_direction(self, dx: int, dy: int):
        self.desired_dir = (dx, dy)

    def update_move(self, walls_grid):
        if is_center_of_cell(self, self.rows, self.tile):
            if self.can_move(self.desired_dir, walls_grid):
                self.current_dir = self.desired_dir
            if not self.can_move(self.current_dir, walls_grid):
                self.current_dir = (0, 0)
            col, row = pixel_to_grid(self.center_x, self.center_y, self.rows, self.tile)
            self.center_x, self.center_y = grid_to_pixel(col, row, self.rows, self.tile)
        self.center_x += self.current_dir[0] * MOVEMENT_SPEED
        self.center_y += self.current_dir[1] * MOVEMENT_SPEED

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        if dx == 0 and dy == 0:
            return True
        col, row = pixel_to_grid(self.center_x, self.center_y, self.rows, self.tile)
        tcol = col + dx
        trow = row - dy
        if tcol < 0 or tcol >= len(walls_grid[0]) or trow < 0 or trow >= len(walls_grid):
            return False
        return walls_grid[trow][tcol] == 0

    # --- Dibujo manual (compat 2.x/3.x) ---
    def draw(self):
        _rect_filled(self.center_x, self.center_y, self.tile, self.tile, self.color)
        # “boca” tipo pac-man (opcional)
        _arc_filled(self.center_x, self.center_y, self.tile, self.tile, self.color, 30, 330)


class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, rows: int, tile: int, state: GhostState):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(tile, arcade.color.WHITE, 255)
        self.color = state.normal_color
        self.center_x, self.center_y = grid_to_pixel(col, row, rows, tile)
        self.spawn_col = col
        self.spawn_row = row
        self.rows = rows
        self.tile = tile
        self.state = state
        self.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
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
            return

        if self.frightened:
            self.color = self.state.frightened_color
            if self.change_counter > 0.4:
                self.current_dir = self._random_dir(walls_grid)
                self.change_counter = 0.0
        else:
            self.color = self.state.normal_color
            if self.change_counter > 0.3:
                self.current_dir = self._chase_dir(pacman, walls_grid)
                self.change_counter = 0.0

        if is_center_of_cell(self, self.rows, self.tile):
            if not self._can_dir(self.current_dir, walls_grid):
                self.current_dir = self._random_dir(walls_grid)
            col, row = pixel_to_grid(self.center_x, self.center_y, self.rows, self.tile)
            self.center_x, self.center_y = grid_to_pixel(col, row, self.rows, self.tile)

        self.center_x += self.current_dir[0] * speed
        self.center_y += self.current_dir[1] * speed

    def _at_target(self, target_cell):
        col, row = pixel_to_grid(self.center_x, self.center_y, self.rows, self.tile)
        return (col, row) == target_cell

    def _move_towards(self, target_cell, walls_grid, speed):
        if is_center_of_cell(self, self.rows, self.tile):
            col, row = pixel_to_grid(self.center_x, self.center_y, self.rows, self.tile)
            tcol, trow = target_cell
            options = []
            if tcol > col: options.append((1, 0))
            if tcol < col: options.append((-1, 0))
            if trow > row: options.append((0, -1))
            if trow < row: options.append((0, 1))
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
        col, row = pixel_to_grid(self.center_x, self.center_y, self.rows, self.tile)
        pcol, prow = pixel_to_grid(pacman.center_x, pacman.center_y, self.rows, self.tile)
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
        col, row = pixel_to_grid(self.center_x, self.center_y, self.rows, self.tile)
        tcol = col + dx
        trow = row - dy
        if tcol < 0 or tcol >= len(walls_grid[0]) or trow < 0 or trow >= len(walls_grid):
            return False
        return walls_grid[trow][tcol] == 0

    def eaten(self):
        self.dead = True
        self.frightened = False
        self.color = arcade.color.GRAY

    # --- Dibujo manual (compat 2.x/3.x) ---
    def draw(self):
        _rect_filled(self.center_x, self.center_y, self.tile, self.tile, self.color)
        # ojitos
        _circle_filled(self.center_x - 5, self.center_y + 5, 3, arcade.color.WHITE)
        _circle_filled(self.center_x + 5, self.center_y + 5, 3, arcade.color.WHITE)
        _circle_filled(self.center_x - 5, self.center_y + 5, 1, arcade.color.BLACK)
        _circle_filled(self.center_x + 5, self.center_y + 5, 1, arcade.color.BLACK)


# =================== IA: PLANIFICADOR SEGURO ==================
CARDINAL = [(1,0), (-1,0), (0,1), (0,-1)]
DIAGONAL = [(1,1), (1,-1), (-1,1), (-1,-1)]
Vec = Tuple[int,int]


def manhattan(a: Vec, b: Vec) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def neighborhood(diag: bool=False):
    return CARDINAL + (DIAGONAL if diag else [])


def predict_ghost_paths(ghosts: List[Vec], is_free, rows, cols, H: int, diag=False) -> List[List[Vec]]:
    """Predicción simple: vecinos libres + quedarse. Usa el estado actual."""
    N = neighborhood(diag)
    paths = []
    for gpos in ghosts:
        path = [gpos]
        cur = gpos
        for _ in range(H):
            candidates = [cur]
            for dr, dc in N:
                nr, nc = cur[0]+dr, cur[1]+dc
                if 0 <= nr < rows and 0 <= nc < cols and is_free(nr, nc):
                    candidates.append((nr, nc))
            cur = random.choice(candidates)
            path.append(cur)
        paths.append(path)
    return paths


def build_threat_map(ghost_paths: List[List[Vec]], rows:int, cols:int, H:int, safety_radius:int) -> List[List[List[float]]]:
    threat = [[[0.0 for _ in range(cols)] for _ in range(rows)] for _ in range(H+1)]
    for t in range(H+1):
        for gpath in ghost_paths:
            gp = gpath[t] if t < len(gpath) else gpath[-1]
            gr, gc = gp
            for r in range(max(0, gr - safety_radius), min(rows, gr + safety_radius + 1)):
                for c in range(max(0, gc - safety_radius), min(cols, gc + safety_radius + 1)):
                    d = manhattan((r, c), (gr, gc))
                    if d <= safety_radius:
                        threat[t][r][c] += 1.0 / (1 + d)
    return threat


def astar_time_safe(start: Vec, goals: Set[Vec], *, is_free, rows, cols,
                    H:int, threat, diag=False, power_left:bool=False, threat_scale:float=1.0,
                    recent_avoid: Optional[Set[Vec]] = None, loop_penalty: float = 0.0) -> Optional[List[Vec]]:
    if not goals: return None
    N = neighborhood(diag)

    def goal_score(p: Vec):
        h = manhattan(start, p)
        approx = 0.0
        T = min(H, max(1,h))
        for i in range(T+1):
            pr = start[0] + (p[0]-start[0]) * i // max(1, T)
            pc = start[1] + (p[1]-start[1]) * i // max(1, T)
            approx += threat_scale * threat[min(i,H)][pr][pc]
        return h + approx

    target = min(goals, key=goal_score)

    open_heap: List[Tuple[float,float,Tuple[int,int,int]]] = []
    parents: Dict[Tuple[int,int,int], Tuple[int,int,int]] = {}
    g_cost: Dict[Tuple[int,int,int], float] = {}

    start_node = (start[0], start[1], 0)
    g_cost[start_node] = 0.0

    def hfun(r,c,t):
        return manhattan((r,c), target)

    def cell_cost(t,r,c):
        th = threat[min(t, H)][r][c]
        cost = (threat_scale * th) if not power_left else (threat_scale * th * AI_POWER_THREAT_SCALE)
        if recent_avoid and (r,c) in recent_avoid:
            cost += loop_penalty
        return cost

    import heapq
    heapq.heappush(open_heap, (hfun(*start,0), 0.0, start_node))
    visited: Set[Tuple[int,int,int]] = set()

    while open_heap:
        f, g, (r,c,t) = heapq.heappop(open_heap)
        if (r,c) == target:
            path = [(r,c)]
            cur = (r,c,t)
            while cur in parents:
                cur = parents[cur]
                path.append((cur[0], cur[1]))
            path.reverse()
            compact: List[Vec] = []
            for pos in path:
                if not compact or compact[-1] != pos:
                    compact.append(pos)
            return compact

        if (r,c,t) in visited: continue
        visited.add((r,c,t))
        if t >= H: continue

        for dr, dc in N + [(0,0)]:  # permitir esperar
            nr, nc, nt = r+dr, c+dc, t+1
            if not (0 <= nr < rows and 0 <= nc < cols and is_free(nr, nc)):
                continue
            ng = g + 1.0 + cell_cost(nt, nr, nc)
            node = (nr, nc, nt)
            if node not in g_cost or ng < g_cost[node]:
                g_cost[node] = ng
                parents[node] = (r, c, t)
                nf = ng + hfun(nr, nc, nt)
                heapq.heappush(open_heap, (nf, ng, node))

    return None


@dataclass
class SafeCollectorAgent:
    horizon: int = AI_HORIZON
    safety_radius: int = AI_SAFETY
    replan_every: int = AI_REPLAN_EVERY

    _cached_plan: List[Vec] = None
    _last_replan_tick: int = -10**9
    _recent: List[Vec] = None
    _last_pellet_count: int = -1

    def decide(self, *, pac_pos: Vec, ghosts: List[Vec], pellets: Set[Vec], is_free, rows:int, cols:int, tick:int, power_active:bool) -> Tuple[int,int]:
        if not pellets:
            return (0,0)

        # memoria reciente para evitar bucles (ABAB, etc.)
        if self._recent is None:
            self._recent = []
        self._recent.append(pac_pos)
        if len(self._recent) > AI_LOOP_MEMORY:
            self._recent.pop(0)
        recent_avoid: Set[Vec] = set(self._recent[-AI_LOOP_MEMORY:]) if self._recent else set()

        # si acabamos de comer un pellet, forzar replanning total
        pellet_count = len(pellets)
        if self._last_pellet_count != -1 and pellet_count < self._last_pellet_count:
            self._cached_plan = None
        self._last_pellet_count = pellet_count

        need_replan = (tick - self._last_replan_tick) >= self.replan_every
        if self._cached_plan is None or need_replan or (self._cached_plan and self._cached_plan[0] != pac_pos):
            # Detectar posible oscilación (si las dos últimas posiciones se repiten)
            osc = False
            if len(self._recent) >= 4 and self._recent[-1] == self._recent[-3] and self._recent[-2] == self._recent[-4]:
                osc = True
            H = self.horizon + (2 if osc else 0)
            safety = self.safety_radius + (AI_OSC_SAFETY_BOOST if osc else 0)
            gpaths = predict_ghost_paths(ghosts, is_free, rows, cols, H, AI_DIAG)
            threat = build_threat_map(gpaths, rows, cols, H, safety)
            # Si hay poder, reducir fuertemente la amenaza
            threat_scale = 1.0
            if power_active:
                threat_scale = AI_POWER_THREAT_SCALE
            path = astar_time_safe(pac_pos, pellets, is_free=is_free, rows=rows, cols=cols,
                                   H=H, threat=threat, diag=AI_DIAG,
                                   power_left=power_active, threat_scale=threat_scale,
                                   recent_avoid=recent_avoid, loop_penalty=AI_LOOP_PENALTY)
            if path and len(path) >= 2:
                self._cached_plan = path[1:]
            else:
                self._cached_plan = []
            self._last_replan_tick = tick

        if self._cached_plan:
            nxt = self._cached_plan.pop(0)
            dr = (1 if nxt[0] > pac_pos[0] else -1 if nxt[0] < pac_pos[0] else 0)
            dc = (1 if nxt[1] > pac_pos[1] else -1 if nxt[1] < pac_pos[1] else 0)
            return (dc, -dr) if False else (dc, -dr)  # convertimos (row,col)->(dx,dy grid pantalla)

        # Fallback: elegir vecina más segura y cercana a algún pellet
        H = max(2, self.horizon//3)
        gpaths = predict_ghost_paths(ghosts, is_free, rows, cols, H, AI_DIAG)
        threat = build_threat_map(gpaths, rows, cols, H, self.safety_radius)
        best = (float('inf'), (0,0))
        recent_avoid = set(self._recent[-AI_LOOP_MEMORY:]) if self._recent else set()
        for (dcol, drow) in CARDINAL + (DIAGONAL if AI_DIAG else []):
            nr, nc = pac_pos[0]+drow, pac_pos[1]+dcol
            if 0 <= nr < rows and 0 <= nc < cols and is_free(nr,nc):
                cost = sum(threat[t][nr][nc] for t in range(min(H, 3)))
                if (nr,nc) in recent_avoid:
                    cost += AI_LOOP_PENALTY
                dist = min((manhattan((nr,nc), p) for p in pellets)) if pellets else 0
                score = cost + dist
                if score < best[0]:
                    best = (score, (dcol, -drow))
        return best[1]

    def report_unreached(self, remaining: Set[Vec]) -> Dict[str, object]:
        return {"remaining_pellets": sorted(list(remaining)), "cause": "Bloqueo dinámico por fantasmas o riesgo alto persistente (horizonte finito)"}

SAFE_AGENT = SafeCollectorAgent()


# =================== JUEGO (AUTÓNOMO) ==================
class PacGPT5(arcade.Window):
    def __init__(self, maze_lines: List[str]):
        rows, cols = len(maze_lines), max(len(r) for r in maze_lines)
        super().__init__(cols * TILE_SIZE, rows * TILE_SIZE, SCREEN_TITLE, update_rate=1 / FPS)
        arcade.set_background_color(arcade.color.BLACK)

        self.rows = rows
        self.cols = cols
        self.tile = TILE_SIZE

        # Lógica mapa
        self.grid, self.start_rc, self.pellets_rc, self.ghosts_rc, _ = parse_maze(maze_lines)
        self.walls_grid = [[1 if ch == '#' else 0 for ch in row] for row in self.grid]

        # Sprites
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts: List[Ghost] = []
        self.pacman: Optional[Pacman] = None

        # Estado
        self.state = "PLAY"  # PLAY, WIN, LOSE
        self.tick = 0

        # Autopiloto con evasión
        self.autopilot = True
        self.solver_time = 0.0
        self.metrics_printed = False

        self._build_world()
        self._compute_initial_plan_stats()  # conserva métricas del BFS original

    def _build_world(self):
        for r in range(self.rows):
            for c in range(self.cols):
                ch = self.grid[r][c]
                x, y = grid_to_pixel(c, r, self.rows, self.tile)
                if ch == '#':
                    s = arcade.SpriteSolidColor(self.tile, self.tile, WALL_COLOR)
                    s.center_x, s.center_y = x, y
                    self.wall_list.append(s)
                elif ch == '.':
                    p = arcade.SpriteSolidColor(6, 6, PELLET_COLOR)
                    p.center_x, p.center_y = x, y
                    self.pellet_list.append(p)
                elif ch == 'o':
                    pw = arcade.SpriteSolidColor(14, 14, arcade.color.ORANGE_PEEL)
                    pw.center_x, pw.center_y = x, y
                    self.power_list.append(pw)

        sr, sc = self.start_rc
        self.pacman = Pacman(sc, sr, self.rows, self.tile, color=PACMAN_COLOR)

        for i, (gr, gc) in enumerate(self.ghosts_rc):
            col = GHOST_COLORS[i % len(GHOST_COLORS)]
            g = Ghost(gc, gr, self.rows, self.tile, GhostState(col))
            self.ghosts.append(g)

    def _compute_initial_plan_stats(self):
        # Mantener compat con tu Ejercicio 2: calcular ruta BFS estática para imprimir métricas
        lines = ["".join(row) for row in self.grid]
        sr, sc = self.start_rc
        tmp = [list(s) for s in lines]
        if 0 <= sr < len(tmp) and 0 <= sc < len(tmp[0]):
            tmp[sr][sc] = 'P'
        lines = ["".join(r) for r in tmp]
        path, visited, steps, elapsed, remaining = solve(lines)
        self.solver_time = elapsed
        print("=== AUTOPILOTO (BFS base, solo métricas) ===")
        print(f"Ruta (UDLR): {''.join(path)}")
        print(f"Pasos totales (BFS): {steps}")
        print(f"Tiempo solver (s): {elapsed:.6f}")
        print(f"Pellets restantes tras plan (BFS estático): {remaining}")

    # === Helpers de IA ===
    def _is_free(self, r:int, c:int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols and self.walls_grid[r][c] == 0

    def _pellet_cells(self) -> Set[Tuple[int,int]]:
        # A partir de sprite-lists actuales (incluye power pellets como objetivos)
        pts: Set[Tuple[int,int]] = set()
        for p in self.pellet_list:
            c, r = pixel_to_grid(p.center_x, p.center_y, self.rows, self.tile)
            pts.add((r,c))
        for pw in self.power_list:
            c, r = pixel_to_grid(pw.center_x, pw.center_y, self.rows, self.tile)
            pts.add((r,c))
        return pts

    def _pac_cell(self) -> Tuple[int,int]:
        c, r = pixel_to_grid(self.pacman.center_x, self.pacman.center_y, self.rows, self.tile)
        return (r,c)

    def _ghost_cells(self) -> List[Tuple[int,int]]:
        out = []
        for g in self.ghosts:
            c, r = pixel_to_grid(g.center_x, g.center_y, self.rows, self.tile)
            out.append((r,c))
        return out

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()
        if self.pacman:
            self.pacman.draw()
        for g in self.ghosts:
            g.draw()

        # UI
        if self.pacman:
            arcade.draw_text(
                f"Score: {self.pacman.score}   Vidas: {self.pacman.lives}   Poder: {max(0.0, self.pacman.power_timer):.1f}",
                10, self.height - 22, arcade.color.YELLOW, 14,
            )
        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", self.width / 2, self.height / 2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", self.width / 2, self.height / 2, arcade.color.RED, 40, anchor_x="center")

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return
        self.tick += 1

        # === PLANIFICACIÓN SEGURA EN TIEMPO REAL ===
        if self.autopilot and is_center_of_cell(self.pacman, self.rows, self.tile):
            pellets = self._pellet_cells()
            pac_rc = self._pac_cell()
            ghosts_rc = self._ghost_cells()
            dr, dc = SAFE_AGENT.decide(
                pac_pos=pac_rc,
                ghosts=ghosts_rc,
                pellets=pellets,
                is_free=self._is_free,
                rows=self.rows,
                cols=self.cols,
                tick=self.tick,
                power_active=(self.pacman.power_timer > 0.0),
            )
            # set_direction usa (dx,dy) en coordenadas de pantalla (col->x, row->-y)
            self.pacman.set_direction(dr, dc)

        # mover pacman
        self.pacman.update_move(self.walls_grid)

        # comer pellets
        pellets_hit = arcade.check_for_collision_with_list(self.pacman, self.pellet_list)
        for p in pellets_hit:
            p.remove_from_sprite_lists()
            self.pacman.score += 10

        # comer power pellets
        powers_hit = arcade.check_for_collision_with_list(self.pacman, self.power_list)
        if powers_hit:
            for pw in powers_hit:
                pw.remove_from_sprite_lists()
            self.pacman.power_timer = POWER_TIME
            for g in self.ghosts:
                if not g.dead:
                    g.frightened = True

        # mover fantasmas
        for g in self.ghosts:
            g.update_move(self.walls_grid, self.pacman, delta_time)

        # colisiones con fantasmas
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
                    break

        # decrementar poder
        if self.pacman.power_timer > 0.0:
            self.pacman.power_timer = max(0.0, self.pacman.power_timer - delta_time)
            if self.pacman.power_timer == 0.0:
                for g in self.ghosts:
                    g.frightened = False

        # victoria
        if len(self.pellet_list) == 0 and len(self.power_list) == 0:
            self.state = "WIN"
            if not self.metrics_printed:
                self.metrics_printed = True
                print("=== RESULTADOS (IA evasiva) ===")
                print(f"Tiempo de ejecución (solver BFS de referencia): {self.solver_time:.6f} s")
                print("Pellets restantes en juego: 0")

        # si perdimos y quedan pellets: reportar
        if self.state == "LOSE" and (len(self.pellet_list) or len(self.power_list)):
            remaining: Set[Tuple[int,int]] = set()
            for p in self.pellet_list:
                c, r = pixel_to_grid(p.center_x, p.center_y, self.rows, self.tile)
                remaining.add((r,c))
            for pw in self.power_list:
                c, r = pixel_to_grid(pw.center_x, pw.center_y, self.rows, self.tile)
                remaining.add((r,c))
            rep = SAFE_AGENT.report_unreached(remaining)
            print("Pellets no alcanzados:", rep["remaining_pellets"]) 
            print("Causa:", rep["cause"])

    def _reset_positions(self):
        # reset pacman
        sr, sc = self.start_rc
        self.pacman.center_x, self.pacman.center_y = grid_to_pixel(sc, sr, self.rows, self.tile)
        self.pacman.current_dir = (0, 0)
        self.pacman.desired_dir = (0, 0)
        # reset fantasmas
        for g in self.ghosts:
            g.center_x, g.center_y = grid_to_pixel(g.spawn_col, g.spawn_row, self.rows, self.tile)
            g.dead = False
            g.frightened = False
            g.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            g.color = g.state.normal_color

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.close_window()


# =================== MAIN =============================
def main():
    game = PacGPT5(RAW_MAP)
    arcade.run()


if __name__ == "__main__":
    main()
