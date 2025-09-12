"""
Procedural Caves with Pathfinding — Interfaz del módulo
=======================================================

Resumen
-------
Este módulo genera cuevas de forma procedural, coloca ítems coleccionables y
ofrece una función de pathfinding (BFS) para encontrar la ruta más corta hacia
un ítem dado.

Formato del mapa (input)
------------------------
Se aceptan dos formas principales para la función `find_item(maze, start, item_type)`:

1) **Diccionario "maze" (recomendado)**:
   {
     'grid': list[list[int]],          # Matriz donde 0 = libre, 1 = pared
     'items': dict[(int,int) -> str]   # Mapa de posiciones a tipo de ítem
   }

   - Coordenadas y convención de índices:
     * `grid[y][x]` con (0,0) en la esquina superior-izquierda.
     * Vecindad 4 (arriba/abajo/izquierda/derecha), sin diagonales.

2) **Solo matriz (list[list[int]])**:
   - `maze` puede ser simplemente `grid` (0 = libre, 1 = pared).
   - En este caso no hay ítems asociados; `find_item` no encontrará objetivos.

Opción adicional: mapa como **lista de strings**
------------------------------------------------
Si se quiere describir mapas como texto (no procesados directamente por el módulo),
se sugiere esta convención para **convertirlos** previamente a `{'grid', 'items'}`:

- Símbolos:
  * `#` o `'1'` → pared        → grid[y][x] = 1
  * `.` o `'0'` → espacio libre → grid[y][x] = 0
  * `G` → 'gem'       (gema)
  * `K` → 'key'       (llave)
  * `P` → 'powerup'   (nuevo elemento)

- Conversión sugerida (pseudocódigo):
  * grid[y][x] = 1 si char in {'#','1'}; de lo contrario 0
  * si char in {'G','K','P'} → items[(x,y)] = {'G':'gem','K':'key','P':'powerup'}[char]

Representación del nuevo elemento
---------------------------------
- **'powerup'**: coleccionable temporal.
- En este módulo:
  * Se almacena como string `'powerup'` en `items[(x,y)]`.
  * Se renderiza como un sprite sólido **verde** (ver `GameView.setup`).
  * Probabilidad de aparición controlada por `ITEM_SPAWN_CHANCE['powerup']`.

Parámetros de entrada (función `find_item`)
-------------------------------------------
- `maze`: dict con `{'grid', 'items'}` o bien `list[list[int]]` (solo grid).
- `start`: tuple[int, int] → posición inicial `(x, y)` en coordenadas de celda.
- `item_type`: str en `{'gem', 'key', 'powerup'}` → tipo de objetivo a buscar.

Formato de salida (función `find_item`)
---------------------------------------
`dict` con las siguientes claves:

- `'path'`: list[tuple[int,int]]
    Secuencia de celdas `(x,y)` desde el inicio hasta el objetivo (incluye ambos extremos).
- `'moves'`: list[str]
    Movimientos elementales correspondientes a `path`: `'up'|'down'|'left'|'right'`.
- `'found'`: bool
    `True` si se encontró algún ítem del tipo solicitado y se construyó la ruta más corta.
- `'distance'`: int
    Número de pasos (len(path) - 1) en vecindad 4 y costo uniforme.
- `'execution_time'`: float
    Tiempo de ejecución en segundos.

Notas y supuestos
-----------------
- BFS garantiza la ruta más corta en número de pasos (costes uniformes y vecindad 4).
- Las paredes (`1` en `grid`) son impasables.
- Si `maze` es solo `grid` o no hay ítems del tipo solicitado, `'found'` será `False`.
- El sistema de generación de ítems (`place_items_in_grid`) coloca `'gem'`, `'key'` y `'powerup'`
  únicamente en celdas libres (`0`).

Controles en la demo (GameView)
-------------------------------
- Flechas: mover jugador.
- Teclas `1`/`2`/`3`: trazar ruta al `'gem'`/`'key'`/`'powerup'` más cercano y visualizarla.
--------------------------------
Ejemplo de Salida:

left', 'left', 'down', 'left']...
Distancia: 15 pasos
Tiempo ejecución: 0.0004s
Collected key! Total: 1
Collected gem! Total: 1
Collected gem! Total: 2
Collected powerup! Total: 1
Collected key! Total: 2
Collected powerup! Total: 2
Collected gem! Total: 3
Collected gem! Total: 4
Collected powerup! Total: 3
Collected gem! Total: 5

"""

