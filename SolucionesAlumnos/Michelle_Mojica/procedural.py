"""
Procedural Caves with autonomous A* solver and solving time overlay.
"""

import random
import arcade
import timeit

# ===== Configuración original =====
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

GRID_WIDTH = 450
GRID_HEIGHT = 400

CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

MOVEMENT_SPEED = 5
VIEWPORT_MARGIN = 300

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves Cellular Automata Example"
CAMERA_SPEED = 0.1


def create_grid(width, height):
    return [[0 for _x in range(width)] for _y in range(height)]


def initialize_grid(grid):
    height = len(grid)
    width = len(grid[0])
    for row in range(height):
        for column in range(width):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[row][column] = 1


def count_alive_neighbors(grid, x, y):
    height = len(grid)
    width = len(grid[0])
    alive_count = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            nx = x + i
            ny = y + j
            if i == 0 and j == 0:
                continue
            elif nx < 0 or ny < 0 or ny >= height or nx >= width:
                alive_count += 1
            elif grid[ny][nx] == 1:
                alive_count += 1
    return alive_count


def do_simulation_step(old_grid):
    height = len(old_grid)
    width = len(old_grid[0])
    new_grid = create_grid(width, height)
    for x in range(width):
        for y in range(height):
            alive_neighbors = count_alive_neighbors(old_grid, x, y)
            if old_grid[y][x] == 1:
                new_grid[y][x] = 0 if alive_neighbors < DEATH_LIMIT else 1
            else:
                new_grid[y][x] = 1 if alive_neighbors > BIRTH_LIMIT else 0
    return new_grid


