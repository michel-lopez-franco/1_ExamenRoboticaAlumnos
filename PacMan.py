import arcade
from dataclasses import dataclass
from typing import List, Tuple, Deque, Dict, Optional
import random
from collections import deque

# Alias de tipo para colores (arcade usa tuplas RGB o RGBA)
ColorType = Tuple[int, int, int] | Tuple[int, int, int, int]

# ===================== CONFIGURACIÓN GENERAL =====================
SCREEN_TITLE = "PacGPT5"
TILE_SIZE = 32
SCALE = 1
MOVEMENT_SPEED = 4  # píxeles por frame (debe dividir TILE_SIZE)
GHOST_SPEED = 2
POWER_TIME = 7.0
SCREEN_MARGIN = 32

# Mapa: # pared, . punto, o power pellet, P pacman start, G ghost start, ' ' vacío
# Debe ser rectangular
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

ROWS = len(RAW_MAP)
COLS = len(RAW_MAP[0])
SCREEN_WIDTH = COLS * TILE_SIZE
SCREEN_HEIGHT = ROWS * TILE_SIZE

# ===================== DATACLASES / UTILIDADES =====================


def grid_to_pixel(col: int, row: int) -> Tuple[int, int]:
    x = col * TILE_SIZE + TILE_SIZE // 2
    y = (ROWS - row - 1) * TILE_SIZE + TILE_SIZE // 2
    return x, y


