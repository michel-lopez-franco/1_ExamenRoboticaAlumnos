"""
Versión extendida de Pac-Man con enemigos móviles.

==================== Reglas del Juego ====================

1. Enemigos móviles
   - Se colocan enemigos en el mapa marcados con 'E'.
   - Los enemigos se mueven continuamente por el laberinto.
   - Su movimiento es **aleatorio con restricciones**:
     - Solo cambian de dirección en las intersecciones.
     - Evitan retroceder en línea recta, a menos que no haya otra opción.
     - Nunca atraviesan muros.

2. Colisiones y vidas
   - Pac-Man comienza con 3 vidas.
   - Cada vez que un enemigo toca a Pac-Man:
       - Pierde 1 vida.
       - Se reinicia su posición en el punto de partida.
   - Si las vidas llegan a 0 → el juego termina en derrota.

3. Condiciones de fin
   - Éxito: Pac-Man recoge todos los pellets y power pellets, siempre que le queden vidas.
   - Fracaso: Pac-Man pierde todas sus vidas antes de completar el mapa.

4. Salida de información
   - Durante la ejecución se muestran mensajes de:
       - Colisiones y número de vidas restantes.
       - Estado final (Victoria o Game Over).
       - Tiempo total de juego y número de pasos dados.
"""



import arcade, heapq, time, random
from typing import List, Tuple

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
    "#P.......E  E.......P#",
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
TITLE = "PacMan con Enemigos"
ROWS, COLS = len(MAP), len(MAP[0])
W, H = COLS * CELL, ROWS * CELL

# ===================== UTILS =====================
def grid_to_px(c: int, r: int) -> Tuple[int, int]:
    return c * CELL + CELL // 2, (ROWS - r - 1) * CELL + CELL // 2

def px_to_grid(x: float, y: float) -> Tuple[int, int]:
    c = int(x // CELL)
    r = ROWS - int(y // CELL) - 1
    return c, r

def en_centro(spr: arcade.Sprite) -> bool:
    c, r = px_to_grid(spr.center_x, spr.center_y)
    cx, cy = grid_to_px(c, r)
    return abs(spr.center_x - cx) < 2 and abs(spr.center_y - cy) < 2

# ===================== A* =====================
def vecinos(nodo: Tuple[int, int], grid):
    c, r = nodo
    for dc, dr in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nc, nr = c + dc, r + dr
        if 0 <= nc < COLS and 0 <= nr < ROWS and grid[nr][nc] == 0:
            yield (nc, nr)

def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(start: Tuple[int, int], goal: Tuple[int, int], grid):
    if start == goal:
        return [start]
    openh = [(0, start)]
    came, g = {}, {start: 0}
    while openh:
        _, cur = heapq.heappop(openh)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return list(reversed(path))
        for nb in vecinos(cur, grid):
            newg = g[cur] + 1
            if nb not in g or newg < g[nb]:
                g[nb] = newg
                came[nb] = cur
                f = newg + manhattan(nb, goal)
                heapq.heappush(openh, (f, nb))
    return []

# ===================== SPRITES =====================
class Pac(arcade.Sprite):
    def __init__(self, c: int, r: int):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(CELL, arcade.color.WHITE, 255)
        self.color = arcade.color.YELLOW
        self.center_x, self.center_y = grid_to_px(c, r)
        self.dir = (0, 0)
        self.deseada = (0, 0)
        self.score = 0
        self.vidas = 3
        self.steps = 0
        self.spawn = (c, r)

    def set_dir(self, dx, dy):
        self.deseada = (dx, dy)

    def mover(self, grid):
        if en_centro(self):
            if self._puede(self.deseada, grid):
                self.dir = self.deseada
            if not self._puede(self.dir, grid):
                self.dir = (0, 0)
            c, r = px_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_px(c, r)
        self.center_x += self.dir[0] * SPEED
        self.center_y += self.dir[1] * SPEED

    def _puede(self, d, grid) -> bool:
        dx, dy = d
        if dx == dy == 0:
            return True
        c, r = px_to_grid(self.center_x, self.center_y)
        nc, nr = c + dx, r - dy
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            return False
        return grid[nr][nc] == 0

    def reset_pos(self):
        c, r = self.spawn
        self.center_x, self.center_y = grid_to_px(c, r)
        self.dir = (0, 0)
        self.deseada = (0, 0)

class Enemy(arcade.Sprite):
    def __init__(self, c: int, r: int, color):
        super().__init__()
        self.texture = arcade.make_soft_square_texture(CELL, arcade.color.WHITE, 255)
        self.color = color
        self.spawn = (c, r)
        self.center_x, self.center_y = grid_to_px(c, r)
        self.dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])

    def mover(self, grid):
        if en_centro(self):
            c, r = px_to_grid(self.center_x, self.center_y)
            opciones = []
            for d in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nc, nr = c + d[0], r - d[1]
                if 0 <= nc < COLS and 0 <= nr < ROWS and grid[nr][nc] == 0:
                    opciones.append(d)

            # Si hay varias opciones, cambiar con probabilidad
            if len(opciones) > 1:
                # eliminar la opción de retroceder para hacerlo más natural
                opuestas = (-self.dir[0], -self.dir[1])
                if opuestas in opciones and len(opciones) > 1:
                    opciones.remove(opuestas)

                self.dir = random.choice(opciones)
            elif opciones:
                self.dir = opciones[0]

            # alinear al centro
            self.center_x, self.center_y = grid_to_px(c, r)

        # avanzar
        self.center_x += self.dir[0] * SPEED // 2
        self.center_y += self.dir[1] * SPEED // 2



