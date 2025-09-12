import arcade
from typing import List, Tuple
import random
import heapq

# ===================== CONFIG =====================
SCREEN_TITLE = "PacGPT5 con Enemigos (con menú y autopiloto)"
TILE_SIZE = 32
MOVEMENT_SPEED = 4
GHOST_SPEED = 2
POWER_TIME = 7.0

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
    ]
}

ROWS, COLS = len(RAW_MAPS["1"]), len(RAW_MAPS["1"][0])
SCREEN_WIDTH, SCREEN_HEIGHT = COLS * TILE_SIZE, ROWS * TILE_SIZE

# ===================== UTILS =====================
def grid_to_pixel(col, row) -> Tuple[int,int]:
    x = col * TILE_SIZE + TILE_SIZE//2
    y = (ROWS-row-1)*TILE_SIZE + TILE_SIZE//2
    return x, y

def pixel_to_grid(x, y) -> Tuple[int,int]:
    col = int(x // TILE_SIZE)
    row_from_bottom = int(y // TILE_SIZE)
    return col, ROWS - row_from_bottom -1

def is_center_of_cell(sprite) -> bool:
    col,row = pixel_to_grid(sprite.center_x, sprite.center_y)
    cx,cy = grid_to_pixel(col,row)
    return abs(sprite.center_x-cx)<2 and abs(sprite.center_y-cy)<2

# ===================== ASTAR =====================
def neighbors(cell: Tuple[int,int], walls_grid):
    c,r = cell
    for dc,dr in [(1,0),(-1,0),(0,1),(0,-1)]:
        nc,nr = c+dc,r+dr
        if 0<=nc<COLS and 0<=nr<ROWS and walls_grid[nr][nc]==0:
            yield (nc,nr)

def manhattan(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])

def astar(start: Tuple[int,int], goal: Tuple[int,int], walls_grid):
    if start==goal: return [start]
    openh = [(0,start)]
    came,g = {}, {start:0}
    while openh:
        _,cur = heapq.heappop(openh)
        if cur==goal:
            path=[cur]
            while cur in came:
                cur=came[cur]
                path.append(cur)
            return list(reversed(path))
        for nb in neighbors(cur,walls_grid):
            tentative = g[cur]+1
            if nb not in g or tentative<g[nb]:
                g[nb]=tentative
                f = tentative + manhattan(nb,goal)
                came[nb]=cur
                heapq.heappush(openh,(f,nb))
    return []

# ===================== SPRITES =====================
class Pacman(arcade.Sprite):
    def __init__(self,col,row):
        super().__init__()
        self.color = arcade.color.YELLOW
        self.center_x,self.center_y = grid_to_pixel(col,row)
        self.current_dir=(0,0)
        self.desired_dir=(0,0)
        self.score=0
        self.lives=3
        self.invulnerable_timer=0

    def set_direction(self, dx,dy): self.desired_dir=(dx,dy)

    def can_move(self,direction,walls_grid):
        dx,dy = direction
        if dx==dy==0: return True
        col,row = pixel_to_grid(self.center_x,self.center_y)
        nc,nr = col+dx,row-dy
        if not(0<=nc<COLS and 0<=nr<ROWS): return False
        return walls_grid[nr][nc]==0

    def update_move(self,walls_grid):
        if is_center_of_cell(self):
            if self.can_move(self.desired_dir,walls_grid): self.current_dir=self.desired_dir
            if not self.can_move(self.current_dir,walls_grid): self.current_dir=(0,0)
            col,row = pixel_to_grid(self.center_x,self.center_y)
            self.center_x,self.center_y = grid_to_pixel(col,row)
        self.center_x += self.current_dir[0]*MOVEMENT_SPEED
        self.center_y += self.current_dir[1]*MOVEMENT_SPEED

class Ghost(arcade.Sprite):
    def __init__(self,col,row,color):
        super().__init__()
        self.color = color
        self.center_x,self.center_y = grid_to_pixel(col,row)
        self.current_dir=random.choice([(1,0),(-1,0),(0,1),(0,-1)])

    def can_move(self,direction,walls_grid):
        dx,dy=direction
        col,row = pixel_to_grid(self.center_x,self.center_y)
        nc,nr = col+dx,row-dy
        if not(0<=nc<COLS and 0<=nr<ROWS): return False
        return walls_grid[nr][nc]==0

    def update_move(self,walls_grid):
        if is_center_of_cell(self):
            options=[d for d in [(1,0),(-1,0),(0,1),(0,-1)] if self.can_move(d,walls_grid)]
            back=(-self.current_dir[0],-self.current_dir[1])
            valid=[d for d in options if d!=back] or options
            self.current_dir=random.choice(valid)
            col,row = pixel_to_grid(self.center_x,self.center_y)
            self.center_x,self.center_y = grid_to_pixel(col,row)
        self.center_x += self.current_dir[0]*GHOST_SPEED
        self.center_y += self.current_dir[1]*GHOST_SPEED

# ===================== JUEGO =====================
class PacGPT5(arcade.Window):
    def __init__(self, autopilot=True):
        super().__init__(SCREEN_WIDTH,SCREEN_HEIGHT,SCREEN_TITLE,update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list,self.pellet_list,self.power_list = arcade.SpriteList(),arcade.SpriteList(),arcade.SpriteList()
        self.ghosts=[]
        self.walls_grid=[[0]*COLS for _ in range(ROWS)]
        self.pacman=None
        self.state="PLAY"
        self.autopilot=autopilot
        self.route=[]
        self.auto_path=[]
        self.auto_index=0

    def setup(self):
        self.wall_list,self.pellet_list,self.power_list=arcade.SpriteList(),arcade.SpriteList(),arcade.SpriteList()
        self.ghosts=[]
        self.walls_grid=[[0]*COLS for _ in range(ROWS)]
        pacman_pos=None
        ghost_positions=[]
        for r,row in enumerate(RAW_MAPS["1"]):
            for c,ch in enumerate(row):
                x,y=grid_to_pixel(c,r)
                if ch=="#":
                    wall=arcade.SpriteSolidColor(TILE_SIZE,TILE_SIZE,arcade.color.DARK_BLUE)
                    wall.center_x,wall.center_y=x,y
                    self.wall_list.append(wall)
                    self.walls_grid[r][c]=1
                elif ch in [".","o"]:
                    pellet=arcade.SpriteSolidColor(6,6,arcade.color.WHITE)
                    pellet.center_x,pellet.center_y=x,y
                    self.pellet_list.append(pellet)
                elif ch=="P":
                    pacman_pos=(c,r)
                elif ch=="G":
                    ghost_positions.append((c,r))
        if pacman_pos: self.pacman=Pacman(*pacman_pos)

        colors = [arcade.color.RED, arcade.color.GREEN, arcade.color.PINK, arcade.color.ORANGE]
        for idx,(c,r) in enumerate(ghost_positions):
            self.ghosts.append(Ghost(c,r,colors[idx % len(colors)]))

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        if self.pacman:
            rect_p=arcade.rect.XYWH(self.pacman.center_x,self.pacman.center_y,TILE_SIZE,TILE_SIZE)
            arcade.draw_rect_filled(rect_p,self.pacman.color)
        for g in self.ghosts:
            rect_g=arcade.rect.XYWH(g.center_x,g.center_y,TILE_SIZE,TILE_SIZE)
            arcade.draw_rect_filled(rect_g,g.color)
        if self.pacman:
            arcade.draw_text(f"Vidas: {self.pacman.lives} | Pellets: {len(self.pellet_list)}",10,SCREEN_HEIGHT-22,arcade.color.CYAN,14)
        if self.state == "WIN":
            arcade.draw_text("¡GANASTE!", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, arcade.color.GREEN, 40, anchor_x="center")
        elif self.state == "LOSE":
            arcade.draw_text("GAME OVER", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, arcade.color.RED, 40, anchor_x="center")

    def on_update(self,delta_time:float):
        if self.state!="PLAY" or not self.pacman: return

        if self.autopilot and is_center_of_cell(self.pacman):
            col,row = pixel_to_grid(self.pacman.center_x,self.pacman.center_y)
            if not self.auto_path or self.auto_index>=len(self.auto_path):
                if self.pellet_list:
                    targets=[pixel_to_grid(p.center_x,p.center_y) for p in self.pellet_list]
                    target=min(targets,key=lambda t: manhattan((col,row),t))
                    self.auto_path=astar((col,row),target,self.walls_grid)
                    self.auto_index=0
            if self.auto_path and self.auto_index+1<len(self.auto_path):
                nx,ny=self.auto_path[self.auto_index+1]
                dx,dy=nx-col,ny-row
                self.pacman.set_direction(dx,-dy)
                self.auto_index+=1

        self.pacman.update_move(self.walls_grid)
        for g in self.ghosts:
            g.update_move(self.walls_grid)

        pac_col,pac_row=pixel_to_grid(self.pacman.center_x,self.pacman.center_y)
        for p in self.pellet_list:
            p_col,p_row=pixel_to_grid(p.center_x,p.center_y)
            if pac_col==p_col and pac_row==p_row:
                p.remove_from_sprite_lists()
                break

        for g in self.ghosts:
            g_col,g_row=pixel_to_grid(g.center_x,g.center_y)
            if pac_col==g_col and pac_row==g_row and self.pacman.invulnerable_timer<=0:
                self.pacman.lives-=1
                if self.pacman.lives<=0:
                    self.state="LOSE"
                else:
                    # Respawn Pacman
                    for r,row in enumerate(RAW_MAPS["1"]):
                        for c,ch in enumerate(row):
                            if ch=="P":
                                self.pacman.center_x,self.pacman.center_y=grid_to_pixel(c,r)
                                self.pacman.current_dir=(0,0)
                                self.pacman.desired_dir=(0,0)
                                self.pacman.invulnerable_timer=2.0
                                break
                        else: continue
                        break

        if not self.pellet_list and self.pacman.lives>0:
            self.state="WIN"

    def on_key_press(self,key,modifiers):
        if not self.pacman: return
        if key==arcade.key.UP: self.pacman.set_direction(0,1)
        elif key==arcade.key.DOWN: self.pacman.set_direction(0,-1)
        elif key==arcade.key.LEFT: self.pacman.set_direction(-1,0)
        elif key==arcade.key.RIGHT: self.pacman.set_direction(1,0)
        elif key==arcade.key.ESCAPE: arcade.close_window()
        elif key==arcade.key.R and self.state!="PLAY": self.setup(); self.pacman.lives=3; self.state="PLAY"

# ===================== MENÚ =====================
def menu():
    while True:
        print("\n=== PACMAN MENU ===")
        print("1. Jugar en arcade (manual)")
        print("2. Jugar en arcade (autopiloto)")
        print("0. Salir")
        choice = input("Selecciona una opción: ")

        if choice == "1":
            game=PacGPT5(autopilot=False)
            game.setup()
            arcade.run()
        elif choice == "2":
            game=PacGPT5(autopilot=True)
            game.setup()
            arcade.run()
        elif choice == "0":
            print("Adiós!")
            break
        else:
            print("Opción inválida.")

# ===================== MAIN =====================
def main():
    menu()

if __name__=="__main__":
    main()