def pixel_to_grid(x: float, y: float) -> Tuple[int, int]:
    col = int(x // TILE_SIZE)
    row_from_bottom = int(y // TILE_SIZE)
    row = ROWS - row_from_bottom - 1
    return col, row


def is_center_of_cell(sprite: arcade.Sprite) -> bool:
    # Consideramos que está centrado si está muy cerca del centro
    col, row = pixel_to_grid(sprite.center_x, sprite.center_y)
    cx, cy = grid_to_pixel(col, row)
    return abs(sprite.center_x - cx) < 2 and abs(sprite.center_y - cy) < 2


@dataclass
class GhostState:
    normal_color: ColorType
    frightened_color: ColorType = arcade.color.BLUE


# ===================== SPRITES PERSONALIZADOS =====================
class Pacman(arcade.Sprite):
    def __init__(self, col: int, row: int):
        super().__init__()
        # Crear textura base blanca y aplicar color (tinte) para compatibilidad
        self.texture = arcade.make_soft_square_texture(
            TILE_SIZE, arcade.color.WHITE, 255
        )
        self.color = arcade.color.YELLOW
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.current_dir = (0, 0)
        self.desired_dir = (0, 0)
        self.lives = 3
        self.score = 0
        self.power_timer = 0

    def set_direction(self, dx: int, dy: int):
        self.desired_dir = (dx, dy)

    def update_move(self, walls_grid):
        # Convertir a movimiento centrado en celdas
        if is_center_of_cell(self):
            # Intentar cambiar a dirección deseada si no hay pared
            if self.can_move(self.desired_dir, walls_grid):
                self.current_dir = self.desired_dir
            # Si la dirección actual está bloqueada, parar
            if not self.can_move(self.current_dir, walls_grid):
                self.current_dir = (0, 0)

            # Ajustar exactamente al centro para evitar acumulación de error
            col, row = pixel_to_grid(self.center_x, self.center_y)
            cx, cy = grid_to_pixel(col, row)
            self.center_x, self.center_y = cx, cy

        self.center_x += self.current_dir[0] * MOVEMENT_SPEED
        self.center_y += self.current_dir[1] * MOVEMENT_SPEED

    def can_move(self, direction, walls_grid) -> bool:
        dx, dy = direction
        if dx == 0 and dy == 0:
            return True
        col, row = pixel_to_grid(self.center_x, self.center_y)
        # mirar celda destino
        target_col = col + dx
        target_row = row - dy  # porque y positiva es arriba (fila menor)
        if target_col < 0 or target_col >= COLS or target_row < 0 or target_row >= ROWS:
            return False
        return walls_grid[target_row][target_col] == 0


class Ghost(arcade.Sprite):
    def __init__(self, col: int, row: int, state: GhostState):
        super().__init__()
        # Textura base blanca y luego se ajusta self.color
        self.texture = arcade.make_soft_square_texture(
            TILE_SIZE, arcade.color.WHITE, 255
        )
        self.color = state.normal_color
        x, y = grid_to_pixel(col, row)
        self.center_x = x
        self.center_y = y
        self.spawn_col = col
        self.spawn_row = row
        self.state = state
        self.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.frightened = False
        self.dead = False
        self.change_counter = 0.0

    def update_move(self, walls_grid, pacman: Pacman, delta_time: float):
        speed = GHOST_SPEED
        self.change_counter += delta_time

        if self.dead:
            # Ir de vuelta a spawn
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
                self.change_counter = 0
        else:
            self.color = self.state.normal_color
            # perseguir o deambular
            if self.change_counter > 0.3:
                self.current_dir = self._chase_dir(pacman, walls_grid)
                self.change_counter = 0

        if is_center_of_cell(self):
            # asegurar no entremos a pared
            if not self._can_dir(self.current_dir, walls_grid):
                self.current_dir = self._random_dir(walls_grid)

            # snap
            col, row = pixel_to_grid(self.center_x, self.center_y)
            self.center_x, self.center_y = grid_to_pixel(col, row)

        self.center_x += self.current_dir[0] * speed
        self.center_y += self.current_dir[1] * speed

    def _at_target(self, target_cell):
        col, row = pixel_to_grid(self.center_x, self.center_y)
        return (col, row) == target_cell

    def _move_towards(self, target_cell, walls_grid, speed):
        if is_center_of_cell(self):
            col, row = pixel_to_grid(self.center_x, self.center_y)
            tcol, trow = target_cell
            options = []
            if tcol > col:
                options.append((1, 0))
            if tcol < col:
                options.append((-1, 0))
            if trow > row:
                options.append((0, -1))  # arriba en pantalla -> fila menor
            if trow < row:
                options.append((0, 1))
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
        # line-of-sight simple: priorizar dirección que reduce distancia Manhattan
        col, row = pixel_to_grid(self.center_x, self.center_y)
        pcol, prow = pixel_to_grid(pacman.center_x, pacman.center_y)
        dirs = []
        if pcol > col:
            dirs.append((1, 0))
        if pcol < col:
            dirs.append((-1, 0))
        if prow > row:
            dirs.append((0, -1))
        if prow < row:
            dirs.append((0, 1))
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
        col, row = pixel_to_grid(self.center_x, self.center_y)
        tcol = col + dx
        trow = row - dy
        if tcol < 0 or tcol >= COLS or trow < 0 or trow >= ROWS:
            return False
        return walls_grid[trow][tcol] == 0

    def eaten(self):
        self.dead = True
        self.frightened = False
        self.color = arcade.color.GRAY


# ===================== JUEGO PRINCIPAL =====================
class PacGPT5(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, update_rate=1 / 60)
        arcade.set_background_color(arcade.color.BLACK)
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts: List[Ghost] = []
        self.pacman: Pacman | None = None
        self.walls_grid = []  # 1 pared, 0 libre
        self.state = "PLAY"  # PLAY, WIN, LOSE
        # Autopiloto
        self.autopilot = False
        self.autopilot_path = []  # Secuencia de celdas (col,row)

    def setup(self):
        self.wall_list = arcade.SpriteList()
        self.pellet_list = arcade.SpriteList()
        self.power_list = arcade.SpriteList()
        self.ghosts = []
        self.state = "PLAY"
        self.walls_grid = [[0] * COLS for _ in range(ROWS)]
        self.autopilot_path.clear()

        pacman_positions = []
        ghost_positions = []

        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                x, y = grid_to_pixel(c, r)
                if ch == "#":
                    wall = arcade.SpriteSolidColor(
                        TILE_SIZE, TILE_SIZE, arcade.color.DARK_BLUE
                    )
                    wall.center_x = x
                    wall.center_y = y
                    self.wall_list.append(wall)
                    self.walls_grid[r][c] = 1
                elif ch == ".":
                    pellet = arcade.SpriteSolidColor(6, 6, arcade.color.WHITE)
                    pellet.center_x = x
                    pellet.center_y = y
                    self.pellet_list.append(pellet)
                elif ch == "o":
                    power = arcade.SpriteSolidColor(14, 14, arcade.color.ORANGE_PEEL)
                    power.center_x = x
                    power.center_y = y
                    self.power_list.append(power)
                elif ch == "P":
                    pacman_positions.append((c, r))
                elif ch == "G":
                    ghost_positions.append((c, r))

        # Crear Pac-Man (usar primera P; si hay dos, la segunda se convierte en pellet start)
        if pacman_positions:
            col, row = pacman_positions[0]
            self.pacman = Pacman(col, row)
            # Las otras P se tratan como pellets
            for extra in pacman_positions[1:]:
                c, r = extra
                px, py = grid_to_pixel(c, r)
                pellet = arcade.SpriteSolidColor(6, 6, arcade.color.WHITE)
                pellet.center_x = px
                pellet.center_y = py
                self.pellet_list.append(pellet)
        else:
            # fallback centro
            self.pacman = Pacman(COLS // 2, ROWS // 2)

        # Crear fantasmas
        colors = [
            arcade.color.RED,
            arcade.color.GREEN,
            arcade.color.PURPLE,
            arcade.color.PINK,
        ]
        for idx, pos in enumerate(ghost_positions):
            col, row = pos
            ghost = Ghost(col, row, GhostState(colors[idx % len(colors)]))
            self.ghosts.append(ghost)

    # ===================== CICLO =====================
    def on_draw(self):
        # En Arcade 3.x se debe usar clear() dentro de on_draw en vez de start_render()
        self.clear()
        self.wall_list.draw()
        self.pellet_list.draw()
        self.power_list.draw()
        # Dibujar Pac-Man y fantasmas manualmente (evita dependencia de sprite.draw)
        if self.pacman:
            rect_p = arcade.rect.XYWH(
                self.pacman.center_x, self.pacman.center_y, TILE_SIZE, TILE_SIZE
            )
            arcade.draw_rect_filled(
                rect_p, getattr(self.pacman, "color", arcade.color.YELLOW)
            )
        for g in self.ghosts:
            rect_g = arcade.rect.XYWH(g.center_x, g.center_y, TILE_SIZE, TILE_SIZE)
            arcade.draw_rect_filled(rect_g, getattr(g, "color", arcade.color.RED))

        # UI
        if self.pacman:
            arcade.draw_text(
                f"Score: {self.pacman.score}",
                10,
                SCREEN_HEIGHT - 22,
                arcade.color.YELLOW,
                14,
            )
            arcade.draw_text(
                f"Vidas: {self.pacman.lives}",
                10,
                SCREEN_HEIGHT - 40,
                arcade.color.YELLOW,
                14,
            )
            if self.pacman.power_timer > 0:
                arcade.draw_text(
                    f"Poder: {self.pacman.power_timer:0.1f}",
                    10,
                    SCREEN_HEIGHT - 58,
                    arcade.color.ORANGE_PEEL,
                    14,
                )

        if self.state == "WIN":
            arcade.draw_text(
                "¡GANASTE!",
                SCREEN_WIDTH / 2,
                SCREEN_HEIGHT / 2,
                arcade.color.GREEN,
                40,
                anchor_x="center",
            )
        elif self.state == "LOSE":
            arcade.draw_text(
                "GAME OVER",
                SCREEN_WIDTH / 2,
                SCREEN_HEIGHT / 2,
                arcade.color.RED,
                40,
                anchor_x="center",
            )
        # Indicador de autopiloto
        arcade.draw_text(
            f"Autopiloto: {'ON' if self.autopilot else 'OFF'} (tecla A)",
            SCREEN_WIDTH - 10,
            10,
            arcade.color.WHITE,
            12,
            anchor_x="right",
        )

    def on_update(self, delta_time: float):
        if self.state != "PLAY" or not self.pacman:
            return

        # Update timers
        if self.pacman.power_timer > 0:
            self.pacman.power_timer -= delta_time
            if self.pacman.power_timer <= 0:
                # fin del poder
                for g in self.ghosts:
                    if not g.dead:
                        g.frightened = False

        # Movimiento Pac-Man
        self.pacman.update_move(self.walls_grid)

        # Comer pellets
        pellets_hit = arcade.check_for_collision_with_list(
            self.pacman, self.pellet_list
        )
        for p in pellets_hit:
            p.remove_from_sprite_lists()
            self.pacman.score += 10

        powers_hit = arcade.check_for_collision_with_list(self.pacman, self.power_list)
        if powers_hit:
            for pw in powers_hit:
                pw.remove_from_sprite_lists()
            self.pacman.power_timer = POWER_TIME
            for g in self.ghosts:
                if not g.dead:
                    g.frightened = True

        # Ver victoria
        if len(self.pellet_list) == 0 and len(self.power_list) == 0:
            self.state = "WIN"

    def _reset_positions(self):
        # Reiniciar pacman y fantasmas a spawn
        if not self.pacman:
            return
        # Buscar spawn original (el primero P del mapa)
        for r, row in enumerate(RAW_MAP):
            for c, ch in enumerate(row):
                if ch == "P":
                    x, y = grid_to_pixel(c, r)
                    self.pacman.center_x = x
                    self.pacman.center_y = y
                    self.pacman.current_dir = (0, 0)
                    self.pacman.desired_dir = (0, 0)
                    self.pacman.power_timer = 0
                    break
            else:
                continue
            break
        for g in self.ghosts:
            x, y = grid_to_pixel(g.spawn_col, g.spawn_row)
            g.center_x = x
            g.center_y = y
            g.dead = False
            g.frightened = False
            g.current_dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            g.color = g.state.normal_color

    # ===================== INPUT =====================
    def on_key_press(self, key, modifiers):
        if not self.pacman:
            return
        if key == arcade.key.UP:
            self.pacman.set_direction(0, 1)
        elif key == arcade.key.DOWN:
            self.pacman.set_direction(0, -1)
        elif key == arcade.key.LEFT:
            self.pacman.set_direction(-1, 0)
        elif key == arcade.key.RIGHT:
            self.pacman.set_direction(1, 0)
        elif key == arcade.key.R and self.state != "PLAY":
            self.setup()
        elif key == arcade.key.ESCAPE:
            arcade.close_window()


# ===================== MAIN =====================


def main():
    game = PacGPT5()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()
