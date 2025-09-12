"""
Versión de Pac-Man con evasión de enemigos.

==================== Estrategia ====================

- El agente utiliza planificación dinámica con A*.
- Cada vez que necesita una nueva ruta, calcula un camino hacia
  el pellet más cercano, pero considera a los enemigos como
  obstáculos dinámicos.
- Además, se incluye una "zona de peligro" (radio=1 celda) alrededor
  de cada enemigo. Esto obliga a Pac-Man a buscar caminos alternativos
  en lugar de acercarse demasiado.
- Si un pellet queda rodeado por enemigos y no existe un camino válido,
  se marca como "inalcanzable" y se elimina del mapa.

==================== Condiciones ====================

- Pac-Man comienza con 3 vidas.
- Si colisiona con un enemigo: pierde 1 vida y regresa al punto de inicio.
- Si las vidas llegan a 0: derrota (FAIL).
- Si recoge todos los pellets: victoria (WIN).
- Si algunos pellets no pueden alcanzarse: parcial (se reportan en consola).

==================== Resultados mostrados ====================

- Tiempo total de ejecución.
- Número de pasos dados por Pac-Man.
- Colisiones y vidas restantes.
- Estado final (Victoria, Parcial o Derrota).

"""

import arcade, heapq, time, random
from typing import List, Tuple, Set

# ===================== CONFIG =====================
CELL = 32
SPEED = 4
TITLE = "PacMan Evita Enemigos"

MAP = [
    "######################",
    "#........##..........#",
    "#.##.###.##.###.##..#",
    "#o##.............##o.#",
    "#....................#",
    "#.##.#.######.#.##.#.#",
    "#....#....##....#....#",
    "####.### #### ###.####",
    "#P.......E  E.......P#",
    "####.### #### ###.####",
    "#....#....##....#....#",
    "#.##.#.######.#.##.#.#",
    "#....................#",
    "#o##.............##o.#",
    "#.##.###.##.###.##..#",
    "#........##..........#",
    "######################",
]

ROWS, COLS = len(MAP), len(MAP[0])
W, H = COLS * CELL, ROWS * CELL

# ===================== UTILS =====================
def grid_to_px(c: int, r: int) -> Tuple[int, int]:
    return c * CELL + CELL // 2, (ROWS - r - 1) * CELL + CELL // 2

