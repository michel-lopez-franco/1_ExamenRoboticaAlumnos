"""
This example procedurally develops a random cave based on cellular automata.

For more information, see:
https://gamedevelopment.tutsplus.com/tutorials/generate-random-cave-levels-using-cellular-automata--gamedev-9664

If Python and Arcade are installed, this example can be run from the command line with:
python -m arcade.examples.procedural_caves_cellular
"""

import random
import arcade
import time
from collections import deque

# Sprite scaling
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

# Grid
GRID_WIDTH = 120
GRID_HEIGHT = 100

# Cellular automata params
CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

# Player
MOVEMENT_SPEED = 5
PLAYER_LIVES = 3
INVULNERABILITY_TIME = 3.0

# Enemy
ENEMY_SPEED = 2
SPAWN_INTERVAL = 5.0

# Window
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Escape de la Cueva"
CAMERA_SPEED = 0.1


# ---- GRID HELPERS ----
def create_grid(width, height):
    return [[0 for _x in range(width)] for _y in range(height)]


def initialize_grid(grid):
    for row in range(len(grid)):
        for column in range(len(grid[0])):
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
            neighbors = count_alive_neighbors(old_grid, x, y)
            if old_grid[y][x] == 1:
                new_grid[y][x] = 1 if neighbors >= DEATH_LIMIT else 0
            else:
                new_grid[y][x] = 1 if neighbors > BIRTH_LIMIT else 0
    return new_grid


