"""
Cambios:
    Menú inicial: (1) Autopilot ON, (2) Manual, (3) Cambiar color muros
    Tecla C en juego: alterna color muros (reinicia tablero)
    Tecla T: alterna Autopilot ON/OFF
    Flechas / WASD: movimiento manual
    R: respawn rápido tras perder una vida (invulnerable 2s)
    ESC: salir
==================== Reglas ====================

- Pac-Man:
    * Se mueve con las teclas de dirección (ARRIBA, ABAJO, IZQUIERDA, DERECHA).
    * Se desplaza celda por celda respetando paredes.
    * Tiene un contador de vidas inicial de 3.
    * Tras recibir daño por colisión con un fantasma, reaparece en su posición inicial y es invulnerable durante 2 segundos.

- Enemigos (fantasmas):
    * Se mueven de forma aleatoria dentro del laberinto.
    * En pasillos continúan en línea recta.
    * En intersecciones eligen una dirección aleatoria, evitando retroceder si hay otras opciones.
    * Su colisión con Pac-Man reduce una vida.

- Pellets:
    * Se consumen únicamente cuando Pac-Man se encuentra exactamente sobre la celda del pellet.
    * Power pellets funcionan igual que pellets normales (solo para efectos visuales).

==================== Condiciones de fin ====================

- GAME OVER: Pac-Man pierde todas las vidas.
- WIN: Todos los pellets y power pellets son recogidos y Pac-Man tiene al menos una vida.

==================== Interfaz gráfica ====================

- La ventana muestra:
    * Paredes: color azul.
    * Pac-Man: color amarillo.
    * Fantasmas: color rojo.
    * Pellets: color blanco.
- HUD:
    * Score, vidas restantes, pellets restantes y pasos recorridos.
    * Indica si el autopiloto está activado (opcional).

==================== Salida en consola ====================

- Se registran eventos importantes:
    * Colisiones con enemigos y vidas restantes.
    * Estado final: WIN o GAME OVER.
    * Ruta seguida por Pac-Man, pasos y movimientos.
"""
import arcade
from dataclasses import dataclass
from typing import List, Tuple
import random
import time
import heapq
import argparse

# ===================== CONFIG =====================
SCREEN_TITLE = "PacGPT5 con Enemigos - Enhanced"
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

def manhattan(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])

# ===================== ASTAR CON EVASIÓN =====================
def neighbors(cell: Tuple[int,int], walls_grid, forbidden=None):
    if forbidden is None:
        forbidden = set()
    c,r = cell
    for dc,dr in [(1,0),(-1,0),(0,1),(0,-1)]:
        nc,nr = c+dc,r+dr
        if 0<=nc<COLS and 0<=nr<ROWS:
            if walls_grid[nr][nc]==0 and (nc,nr) not in forbidden:
                yield (nc,nr)

def astar(start: Tuple[int,int], goal: Tuple[int,int], walls_grid, forbidden=None):
    if forbidden is None:
        forbidden = set()
    if start==goal: 
        return [start]
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
        for nb in neighbors(cur,walls_grid,forbidden):
            tentative = g[cur]+1
            if nb not in g or tentative<g[nb]:
                g[nb]=tentative
                f = tentative + manhattan(nb,goal)
                came[nb]=cur
                heapq.heappush(openh,(f,nb))
    return []

# ===================== DATACLASSES =====================
@dataclass
class GhostState:
    normal_color: Tuple[int,int,int]

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
        self.power_timer=0
        self.invulnerable_timer=0

    def set_direction(self, dx,dy): 
        self.desired_dir=(dx,dy)

    def can_move(self,direction,walls_grid):
        dx,dy = direction
        if dx==dy==0: return True
        col,row = pixel_to_grid(self.center_x,self.center_y)
        nc,nr = col+dx,row-dy
        if not(0<=nc<COLS and 0<=nr<ROWS): return False
        return walls_grid[nr][nc]==0

    def update_move(self,walls_grid):
        if is_center_of_cell(self):
            if self.can_move(self.desired_dir,walls_grid): 
                self.current_dir=self.desired_dir
            if not self.can_move(self.current_dir,walls_grid): 
                self.current_dir=(0,0)
            col,row = pixel_to_grid(self.center_x,self.center_y)
            self.center_x,self.center_y = grid_to_pixel(col,row)
        self.center_x += self.current_dir[0]*MOVEMENT_SPEED
        self.center_y += self.current_dir[1]*MOVEMENT_SPEED

