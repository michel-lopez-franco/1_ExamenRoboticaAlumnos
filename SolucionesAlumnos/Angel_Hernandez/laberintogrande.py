import random
import arcade
import timeit
from collections import deque

# Sprite scaling
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

# Grid dimensions (como en el código original del profe)
GRID_WIDTH = 450
GRID_HEIGHT = 400

# Cellular automata parameters
CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

# Player speed (pixels per frame)
MOVEMENT_SPEED = 5

# Window config
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves with Keys"

# Camera speed
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
            neighbor_x = x + i
            neighbor_y = y + j
            if i == 0 and j == 0:
                continue
            elif (
                neighbor_x < 0
                or neighbor_y < 0
                or neighbor_y >= height
                or neighbor_x >= width
            ):
                alive_count += 1
            elif grid[neighbor_y][neighbor_x] == 1:
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
                if alive_neighbors < DEATH_LIMIT:
                    new_grid[y][x] = 0
                else:
                    new_grid[y][x] = 1
            else:
                if alive_neighbors > BIRTH_LIMIT:
                    new_grid[y][x] = 1
                else:
                    new_grid[y][x] = 0
    return new_grid


def find_item(grid, start, item_positions):
 
    start_time = timeit.default_timer()

    rows, cols = len(grid), len(grid[0])
    visited = [[False] * cols for _ in range(rows)]
    queue = deque([(start, [])])
    visited[start[0]][start[1]] = True

    while queue:
        (r, c), path = queue.popleft()

        if (r, c) in item_positions:
            elapsed = timeit.default_timer() - start_time
            ruta = path + [(r, c)]
            print(f"Ruta encontrada: {ruta}")
            print(f"Pasos: {len(ruta)}")
            print(f"Tiempo BFS: {elapsed:.4f} s")
            return ruta

        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if not visited[nr][nc] and grid[nr][nc] == 0:
                    visited[nr][nc] = True
                    queue.append(((nr, nc), path + [(r, c)]))

    return None


