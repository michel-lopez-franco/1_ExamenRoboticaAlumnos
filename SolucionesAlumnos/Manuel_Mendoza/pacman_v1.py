"""
PacMan.py — Ejercicios 2, 3 y 4 (Arcade 3.6) — versión con POWER y colisiones sólidas
- BFS al pellet más cercano (sin imprimir rutas/HUD).
- Fantasmas no atraviesan muros (movimiento por celdas, con snap a grid).
- Power pellet: fantasmas comibles (azul) por POWER_TIME y respawn tras ser comidos.

Controles:
- Flechas: mover (si Autopiloto OFF)
- A: Autopiloto ON/OFF (default ON)
- V: Evasión ON/OFF (default ON)
- H/J: +/− horizonte de predicción
- S/D: +/− margen de seguridad
- ESC: salir

Requisitos:
- Python 3.9+
- arcade == 3.6
"""

from __future__ import annotations
import random, time
from collections import deque
from typing import List, Tuple, Iterable, Optional, Deque

import arcade

# ===================== MAPA BASE =====================
RAW_MAP = [
    "######################",
    "#....................#",
    "#.##.###.####.###.##.#",
    "#o##.###.####.###.##.#",
    "#....................#",
    "#.##.#.########.#.##.#",
    "#....#....##....#....#",
    "####.### #### ###.####",
    "#P.......G  G.......P#",
    "####.### #### ###.####",
    "#....#....##....#....#",
    "#.##.#.######.#.##.#.#",
    "#....................#",
    "#.#o#.###.##.###.#o#.#",
    "#.#.#.###.##.###.#.#.#",
    "#.........##.........#",
    "######################",
]

# ===================== PARÁMETROS =====================
TILE = 24
PAC_SPEED = 4
GHOST_SPEED = 2
POWER_TIME = 6.0
START_LIVES = 3
DEFAULT_SEED = 7

DEFAULT_AVOID = True
DEFAULT_AUTOPILOT = True
DEFAULT_HORIZON = 2
DEFAULT_SAFETY = 0

Grid = List[List[int]]
RC   = Tuple[int,int]

# ===================== UTILIDADES =====================
def parse_ascii_map(ascii_map: List[str]) -> Tuple[Grid, RC, List[RC], List[RC]]:
    h, w = len(ascii_map), len(ascii_map[0])
    grid = [[0]*w for _ in range(h)]
    start=None; pellets=[]; enemies=[]
    for r,row in enumerate(ascii_map):
        for c,ch in enumerate(row):
            grid[r][c]= 1 if ch=='#' else 0
            if ch=='P' and start is None: start=(r,c)
            if ch in '.o': pellets.append((r,c))
            if ch=='G': enemies.append((r,c))
    if start is None: start=(1,1)
    return grid,start,pellets,enemies

def neighbors4(r:int,c:int)->Iterable[RC]:
    return ((r-1,c),(r+1,c),(r,c-1),(r,c+1))

def in_bounds(grid:Grid, rc:RC)->bool:
    r,c=rc; return 0<=r<len(grid) and 0<=c<len(grid[0])

def bfs_nearest_target(grid:Grid, start:RC, targets:List[RC], blocked:set[RC]|None=None)\
    -> Optional[List[RC]]:
    if blocked and start in blocked:
        return None
    tgt_set = set(targets)
    if not tgt_set:
        return None
    if start in tgt_set:
        return [start]
    q = deque([start])
    parent = {start: None}
    while q:
        cur = q.popleft()
        for nb in neighbors4(*cur):
            if not in_bounds(grid, nb): continue
            if grid[nb[0]][nb[1]]==1: continue
            if blocked and nb in blocked: continue
            if nb in parent: continue
            parent[nb] = cur
            if nb in tgt_set:
                path=[nb]; p=cur
                while p is not None:
                    path.append(p); p=parent[p]
                path.reverse()
                return path
            q.append(nb)
    return None

def predict_enemy_positions(grid:Grid,enemies:List[RC],horizon:int)->List[set[RC]]:
    reach=[set() for _ in range(horizon+1)]
    cur=set(enemies); reach[0]=set(cur)
    for _ in range(1,horizon+1):
        nxt=set()
        for r,c in cur:
            nxt.add((r,c))
            for nb in neighbors4(r,c):
                if in_bounds(grid,nb) and grid[nb[0]][nb[1]]==0:
                    nxt.add(nb)
        reach.append(nxt)
        cur=nxt
    return reach