import random
import arcade
import timeit
from collections import deque
import time

# Sprite scaling. Make this larger, like 0.5 to zoom in and add
# 'mystery' to what you can see. Make it smaller, like 0.1 to see
# more of the map.
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

# How big the grid is
GRID_WIDTH = 450
GRID_HEIGHT = 400

# Parameters for cellular automata
CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

# How fast the player moves
MOVEMENT_SPEED = 5

# How close the player can get to the edge before we scroll.
VIEWPORT_MARGIN = 300

# How big the window is
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves with Pathfinding"

# How fast the camera pans to the player. 1.0 is instant.
CAMERA_SPEED = 0.1

# Item generation parameters
ITEM_SPAWN_CHANCE = {
    'gem': 0.002,      # Gemas (más comunes)
    'key': 0.0005,     # Llaves (raras)
    'powerup': 0.001   # Power-ups (medianos)
}

# Item types mapping
ITEM_TYPES = {
    0: 'empty',
    1: 'wall',
    2: 'gem',
    3: 'key', 
    4: 'powerup'
}


def create_grid(width, height):
    """Create a two-dimensional grid of specified size."""
    return [[0 for _x in range(width)] for _y in range(height)]


def initialize_grid(grid):
    """Randomly set grid locations to on/off based on chance."""
    height = len(grid)
    width = len(grid[0])
    for row in range(height):
        for column in range(width):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[row][column] = 1


def count_alive_neighbors(grid, x, y):
    """Count neighbors that are alive."""
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
                # Edges are considered alive. Makes map more likely to appear naturally closed.
                alive_count += 1
            elif grid[neighbor_y][neighbor_x] == 1:
                alive_count += 1
    return alive_count


def do_simulation_step(old_grid):
    """Run a step of the cellular automaton."""
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


def place_items_in_grid(grid):
    """
    Place collectible items (gems, keys, power-ups) in empty spaces of the grid.
    
    Args:
        grid: 2D list representing the cave system (0=empty, 1=wall)
        
    Returns:
        dict: Dictionary with item positions as keys and item types as values
    """
    height = len(grid)
    width = len(grid[0])
    items = {}
    
    for y in range(height):
        for x in range(width):
            if grid[y][x] == 0:  # Only place items in empty spaces
                for item_type, chance in ITEM_SPAWN_CHANCE.items():
                    if random.random() <= chance:
                        items[(x, y)] = item_type
                        break  # Only one item per position
    
    return items