class InstructionView(arcade.View):
    def on_show_view(self):
        self.window.background_color = arcade.csscolor.DARK_GREEN       
        class GameView(arcade.View):
            def __init__(self):
                super().__init__()
                # ...existing code...
                self.grid = None
                self.wall_list = None
                self.player_sprite = None
                self.player_list = None
                self.key_list = None
                self.camera_sprites = arcade.Camera2D()
                self.camera_gui = arcade.Camera2D()
                self.path = []
                self.keys_remaining = 1
                self.key_positions = []
                # ...existing code...
                self.victory = False
                self.banana_texture = arcade.load_texture("C:\\Users\\lap15\\OneDrive\\Imágenes\\platanos_0.jpg")  # Ruta de la imagen
        
            # ...existing code...
        
            def on_draw(self):
                draw_start_time = timeit.default_timer()
        
                self.clear()
                self.camera_sprites.use()                
                class GameView(arcade.View):
                    def __init__(self):
                        super().__init__()
                        # ...existing code...
                        self.banana_texture = arcade.load_texture("C:/Users/lap15/OneDrive/Imágenes/platanos_0.jpg")  # Cambia la ruta si es necesario
                        # ...existing code...
                self.wall_list.draw(pixelated=True)
                self.key_list.draw()
                self.player_list.draw()
        
                self.camera_gui.use()
                self.sprite_count_text.draw()
                self.draw_time_text.text = f"Drawing time: {self.draw_time:.3f}"
                self.draw_time_text.draw()
                self.processing_time_text.text = f"Processing time: {self.processing_time:.3f}"
                self.processing_time_text.draw()
                self.keys_text.text = f"Llaves restantes: {self.keys_remaining}"
                self.keys_text.draw()
        
                if self.victory:
                    # Dibuja la imagen del plátano en el centro de la pantalla
                    arcade.draw_texture_rectangle(
                        self.window.width // 2,
                        self.window.height // 2,
                        600, 400,  # tamaño de la imagen
                        self.banana_texture
                    )
                    arcade.draw_text(
                        "¡Has recogido todas las llaves!",
                        self.window.width // 2,
                        self.window.height // 2 + 220,
                        arcade.color.YELLOW,
                        font_size=40,
                        anchor_x="center",
                    )
                    # Si quieres ocultar el personaje y las llaves, puedes no dibujarlos cuando self.victory es True

                self.draw_time = timeit.default_timer() - draw_start_time
            class GameView(arcade.View):
                # ...existing code...

                def __init__(self):
                    super().__init__()
                    class GameView(arcade.View):
                        def __init__(self):
                            super().__init__()
                            # ...existing code...
                            self.banana_texture = arcade.load_texture("C:/Users/lap15/OneDrive/Imágenes/platanos_0.jpg")  # Cambia la ruta si es necesario
                            # ...existing code...
                    
                        # ...existing code...
                    
                        def on_draw(self):
                            draw_start_time = timeit.default_timer()
                    
                            self.clear()
                            self.camera_sprites.use()
                            self.wall_list.draw(pixelated=True)
                            self.key_list.draw()
                            self.player_list.draw()
                    
                            self.camera_gui.use()
                            self.sprite_count_text.draw()
                            self.draw_time_text.text = f"Drawing time: {self.draw_time:.3f}"
                            self.draw_time_text.draw()
                            self.processing_time_text.text = f"Processing time: {self.processing_time:.3f}"
                            self.processing_time_text.draw()
                            self.keys_text.text = f"Llaves restantes: {self.keys_remaining}"
                            self.keys_text.draw()
                    
                            if self.victory:
                                # Dibuja la imagen del plátano en el centro de la pantalla
                                arcade.draw_texture_rectangle(
                                    self.window.width // 2,
                                    self.window.height // 2,
                                    600, 400,  # tamaño de la imagen
                                    self.banana_texture
                                )
                                arcade.draw_text(
                                    "¡Has recogido todas las llaves!",
                                    self.window.width // 2,
                                    self.window.height // 2 + 220,
                                    arcade.color.YELLOW,
                                    font_size=40,
                                    anchor_x="center",
                                )
                    
                            self.draw_time = timeit.default_timer() - draw_start_time                # ...existing code...
                self.at_exit = False
                self.exit_texture = arcade.load_texture("C:\\Users\\lap15\\OneDrive\\Imágenes\\platanos_0.jpg")  # Cambia la ruta

            def on_update(self, delta_time):
                if self.victory or self.at_exit:
                    return
        
                # ...existing movement code...
        
                # Detectar si el personaje está en el borde
                col = int(self.player_sprite.center_x // SPRITE_SIZE)
                row = int(self.player_sprite.center_y // SPRITE_SIZE)
                if col == 0 or col == GRID_WIDTH - 1 or row == 0 or row == GRID_HEIGHT - 1:
                    self.at_exit = True
        
                # ...existing code...
        
            def on_draw(self):
                # ...existing code...
                if self.at_exit:
                    # Dibuja la imagen de salida en el centro de la pantalla
                    arcade.draw_texture_rectangle(
                        self.window.width // 2,
                        self.window.height // 2,
                        600, 400,  # tamaño de la imagen
                        self.exit_texture
                    )
                    arcade.draw_text(
                        "¡Has escapado del laberinto!",
                        self.window.width // 2,
                        self.window.height // 2 + 220,
                        arcade.color.YELLOW,
                        font_size=40,
                        anchor_x="center",
                    )
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
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.grid = None
        self.wall_list = None
        self.player_sprite = None
        self.player_list = None
        self.key_list = None
        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()
        self.path = []
        self.keys_remaining = 3
        self.key_positions = []

        # Textos
        self.sprite_count_text = None
        self.draw_time_text = None
        self.processing_time_text = None
        self.keys_text = None

        # Tiempos
        self.draw_time = 0
        self.processing_time = 0

        # Estado de victoria
        self.victory = False

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.key_list = arcade.SpriteList()

        # Crear mapa
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for step in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.BasicSprite(texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # Player
        self.player_sprite = arcade.Sprite(
    "C:\\Users\\lap15\\OneDrive\\Imágenes\\Saved Pictures\\mono.jpg",
    scale=SPRITE_SCALING,
)
        self.player_list.append(self.player_sprite)

        placed = False
        while not placed:
            max_x = int(GRID_WIDTH * SPRITE_SIZE)
            max_y = int(GRID_HEIGHT * SPRITE_SIZE)
            self.player_sprite.center_x = random.randrange(max_x)
            self.player_sprite.center_y = random.randrange(max_y)
            if not arcade.check_for_collision_with_list(self.player_sprite, self.wall_list):
                placed = True

        # Keys
        for _ in range(1):
            placed = False
            while not placed:
                col = random.randrange(GRID_WIDTH)
                row = random.randrange(GRID_HEIGHT)
                if self.grid[row][col] == 0 and (row, col) not in self.key_positions:
                    key = arcade.Sprite(
                        ":resources:images/items/keyYellow.png", scale=SPRITE_SCALING
                    )
                    key.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                    key.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.key_list.append(key)
                    self.key_positions.append((row, col))
                    placed = True

        # Textos
        self.sprite_count_text = arcade.Text(
            f"Sprite Count: {len(self.wall_list):,}",
            20, self.window.height - 20, arcade.color.WHITE, 16
        )
        self.draw_time_text = arcade.Text(
            "Drawing time:", 20, self.window.height - 40, arcade.color.WHITE, 16
        )
        self.processing_time_text = arcade.Text(
            "Processing time:", 20, self.window.height - 60, arcade.color.WHITE, 16
        )
        self.keys_text = arcade.Text(
            f"Llaves restantes: {self.keys_remaining}",
            20, self.window.height - 80, arcade.color.YELLOW, 20
        )

        # Calcular primera ruta
        self.calculate_new_path()

        # Cámara en el jugador desde inicio
        self.scroll_to_player(1.0)

    def calculate_new_path(self):
        if not self.key_positions:
            print("¡Has recogido todas las llaves!")
            self.victory = True
            return

        start_row = int(self.player_sprite.center_y // SPRITE_SIZE)
        start_col = int(self.player_sprite.center_x // SPRITE_SIZE)
        path = find_item(self.grid, (start_row, start_col), self.key_positions)
        if path:
            self.path = path[1:]  # quitar la posición inicial
        else:
            print("No se encontró camino a ninguna llave.")
            self.victory = True   # activa modo pausa
            self.no_path = True   # (nuevo flag para distinguir del final normal)

    def on_draw(self):
        draw_start_time = timeit.default_timer()

        self.clear()
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.key_list.draw()
        self.player_list.draw()

        self.camera_gui.use()
        self.sprite_count_text.draw()
        self.draw_time_text.text = f"Drawing time: {self.draw_time:.3f}"
        self.draw_time_text.draw()
        self.processing_time_text.text = f"Processing time: {self.processing_time:.3f}"
        self.processing_time_text.draw()
        self.keys_text.text = f"Llaves restantes: {self.keys_remaining}"
        self.keys_text.draw()

        if self.victory:
            if hasattr(self, "no_path") and self.no_path:
                arcade.draw_text(
                    "No se encontró camino a las llaves",
                    self.window.width // 2,
                    self.window.height // 2,
                    arcade.color.RED,
                    font_size=40,
                    anchor_x="center",
                )
            else:
                arcade.draw_text(
                    "¡Has recogido todas las llaves!",
                    self.window.width // 2,
                    self.window.height // 2,
                    arcade.color.GREEN,
                    font_size=40,
                    anchor_x="center",
                )


        self.draw_time = timeit.default_timer() - draw_start_time

    def on_update(self, delta_time):
        if self.victory:
            return

        start_time = timeit.default_timer()

        # Movimiento paso a paso
        if self.path:
            next_row, next_col = self.path[0]
            target_x = next_col * SPRITE_SIZE + SPRITE_SIZE / 2
            target_y = next_row * SPRITE_SIZE + SPRITE_SIZE / 2

            dx = target_x - self.player_sprite.center_x
            dy = target_y - self.player_sprite.center_y

            if abs(dx) < MOVEMENT_SPEED and abs(dy) < MOVEMENT_SPEED:
                self.player_sprite.center_x = target_x
                self.player_sprite.center_y = target_y
                self.path.pop(0)
            else:
                if dx > 0:
                    self.player_sprite.center_x += MOVEMENT_SPEED
                elif dx < 0:
                    self.player_sprite.center_x -= MOVEMENT_SPEED
                if dy > 0:
                    self.player_sprite.center_y += MOVEMENT_SPEED
                elif dy < 0:
                    self.player_sprite.center_y -= MOVEMENT_SPEED

        # Colisión con llaves
        hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.key_list)
        for key in hit_list:
            idx = self.key_list.index(key)
            key.remove_from_sprite_lists()
            self.key_positions.pop(idx)
            self.keys_remaining -= 1
            self.calculate_new_path()

        # Scroll cámara
        self.scroll_to_player(CAMERA_SPEED)

        self.processing_time = timeit.default_timer() - start_time

    def scroll_to_player(self, camera_speed):
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(
            self.camera_sprites.position,
            position,
            camera_speed,
        )


def main():
    # === Caso de prueba sencillo de BFS ===
    test_maze = [
        [0, 1, 0],
        [0, 0, 0],
        [1, 0, 1],
    ]
    test_start = (0, 0)
    test_items = [(1, 2)]
    print("=== Caso de prueba BFS ===")
    path = find_item(test_maze, test_start, test_items)
    print("Salida esperada: [(0,0), (1,0), (1,1), (1,2)]")
    print("Salida obtenida:", path)
    print("==========================\n")

    # === Inicio del juego ===
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = InstructionView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()