def px_to_grid(x: float, y: float) -> Tuple[int, int]:
    c = int(x // CELL)
    rb = int(y // CELL)
    return c, ROWS - rb - 1

def en_centro(sprite: arcade.Sprite) -> bool:
    c, r = px_to_grid(sprite.center_x, sprite.center_y)
    cx, cy = grid_to_px(c, r)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2

# ===================== A* =====================
def vecinos(cell, grid, peligros: Set[Tuple[int,int]]):
    c, r = cell
    for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
        nc, nr = c+dc, r+dr
        if 0 <= nc < COLS and 0 <= nr < ROWS and grid[nr][nc] == 0:
            if (nc, nr) not in peligros:   # evitar zonas peligrosas
                yield (nc, nr)

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def astar(inicio, meta, grid, peligros: Set[Tuple[int,int]]):
    if inicio == meta: return [inicio]
    abiertos = [(0, inicio)]
    came, g = {}, {inicio: 0}
    while abiertos:
        _, actual = heapq.heappop(abiertos)
        if actual == meta:
            path = [actual]
            while actual in came:
                actual = came[actual]
                path.append(actual)
            return list(reversed(path))
        for nb in vecinos(actual, grid, peligros):
            nuevo = g[actual] + 1
            if nb not in g or nuevo < g[nb]:
                g[nb] = nuevo
                came[nb] = actual
                f = nuevo + manhattan(nb, meta)
                heapq.heappush(abiertos, (f, nb))
    return []

# ===================== FUNC PELIGROS =====================
def zonas_peligro(enemigos, radio=1):
    peligros = set()
    for e in enemigos:
        c, r = px_to_grid(e.center_x, e.center_y)
        for dx in range(-radio, radio+1):
            for dy in range(-radio, radio+1):
                nc, nr = c+dx, r+dy
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    peligros.add((nc, nr))
    return peligros

# ===================== SPRITES =====================
class Pac(arcade.Sprite):
    def __init__(self, c, r):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(CELL, arcade.color.WHITE, 255)
        self.color = arcade.color.YELLOW
        self.center_x, self.center_y = grid_to_px(c, r)
        self.dir = (0,0)
        self.des = (0,0)
        self.vidas = 3
        self.score = 0
        self.steps = 0

    def set_dir(self, dx, dy): self.des = (dx,dy)

    def mover(self, grid):
        if en_centro(self):
            if self._puede(self.des, grid):
                self.dir = self.des
            if not self._puede(self.dir, grid):
                self.dir = (0,0)
            c,r = px_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_px(c,r)
        self.center_x += self.dir[0]*SPEED
        self.center_y += self.dir[1]*SPEED

    def _puede(self, d, grid):
        dx,dy = d
        if dx==dy==0: return True
        c,r = px_to_grid(self.center_x,self.center_y)
        nc,nr = c+dx, r-dy
        if not(0<=nc<COLS and 0<=nr<ROWS): return False
        return grid[nr][nc]==0

    def reset_pos(self):
        for r,row in enumerate(MAP):
            for c,ch in enumerate(row):
                if ch=="P":
                    self.center_x,self.center_y = grid_to_px(c,r)
                    self.dir=(0,0); self.des=(0,0)
                    return

class Enemy(arcade.Sprite):
    def __init__(self, c, r, color):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(CELL, arcade.color.WHITE, 255)
        self.color=color
        self.center_x,self.center_y = grid_to_px(c,r)
        self.dir=random.choice([(1,0),(-1,0),(0,1),(0,-1)])

    def mover(self,grid):
        if en_centro(self):
            c,r=px_to_grid(self.center_x,self.center_y)
            opciones=[]
            for d in [(1,0),(-1,0),(0,1),(0,-1)]:
                nc,nr=c+d[0], r-d[1]
                if 0<=nc<COLS and 0<=nr<ROWS and grid[nr][nc]==0:
                    opciones.append(d)
            if len(opciones)>1:
                opuestas=(-self.dir[0],-self.dir[1])
                if opuestas in opciones:
                    opciones.remove(opuestas)
                self.dir=random.choice(opciones)
            elif opciones:
                self.dir=opciones[0]
            self.center_x,self.center_y=grid_to_px(c,r)
        self.center_x+=self.dir[0]*SPEED//2
        self.center_y+=self.dir[1]*SPEED//2

# ===================== JUEGO =====================
class Game(arcade.Window):
    def __init__(self):
        super().__init__(W,H,TITLE,update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.walls=arcade.SpriteList()
        self.food=arcade.SpriteList()
        self.enemies=arcade.SpriteList()
        self.pac=None
        self.grid=[]
        self.route=[]
        self.idx=0
        self.state="PLAY"
        self.start=0
        self.unreachable=[]

    def setup(self):
        self.walls,self.food=arcade.SpriteList(),arcade.SpriteList()
        self.enemies=arcade.SpriteList()
        self.grid=[[0]*COLS for _ in range(ROWS)]
        pacpos=None
        for r,row in enumerate(MAP):
            for c,ch in enumerate(row):
                x,y=grid_to_px(c,r)
                if ch=="#":
                    w=arcade.SpriteSolidColor(CELL,CELL,arcade.color.BLUE)
                    w.center_x,w.center_y=x,y
                    self.walls.append(w)
                    self.grid[r][c]=1
                elif ch==".":
                    f=arcade.SpriteSolidColor(6,6,arcade.color.WHITE)
                    f.center_x,f.center_y=x,y
                    self.food.append(f)
                elif ch=="P":
                    pacpos=(c,r)
                elif ch=="E":
                    self.enemies.append(Enemy(c,r,arcade.color.RED))
        if pacpos:
            self.pac=Pac(*pacpos)
        self.start=time.time()

    def on_draw(self):
        self.clear()
        self.walls.draw(); self.food.draw(); self.enemies.draw()
        if self.pac:
            arcade.draw_rect_filled(arcade.rect.XYWH(self.pac.center_x,self.pac.center_y,CELL,CELL),arcade.color.YELLOW)
        arcade.draw_text(f"Puntos:{self.pac.score}",10,H-20,arcade.color.YELLOW,14)
        arcade.draw_text(f"Vidas:{self.pac.vidas}",10,H-40,arcade.color.WHITE,14)

    def on_update(self,dt):
        if self.state!="PLAY" or not self.pac: return
        # mover enemigos
        for e in self.enemies: e.mover(self.grid)

        # recalculo de ruta con evasión
        if en_centro(self.pac) and (not self.route or self.idx>=len(self.route)):
            pos=px_to_grid(self.pac.center_x,self.pac.center_y)
            pellets=[px_to_grid(s.center_x,s.center_y) for s in self.food]
            if pellets:
                pellets.sort(key=lambda t:manhattan(pos,t))
                goal=pellets[0]
                peligros=zonas_peligro(self.enemies,radio=1)
                self.route=astar(pos,goal,self.grid,peligros)
                if not self.route:
                    print(f"Pellet {goal} inalcanzable por enemigos")
                    self.unreachable.append(goal)
                    # eliminar solo el pellet correspondiente
                    for f in self.food:
                        if px_to_grid(f.center_x,f.center_y)==goal:
                            f.remove_from_sprite_lists()
                            break
                else:
                    self.idx=1

        # avanzar
        if self.route and self.idx<len(self.route):
            pos=px_to_grid(self.pac.center_x,self.pac.center_y)
            nxt=self.route[self.idx]
            dx,dy=nxt[0]-pos[0],pos[1]-nxt[1]
            self.pac.set_dir(dx,dy)
            if pos==nxt:
                self.idx+=1
                self.pac.steps+=1

        self.pac.mover(self.grid)

        # comer pellets
        for f in arcade.check_for_collision_with_list(self.pac,self.food):
            f.remove_from_sprite_lists()
            self.pac.score+=10

        # colisiones con enemigos
        for e in arcade.check_for_collision_with_list(self.pac,self.enemies):
            self.pac.vidas-=1
            print(f"Colisión! Vidas:{self.pac.vidas}")
            self.pac.reset_pos()
            if self.pac.vidas<=0:
                self.state="FAIL"
                t=round(time.time()-self.start,2)
                print(f"Derrota. Tiempo:{t}s Pasos:{self.pac.steps}")
                return

        # victoria o parcial
        if not self.food:
            t=round(time.time()-self.start,2)
            if self.unreachable:
                print(f"Parcialmente completado. Pellets sin recolectar:{self.unreachable}")
            else:
                print(f"Victoria! Tiempo:{t}s Pasos:{self.pac.steps}")
            self.state="END"

# ===================== MAIN =====================
def main():
    game=Game(); game.setup(); arcade.run()

if __name__=="__main__":
    main()