class Ghost(arcade.Sprite):
    def __init__(self,col,row,state:GhostState):
        super().__init__()
        self.color = state.normal_color
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
            col,row = pixel_to_grid(self.center_x,self.center_y)
            options=[d for d in [(1,0),(-1,0),(0,1),(0,-1)] if self.can_move(d,walls_grid)]
            if self.current_dir in options and len(options)==2:
                pass  # seguir recto en pasillo
            else:
                back=(-self.current_dir[0],-self.current_dir[1])
                valid=[d for d in options if d!=back] or options
                if valid:
                    self.current_dir=random.choice(valid)
            self.center_x,self.center_y = grid_to_pixel(col,row)
        self.center_x += self.current_dir[0]*GHOST_SPEED
        self.center_y += self.current_dir[1]*GHOST_SPEED

# ===================== JUEGO =====================
class PacGPT5(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH,SCREEN_HEIGHT,SCREEN_TITLE,update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        
        # Estado del juego
        self.show_menu = True
        self.wall_color = arcade.color.DARK_BLUE
        self.wall_list,self.pellet_list,self.power_list = arcade.SpriteList(),arcade.SpriteList(),arcade.SpriteList()
        self.ghosts=[]
        self.walls_grid=[[0]*COLS for _ in range(ROWS)]
        self.pacman=None
        self.state="PLAY"  # PLAY | WIN | LOSE
        
        # Autopilot
        self.autopilot=True
        self.auto_path=[]
        self.auto_index=0
        
        # Stats
        self.total_steps=0
        self.route=[]
        
        # Posiciones iniciales para respawn
        self._pacman_start = None
        self._ghost_starts = []
        
        # Crear objetos Text para mejor rendimiento
        self.setup_text_objects()

    def setup_text_objects(self):
        """Crear objetos Text reutilizables"""
        # Textos del menú
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
        
        # Textos del HUD
        self.hud_text = arcade.Text("", 10, SCREEN_HEIGHT-22, arcade.color.CYAN, 14)
        self.controls_text = arcade.Text("", 10, SCREEN_HEIGHT-40, arcade.color.WHITE, 12)
        
        # Textos de estado final
        self.win_text = arcade.Text("¡GANASTE!", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 
                                   arcade.color.GREEN, 40, anchor_x="center")
        self.lose_text = arcade.Text("GAME OVER", SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 
                                    arcade.color.RED, 40, anchor_x="center")
        self.restart_text = arcade.Text("Presiona R para reiniciar", SCREEN_WIDTH/2, SCREEN_HEIGHT/2-50, 
                                       arcade.color.WHITE, 16, anchor_x="center")

    def update_hud_text(self):
        """Actualizar texto del HUD"""
        if self.pacman:
            autopilot_status = "ON" if self.autopilot else "OFF"
            wall_color_name = "Gris" if self.wall_color == arcade.color.GRAY else "Azul"
            
            self.hud_text.text = f"Vidas: {self.pacman.lives} | Pellets: {len(self.pellet_list)} | Pasos: {self.total_steps} | Autopilot: {autopilot_status}"
            self.controls_text.text = f"Muros: {wall_color_name} | T=Autopilot | C=Color | R=Respawn | WASD/Flechas=Mover"

    def setup(self):
        """Configurar el juego"""
        self.wall_list,self.pellet_list,self.power_list=arcade.SpriteList(),arcade.SpriteList(),arcade.SpriteList()
        self.ghosts=[]
        self.walls_grid=[[0]*COLS for _ in range(ROWS)]
        pacman_pos=None
        ghost_positions=[]
        
        for r,row in enumerate(RAW_MAPS["1"]):
            for c,ch in enumerate(row):
                x,y=grid_to_pixel(c,r)
                if ch=="#":
                    wall=arcade.SpriteSolidColor(TILE_SIZE,TILE_SIZE,self.wall_color)
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
        
        # Crear Pacman
        if pacman_pos: 
            self.pacman=Pacman(*pacman_pos)
            self._pacman_start = pacman_pos
            
        # Crear fantasmas
        self._ghost_starts = []
        colors = [arcade.color.RED, arcade.color.GREEN, arcade.color.CYAN, arcade.color.ORANGE]
        for idx, (c,r) in enumerate(ghost_positions):
            color = colors[idx % len(colors)]
            self.ghosts.append(Ghost(c,r,GhostState(color)))
            self._ghost_starts.append((c,r))
        
        # Reset stats
        self.total_steps=0
        self.route=[]
        self.auto_path=[]
        self.auto_index=0

    def reset_positions(self):
        """Respawn de Pacman y fantasmas"""
        if self._pacman_start and self.pacman:
            col, row = self._pacman_start
            self.pacman.center_x, self.pacman.center_y = grid_to_pixel(col, row)
            self.pacman.current_dir = (0, 0)
            self.pacman.desired_dir = (0, 0)
            self.pacman.invulnerable_timer = 2.0
        
        # Respawn fantasmas
        for ghost, (c, r) in zip(self.ghosts, self._ghost_starts):
            ghost.center_x, ghost.center_y = grid_to_pixel(c, r)
            ghost.current_dir = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        
        # Reset autopilot
        self.auto_path = []
        self.auto_index = 0

    def on_draw(self):
        self.clear()
        
        if self.show_menu:
            # Dibujar menú
            self.title_text.draw()
            self.menu_text1.draw()
            self.menu_text2.draw()
            self.menu_text3.draw()
            self.menu_text4.draw()
            return

        # Dibujar juego
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()
        
        if self.pacman:
            # Dibujar Pacman
            rect_p=arcade.rect.XYWH(self.pacman.center_x,self.pacman.center_y,TILE_SIZE,TILE_SIZE)
            arcade.draw_rect_filled(rect_p,self.pacman.color)
            
        # Dibujar fantasmas
        for g in self.ghosts:
            rect_g=arcade.rect.XYWH(g.center_x,g.center_y,TILE_SIZE,TILE_SIZE)
            arcade.draw_rect_filled(rect_g,g.color)
        
        # Actualizar y dibujar HUD
        self.update_hud_text()
        self.hud_text.draw()
        self.controls_text.draw()
        
        # Dibujar mensajes de estado final
        if self.state == "WIN":
            self.win_text.draw()
            self.restart_text.draw()
        elif self.state == "LOSE":
            self.lose_text.draw()
            self.restart_text.draw()

    def on_update(self,delta_time:float):
        if self.show_menu or self.state!="PLAY" or not self.pacman: 
            return

        if self.pacman.invulnerable_timer>0: 
            self.pacman.invulnerable_timer-=delta_time

        # Autopilot con evasión
        if self.autopilot and is_center_of_cell(self.pacman) and (not self.auto_path or self.auto_index >= len(self.auto_path)):
            start = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
            
            # Crear zona prohibida alrededor de los fantasmas
            forbidden = set()
            for g in self.ghosts:
                gc, gr = pixel_to_grid(g.center_x, g.center_y)
                # Agregar posición del fantasma y posiciones adyacentes
                for dc, dr in [(0,0), (1,0), (-1,0), (0,1), (0,-1)]:
                    nc, nr = gc + dc, gr + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS:
                        forbidden.add((nc, nr))
            
            # Buscar el pellet más cercano alcanzable
            targets = [pixel_to_grid(p.center_x, p.center_y) for p in self.pellet_list]
            
            best_path = None
            for target in sorted(targets, key=lambda t: manhattan(start, t)):
                path = astar(start, target, self.walls_grid, forbidden)
                if path and len(path) > 1:
                    best_path = path
                    break
            
            if best_path:
                self.auto_path = best_path
                self.auto_index = 1

        # Seguir ruta de autopilot
        if self.autopilot and self.auto_path and self.auto_index < len(self.auto_path):
            current_pos = pixel_to_grid(self.pacman.center_x, self.pacman.center_y)
            next_pos = self.auto_path[self.auto_index]
            
            dx = next_pos[0] - current_pos[0]
            dy = current_pos[1] - next_pos[1]  # Invertido por sistema de coordenadas
            
            self.pacman.set_direction(dx, dy)
            
            if current_pos == next_pos:
                self.auto_index += 1

        # Movimiento
        self.pacman.update_move(self.walls_grid)
        self.total_steps+=1
        
        # Actualizar ruta
        pos=pixel_to_grid(self.pacman.center_x,self.pacman.center_y)
        if not self.route or self.route[-1]!=pos: 
            self.route.append(pos)

        # Comer pellets
        pac_col,pac_row=pos
        for p in self.pellet_list:
            p_col,p_row=pixel_to_grid(p.center_x,p.center_y)
            if pac_col==p_col and pac_row==p_row:
                p.remove_from_sprite_lists()
                self.pacman.score += 10
                break

        # Mover fantasmas
        for g in self.ghosts:
            g.update_move(self.walls_grid)
            
        # Colisiones con fantasmas
        for g in self.ghosts:
            g_col,g_row=pixel_to_grid(g.center_x,g.center_y)
            if pac_col==g_col and pac_row==g_row and self.pacman.invulnerable_timer<=0:
                self.pacman.lives-=1
                print(f"¡Colisión con enemigo! Vidas restantes: {self.pacman.lives}")
                if self.pacman.lives<=0:
                    self.state="LOSE"
                    print("GAME OVER")
                    print(f"Ruta seguida: {self.route}")
                    return
                # Respawn rápido
                self.reset_positions()

        # Victoria
        if not self.pellet_list and self.pacman.lives>0:
            self.state="WIN"
            print("¡GANASTE!")
            print(f"Ruta seguida: {self.route}")
            print(f"Total pasos: {self.total_steps}")

    def on_key_press(self,key,modifiers):
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
                # Cambiar color y refrescar muros
                self.wall_color = arcade.color.GRAY if self.wall_color == arcade.color.DARK_BLUE else arcade.color.DARK_BLUE
                self.setup()  # Recrear con nuevo color
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
            print(f"Autopilot {'activado' if self.autopilot else 'desactivado'}")
        elif key == arcade.key.C:
            # Alternar color de muros (reinicia tablero)
            self.wall_color = arcade.color.GRAY if self.wall_color == arcade.color.DARK_BLUE else arcade.color.DARK_BLUE
            # Conservar stats actuales
            if self.pacman:
                current_score = self.pacman.score
                current_lives = self.pacman.lives
                self.setup()
                self.pacman.score = current_score
                self.pacman.lives = current_lives
            print(f"Color de muros cambiado a {'Gris' if self.wall_color == arcade.color.GRAY else 'Azul'}")
        elif key == arcade.key.R:
            if self.state in ["LOSE", "WIN"]:
                # Reiniciar juego completo
                self.setup()
                if self.pacman:
                    self.pacman.lives = 3
                    self.pacman.score = 0
                self.state = "PLAY"
                print("Juego reiniciado")
            elif self.state == "PLAY":
                # Respawn rápido
                self.reset_positions()
                print("Respawn rápido")
        
        # Movimiento manual (solo si autopilot está OFF)
        if not self.autopilot and self.pacman and self.state == "PLAY":
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
    game=PacGPT5()
    # No llamamos setup aquí; se llama al elegir en el menú
    arcade.run()

if __name__=="__main__":
    main()