class InstructionView(arcade.View):
    def __init__(self):
        super().__init__()
        self.frame_count = 0

    def on_show_view(self):
        self.window.background_color = arcade.csscolor.DARK_SLATE_BLUE
        self.window.default_camera.use()

    def on_draw(self):
        self.clear()
        arcade.draw_text(
            "Loading...",
            self.window.width // 2,
            self.window.height // 2,
            arcade.color.BLACK,
            font_size=50,
            anchor_x="center",
        )

    def on_update(self, dt):
        if self.frame_count == 0:
            self.frame_count += 1
            return
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.grid = None
        self.wall_list = None
        self.player_list = None
        self.player_sprite = None
        self.draw_time = 0
        self.processing_time = 0
        self.physics_engine = None

        # Cámaras
        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()

        self.window.background_color = arcade.color.BLACK

        # ===== Navegación y tiempo (nuevo) =====
        self.path_cells = None
        self.waypoints = []
        self.current_wp = None
        self.solving = False
        self.solved = False
        self.solve_time = 0.0
        self.solve_start = None

        # Texto único
        self.solving_text = None

    # ======= Utilidades de grilla y A* (nuevo) =======
    def _pos_to_cell(self, x, y):
        c = int(x // SPRITE_SIZE)
        r = int(y // SPRITE_SIZE)
        return r, c

    def _cell_to_pos_center(self, r, c):
        return (c * SPRITE_SIZE + SPRITE_SIZE / 2,
                r * SPRITE_SIZE + SPRITE_SIZE / 2)

    def _is_free(self, r, c):
        return 0 <= r < GRID_HEIGHT and 0 <= c < GRID_WIDTH and self.grid[r][c] == 0

    def _neighbors4(self, r, c):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if self._is_free(nr, nc):
                yield nr, nc

    def _is_border_cell(self, r, c):
        return r == 0 or r == GRID_HEIGHT - 1 or c == 0 or c == GRID_WIDTH - 1

    def _astar_to_nearest_border(self, start_rc):
        import heapq
        sr, sc = start_rc

        def h(r, c):
            return min(r, GRID_HEIGHT - 1 - r, c, GRID_WIDTH - 1 - c)

        openq = []
        heapq.heappush(openq, (h(sr, sc), 0, (sr, sc)))
        came = {}
        g = {(sr, sc): 0}
        visited = set()

        while openq:
            f, gcost, (r, c) = heapq.heappop(openq)
            if (r, c) in visited:
                continue
            visited.add((r, c))

            if self._is_border_cell(r, c):
                path = [(r, c)]
                while (r, c) in came:
                    r, c = came[(r, c)]
                    path.append((r, c))
                path.reverse()
                return path

            for nr, nc in self._neighbors4(r, c):
                ng = g[(r, c)] + 1
                if (nr, nc) not in g or ng < g[(nr, nc)]:
                    g[(nr, nc)] = ng
                    came[(nr, nc)] = (r, c)
                    heapq.heappush(openq, (ng + h(nr, nc), ng, (nr, nc)))
        return None

    # ======= Fin utilidades =======

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()

        # Generar cueva
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for _ in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.BasicSprite(texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # Jugador
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING,
        )
        self.player_list.append(self.player_sprite)

        # Colocar jugador en espacio libre
        placed = False
        while not placed:
            max_x = int(GRID_WIDTH * SPRITE_SIZE)
            max_y = int(GRID_HEIGHT * SPRITE_SIZE)
            self.player_sprite.center_x = random.randrange(max_x)
            self.player_sprite.center_y = random.randrange(max_y)
            if not arcade.check_for_collision_with_list(self.player_sprite, self.wall_list):
                placed = True

        self.physics_engine = arcade.PhysicsEngineSimple(self.player_sprite, self.wall_list)

        # Texto “Solving time:”
        self.solving_text = arcade.Text(
            "Solving time: 0.000", 20, self.window.height - 20, arcade.color.WHITE, 16
        )

        # Planear ruta con A*
        start_rc = self._pos_to_cell(self.player_sprite.center_x, self.player_sprite.center_y)
        if not self._is_free(*start_rc):
            # Ajuste local a celda libre vecina si cayó en borde de celda
            for nr, nc in self._neighbors4(*start_rc):
                start_rc = (nr, nc)
                break

        self.path_cells = self._astar_to_nearest_border(start_rc)
        self.waypoints = []
        if self.path_cells:
            for r, c in self.path_cells:
                self.waypoints.append(self._cell_to_pos_center(r, c))
            if self.waypoints and abs(self.player_sprite.center_x - self.waypoints[0][0]) < 1e-3 \
               and abs(self.player_sprite.center_y - self.waypoints[0][1]) < 1e-3:
                self.waypoints = self.waypoints[1:]
            self.current_wp = self.waypoints[0] if self.waypoints else None
            self.solving = True
            self.solve_start = timeit.default_timer()
        else:
            # No hay salida conectada
            self.solving = False
            self.solved = True
            self.solve_time = 0.0

        self.scroll_to_player(1.0)

    def on_draw(self):
        draw_start_time = timeit.default_timer()
        self.clear()

        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.player_list.draw()

        self.camera_gui.use()
        if self.solved:
            self.solving_text.text = f"Solving time: {self.solve_time:.3f}"
        else:
            elapsed = (timeit.default_timer() - self.solve_start) if self.solving and self.solve_start else 0.0
            self.solving_text.text = f"Solving time: {elapsed:.3f}"
        self.solving_text.draw()

        self.draw_time = timeit.default_timer() - draw_start_time

    def scroll_to_player(self, camera_speed):
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(
            self.camera_sprites.position, position, camera_speed
        )

    def on_resize(self, width: int, height: int):
        super().on_resize(width, height)
        self.camera_sprites.match_window()
        self.camera_gui.match_window()
        # Reposicionar texto al redimensionar
        if self.solving_text:
            self.solving_text.x = 20
            self.solving_text.y = self.window.height - 20

    def on_update(self, delta_time):
        start_time = timeit.default_timer()

        # Movimiento autónomo hacia el siguiente waypoint
        if self.solving and self.current_wp:
            dx = self.current_wp[0] - self.player_sprite.center_x
            dy = self.current_wp[1] - self.player_sprite.center_y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < MOVEMENT_SPEED:
                # alcanzar waypoint
                self.player_sprite.center_x, self.player_sprite.center_y = self.current_wp
                if self.waypoints:
                    self.waypoints.pop(0)
                self.current_wp = self.waypoints[0] if self.waypoints else None
                if self.current_wp is None:
                    # llegó a salida en el borde
                    self.solving = False
                    self.solved = True
                    self.solve_time = timeit.default_timer() - self.solve_start if self.solve_start else 0.0
            else:
                vx = MOVEMENT_SPEED * dx / dist
                vy = MOVEMENT_SPEED * dy / dist
                self.player_sprite.change_x = vx
                self.player_sprite.change_y = vy
                self.physics_engine.update()
        else:
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0

        self.scroll_to_player(camera_speed=CAMERA_SPEED)
        self.processing_time = timeit.default_timer() - start_time


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = InstructionView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
