import random
import arcade
import timeit
import heapq

SPRITE_SCALING = 0.25
SPRITE_SIZE = 128 * SPRITE_SCALING
GRID_WIDTH = 450
GRID_HEIGHT = 400
CHANCE_TO_START_ALIVE = 0.4
DEATH_LIMIT = 3
BIRTH_LIMIT = 4
NUMBER_OF_STEPS = 4
MOVEMENT_SPEED = 6
FAST_MOVEMENT_SPEED = 10
VIEWPORT_MARGIN = 300
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Procedural Caves Cellular Automata Example"
CAMERA_SPEED = 0.1
POWERUP_DURATION = 10.0

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

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(grid, start, goal):
    width, height = len(grid[0]), len(grid)
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        current = heapq.heappop(open_set)[1]
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        neighbors = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        for dx, dy in neighbors:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < width and 0 <= neighbor[1] < height:
                if grid[neighbor[1]][neighbor[0]] == 1:
                    continue
                tentative_g_score = g_score[current] + 1
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return []

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.grid = None
        self.wall_list = None
        self.player_list = None
        self.coin_list = None
        self.gem_list = None
        self.player_sprite = None
        self.camera_sprites = arcade.Camera2D()
        self.camera_gui = arcade.Camera2D()
        self.window.background_color = arcade.color.BLACK
        self.path = []
        self.powerup_timer = 0
        self.remaining_targets = 0

    def get_random_free_pos(self):
        while True:
            col = random.randrange(GRID_WIDTH)
            row = random.randrange(GRID_HEIGHT)
            if self.grid[row][col] == 0:
                x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                return x, y, col, row

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash=True)
        self.player_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()
        self.gem_list = arcade.SpriteList()

        self.grid = create_grid(GRID_WIDTH, GRID_HEIGHT)
        initialize_grid(self.grid)
        for step in range(NUMBER_OF_STEPS):
            self.grid = do_simulation_step(self.grid)

        texture = arcade.load_texture(":resources:images/tiles/lava.png")
        for row in range(GRID_HEIGHT):
            for column in range(GRID_WIDTH):
                if self.grid[row][column] == 1:
                    wall = arcade.BasicSprite(texture, scale=SPRITE_SCALING)
                    wall.center_x = column * SPRITE_SIZE + SPRITE_SIZE / 2
                    wall.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                    self.wall_list.append(wall)

        x, y, px, py = self.get_random_free_pos()
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING
        )
        self.player_sprite.center_x = x
        self.player_sprite.center_y = y
        self.player_list.append(self.player_sprite)

        placed_positions = [(px, py)]
        min_distance = 15
        for _ in range(3):
            while True:
                coin = arcade.Sprite(":resources:images/items/coinGold.png", scale=SPRITE_SCALING)
                col = random.randrange(GRID_WIDTH)
                row = random.randrange(GRID_HEIGHT)
                if self.grid[row][col] == 0:
                    too_close = any(abs(px2 - col) + abs(py2 - row) < min_distance for (px2, py2) in placed_positions)
                    if not too_close:
                        coin.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                        coin.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                        self.coin_list.append(coin)
                        placed_positions.append((col, row))
                        break

        for _ in range(2):
            while True:
                gem = arcade.Sprite(":resources:images/items/gemRed.png", scale=SPRITE_SCALING)
                col = random.randrange(GRID_WIDTH)
                row = random.randrange(GRID_HEIGHT)
                if self.grid[row][col] == 0:
                    too_close = any(abs(px3 - col) + abs(py3 - row) < min_distance for (px3, py3) in placed_positions)
                    if not too_close:
                        gem.center_x = col * SPRITE_SIZE + SPRITE_SIZE / 2
                        gem.center_y = row * SPRITE_SIZE + SPRITE_SIZE / 2
                        self.gem_list.append(gem)
                        placed_positions.append((col, row))
                        break

        self.remaining_targets = len(self.coin_list)
        self.find_next_target()

    def find_next_target(self):
        if len(self.coin_list) > 0:
            targets = self.coin_list
        elif len(self.gem_list) > 0:
            targets = self.gem_list
        else:
            self.path = []
            return

        player_col = int(self.player_sprite.center_x // SPRITE_SIZE)
        player_row = int(self.player_sprite.center_y // SPRITE_SIZE)
        closest = min(targets, key=lambda sprite: heuristic((player_col, player_row), (int(sprite.center_x // SPRITE_SIZE), int(sprite.center_y // SPRITE_SIZE))))
        target_col = int(closest.center_x // SPRITE_SIZE)
        target_row = int(closest.center_y // SPRITE_SIZE)
        self.path = astar(self.grid, (player_col, player_row), (target_col, target_row))

    def on_draw(self):
        self.clear()
        self.camera_sprites.use()
        self.wall_list.draw()
        self.player_list.draw()
        self.coin_list.draw()
        self.gem_list.draw()
        self.camera_gui.use()
        arcade.draw_text(f"Coins remaining: {self.remaining_targets}", 10, WINDOW_HEIGHT - 30, arcade.color.WHITE, 20)

    def scroll_to_player(self, camera_speed):
        position = (self.player_sprite.center_x, self.player_sprite.center_y)
        self.camera_sprites.position = arcade.math.lerp_2d(
            self.camera_sprites.position,
            position,
            camera_speed,
        )

    def on_update(self, delta_time):
        speed = FAST_MOVEMENT_SPEED if self.powerup_timer > 0 else MOVEMENT_SPEED
        self.powerup_timer = max(0, self.powerup_timer - delta_time)
        if self.path:
            next_pos = self.path[0]
            dest_x = next_pos[0] * SPRITE_SIZE + SPRITE_SIZE / 2
            dest_y = next_pos[1] * SPRITE_SIZE + SPRITE_SIZE / 2
            dx = dest_x - self.player_sprite.center_x
            dy = dest_y - self.player_sprite.center_y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist < speed:
                self.player_sprite.center_x = dest_x
                self.player_sprite.center_y = dest_y
                self.path.pop(0)
            else:
                self.player_sprite.center_x += speed * dx / dist
                self.player_sprite.center_y += speed * dy / dist

        hit_coins = arcade.check_for_collision_with_list(self.player_sprite, self.coin_list)
        for coin in hit_coins:
            coin.remove_from_sprite_lists()
            self.remaining_targets -= 1
            self.find_next_target()

        hit_gems = arcade.check_for_collision_with_list(self.player_sprite, self.gem_list)
        for gem in hit_gems:
            gem.remove_from_sprite_lists()
            self.powerup_timer = POWERUP_DURATION
            self.find_next_target()

        self.scroll_to_player(CAMERA_SPEED)

def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    window.show_view(game)
    game.setup()
    arcade.run()

if __name__ == "__main__":
    main()