# ===================== JUEGO =====================
class Game(arcade.Window):
    def __init__(self):
        super().__init__(W, H, TITLE, update_rate=1/60)
        arcade.set_background_color(arcade.color.BLACK)
        self.walls, self.food, self.power = arcade.SpriteList(), arcade.SpriteList(), arcade.SpriteList()
        self.enemies = arcade.SpriteList()
        self.pac = None
        self.grid = []
        self.route = []
        self.idx = 0
        self.state = "PLAY"
        self.start_time = 0
        self.total_time = 0

    def setup(self):
        self.walls, self.food, self.power = arcade.SpriteList(), arcade.SpriteList(), arcade.SpriteList()
        self.enemies = arcade.SpriteList()
        self.grid = [[0] * COLS for _ in range(ROWS)]
        pacpos = None
        epos = []

        for r, row in enumerate(MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_px(c, r)
                if ch == "#":
                    w = arcade.SpriteSolidColor(CELL, CELL, arcade.color.BLUE)
                    w.center_x, w.center_y = x, y
                    self.walls.append(w)
                    self.grid[r][c] = 1
                elif ch == ".":
                    f = arcade.SpriteSolidColor(6, 6, arcade.color.WHITE)
                    f.center_x, f.center_y = x, y
                    self.food.append(f)
                elif ch == "o":
                    pw = arcade.SpriteSolidColor(12, 12, arcade.color.ORANGE)
                    pw.center_x, pw.center_y = x, y
                    self.power.append(pw)
                elif ch == "P":
                    pacpos = (c, r)
                elif ch == "E":
                    epos.append((c, r))

        if pacpos:
            self.pac = Pac(*pacpos)

        for (c, r) in epos:
            self.enemies.append(Enemy(c, r, arcade.color.RED))

        self.start_time = time.time()

    def on_draw(self):
        self.clear()
        self.walls.draw()
        self.food.draw()
        self.power.draw()
        if self.pac:
            arcade.draw_rect_filled(
                arcade.rect.XYWH(self.pac.center_x, self.pac.center_y, CELL, CELL),
                arcade.color.YELLOW,
            )
        self.enemies.draw()
        arcade.draw_text(f"Puntos: {self.pac.score}", 10, H - 20, arcade.color.YELLOW, 14)
        arcade.draw_text(f"Vidas: {self.pac.vidas}", 10, H - 40, arcade.color.WHITE, 14)

        if self.state == "WIN":
            arcade.draw_text("¡VICTORIA!", W / 2, H / 2, arcade.color.GREEN, 40, anchor_x="center")
            arcade.draw_text(f"Tiempo: {self.total_time}s  Pasos: {self.pac.steps}",
                             W / 2, H / 2 - 50, arcade.color.WHITE, 20, anchor_x="center")
        elif self.state == "FAIL":
            arcade.draw_text("GAME OVER", W / 2, H / 2, arcade.color.RED, 40, anchor_x="center")
            arcade.draw_text(f"Tiempo: {self.total_time}s  Pasos: {self.pac.steps}",
                             W / 2, H / 2 - 50, arcade.color.WHITE, 20, anchor_x="center")

    def on_update(self, dt):
        if self.state != "PLAY" or not self.pac:
            return

        for e in self.enemies:
            e.mover(self.grid)

        # Autopilot pellets
        if en_centro(self.pac) and (not self.route or self.idx >= len(self.route)):
            pos = px_to_grid(self.pac.center_x, self.pac.center_y)
            targets = [px_to_grid(s.center_x, s.center_y) for s in self.food] + \
                      [px_to_grid(s.center_x, s.center_y) for s in self.power]
            if targets:
                targets.sort(key=lambda t: manhattan(pos, t))
                goal = targets[0]
                self.route = astar(pos, goal, self.grid)
                self.idx = 1

        if self.route and self.idx < len(self.route):
            pos = px_to_grid(self.pac.center_x, self.pac.center_y)
            nxt = self.route[self.idx]
            dx = nxt[0] - pos[0]
            dy = pos[1] - nxt[1]
            self.pac.set_dir(dx, dy)
            if pos == nxt:
                self.idx += 1
                self.pac.steps += 1

        self.pac.mover(self.grid)

        # Comer pellets
        for f in arcade.check_for_collision_with_list(self.pac, self.food):
            f.remove_from_sprite_lists()
            self.pac.score += 10
        for pw in arcade.check_for_collision_with_list(self.pac, self.power):
            pw.remove_from_sprite_lists()
            self.pac.score += 50

        # Colisiones con enemigos
        for e in arcade.check_for_collision_with_list(self.pac, self.enemies):
            self.pac.vidas -= 1
            print(f"Colisión! Vidas restantes: {self.pac.vidas}")
            self.pac.reset_pos()
            # Resetear ruta al perder vida
            self.route, self.idx = [], 0
            if self.pac.vidas <= 0:
                self.state = "FAIL"
                self.total_time = round(time.time() - self.start_time, 2)
                print(f"Derrota. Tiempo: {self.total_time}s Pasos: {self.pac.steps}")

        # Victoria
        if not self.food and not self.power and self.pac.vidas > 0:
            self.state = "WIN"
            self.total_time = round(time.time() - self.start_time, 2)
            print(f"Victoria! Tiempo: {self.total_time}s Pasos: {self.pac.steps}")

# ===================== MAIN =====================
def main():
    game = Game()
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