def find_item(maze, start, item_type):
    """
    Encuentra la ruta más corta hasta el elemento especificado usando BFS.
    
    Formato del mapa:
        - maze: Lista 2D donde 0=espacio libre, 1=pared, o diccionario con posiciones de items
        - start: Tupla (x, y) con posición inicial
        - item_type: String con tipo de elemento ('gem', 'key', 'powerup')
    
    Representación de elementos:
        - 'gem': Gemas coleccionables (círculos azules)
        - 'key': Llaves especiales (rectángulos dorados)  
        - 'powerup': Power-ups temporales (triángulos verdes)
    
    Parámetros:
        maze: 2D list o dict - Representación del laberinto/cueva
        start: tuple(int, int) - Posición inicial (x, y)
        item_type: str - Tipo de elemento a buscar
        
    Retorna:
        dict: {
            'path': list[tuple] - Lista de posiciones (x,y) hasta el objetivo,
            'moves': list[str] - Secuencia de movimientos ('up','down','left','right'),
            'found': bool - True si se encontró el elemento,
            'distance': int - Número de pasos hasta el objetivo,
            'execution_time': float - Tiempo de ejecución en segundos
        }
    
    Algoritmo: BFS (Breadth-First Search)
    Justificación: BFS garantiza encontrar la ruta más corta en términos de número
    de pasos, ideal para movimiento en grilla donde cada paso tiene costo uniforme.
    """
    start_time = time.time()
    
    # Si maze es una lista 2D, convertir a formato compatible
    if isinstance(maze, list):
        grid = maze
        items = {}
    else:
        # Asumir que maze contiene grid e items
        grid = maze.get('grid', [])
        items = maze.get('items', {})
    
    height = len(grid)
    width = len(grid[0]) if grid else 0
    
    if not (0 <= start[0] < width and 0 <= start[1] < height):
        return {
            'path': [],
            'moves': [],
            'found': False,
            'distance': 0,
            'execution_time': time.time() - start_time
        }
    
    # Buscar todas las posiciones del tipo de elemento solicitado
    targets = [pos for pos, item in items.items() if item == item_type]
    
    if not targets:
        return {
            'path': [],
            'moves': [],
            'found': False,
            'distance': 0,
            'execution_time': time.time() - start_time
        }
    
    # BFS para encontrar la ruta más corta a cualquier target
    queue = deque([(start, [])])
    visited = {start}
    
    directions = [
        (0, -1, 'up'),
        (0, 1, 'down'), 
        (-1, 0, 'left'),
        (1, 0, 'right')
    ]
    
    while queue:
        (x, y), path = queue.popleft()
        
        # Verificar si llegamos a un objetivo
        if (x, y) in targets:
            moves = []
            for i in range(1, len(path)):
                prev_x, prev_y = path[i-1]
                curr_x, curr_y = path[i]
                dx, dy = curr_x - prev_x, curr_y - prev_y
                
                for dir_x, dir_y, move in directions:
                    if dx == dir_x and dy == dir_y:
                        moves.append(move)
                        break
            
            execution_time = time.time() - start_time
            return {
                'path': path,
                'moves': moves,
                'found': True,
                'distance': len(path) - 1,
                'execution_time': execution_time
            }
        
        # Explorar vecinos
        for dx, dy, move in directions:
            nx, ny = x + dx, y + dy
            
            if (0 <= nx < width and 0 <= ny < height and 
                (nx, ny) not in visited and grid[ny][nx] == 0):
                visited.add((nx, ny))
                new_path = path + [(x, y)]
                queue.append(((nx, ny), new_path))
    
    # No se encontró ruta
    execution_time = time.time() - start_time
    return {
        'path': [],
        'moves': [],
        'found': False,
        'distance': 0,
        'execution_time': execution_time
    }


