import random
import arcade
import timeit
from collections import deque

# --- Constantes ---
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING
GRID_WIDTH = 450
GRID_HEIGHT = 400
MOVEMENT_SPEED = 5
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves with Keys"
CAMERA_SPEED = 0.1

# --- Parámetros del Autómata Celular ---
CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

# --- Lógica del Laberinto ---

def create_grid(width, height):
    """Crea una grilla vacía."""
    return [[0 for _x in range(width)] for _y in range(height)]

def initialize_grid(grid):
    """Inicializa la grilla con celdas vivas aleatoriamente."""
    height = len(grid)
    width = len(grid[0])
    for row in range(height):
        for column in range(width):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[row][column] = 1

def count_alive_neighbors(grid, x, y):
    """Cuenta los vecinos vivos de una celda."""
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
                alive_count += 1  # Los bordes cuentan como vivos
            elif grid[neighbor_y][neighbor_x] == 1:
                alive_count += 1
    return alive_count

def do_simulation_step(old_grid):
    """Ejecuta un paso de la simulación del autómata celular."""
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
    """Encuentra la ruta más corta a cualquiera de los items usando BFS."""
    start_time = timeit.default_timer()
    rows, cols = len(grid), len(grid[0])
    queue = deque([(start, [start])])
    visited = {start}

    while queue:
        (r, c), path = queue.popleft()

        if (r, c) in item_positions:
            elapsed = timeit.default_timer() - start_time
            print(f"Ruta encontrada: {path}")
            print(f"Pasos: {len(path) - 1}")
            print(f"Tiempo BFS: {elapsed:.4f} s")
            return path

        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0 and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append(((nr, nc), path + [(nr, nc)]))
    return None

# --- Vistas del Juego ---