def blocked_from_prediction(pred:List[set[RC]],safety:int)->set[RC]:
    blocked=set()
    frontier=set()
    for S in pred:
        for r,c in S:
            blocked.add((r,c))
            frontier.add((r,c))
    for _ in range(safety):
        new=set()
        for r,c in frontier:
            for nb in neighbors4(r,c):
                new.add(nb)
        blocked |= new
        frontier = new
    return blocked

# ===================== JUEGO ARCADE =====================
def run_game(ascii_map:List[str],seed:int=DEFAULT_SEED,
             autopilot:bool=DEFAULT_AUTOPILOT,avoid:bool=DEFAULT_AVOID,
             horizon:int=DEFAULT_HORIZON,safety:int=DEFAULT_SAFETY,
             lives:int=START_LIVES,pac_speed:int=PAC_SPEED,ghost_speed:int=GHOST_SPEED):
    random.seed(seed)
    grid,start,pellets,enemies=parse_ascii_map(ascii_map)
    H,W=len(grid),len(grid[0])
    SCREEN_W,SCREEN_H=W*TILE,H*TILE

    def grid_to_screen(rc:RC)->Tuple[int,int]:
        r,c=rc; return c*TILE+TILE//2,(H-1-r)*TILE+TILE//2
    def screen_to_grid(x,y)->RC:
        c=int(x//TILE); rb=int(y//TILE); return H-1-rb,c

    class Pac(arcade.Sprite):
        def __init__(self,rc:RC):
            super().__init__()
            self.texture=arcade.make_soft_square_texture(TILE,arcade.color.WHITE,255)
            self.color=arcade.color.YELLOW
            self.center_x,self.center_y=grid_to_screen(rc)
            self.dir=(0,0); self.des=(0,0)
        def set_dir(self,dx,dy): self.des=(dx,dy)
        def _at_cell_center(self)->bool:
            r,c=screen_to_grid(self.center_x,self.center_y)
            sx,sy=grid_to_screen((r,c))
            return abs(self.center_x-sx)<2 and abs(self.center_y-sy)<2
        def update_move(self):
            r,c=screen_to_grid(self.center_x,self.center_y)
            sx,sy=grid_to_screen((r,c))
            if self._at_cell_center():
                self.center_x,self.center_y=sx,sy
                if self._can(self.des): self.dir=self.des
                if not self._can(self.dir): self.dir=(0,0)
            self.center_x+=self.dir[0]*pac_speed
            self.center_y+=self.dir[1]*pac_speed
        def _can(self,d):
            dx,dy=d
            if dx==0 and dy==0:  # no permitir quedarse como movimiento válido
                return False
            r,c=screen_to_grid(self.center_x,self.center_y)
            t=(r-dy,c+dx)
            return in_bounds(grid,t) and grid[t[0]][t[1]]==0

    class Ghost(arcade.Sprite):
        def __init__(self,rc:RC,color):
            super().__init__()
            self.texture=arcade.make_soft_square_texture(TILE,arcade.color.WHITE,255)
            self.base_color=color
            self.color=color
            self.center_x,self.center_y=grid_to_screen(rc)
            self.dir=random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            self.des=self.dir
            self.turn_timer=0.0
            self.spawn_rc=rc
            self.respawn_cooldown=0.0
        def _at_cell_center(self)->bool:
            r,c=screen_to_grid(self.center_x,self.center_y)
            sx,sy=grid_to_screen((r,c))
            return abs(self.center_x-sx)<2 and abs(self.center_y-sy)<2
        def _nudge_to_center(self, speed):
            """Si está fuera de centro y detenido, acércalo al centro para re-evaluar ruta."""
            r,c=screen_to_grid(self.center_x,self.center_y)
            sx,sy=grid_to_screen((r,c))
            dx = 0 if abs(self.center_x - sx) < 1 else (1 if sx > self.center_x else -1)
            dy = 0 if abs(self.center_y - sy) < 1 else (1 if sy > self.center_y else -1)
            self.center_x += dx * speed
            self.center_y += dy * speed
        def _can(self,d):
            dx,dy=d
            if dx==0 and dy==0:
                return False
            r,c=screen_to_grid(self.center_x,self.center_y)
            t=(r-dy,c+dx)
            return in_bounds(grid,t) and grid[t[0]][t[1]]==0
        def _pick_dir_towards(self, target:RC):
            tr,tc=target
            r,c=screen_to_grid(self.center_x,self.center_y)
            prefs=[]
            if tc>c:prefs.append((1,0))
            if tc<c:prefs.append((-1,0))
            if tr>r:prefs.append((0,-1))
            if tr<r:prefs.append((0,1))
            if not prefs:
                prefs=[(1,0),(-1,0),(0,1),(0,-1)]
            random.shuffle(prefs)
            for d in prefs:
                if self._can(d):
                    return d
            for d in [(1,0),(-1,0),(0,1),(0,-1)]:
                if self._can(d):
                    return d
            return (0,0)
        def update_move(self,pac:Pac,dt:float, frightened:bool):
            if self.respawn_cooldown>0.0:
                self.respawn_cooldown=max(0.0,self.respawn_cooldown-dt)
                return

            self.turn_timer += dt

            if not self._at_cell_center() and (self.dir==(0,0)):
                self._nudge_to_center(max(1, int(ghost_speed)))

            if self._at_cell_center():
                r,c=screen_to_grid(self.center_x,self.center_y)
                sx,sy=grid_to_screen((r,c))
                self.center_x,self.center_y=sx,sy

                pr,pc=screen_to_grid(pac.center_x,pac.center_y)
                if frightened:
                    prefs=[]
                    if pc<=c:prefs.append((1,0))
                    if pc>=c:prefs.append((-1,0))
                    if pr<=r:prefs.append((0,-1))
                    if pr>=r:prefs.append((0,1))
                    random.shuffle(prefs)
                    chosen=None
                    for d in prefs:
                        if self._can(d): chosen=d; break
                    if chosen is None:
                        for d in [(1,0),(-1,0),(0,1),(0,-1)]:
                            if self._can(d): chosen=d; break
                    self.des = chosen if chosen else (0,0)
                else:
                    self.des = self._pick_dir_towards((pr,pc))

                if self._can(self.des):
                    self.dir = self.des
                else:
                    picked=None
                    for d in [(1,0),(-1,0),(0,1),(0,-1)]:
                        if self._can(d): picked=d; break
                    self.dir = picked if picked else (0,0)

            if self._can(self.dir):
                speed = ghost_speed * (0.6 if frightened else 1.0)
                self.center_x += self.dir[0]*speed
                self.center_y += self.dir[1]*speed
            else:
                if self._at_cell_center():
                    for d in [(1,0),(-1,0),(0,1),(0,-1)]:
                        if self._can(d):
                            self.dir = d
                            break
                else:
                    self._nudge_to_center(max(1, int(ghost_speed)))

        def set_frightened(self, on:bool):
            self.color = (arcade.color.BLUE if on else self.base_color)

        def respawn(self):
            self.center_x, self.center_y = grid_to_screen(self.spawn_rc)
            self.dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
            self.des = self.dir
            self.respawn_cooldown = 1.0
            self.color = self.base_color

    class Game(arcade.Window):
        def __init__(self):
            super().__init__(SCREEN_W,SCREEN_H,"PacMan Arcade")
            arcade.set_background_color(arcade.color.BLACK)
            # Mapa y colecciones
            self.walls=arcade.SpriteList()
            self.pellets=arcade.SpriteList()
            self.powers=arcade.SpriteList()
            # Pac y fantasmas como SpriteList para draw() en Arcade 3.6
            self.pac = Pac(start)
            self.pac_list = arcade.SpriteList()
            self.pac_list.append(self.pac)

            self.ghosts: arcade.SpriteList = arcade.SpriteList()
            self.ghost_spawns:List[RC]=enemies[:]

            self.lives=lives; self.score=0; self.state="PLAY"
            self.autopilot=autopilot; self.avoid=avoid; self.horizon=horizon; self.safety=safety
            self.plan:Deque[Tuple[int,int]]=deque(); self.last_replan=0.0
            self.power_until=0.0

            self._make_world()
            self._spawn_ghosts(enemies)

        def _make_world(self):
            for r,row in enumerate(RAW_MAP):
                for c,ch in enumerate(row):
                    x,y=grid_to_screen((r,c))
                    if ch=='#':
                        wall=arcade.SpriteSolidColor(TILE,TILE,arcade.color.DARK_BLUE)
                        wall.center_x,wall.center_y=x,y
                        self.walls.append(wall)
                    elif ch in '.o':
                        sz=6 if ch=='.' else 12
                        col=arcade.color.WHITE if ch=='.' else arcade.color.ORANGE_PEEL
                        pel=arcade.SpriteSolidColor(sz,sz,col)
                        pel.center_x,pel.center_y=x,y
                        (self.pellets if ch=='.' else self.powers).append(pel)

        def _spawn_ghosts(self,enemy_cells:List[RC]):
            colors=[arcade.color.RED,arcade.color.GREEN,arcade.color.PURPLE,arcade.color.PINK]
            for i,rc in enumerate(enemy_cells):
                g = Ghost(rc,colors[i%len(colors)])
                self.ghosts.append(g)

        def _power_active(self)->bool:
            return time.time() < self.power_until

        def _set_power_state(self, active:bool):
            for g in self.ghosts:
                g.set_frightened(active)

        def on_draw(self):
            self.clear()
            self.walls.draw()
            self.pellets.draw()
            self.powers.draw()
            # Dibujar usando SpriteList (Arcade 3.6)
            self.pac_list.draw()
            self.ghosts.draw()
            # (Sin HUD ni líneas)

        def on_update(self,dt:float):
            if self.state!="PLAY":
                return

            prev = self._power_active()
            now_active = prev
            if prev and time.time() >= self.power_until:
                now_active = False
                self._set_power_state(False)

            if self.autopilot:
                self._autopilot_step()

            self.pac.update_move()

            for p in arcade.check_for_collision_with_list(self.pac,self.pellets):
                p.remove_from_sprite_lists(); self.score+=10
                self.plan.clear()
            for pw in arcade.check_for_collision_with_list(self.pac,self.powers):
                pw.remove_from_sprite_lists()
                self.power_until = max(self.power_until, time.time()) + POWER_TIME
                now_active = True
                self._set_power_state(True)
                self.plan.clear()

            frightened = now_active
            for g in self.ghosts:
                g.update_move(self.pac,dt, frightened)

            for g in self.ghosts:
                if arcade.check_for_collision(self.pac,g):
                    if frightened:
                        self.score += 200
                        g.respawn()
                    else:
                        self.lives-=1
                        self.pac.center_x,self.pac.center_y=grid_to_screen(start)
                        self.plan.clear()
                        if self.lives<=0:
                            self.state="LOSE"

            if len(self.pellets)==0 and len(self.powers)==0:
                self.state="WIN"

        def _collect_remaining_rc(self)->List[RC]:
            pel=[]
            for lst in (self.pellets, self.powers):
                for sp in lst:
                    r,c = screen_to_grid(sp.center_x, sp.center_y)
                    pel.append((r,c))
            return pel

        def _replan_to_nearest(self):
            pellets_rc = self._collect_remaining_rc()
            if not pellets_rc:
                self.plan.clear()
                return
            r0,c0 = screen_to_grid(self.pac.center_x,self.pac.center_y)
            blocked=None
            if self.avoid:
                enemy_rc=[screen_to_grid(g.center_x,g.center_y) for g in self.ghosts]
                pred=predict_enemy_positions(grid,enemy_rc,self.horizon)
                blocked=blocked_from_prediction(pred,self.safety)

            path = bfs_nearest_target(grid,(r0,c0),pellets_rc,blocked)
            self.plan.clear()
            if path and len(path)>1:
                for rr,cc in path[1:]:
                    self.plan.append(grid_to_screen((rr,cc)))

        def _autopilot_step(self):
            now = time.time()
            if not self.plan or (now - self.last_replan) > 0.6:
                self._replan_to_nearest()
                self.last_replan = now
            if self.plan:
                tx,ty=self.plan[0]
                dx=1 if tx>self.pac.center_x+1 else (-1 if tx<self.pac.center_x-1 else 0)
                dy=1 if ty>self.pac.center_y+1 else (-1 if ty<self.pac.center_y-1 else 0)
                self.pac.set_dir(dx,dy)
                if abs(self.pac.center_x-tx)<2 and abs(self.pac.center_y-ty)<2:
                    self.plan.popleft()

        def on_key_press(self,key,mod):
            if key==arcade.key.A:self.autopilot=not self.autopilot
            elif key==arcade.key.V:self.avoid=not self.avoid
            elif key==arcade.key.H:self.horizon+=1
            elif key==arcade.key.J:self.horizon=max(0,self.horizon-1)
            elif key==arcade.key.S:self.safety+=1
            elif key==arcade.key.D:self.safety=max(0,self.safety-1)
            elif key==arcade.key.ESCAPE: arcade.exit()
            elif key==arcade.key.UP:self.pac.set_dir(0,1)
            elif key==arcade.key.DOWN:self.pac.set_dir(0,-1)
            elif key==arcade.key.LEFT:self.pac.set_dir(-1,0)
            elif key==arcade.key.RIGHT:self.pac.set_dir(1,0)

    Game().run()

# ===================== MAIN =====================
if __name__=="__main__":
    run_game(RAW_MAP,
             seed=DEFAULT_SEED,
             autopilot=DEFAULT_AUTOPILOT,
             avoid=DEFAULT_AVOID,
             horizon=DEFAULT_HORIZON,
             safety=DEFAULT_SAFETY,
             lives=START_LIVES,
             pac_speed=PAC_SPEED,
             ghost_speed=GHOST_SPEED)