def test_pathfinding():
    """
    Caso de prueba sencillo para la función find_item.
    
    Entrada:
        - Laberinto 5x5 con paredes y espacios libres
        - Items: gem en (3,1), key en (1,3)
        - Start: (0,0)
    
    Salida esperada:
        - Ruta hasta gem más cercana
        - Lista de movimientos válidos
        - Información de ejecución
    """
    print("=== CASO DE PRUEBA: find_item ===")
    
    # Crear laberinto de prueba 5x5
    test_grid = [
        [0, 1, 0, 0, 0],  # y=0
        [0, 1, 0, 0, 0],  # y=1  
        [0, 0, 0, 1, 0],  # y=2
        [1, 0, 0, 1, 0],  # y=3
        [0, 0, 0, 0, 0]   # y=4
    ]
    
    # Colocar items
    test_items = {
        (3, 1): 'gem',      # Gema en posición (3,1)
        (1, 3): 'key',      # Llave en posición (1,3) 
        (4, 4): 'powerup'   # Power-up en posición (4,4)
    }
    
    test_maze = {
        'grid': test_grid,
        'items': test_items
    }
    
    start_pos = (0, 0)
    
    # Prueba 1: Buscar gema
    print("\n--- Buscando GEM desde (0,0) ---")
    result = find_item(test_maze, start_pos, 'gem')
    print(f"Encontrado: {result['found']}")
    print(f"Ruta: {result['path']}")
    print(f"Movimientos: {result['moves']}")
    print(f"Distancia: {result['distance']} pasos")
    print(f"Tiempo ejecución: {result['execution_time']:.4f}s")
    
    # Prueba 2: Buscar llave
    print("\n--- Buscando KEY desde (0,0) ---")
    result = find_item(test_maze, start_pos, 'key')
    print(f"Encontrado: {result['found']}")
    print(f"Ruta: {result['path']}")
    print(f"Movimientos: {result['moves']}")
    print(f"Distancia: {result['distance']} pasos")
    print(f"Tiempo ejecución: {result['execution_time']:.4f}s")
    
    # Prueba 3: Elemento inexistente
    print("\n--- Buscando TREASURE (inexistente) ---")
    result = find_item(test_maze, start_pos, 'treasure')
    print(f"Encontrado: {result['found']}")
    print(f"Distancia: {result['distance']} pasos")