class InstructionView(arcade.View):
    """Vista inicial que muestra 'Loading...' y luego cambia a la vista del juego."""
    def on_show_view(self):
        self.window.background_color = arcade.csscolor.DARK_SLATE_BLUE

    def on_draw(self):
        self.clear()
        arcade.draw_text(
            "Loading...",
            self.window.width / 2,
            self.window.height / 2,
            arcade.color.WHITE,
            font_size=50,
            anchor_x="center",
        )

    def on_update(self, dt):
        """Una vez que se muestra, crea la vista del juego y cambia a ella."""
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    """Vista principal del juego."""
    def __init__(self):
        super().__init__()
        self.grid = None
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.key_list = arcade.SpriteList()
        
        self.player_sprite = None
        self.camera_sprites = arcade.Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.camera_gui = arcade.Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        self.path = []
        self.keys_remaining = 3
        self.key_positions = []
        
        self.draw_time = 0
        self.processing_time = 0
        
        self.victory = False
        self.no_path = False
        
        # Textura para la pantalla de victoria
        self.victory_texture = None

    def setup(self):
        """Configura el nivel del juego."""
        # Cargar la textura para la pantalla de victoria
        # CAMBIA ESTA RUTA a la de tu imagen. Usa .png o .jpg
        try:
            # Intenta cargar tu imagen. Asegúrate de que la ruta sea correcta y el formato compatible.
            self.victory_texture = arcade.load_texture("C:/Users/gabos/OneDrive/Imágenes/Capturas de pantalla/burrito.png")
        except FileNotFoundError:
            print("Advertencia: No se encontró la imagen 'burrito.png'. Usando imagen de reemplazo.")
            # Si falla, usa una imagen de recursos de arcade para que el juego no se rompa.
            self.victory_texture = arcade.load_texture(":resources:images/items/gemYellow.png")

        # Crear mapa con autómata celular
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for _ in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        # Crear sprites de las paredes
        wall_texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.Sprite(texture=wall_texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # Colocar al jugador en una posición válida
        # CAMBIA ESTA RUTA a la de tu imagen de jugador
        player_texture_path = ":resources:images/animated_characters/robot/robot_idle.png"
        self.player_sprite = arcade.Sprite(player_texture_path, scale=SPRITE_SCALING)
        self.player_list.append(self.player_sprite)
        
        placed = False
        while not placed:
            self.player_sprite.center_x = random.randrange(GRID_WIDTH * SPRITE_SIZE)
            self.player_sprite.center_y = random.randrange(GRID_HEIGHT * SPRITE_SIZE)
            if not arcade.check_for_collision_with_list(self.player_sprite, self.wall_list):
                placed = True

        # Colocar las llaves (gemas)
        for _ in range(self.keys_remaining):
            placed = False
            while not placed:
                col = random.randrange(GRID_WIDTH)
                row = random.randrange(GRID_HEIGHT)
                if self.grid[row][col] == 0 and (row, col) not in self.key_positions:
                    key = arcade.Sprite(":resources:images/items/gemYellow.png", scale=SPRITE_SCALING)
                    key.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                    key.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.key_list.append(key)
                    self.key_positions.append((row, col))
                    placed = True
        
        # Calcular la primera ruta hacia una llave
        self.calculate_new_path()
        self.scroll_to_player(1.0) # Centrar cámara inmediatamente

    def calculate_new_path(self):
        """Calcula la ruta a la llave más cercana."""
        if not self.key_positions:
            print("¡Has recogido todos los diamantes!")
            self.victory = True
            return

        start_row = int(self.player_sprite.center_y // SPRITE_SIZE)
        start_col = int(self.player_sprite.center_x // SPRITE_SIZE)
        
        path = find_item(self.grid, (start_row, start_col), self.key_positions)
        
        if path:
            self.path = path[1:]  # Quitar la posición inicial del camino
        else:
            print("No se encontró camino a ninguna llave.")
            self.victory = True
            self.no_path = True

    def on_draw(self):
        draw_start_time = timeit.default_timer()
        self.clear()
        
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.key_list.draw()
        self.player_list.draw()

        self.camera_gui.use()
        arcade.draw_text(f"Sprites: {len(self.wall_list):,}", 10, self.window.height - 20, arcade.color.WHITE, 12)
        arcade.draw_text(f"Tiempo Dibujo: {self.draw_time:.4f}", 10, self.window.height - 40, arcade.color.WHITE, 12)
        arcade.draw_text(f"Tiempo Lógica: {self.processing_time:.4f}", 10, self.window.height - 60, arcade.color.WHITE, 12)
        arcade.draw_text(f"Diamantes restantes: {self.keys_remaining}", 10, self.window.height - 80, arcade.color.YELLOW, 16)

        if self.victory:
            if self.no_path:
                msg = "NO SE ENCONTRÓ CAMINO"
                color = arcade.color.RED
            else:
                msg = "¡HAS RECOGIDO TODOS LOS DIAMANTES!"
                color = arcade.color.GREEN
                arcade.draw_texture_rectangle(
                    self.window.width / 2, self.window.height / 2, 400, 300, self.victory_texture
                )
            arcade.draw_text(msg, self.window.width / 2, self.window.height / 2 + 200, color, font_size=30, anchor_x="center")

        self.draw_time = timeit.default_timer() - draw_start_time

    def on_update(self, delta_time):
        if self.victory:
            return

        proc_start_time = timeit.default_timer()

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
                angle = arcade.math.atan2(dy, dx)
                self.player_sprite.center_x += MOVEMENT_SPEED * arcade.math.cos(angle)
                self.player_sprite.center_y += MOVEMENT_SPEED * arcade.math.sin(angle)

        hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.key_list)
        if hit_list:
            for key in hit_list:
                key_pos = (int(key.center_y // SPRITE_SIZE), int(key.center_x // SPRITE_SIZE))
                if key_pos in self.key_positions:
                    self.key_positions.remove(key_pos)
                
                key.remove_from_sprite_lists()
                self.keys_remaining -= 1
                
                self.calculate_new_path()

        self.scroll_to_player(CAMERA_SPEED)
        self.processing_time = timeit.default_timer() - proc_start_time

    def scroll_to_player(self, speed):
        """Mueve la cámara suavemente hacia el jugador."""
        target_position = (
            self.player_sprite.center_x - self.window.width / 2,
            self.player_sprite.center_y - self.window.height / 2,
        )
        self.camera_sprites.move_to(target_position, speed)

# --- Función Principal ---

def main():
    """Función principal que inicia el juego."""
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    start_view = InstructionView()
    window.show_view(start_view)
    arcade.run()

if __name__ == "__main__":
    main()
# filepath: c:\Users\gabos\OneDrive\Documentos\Python Scripts\Examen P1\procendural.py
import random
import arcade
import timeit
from collections import deque

# --- Constantes ---
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING
GRID_WIDTH = 450
GRID_HEIGHT = 400
MOVEMENT_SPEED = 5
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves with Keys"
CAMERA_SPEED = 0.1

# --- Parámetros del Autómata Celular ---
CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

# --- Lógica del Laberinto ---

def create_grid(width, height):
    """Crea una grilla vacía."""
    return [[0 for _x in range(width)] for _y in range(height)]

def initialize_grid(grid):
    """Inicializa la grilla con celdas vivas aleatoriamente."""
    height = len(grid)
    width = len(grid[0])
    for row in range(height):
        for column in range(width):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[row][column] = 1

def count_alive_neighbors(grid, x, y):
    """Cuenta los vecinos vivos de una celda."""
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
                alive_count += 1  # Los bordes cuentan como vivos
            elif grid[neighbor_y][neighbor_x] == 1:
                alive_count += 1
    return alive_count

def do_simulation_step(old_grid):
    """Ejecuta un paso de la simulación del autómata celular."""
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
    """Encuentra la ruta más corta a cualquiera de los items usando BFS."""
    start_time = timeit.default_timer()
    rows, cols = len(grid), len(grid[0])
    queue = deque([(start, [start])])
    visited = {start}

    while queue:
        (r, c), path = queue.popleft()

        if (r, c) in item_positions:
            elapsed = timeit.default_timer() - start_time
            print(f"Ruta encontrada: {path}")
            print(f"Pasos: {len(path) - 1}")
            print(f"Tiempo BFS: {elapsed:.4f} s")
            return path

        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0 and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append(((nr, nc), path + [(nr, nc)]))
    return None

# --- Vistas del Juego ---

class InstructionView(arcade.View):
    """Vista inicial que muestra 'Loading...' y luego cambia a la vista del juego."""
    def on_show_view(self):
        self.window.background_color = arcade.csscolor.DARK_SLATE_BLUE

    def on_draw(self):
        self.clear()
        arcade.draw_text(
            "Loading...",
            self.window.width / 2,
            self.window.height / 2,
            arcade.color.WHITE,
            font_size=50,
            anchor_x="center",
        )

    def on_update(self, dt):
        """Una vez que se muestra, crea la vista del juego y cambia a ella."""
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    """Vista principal del juego."""
    def __init__(self):
        super().__init__()
        self.grid = None
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.key_list = arcade.SpriteList()
        
        self.player_sprite = None
        self.camera_sprites = arcade.Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.camera_gui = arcade.Camera(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        self.path = []
        self.keys_remaining = 3
        self.key_positions = []
        
        self.draw_time = 0
        self.processing_time = 0
        
        self.victory = False
        self.no_path = False
        
        # Textura para la pantalla de victoria
        self.victory_texture = None

    def setup(self):
        """Configura el nivel del juego."""
        # Cargar la textura para la pantalla de victoria
        # CAMBIA ESTA RUTA a la de tu imagen. Usa .png o .jpg
        try:
            # Intenta cargar tu imagen. Asegúrate de que la ruta sea correcta y el formato compatible.
            self.victory_texture = arcade.load_texture("C:/Users/gabos/OneDrive/Imágenes/Capturas de pantalla/burrito.png")
        except FileNotFoundError:
            print("Advertencia: No se encontró la imagen 'burrito.png'. Usando imagen de reemplazo.")
            # Si falla, usa una imagen de recursos de arcade para que el juego no se rompa.
            self.victory_texture = arcade.load_texture(":resources:images/items/gemYellow.png")

        # Crear mapa con autómata celular
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for _ in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        # Crear sprites de las paredes
        wall_texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.Sprite(texture=wall_texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # Colocar al jugador en una posición válida
        # CAMBIA ESTA RUTA a la de tu imagen de jugador
        player_texture_path = ":resources:images/animated_characters/robot/robot_idle.png"
        self.player_sprite = arcade.Sprite(player_texture_path, scale=SPRITE_SCALING)
        self.player_list.append(self.player_sprite)
        
        placed = False
        while not placed:
            self.player_sprite.center_x = random.randrange(GRID_WIDTH * SPRITE_SIZE)
            self.player_sprite.center_y = random.randrange(GRID_HEIGHT * SPRITE_SIZE)
            if not arcade.check_for_collision_with_list(self.player_sprite, self.wall_list):
                placed = True

        # Colocar las llaves (gemas)
        for _ in range(self.keys_remaining):
            placed = False
            while not placed:
                col = random.randrange(GRID_WIDTH)
                row = random.randrange(GRID_HEIGHT)
                if self.grid[row][col] == 0 and (row, col) not in self.key_positions:
                    key = arcade.Sprite(":resources:images/items/gemYellow.png", scale=SPRITE_SCALING)
                    key.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                    key.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.key_list.append(key)
                    self.key_positions.append((row, col))
                    placed = True
        
        # Calcular la primera ruta hacia una llave
        self.calculate_new_path()
        self.scroll_to_player(1.0) # Centrar cámara inmediatamente

    def calculate_new_path(self):
        """Calcula la ruta a la llave más cercana."""
        if not self.key_positions:
            print("¡Has recogido todos los diamantes!")
            self.victory = True
            return

        start_row = int(self.player_sprite.center_y // SPRITE_SIZE)
        start_col = int(self.player_sprite.center_x // SPRITE_SIZE)
        
        path = find_item(self.grid, (start_row, start_col), self.key_positions)
        
        if path:
            self.path = path[1:]  # Quitar la posición inicial del camino
        else:
            print("No se encontró camino a ninguna llave.")
            self.victory = True
            self.no_path = True

    def on_draw(self):
        draw_start_time = timeit.default_timer()
        self.clear()
        
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.key_list.draw()
        self.player_list.draw()

        self.camera_gui.use()
        arcade.draw_text(f"Sprites: {len(self.wall_list):,}", 10, self.window.height - 20, arcade.color.WHITE, 12)
        arcade.draw_text(f"Tiempo Dibujo: {self.draw_time:.4f}", 10, self.window.height - 40, arcade.color.WHITE, 12)
        arcade.draw_text(f"Tiempo Lógica: {self.processing_time:.4f}", 10, self.window.height - 60, arcade.color.WHITE, 12)
        arcade.draw_text(f"Diamantes restantes: {self.keys_remaining}", 10, self.window.height - 80, arcade.color.YELLOW, 16)

        if self.victory:
            if self.no_path:
                msg = "NO SE ENCONTRÓ CAMINO"
                color = arcade.color.RED
            else:
                msg = "¡HAS RECOGIDO TODOS LOS DIAMANTES!"
                color = arcade.color.GREEN
                arcade.draw_texture_rectangle(
                    self.window.width / 2, self.window.height / 2, 400, 300, self.victory_texture
                )
            arcade.draw_text(msg, self.window.width / 2, self.window.height / 2 + 200, color, font_size=30, anchor_x="center")

        self.draw_time = timeit.default_timer() - draw_start_time

    def on_update(self, delta_time):
        if self.victory:
            return

        proc_start_time = timeit.default_timer()

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
                angle = arcade.math.atan2(dy, dx)
                self.player_sprite.center_x += MOVEMENT_SPEED * arcade.math.cos(angle)
                self.player_sprite.center_y += MOVEMENT_SPEED * arcade.math.sin(angle)

        hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.key_list)
        if hit_list:
            for key in hit_list:
                key_pos = (int(key.center_y // SPRITE_SIZE), int(key.center_x // SPRITE_SIZE))
                if key_pos in self.key_positions:
                    self.key_positions.remove(key_pos)
                
                key.remove_from_sprite_lists()
                self.keys_remaining -= 1
                
                self.calculate_new_path()

        self.scroll_to_player(CAMERA_SPEED)
        self.processing_time = timeit.default_timer() - proc_start_time

    def scroll_to_player(self, speed):
        """Mueve la cámara suavemente hacia el jugador."""
        target_position = (
            self.player_sprite.center_x - self.window.width / 2,
            self.player_sprite.center_y - self.window.height / 2,
        )
        self.camera_sprites.move_to(target_position, speed)

# --- Función Principal ---

def main():
    """Función principal que inicia el juego."""
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    start_view = InstructionView()
    window.show_view(start_view)
    arcade.run()
if __name__ == "__main__":
    main()