import random
import arcade
import timeit
from collections import deque

# ===================== CONFIG =====================
SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING

GRID_WIDTH = 80
GRID_HEIGHT = 60

CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Caves with Enemies and Coins"

CAMERA_SPEED = 0.1

# Velocidades
PLAYER_SPEED = 3.5
ENEMY_SPEED = 3.0
FAST_ENEMY_SPEED = 5.0   # 👈 enemigo especial más rápido


# ===================== MAPA =====================
def create_grid(width, height):
    return [[0 for _ in range(width)] for _ in range(height)]


def initialize_grid(grid):
    for row in range(len(grid)):
        for col in range(len(grid[0])):
            if random.random() <= CHANCE_TO_START_ALIVE:
                grid[row][col] = 1


def count_alive_neighbors(grid, x, y):
    alive_count = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            nx, ny = x + i, y + j
            if i == 0 and j == 0:
                continue
            if nx < 0 or ny < 0 or ny >= len(grid) or nx >= len(grid[0]):
                alive_count += 1
            elif grid[ny][nx] == 1:
                alive_count += 1
    return alive_count


def do_simulation_step(old_grid):
    new_grid = create_grid(len(old_grid[0]), len(old_grid))
    for x in range(len(old_grid[0])):
        for y in range(len(old_grid)):
            alive_neighbors = count_alive_neighbors(old_grid, x, y)
            if old_grid[y][x] == 1:
                new_grid[y][x] = 1 if alive_neighbors >= DEATH_LIMIT else 0
            else:
                new_grid[y][x] = 1 if alive_neighbors > BIRTH_LIMIT else 0
    return new_grid


