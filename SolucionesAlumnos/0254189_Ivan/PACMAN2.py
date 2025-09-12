"""
# ===================== Algoritmo =====================
#
# El agente usa una estrategia greedy + A*.
# Siempre busca el pellet más cercano (con distancia Manhattan)
# y calcula el camino con A* para llegar a él.
# A* asegura rutas válidas evitando paredes, y el greedy
# hace que el proceso sea rápido y fácil de implementar.
#
# Con esto Pac-Man logra recoger todos los pellets de forma
# eficiente sin complicar demasiado el cálculo.

"""

import arcade, heapq, time
from typing import List, Tuple, Dict

# ===================== MAPA =====================
MAP = [
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
CELL = 32
SPEED = 4
TITLE = "PacMan Auto"
ROWS, COLS = len(MAP), len(MAP[0])
W, H = COLS * CELL, ROWS * CELL

# ===================== FUNCIONES GRID =====================
def grid_to_px(c: int, r: int) -> Tuple[int,int]:
    return c*CELL + CELL//2, (ROWS-r-1)*CELL + CELL//2

def px_to_grid(x: float, y: float) -> Tuple[int,int]:
    c = int(x//CELL)
    r = ROWS - int(y//CELL) - 1
    return c, r

def en_centro(spr: arcade.Sprite) -> bool:
    c, r = px_to_grid(spr.center_x, spr.center_y)
    cx, cy = grid_to_px(c, r)
    return abs(spr.center_x - cx) < 2 and abs(spr.center_y - cy) < 2

# ===================== A* =====================
def adyacentes(nodo: Tuple[int,int], grid):
    c, r = nodo
    for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
        nc, nr = c+dc, r+dr
        if 0 <= nc < COLS and 0 <= nr < ROWS and grid[nr][nc] == 0:
            yield (nc, nr)

def manhattan(a: Tuple[int,int], b: Tuple[int,int]) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def astar(start: Tuple[int,int], goal: Tuple[int,int], grid):
    if start == goal: return [start]
    openh = [(0,start)]
    came, g = {}, {start:0}
    while openh:
        _, cur = heapq.heappop(openh)
        if cur == goal:
            path=[cur]
            while cur in came: cur=came[cur]; path.append(cur)
            return list(reversed(path))
        for nb in adyacentes(cur, grid):
            newg = g[cur]+1
            if nb not in g or newg < g[nb]:
                g[nb]=newg; came[nb]=cur
                f=newg+manhattan(nb,goal)
                heapq.heappush(openh,(f,nb))
    return []

# ===================== SPRITES =====================
class Pac(arcade.Sprite):
    def __init__(self,c:int,r:int):
        super().__init__()
        self.texture=arcade.make_soft_square_texture(CELL,arcade.color.WHITE,255)
        self.color=arcade.color.YELLOW
        self.center_x,self.center_y=grid_to_px(c,r)
        self.dir=(0,0); self.deseada=(0,0); self.score=0
        self.steps=0
    def set_dir(self,dx,dy): self.deseada=(dx,dy)
    def mover(self,grid):
        if en_centro(self):
            if self._puede(self.deseada,grid): self.dir=self.deseada
            if not self._puede(self.dir,grid): self.dir=(0,0)
            c,r=px_to_grid(self.center_x,self.center_y)
            self.center_x,self.center_y=grid_to_px(c,r)
        self.center_x+=self.dir[0]*SPEED; self.center_y+=self.dir[1]*SPEED
    def _puede(self,d,grid)->bool:
        dx,dy=d
        if dx==dy==0: return True
        c,r=px_to_grid(self.center_x,self.center_y)
        nc,nr=c+dx,r-dy
        if not(0<=nc<COLS and 0<=nr<ROWS): return False
        return grid[nr][nc]==0

class Ghost(arcade.Sprite):
    def __init__(self,c:int,r:int,color):
        super().__init__()
        self.texture=arcade.make_soft_square_texture(CELL,arcade.color.WHITE,255)
        self.color=color
        self.center_x,self.center_y=grid_to_px(c,r)

# ===================== JUEGO =====================
class Game(arcade.Window):
    def __init__(self):
        super().__init__(W,H,TITLE,update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.walls,self.food,self.power=arcade.SpriteList(),arcade.SpriteList(),arcade.SpriteList()
        self.ghosts=[]; self.pac=None; self.grid=[]
        self.route=[]; self.idx=0; self.state="PLAY"
        self.start_time=0; self.total_time=0
    def setup(self):
        self.walls,self.food,self.power=arcade.SpriteList(),arcade.SpriteList(),arcade.SpriteList()
        self.ghosts=[]; self.grid=[[0]*COLS for _ in range(ROWS)]
        pacpos=None; gpos=[]
        for r,row in enumerate(MAP):
            for c,ch in enumerate(row):
                x,y=grid_to_px(c,r)
                if ch=="#":
                    w=arcade.SpriteSolidColor(CELL,CELL,arcade.color.BLUE)
                    w.center_x, w.center_y=x,y; self.walls.append(w); self.grid[r][c]=1
                elif ch==".":
                    f=arcade.SpriteSolidColor(6,6,arcade.color.WHITE); f.center_x,f.center_y=x,y; self.food.append(f)
                elif ch=="o":
                    pw=arcade.SpriteSolidColor(12,12,arcade.color.ORANGE); pw.center_x,pw.center_y=x,y; self.power.append(pw)
                elif ch=="P": pacpos=(c,r)
                elif ch=="G": gpos.append((c,r))
        if pacpos: self.pac=Pac(*pacpos)
        for i,(c,r) in enumerate(gpos):
            self.ghosts.append(Ghost(c,r,[arcade.color.RED,arcade.color.GREEN,arcade.color.PURPLE][i%3]))
        self.start_time=time.time()
    def on_draw(self):
        self.clear(); self.walls.draw(); self.food.draw(); self.power.draw()
        if self.pac: arcade.draw_rect_filled(arcade.rect.XYWH(self.pac.center_x,self.pac.center_y,CELL,CELL),arcade.color.YELLOW)
        for g in self.ghosts: arcade.draw_rect_filled(arcade.rect.XYWH(g.center_x,g.center_y,CELL,CELL),g.color)
        if self.state=="PLAY":
            elapsed=round(time.time()-self.start_time,2)
            arcade.draw_text(f"Puntos:{self.pac.score}",10,H-20,arcade.color.YELLOW,14)
            arcade.draw_text(f"Restantes:{len(self.food)+len(self.power)}",10,H-40,arcade.color.WHITE,14)
            arcade.draw_text(f"Tiempo:{elapsed}s",10,H-60,arcade.color.GREEN,14)
            arcade.draw_text(f"Pasos:{self.pac.steps}",10,H-80,arcade.color.PINK,14)
        elif self.state=="WIN":
            msg=f"¡Completado!\nTiempo: {self.total_time}s\nPasos: {self.pac.steps}"
            arcade.draw_text(msg,W/2,H/2,arcade.color.YELLOW,30,anchor_x="center",anchor_y="center",align="center")
    def on_update(self,dt):
        if self.state!="PLAY" or not self.pac: return
        if en_centro(self.pac) and (not self.route or self.idx>=len(self.route)):
            pos=px_to_grid(self.pac.center_x,self.pac.center_y)
            targets=[px_to_grid(s.center_x,s.center_y) for s in self.food]+[px_to_grid(s.center_x,s.center_y) for s in self.power]
            if targets:
                targets.sort(key=lambda t:manhattan(pos,t)); goal=targets[0]
                self.route=astar(pos,goal,self.grid); self.idx=1
        if self.route and self.idx<len(self.route):
            pos=px_to_grid(self.pac.center_x,self.pac.center_y); nxt=self.route[self.idx]
            dx=nxt[0]-pos[0]; dy=pos[1]-nxt[1]
            self.pac.set_dir(dx,dy)
            if pos==nxt:
                self.idx+=1
                self.pac.steps+=1
        self.pac.mover(self.grid)
        for f in arcade.check_for_collision_with_list(self.pac,self.food): f.remove_from_sprite_lists(); self.pac.score+=10
        for pw in arcade.check_for_collision_with_list(self.pac,self.power): pw.remove_from_sprite_lists(); self.pac.score+=50
        if not self.food and not self.power:
            self.state="WIN"
            self.total_time=round(time.time()-self.start_time,2)
            print(f"Juego terminado en {self.total_time}s con {self.pac.steps} pasos")

# ===================== MAIN =====================
def main():
    game=Game(); game.setup(); arcade.run()

if __name__=="__main__":
    main()