# ---- GAME STATES ----
class VictoryView(arcade.View):
    def on_show_view(self):
        self.window.background_color = arcade.color.DARK_GREEN

    def on_draw(self):
        self.clear()
        arcade.draw_text("¡Victoria! Has escapado",
                         self.window.width//2, self.window.height//2,
                         arcade.color.WHITE, 30, anchor_x="center")
        arcade.draw_text("Presiona ENTER para reiniciar",
                         self.window.width//2, self.window.height//2 - 50,
                         arcade.color.YELLOW, 20, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game = GameView()
            game.setup()
            self.window.show_view(game)


class GameOverView(arcade.View):
    def on_show_view(self):
        self.window.background_color = arcade.color.DARK_RED

    def on_draw(self):
        self.clear()
        arcade.draw_text("Game Over",
                         self.window.width//2, self.window.height//2,
                         arcade.color.WHITE, 30, anchor_x="center")
        arcade.draw_text("Presiona ENTER para reiniciar",
                         self.window.width//2, self.window.height//2 - 50,
                         arcade.color.YELLOW, 20, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game = GameView()
            game.setup()
            self.window.show_view(game)


# ---- MAIN GAME ----
class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.grid = None
        self.wall_list = None
        self.player_list = None
        self.enemy_list = None
        self.items_list = None

        self.player_sprite = None
        self.player_lives = PLAYER_LIVES
        self.invulnerable = False
        self.invulnerable_timer = 0

        self.keys_needed = 5
        self.keys_collected = 0
        self.keys_sprites = []
        self.exit_sprite = None

        self.last_enemy_spawn = 0
        self.path = []  # BFS path persistente

        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()
        self.window.background_color = arcade.color.BLACK

    # ---- BFS ----
    def bfs(self, start, goal):
        queue = deque([start])
        came_from = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            x, y = current
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    if self.grid[ny][nx] == 0 and (nx, ny) not in came_from:
                        queue.append((nx, ny))
                        came_from[(nx, ny)] = current
        if goal not in came_from:
            return []
        path = []
        cur = goal
        while cur:
            path.append(cur)
            cur = came_from[cur]
        path.reverse()
        return path

    def place_item(self, texture):
        while True:
            col = random.randrange(GRID_WIDTH)
            row = random.randrange(GRID_HEIGHT)
            if self.grid[row][col] == 0:
                x = col * SPRITE_SIZE + SPRITE_SIZE/2
                y = row * SPRITE_SIZE + SPRITE_SIZE/2
                key = arcade.Sprite(texture, scale=SPRITE_SCALING)
                key.center_x, key.center_y = x, y
                self.items_list.append(key)
                return key

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.items_list = arcade.SpriteList()

        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for _ in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        texture = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.BasicSprite(texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE/2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE/2
                    self.wall_list.append(wall)

        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING,
        )
        self.player_list.append(self.player_sprite)

        placed = False
        while not placed:
            self.player_sprite.center_x = random.randrange(int(GRID_WIDTH * SPRITE_SIZE))
            self.player_sprite.center_y = random.randrange(int(GRID_HEIGHT * SPRITE_SIZE))
            if not arcade.check_for_collision_with_list(self.player_sprite, self.wall_list):
                placed = True

        # Colocar 5 llaves
        self.keys_collected = 0
        self.keys_sprites = []
        for _ in range(self.keys_needed):
            key = self.place_item(":resources:images/items/keyBlue.png")
            self.keys_sprites.append(key)

    # ---- LOGIC ----
    def auto_play(self):
        start_x = int(self.player_sprite.center_x // SPRITE_SIZE)
        start_y = int(self.player_sprite.center_y // SPRITE_SIZE)

        if self.keys_collected < self.keys_needed and self.keys_sprites:
            target = self.keys_sprites[0]
            target_x = int(target.center_x // SPRITE_SIZE)
            target_y = int(target.center_y // SPRITE_SIZE)
        elif self.exit_sprite:
            target_x = int(self.exit_sprite.center_x // SPRITE_SIZE)
            target_y = int(self.exit_sprite.center_y // SPRITE_SIZE)
        else:
            return

        if not self.path:
            self.path = self.bfs((start_x, start_y), (target_x, target_y))

        if len(self.path) > 1:
            next_cell = self.path[1]
            goal_x = next_cell[0]*SPRITE_SIZE + SPRITE_SIZE/2
            goal_y = next_cell[1]*SPRITE_SIZE + SPRITE_SIZE/2
            dx = goal_x - self.player_sprite.center_x
            dy = goal_y - self.player_sprite.center_y
            if abs(dx) > 5:
                self.player_sprite.change_x = MOVEMENT_SPEED if dx > 0 else -MOVEMENT_SPEED
            else:
                self.player_sprite.change_x = 0
            if abs(dy) > 5:
                self.player_sprite.change_y = MOVEMENT_SPEED if dy > 0 else -MOVEMENT_SPEED
            else:
                self.player_sprite.change_y = 0
            if abs(dx) <= 5 and abs(dy) <= 5:
                self.path.pop(0)
        else:
            self.path = []

    def spawn_enemy(self):
        while True:
            x = random.randrange(int(GRID_WIDTH * SPRITE_SIZE))
            y = random.randrange(int(GRID_HEIGHT * SPRITE_SIZE))
            enemy = arcade.Sprite(":resources:images/enemies/slimeBlock.png", scale=SPRITE_SCALING)
            enemy.center_x, enemy.center_y = x, y
            if not arcade.check_for_collision_with_list(enemy, self.wall_list):
                self.enemy_list.append(enemy)
                return

    def check_collisions(self):
        # Recoger llaves
        for key in self.keys_sprites:
            if arcade.check_for_collision(self.player_sprite, key):
                key.remove_from_sprite_lists()
                self.keys_collected += 1
                self.keys_sprites.remove(key)
                break

        # Aparecer salida si tiene todas las llaves
        if self.keys_collected >= self.keys_needed and not self.exit_sprite:
            col = random.randrange(GRID_WIDTH)
            row = random.randrange(GRID_HEIGHT)
            while self.grid[row][col] != 0:
                col = random.randrange(GRID_WIDTH)
                row = random.randrange(GRID_HEIGHT)
            x = col*SPRITE_SIZE + SPRITE_SIZE/2
            y = row*SPRITE_SIZE + SPRITE_SIZE/2
            self.exit_sprite = arcade.Sprite(":resources:images/tiles/doorClosed_mid.png", scale=SPRITE_SCALING)
            self.exit_sprite.center_x, self.exit_sprite.center_y = x, y
            self.items_list.append(self.exit_sprite)

        # Salida
        if self.exit_sprite and arcade.check_for_collision(self.player_sprite, self.exit_sprite):
            self.window.show_view(VictoryView())

        # Colisión con enemigos
        if not self.invulnerable:
            hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.enemy_list)
            if hit_list:
                self.player_lives -= 1
                self.invulnerable = True
                self.invulnerable_timer = time.time()
                if self.player_lives <= 0:
                    self.window.show_view(GameOverView())

    # ---- DRAW ----
    def on_draw(self):
        self.clear()
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.items_list.draw()
        self.player_list.draw()
        self.enemy_list.draw()
        self.camera_gui.use()
        arcade.draw_text(f"Vidas: {self.player_lives}", 20, self.window.height-40, arcade.color.RED, 16)
        arcade.draw_text(f"Llaves: {self.keys_collected}/{self.keys_needed}", 20, self.window.height-70, arcade.color.YELLOW, 16)

    # ---- UPDATE ----
    def on_update(self, delta_time):
        self.auto_play()
        self.player_sprite.center_x += self.player_sprite.change_x
        self.player_sprite.center_y += self.player_sprite.change_y

        for enemy in self.enemy_list:
            if random.random() < 0.02:
                enemy.change_x = random.choice([-ENEMY_SPEED, 0, ENEMY_SPEED])
                enemy.change_y = random.choice([-ENEMY_SPEED, 0, ENEMY_SPEED])
            enemy.center_x += enemy.change_x
            enemy.center_y += enemy.change_y

        if time.time() - self.last_enemy_spawn > SPAWN_INTERVAL:
            self.spawn_enemy()
            self.last_enemy_spawn = time.time()

        if self.invulnerable and (time.time() - self.invulnerable_timer > INVULNERABILITY_TIME):
            self.invulnerable = False

        self.scroll_to_player(camera_speed=CAMERA_SPEED)
        self.check_collisions()

    def scroll_to_player(self, camera_speed):
        pos = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(self.camera_sprites.position, pos, camera_speed)


# ---- MAIN ----
def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    game.setup()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