# ===================== GAME =====================
class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.grid = None
        self.wall_list = None
        self.player_list = None
        self.coin_list = None
        self.enemy_list = None
        self.fast_enemy_list = None  # 👈 lista separada para el enemigo especial
        self.player_sprite = None
        self.physics_engine = None

        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()

        self.window.background_color = arcade.color.BLACK

        # Control del movimiento automático
        self.path = []
        self.target_coin = None

        # Estado del juego
        self.state = "PLAY"  # PLAY | WIN | LOSE

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.fast_enemy_list = arcade.SpriteList()  # 👈 nueva lista

        self.state = "PLAY"

        # --- Generar cueva ---
        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for _ in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        wall_tex = arcade.load_texture(":resources:images/tiles/grassCenter.png")
        for row in range(GRID_HEIGHT):
            for col in range(GRID_WIDTH):
                if self.grid[row][col] == 1:
                    wall = arcade.BasicSprite(wall_tex, scale=SPRITE_SCALING)
                    wall.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        # --- Player ---
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING,
        )
        self.place_sprite_randomly(self.player_sprite)
        self.player_list.append(self.player_sprite)

        # --- Coins ---
        for _ in range(3):
            coin = arcade.Sprite(":resources:images/items/coinGold.png", scale=0.25)
            self.place_sprite_randomly(coin)
            self.coin_list.append(coin)

        # --- Enemigos normales ---
        for _ in range(5):
            enemy = arcade.Sprite(
                ":resources:images/animated_characters/zombie/zombie_idle.png",
                scale=SPRITE_SCALING,
            )
            self.place_sprite_randomly(enemy)
            enemy.change_x, enemy.change_y = random.choice(
                [(ENEMY_SPEED, 0), (-ENEMY_SPEED, 0), (0, ENEMY_SPEED), (0, -ENEMY_SPEED)]
            )
            self.enemy_list.append(enemy)

        # --- Enemigo especial rápido ---
        fast_enemy = arcade.Sprite(
            ":resources:images/animated_characters/robot/robot_idle.png",  # 👈 apariencia distinta
            scale=SPRITE_SCALING,
        )
        self.place_sprite_randomly(fast_enemy)
        fast_enemy.change_x, fast_enemy.change_y = random.choice(
            [(FAST_ENEMY_SPEED, 0), (-FAST_ENEMY_SPEED, 0), (0, FAST_ENEMY_SPEED), (0, -FAST_ENEMY_SPEED)]
        )
        self.fast_enemy_list.append(fast_enemy)

        self.physics_engine = arcade.PhysicsEngineSimple(
            self.player_sprite, self.wall_list
        )
        self.scroll_to_player(1.0)

    # ---------------- Pathfinding ----------------
    def find_path(self, start, goal):
        queue = deque([start])
        came_from = {start: None}

        while queue:
            cur = queue.popleft()
            if cur == goal:
                break
            x, y = cur
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < GRID_WIDTH
                    and 0 <= ny < GRID_HEIGHT
                    and self.grid[ny][nx] == 0
                    and (nx, ny) not in came_from
                ):
                    queue.append((nx, ny))
                    came_from[(nx, ny)] = cur

        if goal not in came_from:
            return []

        path = []
        cur = goal
        while cur != start:
            path.append(cur)
            cur = came_from[cur]
        path.reverse()
        return path

    def place_sprite_randomly(self, sprite):
        placed = False
        while not placed:
            col = random.randrange(GRID_WIDTH)
            row = random.randrange(GRID_HEIGHT)
            sprite.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
            sprite.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
            if self.grid[row][col] == 0:
                if not arcade.check_for_collision_with_list(sprite, self.wall_list):
                    placed = True

    # ---------------- Core ----------------
    def on_draw(self):
        self.clear()
        self.camera_sprites.use()
        self.wall_list.draw(pixelated=True)
        self.coin_list.draw()
        self.enemy_list.draw()
        self.fast_enemy_list.draw()  # 👈 dibujar enemigo rápido
        self.player_list.draw()

        self.camera_gui.use()
        arcade.draw_text(
            f"Coins left: {len(self.coin_list)}",
            20,
            self.window.height - 20,
            arcade.color.YELLOW,
            16,
        )

        if self.state == "WIN":
            arcade.draw_text(
                "🎉 FELICIDADES 🎉",
                self.window.width // 2,
                self.window.height // 2,
                arcade.color.GREEN,
                50,
                anchor_x="center",
            )
        elif self.state == "LOSE":
            arcade.draw_text(
                "💀 GAME OVER 💀",
                self.window.width // 2,
                self.window.height // 2,
                arcade.color.RED,
                50,
                anchor_x="center",
            )

    def on_update(self, delta_time):
        if self.state != "PLAY":
            return

        # --- Movimiento automático del jugador ---
        if not self.path and self.coin_list:
            col = int(self.player_sprite.center_x // SPRITE_SIZE)
            row = int(self.player_sprite.center_y // SPRITE_SIZE)

            self.target_coin = min(
                self.coin_list,
                key=lambda c: (c.center_x - self.player_sprite.center_x) ** 2
                + (c.center_y - self.player_sprite.center_y) ** 2,
            )
            target_col = int(self.target_coin.center_x // SPRITE_SIZE)
            target_row = int(self.target_coin.center_y // SPRITE_SIZE)

            self.path = self.find_path((col, row), (target_col, target_row))

        if self.path:
            next_col, next_row = self.path[0]
            target_x = next_col * SPRITE_SIZE + SPRITE_SIZE / 2
            target_y = next_row * SPRITE_SIZE + SPRITE_SIZE / 2

            dx = target_x - self.player_sprite.center_x
            dy = target_y - self.player_sprite.center_y
            dist = (dx**2 + dy**2) ** 0.5

            if dist < PLAYER_SPEED:
                self.player_sprite.center_x = target_x
                self.player_sprite.center_y = target_y
                self.path.pop(0)
            else:
                self.player_sprite.center_x += PLAYER_SPEED * dx / dist
                self.player_sprite.center_y += PLAYER_SPEED * dy / dist

        # --- Recoger monedas ---
        coins_hit = arcade.check_for_collision_with_list(
            self.player_sprite, self.coin_list
        )
        for coin in coins_hit:
            coin.remove_from_sprite_lists()
            self.path = []

        if len(self.coin_list) == 0:
            self.state = "WIN"

        # --- Enemigos normales ---
        for enemy in self.enemy_list:
            self.update_enemy(enemy, ENEMY_SPEED)

        # --- Enemigo especial ---
        for fast_enemy in self.fast_enemy_list:
            self.update_enemy(fast_enemy, FAST_ENEMY_SPEED)

        # --- Colisión con enemigos ---
        if arcade.check_for_collision_with_list(self.player_sprite, self.enemy_list) or \
           arcade.check_for_collision_with_list(self.player_sprite, self.fast_enemy_list):
            self.state = "LOSE"

        self.scroll_to_player(CAMERA_SPEED)

    def update_enemy(self, enemy, speed):
        next_x = enemy.center_x + enemy.change_x
        next_y = enemy.center_y + enemy.change_y
        col = int(next_x // SPRITE_SIZE)
        row = int(next_y // SPRITE_SIZE)

        if not (0 <= col < GRID_WIDTH and 0 <= row < GRID_HEIGHT) or self.grid[row][col] == 1:
            enemy.change_x, enemy.change_y = random.choice(
                [(speed, 0), (-speed, 0), (0, speed), (0, -speed)]
            )
        else:
            enemy.center_x = next_x
            enemy.center_y = next_y

    def scroll_to_player(self, camera_speed):
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(
            self.camera_sprites.position, position, camera_speed
        )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.N:  # Reinicio completo del juego
            new_game = GameView()
            new_game.setup()
            self.window.show_view(new_game)



# ===================== MAIN =====================
def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    game.setup()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