class InstructionView(arcade.View):
    """View to show instructions"""

    def __init__(self):
        super().__init__()
        self.frame_count = 0

    def on_show_view(self):
        """This is run once when we switch to this view"""
        self.window.background_color = arcade.csscolor.DARK_SLATE_BLUE
        self.window.default_camera.use()

    def on_draw(self):
        """Draw this view"""
        self.clear()
        arcade.draw_text(
            "Loading Cave System...",
            self.window.width // 2,
            self.window.height // 2,
            arcade.color.WHITE,
            font_size=40,
            anchor_x="center",
        )
        arcade.draw_text(
            "Generating items and pathfinding system",
            self.window.width // 2,
            self.window.height // 2 - 50,
            arcade.color.LIGHT_GRAY,
            font_size=16,
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
    """Main application class with enhanced item system."""

    def __init__(self):
        super().__init__()

        self.grid = None
        self.items = {}
        self.wall_list = None
        self.player_list = None
        self.item_list = None
        self.player_sprite = None
        self.draw_time = 0
        self.processing_time = 0
        self.physics_engine = None
        
        # Inventory system
        self.inventory = {'gem': 0, 'key': 0, 'powerup': 0}
        self.collected_items = set()

        # Track the current state of what key is pressed
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        # UI text objects
        self.sprite_count_text = None
        self.draw_time_text = None
        self.processing_time_text = None
        self.inventory_text = None
        self.pathfinding_text = None

        # Create the cameras
        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()

        self.window.background_color = arcade.color.BLACK
        
        # Pathfinding demo
        self.demo_target = None
        self.demo_path = []

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.item_list = arcade.SpriteList()

        # Create cave system using a 2D grid
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for step in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)
        
        # Place items in the generated cave
        self.items = place_items_in_grid(self.grid)

        # Create wall sprites
        texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.BasicSprite(texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # Create item sprites
        for (x, y), item_type in self.items.items():
            if item_type == 'gem':
                color = arcade.color.BLUE
                item_sprite = arcade.SpriteSolidColor(16, 16, color)
            elif item_type == 'key':
                color = arcade.color.GOLD
                item_sprite = arcade.SpriteSolidColor(12, 8, color)
            elif item_type == 'powerup':
                color = arcade.color.GREEN
                item_sprite = arcade.SpriteSolidColor(14, 14, color)
            
            item_sprite.center_x = x * SPRITE_SIZE + SPRITE_SIZE / 2
            item_sprite.center_y = y * SPRITE_SIZE + SPRITE_SIZE / 2
            item_sprite.item_type = item_type
            item_sprite.grid_pos = (x, y)
            self.item_list.append(item_sprite)

        # Set up the player
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING,
        )
        self.player_list.append(self.player_sprite)

        # Randomly place the player in an empty space
        placed = False
        attempts = 0
        while not placed and attempts < 1000:
            max_x = int(GRID_WIDTH * SPRITE_SIZE)
            max_y = int(GRID_HEIGHT * SPRITE_SIZE)
            self.player_sprite.center_x = random.randrange(max_x)
            self.player_sprite.center_y = random.randrange(max_y)

            walls_hit = arcade.check_for_collision_with_list(
                self.player_sprite, self.wall_list
            )
            if len(walls_hit) == 0:
                placed = True
            attempts += 1

        # UI Setup
        sprite_count = len(self.wall_list)
        item_count = len(self.item_list)
        
        self.sprite_count_text = arcade.Text(
            f"Walls: {sprite_count:,} | Items: {item_count}",
            20, self.window.height - 20, arcade.color.WHITE, 16
        )

        self.draw_time_text = arcade.Text(
            "Drawing time:", 20, self.window.height - 40, arcade.color.WHITE, 16
        )

        self.processing_time_text = arcade.Text(
            "Processing time:", 20, self.window.height - 60, arcade.color.WHITE, 16
        )
        
        self.inventory_text = arcade.Text(
            "Inventory:", 20, self.window.height - 80, arcade.color.YELLOW, 16
        )
        
        self.pathfinding_text = arcade.Text(
            "Press 1,2,3 to find nearest Gem/Key/PowerUp", 
            20, self.window.height - 100, arcade.color.CYAN, 14
        )

        self.physics_engine = arcade.PhysicsEngineSimple(
            self.player_sprite, self.wall_list
        )

        self.scroll_to_player(1.0)
        
        # Run pathfinding test
        print("\n" + "="*50)
        test_pathfinding()
        print("="*50)

    def get_player_grid_pos(self):
        """Get player position in grid coordinates"""
        grid_x = int(self.player_sprite.center_x // SPRITE_SIZE)
        grid_y = int(self.player_sprite.center_y // SPRITE_SIZE)
        return (grid_x, grid_y)

    def on_draw(self):
        """Render the screen."""
        draw_start_time = timeit.default_timer()
        self.clear()

        # Draw sprites
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.item_list.draw()
        self.player_list.draw()
        
        # Draw pathfinding visualization
        if self.demo_path:
            for i, (x, y) in enumerate(self.demo_path):
                pixel_x = x * SPRITE_SIZE + SPRITE_SIZE / 2
                pixel_y = y * SPRITE_SIZE + SPRITE_SIZE / 2
                color = arcade.color.RED if i == 0 else arcade.color.YELLOW
                arcade.draw_circle_outline(pixel_x, pixel_y, 8, color, 3)

        # Draw GUI
        self.camera_gui.use()
        self.sprite_count_text.draw()
        
        self.draw_time_text.text = f"Drawing time: {self.draw_time:.3f}"
        self.draw_time_text.draw()

        self.processing_time_text.text = f"Processing time: {self.processing_time:.3f}"
        self.processing_time_text.draw()
        
        inventory_str = f"Inventory: Gems:{self.inventory['gem']} Keys:{self.inventory['key']} PowerUps:{self.inventory['powerup']}"
        self.inventory_text.text = inventory_str
        self.inventory_text.draw()
        
        self.pathfinding_text.draw()

        self.draw_time = timeit.default_timer() - draw_start_time

    def update_player_speed(self):
        self.player_sprite.change_x = 0
        self.player_sprite.change_y = 0

        if self.up_pressed and not self.down_pressed:
            self.player_sprite.change_y = MOVEMENT_SPEED
        elif self.down_pressed and not self.up_pressed:
            self.player_sprite.change_y = -MOVEMENT_SPEED
        if self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = -MOVEMENT_SPEED
        elif self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = MOVEMENT_SPEED

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""
        if key == arcade.key.UP:
            self.up_pressed = True
        elif key == arcade.key.DOWN:
            self.down_pressed = True
        elif key == arcade.key.LEFT:
            self.left_pressed = True
        elif key == arcade.key.RIGHT:
            self.right_pressed = True
        elif key == arcade.key.KEY_1:
            self.find_nearest_item('gem')
        elif key == arcade.key.KEY_2:
            self.find_nearest_item('key')
        elif key == arcade.key.KEY_3:
            self.find_nearest_item('powerup')

    def find_nearest_item(self, item_type):
        """Demonstrate pathfinding to nearest item"""
        start_pos = self.get_player_grid_pos()
        
        maze_data = {
            'grid': self.grid,
            'items': self.items
        }
        
        result = find_item(maze_data, start_pos, item_type)
        
        print(f"\n=== BÚSQUEDA DE {item_type.upper()} ===")
        print(f"Posición inicial: {start_pos}")
        print(f"Encontrado: {result['found']}")
        if result['found']:
            print(f"Ruta: {result['path'][:5]}..." if len(result['path']) > 5 else f"Ruta: {result['path']}")
            print(f"Movimientos: {result['moves'][:10]}..." if len(result['moves']) > 10 else f"Movimientos: {result['moves']}")
            print(f"Distancia: {result['distance']} pasos")
            print(f"Tiempo ejecución: {result['execution_time']:.4f}s")
            self.demo_path = result['path']
        else:
            print(f"No se encontró {item_type} accesible")
            self.demo_path = []

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key."""
        if key == arcade.key.UP:
            self.up_pressed = False
        elif key == arcade.key.DOWN:
            self.down_pressed = False
        elif key == arcade.key.LEFT:
            self.left_pressed = False
        elif key == arcade.key.RIGHT:
            self.right_pressed = False

    def scroll_to_player(self, camera_speed):
        """Scroll the window to the player."""
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(
            self.camera_sprites.position, position, camera_speed,
        )

    def on_resize(self, width: int, height: int):
        """Resize window"""
        super().on_resize(width, height)
        self.camera_sprites.match_window()
        self.camera_gui.match_window()

    def on_update(self, delta_time):
        """Movement and game logic"""
        start_time = timeit.default_timer()

        self.update_player_speed()
        self.physics_engine.update()
        
        # Check for item collection
        items_collected = arcade.check_for_collision_with_list(
            self.player_sprite, self.item_list
        )
        
        for item in items_collected:
            if item.grid_pos not in self.collected_items:
                self.inventory[item.item_type] += 1
                self.collected_items.add(item.grid_pos)
                item.remove_from_sprite_lists()
                print(f"Collected {item.item_type}! Total: {self.inventory[item.item_type]}")

        self.scroll_to_player(camera_speed=CAMERA_SPEED)
        self.processing_time = timeit.default_timer() - start_time


def main():
    """
    Ejemplo de ejecución principal.
    
    El juego genera un sistema de cuevas procedural con elementos coleccionables:
    - Gemas (azules): Comunes, para puntuación
    - Llaves (doradas): Raras, para abrir áreas especiales  
    - Power-ups (verdes): Temporales, mejoran habilidades
    
    Controles:
    - Flechas: Mover jugador
    - 1/2/3: Encontrar ruta al Gem/Key/PowerUp más cercano
    
    El sistema de pathfinding usa BFS para garantizar la ruta más corta.
    """
    print("=== PROCEDURAL CAVES CON PATHFINDING ===")
    print("Controles:")
    print("- Flechas: Mover jugador")  
    print("- Teclas 1,2,3: Buscar Gem/Key/PowerUp más cercano")
    print("- Los elementos encontrados se muestran con círculos en el mapa")
    
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = InstructionView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()