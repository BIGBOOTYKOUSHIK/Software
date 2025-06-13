"""Main game module for Memory Match.

This file contains all game logic, rendering code and data handling. The goal
is to keep the code readable for new developers, so the following sections are
annotated extensively with inline comments.
"""

import pygame  # graphics and input library
import json  # used for saving and loading progress
import os  # file path utilities
import random  # shuffling and random placement
from dataclasses import dataclass, field  # convenient data containers
from typing import Tuple, List, Optional  # type hints
import math  # math helper functions

# Name of the JSON file used for storing persistent data
SAVE_FILE = 'save.json'

# Number of scores to keep in each leaderboard table
MAX_RANKS = 10

# Configuration for each of the ten levels. The ``grid`` value defines the
# board size as ``(rows, columns)`` while ``time`` sets the starting timer in
# seconds.
LEVELS = [
    {'grid': (2, 2), 'time': 60},
    {'grid': (2, 4), 'time': 75},
    {'grid': (3, 4), 'time': 90},
    {'grid': (4, 4), 'time': 90},
    {'grid': (4, 5), 'time': 90},
    {'grid': (4, 6), 'time': 100},
    {'grid': (5, 6), 'time': 110},
    {'grid': (6, 6), 'time': 120},
    {'grid': (6, 7), 'time': 135},
    {'grid': (8, 8), 'time': 180},
]

# Starting leaderboard data so the tables are never empty on a new install
PLACEHOLDER_TIMES = [['AAA', 30], ['BBB', 35], ['CCC', 40]]
PLACEHOLDER_MOVES = [['AAA', 4], ['BBB', 5], ['CCC', 6]]

# Default structure for a brand new save file. It tracks which level is
# unlocked, the current level in progress and an empty leaderboard for each
# stage. The settings block stores all visual and sound preferences.
DEFAULT_DATA = {
    'unlocked_level': 1,
    'current_level': 1,
    'leaderboard': {
        str(i): {
            'best_time': PLACEHOLDER_TIMES.copy(),
            'least_moves': PLACEHOLDER_MOVES.copy(),
        } for i in range(1, 11)
    },
    'settings': {
        'music_volume': 0.5,
        'sfx_volume': 0.5,
        'theme': 'Numbers',
        'background': 'Blue',
        'word_color': 'White',
        'timer_enabled': True,
        'fullscreen': False,
        'bg_style': 'Stars',
    },
}

# Short congratulatory messages displayed when a pair is found
CELEBRATIONS = [
    'Great!', 'Nice!', 'Well done!', 'Awesome!', 'Good job!'
]

# configuration options
# Colors the player can choose from for the background tint
BACKGROUND_OPTIONS = {
    'Blue': (30, 30, 90),
    'Green': (0, 70, 0),
    'Purple': (60, 0, 60),
    'Black': (0, 0, 0),
    'Orange': (90, 40, 0),
}

# Available animated background patterns
BACKGROUND_STYLES = ['Stars', 'Grid', 'Dots', 'Stripes', 'Solid']

# Text colors used throughout the UI
WORD_OPTIONS = {
    'White': (255, 255, 255),
    'Yellow': (255, 255, 0),
    'Red': (255, 0, 0),
    'Black': (0, 0, 0),
    'Blue': (0, 0, 255),
}

# Different sets of card faces that players can choose between
CARD_THEMES = {
    'Numbers': [str(i) for i in range(1, 33)],
    'Letters': (
        list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + [f'{c}{c}' for c in 'ABCDEF']
    ),
    'Colors': [
        'Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Purple', 'HotPink',
        'Cyan', 'Magenta', 'Lime', 'Teal', 'Turquoise', 'Gold', 'Coral',
        'Crimson', 'Fuchsia', 'Violet', 'Indigo', 'Azure', 'Chartreuse',
        'Tomato', 'SpringGreen', 'DeepSkyBlue', 'MediumOrchid',
        'DodgerBlue', 'MediumVioletRed', 'OrangeRed', 'SkyBlue',
        'LawnGreen', 'MediumSeaGreen', 'FireBrick', 'DeepPink'
    ],
    'Animals': [
        'Cat', 'Dog', 'Cow', 'Pig', 'Fox', 'Bear', 'Lion', 'Tiger',
        'Wolf', 'Frog', 'Bird', 'Fish', 'Duck', 'Deer', 'Goat',
        'Horse', 'Zebra', 'Koala', 'Panda', 'Monkey', 'Mouse', 'Rabbit',
        'Sheep', 'Snake', 'Bee', 'Ant', 'Crab', 'Whale', 'Shark',
        'Dolphin', 'Llama', 'Camel'
    ],
    'Emojis': [
        '😀', '😁', '😂', '🤣', '😃', '😄', '😅', '😆',
        '😉', '😊', '😋', '😎', '😍', '😘', '😗', '😙',
        '😚', '🙂', '🤗', '🤔', '😐', '😑', '😶', '🙄',
        '😏', '😣', '😥', '😮', '🤐', '😯', '😪', '😫'
    ],
}

MENU_BG = (30, 30, 90)
LEVEL_BG = (30, 30, 80)
# Commonly used UI colors
GAME_BG = (0, 0, 0)          # plain black background for gameplay
COMPLETE_BG = (0, 100, 0)    # green backdrop on level completion
LEADER_BG = (40, 40, 60)     # darker background for leaderboards
KEYPAD_BG = (0, 0, 0)        # keypad overlay color
BUTTON_COLOR = (80, 80, 80)  # default button fill
CARD_BACK_COLOR = (200, 200, 200)  # color of hidden cards
CARD_FACE_COLOR = (50, 150, 50)    # default face color when not using 'Colors'
HOVER_COLOR = (100, 100, 100)      # button hover state
LOCKED_COLOR = (100, 100, 100)     # color for locked level tiles


def load_data() -> dict:
    """Load the persistent save file.

    If the file exists we try to parse JSON and validate the structure so the
    rest of the game code can assume sane values. When anything goes wrong we
    fall back to ``DEFAULT_DATA``.
    """
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                if 'leaderboard' not in data or not isinstance(
                        data['leaderboard'], dict):
                    data['leaderboard'] = {}
                for i in range(1, 11):
                    key = str(i)
                    lvl = data['leaderboard'].setdefault(key, {})
                    if not isinstance(lvl.get('best_time'), list):
                        lvl['best_time'] = []
                    else:
                        lvl['best_time'] = lvl['best_time'][:MAX_RANKS]
                    if not isinstance(lvl.get('least_moves'), list):
                        lvl['least_moves'] = []
                    else:
                        lvl['least_moves'] = lvl['least_moves'][:MAX_RANKS]
                if not isinstance(data.get('current_level'), int):
                    data['current_level'] = 1
                settings = data.setdefault('settings', {})
                settings.setdefault('theme', 'Numbers')
                settings.setdefault('background', 'Blue')
                settings.setdefault('word_color', 'White')
                return data
        except Exception:
            pass
    # Return a deep copy of the defaults so callers can modify the dict safely
    return json.loads(json.dumps(DEFAULT_DATA))


def save_data(data: dict):
    """Write the in-memory save data back to disk."""
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@dataclass
class Card:
    """Representation of a single card on the board."""

    value: str  # what is shown when the card is flipped
    rect: pygame.Rect  # position and size on screen
    is_face_up: bool = False  # whether the card is currently revealed
    is_matched: bool = False  # has this card been successfully paired?
    target: Optional[Tuple[int, int]] = None  # animation target location
    visible: bool = True  # used when sliding matched cards off screen


@dataclass
class Star:
    """Simple particle used for the star field background."""

    x: int
    y: int
    speed: float
    size: int


@dataclass
class MemoryMatchGame:
    """Main game class holding all state and behavior."""

    width: int = 800  # screen width
    height: int = 600  # screen height
    data: dict = field(default_factory=load_data)  # persistent game data
    stars: List[Star] = field(default_factory=list)  # star particles for BG

    def __post_init__(self):
        """Initialize pygame and set up the main state variables."""

        pygame.init()
        # Create the display surface, respecting the saved fullscreen setting
        flags = pygame.FULLSCREEN if self.data['settings'].get(
            'fullscreen') else 0
        self.screen = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption('Memory Match')
        self.clock = pygame.time.Clock()
        # Fonts used for most text and large headings
        self.font = pygame.font.SysFont(None, 36)
        self.large_font = pygame.font.SysFont(None, 72)
        # Game state values
        self.state = 'menu'
        self.current_level = 1
        self.dev_mode = False
        self.saved_unlocked = self.data.get('unlocked_level', 1)
        self.keypad_input = ''
        self.prev_state = None
        # Gameplay related variables
        self.cards: List[Card] = []
        self.first_card: Optional[Card] = None
        self.second_card: Optional[Card] = None
        self.moves = 0
        self.start_ticks = 0
        self.time_limit = 0
        self.time_left = 0
        self.flip_start: Optional[int] = None
        self.card_w = 0
        self.card_h = 0
        # Message shown when a pair is matched
        self.message: str = ''
        self.message_timer = 0
        self.finished_level = 1
        # Offsets for animated backgrounds
        self.grid_offset = 0
        self.dot_offset = 0
        self.stripe_offset = 0
        self.solid_phase = 0
        self.update_colors()
        self.init_background()

    def init_background(self):
        """Create particles and reset animation offsets for the background."""

        if getattr(self, 'bg_style', 'Stars') == 'Stars':
            self.stars = [
                Star(
                    random.randint(0, self.width),
                    random.randint(0, self.height),
                    random.uniform(30, 90),
                    random.randint(1, 3),
                )
                for _ in range(60)
            ]
        else:
            self.stars = []
        self.grid_offset = 0
        self.dot_offset = 0
        self.stripe_offset = 0
        self.solid_phase = 0

    def update_background(self, dt: int):
        """Animate whichever background style is currently active."""

        if self.bg_style == 'Stars':
            for star in self.stars:
                star.y += star.speed * dt / 1000
                if star.y > self.height:
                    star.y = 0
                    star.x = random.randint(0, self.width)
        elif self.bg_style == 'Grid':
            self.grid_offset = (self.grid_offset + dt * 0.02) % 40
        elif self.bg_style == 'Dots':
            self.dot_offset = (self.dot_offset + dt * 0.05) % 40
        elif self.bg_style == 'Stripes':
            self.stripe_offset = (self.stripe_offset + dt * 0.03) % 40
        else:  # Solid
            self.solid_phase = (self.solid_phase + dt * 0.002) % (math.tau)

    def draw_background(self):
        """Render the animated background behind everything else."""

        if self.bg_style == 'Stars':
            self.screen.fill((0, 0, 0))
            for star in self.stars:
                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    pygame.Rect(star.x, int(star.y), star.size, star.size),
                )
            overlay = pygame.Surface((self.width, self.height))
            overlay.set_alpha(80)
            overlay.fill(self.bg_color)
            self.screen.blit(overlay, (0, 0))
        elif self.bg_style == 'Grid':
            self.screen.fill(self.bg_color)
            grid_size = 40
            line_color = (80, 80, 80)
            offset = int(self.grid_offset)
            for x in range(-grid_size + offset, self.width, grid_size):
                pygame.draw.line(
                    self.screen, line_color, (x, 0), (x, self.height)
                )
            for y in range(-grid_size + offset, self.height, grid_size):
                pygame.draw.line(
                    self.screen, line_color, (0, y), (self.width, y)
                )
        elif self.bg_style == 'Dots':
            self.screen.fill(self.bg_color)
            dot_color = (80, 80, 80)
            spacing = 40
            offset = int(self.dot_offset)
            for x in range(-spacing + offset, self.width, spacing):
                for y in range(-spacing + offset, self.height, spacing):
                    pygame.draw.circle(self.screen, dot_color, (x, y), 2)
        elif self.bg_style == 'Stripes':
            self.screen.fill(self.bg_color)
            stripe_color = (80, 80, 80)
            spacing = 40
            offset = int(self.stripe_offset)
            for y in range(-spacing + offset, self.height, spacing):
                pygame.draw.rect(
                    self.screen, stripe_color, (0, y, self.width, 20)
                )
        else:  # Solid
            phase = (math.sin(self.solid_phase) + 1) / 2
            r, g, b = self.bg_color
            shade = int(20 * phase)
            color = (
                min(255, max(0, r + shade)),
                min(255, max(0, g + shade)),
                min(255, max(0, b + shade)),
            )
            self.screen.fill(color)

    def run(self):
        """Main game loop router."""

        while True:
            if self.state == 'menu':
                self.menu_loop()
            elif self.state == 'levels':
                self.levels_loop()
            elif self.state == 'play':
                self.play_loop()
            elif self.state == 'level_complete':
                self.level_complete_loop()
            elif self.state == 'leader_select':
                self.leader_select_loop()
            elif self.state == 'leaderboard':
                self.leaderboard_loop()
            elif self.state == 'settings':
                self.settings_loop()
            elif self.state == 'keypad':
                self.keypad_loop()
            elif self.state == 'quit':
                break
        pygame.quit()

    def draw_text_center(self, text: str, y: int, font=None):
        """Helper to render centered text."""

        font = font or self.font
        surface = font.render(text, True, self.word_color)
        rect = surface.get_rect(center=(self.width // 2, y))
        self.screen.blit(surface, rect)

    def draw_text(self, text: str, x: int, y: int, font=None):
        """Draw text at a specific screen position."""

        font = font or self.font
        surface = font.render(text, True, self.word_color)
        self.screen.blit(surface, (x, y))

    def draw_menu_button(self):
        """Draw the universal Menu button in the top-left."""

        self.menu_rect = pygame.Rect(10, 10, 80, 30)
        pygame.draw.rect(
            self.screen, BUTTON_COLOR, self.menu_rect, border_radius=6)
        pygame.draw.rect(
            self.screen, (200, 200, 200), self.menu_rect, 2, border_radius=6)
        txt = self.font.render('Menu', True, self.word_color)
        self.screen.blit(txt, txt.get_rect(center=self.menu_rect.center))

    def draw_dev_button(self):
        """Draw the Dev/Normal toggle in the bottom-right."""

        label = 'Normal' if self.dev_mode else 'Dev'
        self.dev_rect = pygame.Rect(self.width - 100, self.height - 40, 90, 30)
        pygame.draw.rect(
            self.screen, BUTTON_COLOR, self.dev_rect, border_radius=6)
        pygame.draw.rect(
            self.screen, (200, 200, 200), self.dev_rect, 2, border_radius=6)
        txt = self.font.render(label, True, (0, 0, 0))
        self.screen.blit(txt, txt.get_rect(center=self.dev_rect.center))

    def draw_back_button(self):
        """Draw a Back button used on secondary screens."""

        self.back_rect = pygame.Rect(100, 10, 80, 30)
        pygame.draw.rect(
            self.screen, BUTTON_COLOR, self.back_rect, border_radius=6)
        pygame.draw.rect(
            self.screen, (200, 200, 200), self.back_rect, 2, border_radius=6)
        txt = self.font.render('Back', True, self.word_color)
        self.screen.blit(txt, txt.get_rect(center=self.back_rect.center))

    # -------- Menu ---------
    def menu_loop(self):
        """Handle the main menu screen."""

        while self.state == 'menu':
            dt = self.clock.get_time()
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if self.play_rect.collidepoint(mx, my):
                        self.start_new_game()
                        self.state = 'play'
                    elif self.levels_rect.collidepoint(mx, my):
                        self.state = 'levels'
                    elif (
                        self.continue_rect.collidepoint(mx, my)
                        and 'current_level' in self.data
                    ):
                        self.current_level = self.data.get('current_level', 1)
                        self.start_level(self.current_level)
                        self.state = 'play'
                    elif self.leader_rect.collidepoint(mx, my):
                        self.state = 'leader_select'
                    elif self.settings_rect.collidepoint(mx, my):
                        self.state = 'settings'
                    elif self.dev_rect.collidepoint(mx, my):
                        if self.dev_mode:
                            self.dev_mode = False
                            self.data['unlocked_level'] = self.saved_unlocked
                        else:
                            self.prev_state = 'menu'
                            self.keypad_input = ''
                            self.state = 'keypad'
                    elif self.menu_rect.collidepoint(mx, my):
                        self.state = 'menu'
                    elif self.exit_rect.collidepoint(mx, my):
                        self.state = 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
            self.update_background(dt)
            self.draw_background()
            self.draw_text_center('Memory Match', 100, self.large_font)
            y = 220
            self.play_rect = self.draw_button('Play', y)
            y += 60
            self.levels_rect = self.draw_button('Levels', y)
            can_continue = 'current_level' in self.data
            cont_text = 'Continue' if can_continue else 'Continue (locked)'
            text_color = (255, 255, 255) if can_continue else (150, 150, 150)
            y += 60
            self.continue_rect = self.draw_button(cont_text, y, text_color)
            y += 60
            self.leader_rect = self.draw_button('Leaderboards', y)
            y += 60
            self.settings_rect = self.draw_button('Settings', y)
            y += 60
            self.exit_rect = self.draw_button('Exit', y)
            self.draw_menu_button()
            self.draw_dev_button()
            pygame.display.flip()
            self.clock.tick(60)

    def settings_loop(self):
        """Allow the player to cycle through visual preference options."""

        bg_opts = list(BACKGROUND_OPTIONS.keys())
        word_opts = list(WORD_OPTIONS.keys())
        theme_opts = list(CARD_THEMES.keys())
        style_opts = BACKGROUND_STYLES
        bg_val = self.data['settings'].get('background', 'Blue')
        if bg_val not in bg_opts:
            bg_val = 'Blue'
            self.data['settings']['background'] = bg_val
        bg_idx = bg_opts.index(bg_val)

        word_val = self.data['settings'].get('word_color', 'White')
        if word_val not in word_opts:
            word_val = 'White'
            self.data['settings']['word_color'] = word_val
        word_idx = word_opts.index(word_val)

        theme_val = self.data['settings'].get('theme', 'Numbers')
        if theme_val not in theme_opts:
            theme_val = 'Numbers'
            self.data['settings']['theme'] = theme_val
        theme_idx = theme_opts.index(theme_val)

        style_val = self.data['settings'].get('bg_style', 'Stars')
        if style_val not in style_opts:
            style_val = 'Stars'
            self.data['settings']['bg_style'] = style_val
        style_idx = style_opts.index(style_val)
        while self.state == 'settings':
            dt = self.clock.get_time()
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if self.menu_rect.collidepoint(mx, my):
                        save_data(self.data)
                        self.state = 'menu'
                    elif self.bg_rect.collidepoint(mx, my):
                        bg_idx = (bg_idx + 1) % len(bg_opts)
                        self.data['settings']['background'] = bg_opts[bg_idx]
                        self.update_colors()
                    elif self.word_rect.collidepoint(mx, my):
                        word_idx = (word_idx + 1) % len(word_opts)
                        self.data['settings']['word_color'] = (
                            word_opts[word_idx]
                        )
                        self.update_colors()
                    elif self.theme_rect.collidepoint(mx, my):
                        theme_idx = (theme_idx + 1) % len(theme_opts)
                        self.data['settings']['theme'] = (
                            theme_opts[theme_idx]
                        )
                        self.update_colors()
                    elif self.style_rect.collidepoint(mx, my):
                        style_idx = (style_idx + 1) % len(style_opts)
                        self.data['settings']['bg_style'] = (
                            style_opts[style_idx]
                        )
                        self.update_colors()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
            self.update_background(dt)
            self.draw_background()
            self.draw_text_center('Settings', 80, self.large_font)
            self.bg_rect = self.draw_button(
                f'Background: {bg_opts[bg_idx]}', 200)
            self.word_rect = self.draw_button(
                f'Word Color: {word_opts[word_idx]}', 250)
            self.theme_rect = self.draw_button(
                f'Theme: {theme_opts[theme_idx]}', 300)
            self.style_rect = self.draw_button(
                f'Background Style: {style_opts[style_idx]}', 350)
            self.draw_menu_button()
            pygame.display.flip()
            self.clock.tick(60)

    def draw_button(self, text: str, y: int,
                    color=None) -> pygame.Rect:
        """Draw a clickable button and return its rectangle."""

        color = color or self.word_color
        surface = self.font.render(text, True, color)
        rect = surface.get_rect(center=(self.width // 2, y))
        button_rect = rect.inflate(40, 20)
        mouse_over = button_rect.collidepoint(pygame.mouse.get_pos())
        fill = HOVER_COLOR if mouse_over else BUTTON_COLOR
        pygame.draw.rect(
            self.screen, fill, button_rect, border_radius=8)
        pygame.draw.rect(
            self.screen, (200, 200, 200), button_rect, 2, border_radius=8)
        self.screen.blit(surface, rect)
        return button_rect

    def levels_loop(self):
        """Show available levels and handle unlocking/dev mode."""

        tile_w = 100
        tile_h = 60
        margin_x = (self.width - tile_w * 5) // 6
        margin_y = 40
        while self.state == 'levels':
            dt = self.clock.get_time()
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    for idx, rect in enumerate(self.level_rects):
                        if rect.collidepoint(mx, my):
                            level = idx + 1
                            if (
                                level <= self.data['unlocked_level']
                                or self.dev_mode
                            ):
                                self.current_level = level
                                self.start_level(level)
                                self.state = 'play'
                            break
                    if self.dev_rect.collidepoint(mx, my):
                        if self.dev_mode:
                            self.dev_mode = False
                            self.data['unlocked_level'] = self.saved_unlocked
                        else:
                            self.prev_state = 'levels'
                            self.keypad_input = ''
                            self.state = 'keypad'
                    if self.menu_rect.collidepoint(mx, my):
                        self.state = 'menu'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
            self.update_background(dt)
            self.draw_background()
            self.level_rects = []
            y_start = 100
            level = 1
            for row in range(2):
                x = margin_x
                for col in range(5):
                    rect = pygame.Rect(
                        x, y_start + row * (tile_h + margin_y), tile_w, tile_h)
                    unlocked = (
                        level <= self.data['unlocked_level']
                        or self.dev_mode
                    )
                    color = CARD_BACK_COLOR if unlocked else LOCKED_COLOR
                    pygame.draw.rect(
                        self.screen, color, rect, border_radius=8)
                    pygame.draw.rect(
                        self.screen, (200, 200, 200), rect, 2, border_radius=8)
                    text = self.font.render(str(level), True, (0, 0, 0))
                    text_rect = text.get_rect(center=rect.center)
                    self.screen.blit(text, text_rect)
                    self.level_rects.append(rect)
                    level += 1
                    x += tile_w + margin_x
            self.draw_menu_button()
            self.draw_dev_button()
            pygame.display.flip()
            self.clock.tick(60)

    def leader_select_loop(self):
        """Allow the user to pick which level's leaderboard to view."""

        tile_w = 100
        tile_h = 60
        margin_x = (self.width - tile_w * 5) // 6
        margin_y = 40
        while self.state == 'leader_select':
            dt = self.clock.get_time()
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    for idx, rect in enumerate(self.level_rects):
                        if rect.collidepoint(mx, my):
                            self.leader_level = idx + 1
                            self.state = 'leaderboard'
                            break
                    if self.dev_rect.collidepoint(mx, my):
                        if self.dev_mode:
                            self.dev_mode = False
                            self.data['unlocked_level'] = self.saved_unlocked
                        else:
                            self.prev_state = 'leader_select'
                            self.keypad_input = ''
                            self.state = 'keypad'
                    if self.menu_rect.collidepoint(mx, my):
                        self.state = 'menu'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
            self.update_background(dt)
            self.draw_background()
            self.level_rects = []
            y_start = 100
            level = 1
            for row in range(2):
                x = margin_x
                for col in range(5):
                    rect = pygame.Rect(
                        x, y_start + row * (tile_h + margin_y), tile_w, tile_h)
                    color = (180, 180, 180)
                    pygame.draw.rect(
                        self.screen, color, rect, border_radius=8)
                    pygame.draw.rect(
                        self.screen, (200, 200, 200), rect, 2, border_radius=8)
                    text = self.font.render(str(level), True, (0, 0, 0))
                    text_rect = text.get_rect(center=rect.center)
                    self.screen.blit(text, text_rect)
                    self.level_rects.append(rect)
                    level += 1
                    x += tile_w + margin_x
            self.draw_text_center('Select Level', 60)
            self.draw_menu_button()
            self.draw_dev_button()
            pygame.display.flip()
            self.clock.tick(60)

    # -------- Gameplay ---------
    def start_new_game(self):
        """Reset progress and begin at level 1."""

        self.current_level = 1
        self.data['current_level'] = 1
        save_data(self.data)
        self.start_level(self.current_level)

    def start_level(self, level: int):
        """Setup all game objects for the chosen level."""

        config = LEVELS[level - 1]
        cols, rows = config['grid'][1], config['grid'][0]
        num_pairs = cols * rows // 2
        symbol_pool = self.card_theme.copy()
        random.shuffle(symbol_pool)
        if len(symbol_pool) < num_pairs:
            symbol_pool *= (num_pairs // len(symbol_pool) + 1)
        values = symbol_pool[:num_pairs] * 2
        random.shuffle(values)
        card_w = self.width // cols
        card_h = (self.height - 100) // rows
        self.card_w = card_w - 10
        self.card_h = card_h - 10
        self.cards = []
        # Create card objects positioned in the grid
        for r in range(rows):
            for c in range(cols):
                x = c * card_w + 5
                y = r * card_h + 50
                rect = pygame.Rect(x, y, card_w - 10, card_h - 10)
                value = str(values.pop())
                self.cards.append(Card(value=value, rect=rect))
        self.first_card = None
        self.second_card = None
        self.moves = 0
        self.time_limit = config['time']
        self.start_ticks = pygame.time.get_ticks()
        self.time_left = self.time_limit
        if not self.dev_mode:
            self.data['current_level'] = level
            save_data(self.data)

    def play_loop(self):
        """Main gameplay loop for a level."""

        while self.state == 'play':
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.menu_rect.collidepoint(event.pos):
                        self.state = 'menu'
                    else:
                        self.handle_click(event.pos)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
            self.update_game(dt)
            self.update_background(dt)
            self.draw_background()
            self.draw_game()
            self.draw_menu_button()
            if self.check_complete():
                self.finish_level()
            elif self.time_left <= 0:
                self.state = 'menu'
            pygame.display.flip()

    def handle_click(self, pos: Tuple[int, int]):
        """Flip cards based on a mouse click."""

        if self.flip_start or self.message_timer > 0:
            return
        for card in self.cards:
            if card.rect.collidepoint(
                    pos) and not card.is_face_up and not card.is_matched:
                card.is_face_up = True
                if not self.first_card:
                    self.first_card = card
                elif not self.second_card and card != self.first_card:
                    self.second_card = card
                    self.moves += 1
                    self.flip_start = pygame.time.get_ticks()
                break

    def update_game(self, dt: int):
        """Advance animations and check for completed pairs."""

        self.update_timer()
        now = pygame.time.get_ticks()
        if self.first_card and self.second_card and self.flip_start:
            if now - self.flip_start >= 600:
                if self.first_card.value == self.second_card.value:
                    self.first_card.is_matched = True
                    self.second_card.is_matched = True
                    for card in (self.first_card, self.second_card):
                        card.target = (
                            self.width + self.card_w, card.rect.centery)
                    self.message = random.choice(CELEBRATIONS)
                    self.message_timer = 1000
                else:
                    self.first_card.is_face_up = False
                    self.second_card.is_face_up = False
                self.first_card = None
                self.second_card = None
                self.flip_start = None
        if self.message_timer > 0:
            self.message_timer = max(0, self.message_timer - dt)
        for card in self.cards:
            if card.target and card.visible:
                cx, cy = card.rect.center
                tx, ty = card.target
                dx, dy = tx - cx, ty - cy
                dist = math.hypot(dx, dy)
                speed = 15
                if dist <= speed:
                    card.rect.center = card.target
                    if card.rect.left > self.width:
                        card.visible = False
                else:
                    card.rect.centerx += int(speed * dx / dist)
                    card.rect.centery += int(speed * dy / dist)

    def update_timer(self):
        """Recalculate how much time the player has left."""

        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000
        self.time_left = max(0, self.time_limit - int(elapsed))

    def draw_game(self):
        """Render all cards and HUD elements."""

        # background already drawn
        theme_key = self.data['settings'].get('theme', 'Numbers')
        for card in self.cards:
            if not card.visible:
                continue
            color = CARD_BACK_COLOR
            face_shown = card.is_face_up or card.is_matched
            if face_shown:
                if theme_key == 'Colors':
                    try:
                        color = pygame.Color(card.value.lower())
                    except ValueError:
                        color = CARD_FACE_COLOR
                else:
                    color = CARD_FACE_COLOR
            pygame.draw.rect(
                self.screen, color, card.rect, border_radius=6)
            pygame.draw.rect(
                self.screen, (255, 255, 255), card.rect, 2, border_radius=6)
            if face_shown and theme_key != 'Colors':
                val_surf = self.font.render(card.value, True, (0, 0, 0))
                val_rect = val_surf.get_rect(center=card.rect.center)
                self.screen.blit(val_surf, val_rect)
            elif not face_shown and self.dev_mode:
                val_surf = self.font.render(card.value, True, LOCKED_COLOR)
                val_surf.set_alpha(80)
                val_rect = val_surf.get_rect(center=card.rect.center)
                self.screen.blit(val_surf, val_rect)
        time_surf = self.font.render(
            f'Time: {self.time_left}s', True, self.word_color)
        moves_surf = self.font.render(
            f'Moves: {self.moves}', True, self.word_color)
        spacing = 20
        total_w = time_surf.get_width() + spacing + moves_surf.get_width()
        start_x = (self.width - total_w) // 2
        self.screen.blit(time_surf, (start_x, 20))
        self.screen.blit(
            moves_surf,
            (start_x + time_surf.get_width() + spacing, 20),
        )
        if self.message_timer > 0:
            msg_surf = self.large_font.render(
                self.message, True, (255, 215, 0)
            )
            alpha = int(255 * self.message_timer / 1000)
            msg_surf.set_alpha(alpha)
            msg_rect = msg_surf.get_rect(
                center=(self.width // 2, self.height // 2)
            )
            self.screen.blit(msg_surf, msg_rect)

    def check_complete(self) -> bool:
        """Return ``True`` when all cards have been matched."""

        return all(card.is_matched for card in self.cards)

    def get_rank(self, table: List[List], value: int) -> Optional[int]:
        """Return leaderboard insertion index for ``value`` or ``None``."""

        for i, (_, val) in enumerate(table):
            if value < val:
                return i
        if len(table) < MAX_RANKS:
            return len(table)
        return None

    def finish_level(self):
        """Handle end-of-level logic and leaderboard checks."""

        time_taken = self.time_limit - self.time_left
        leaderboards = self.data.setdefault('leaderboard', {})
        self.finished_level = self.current_level
        level_key = str(self.finished_level)
        board = leaderboards.setdefault(
            level_key, {'best_time': [], 'least_moves': []})
        if not isinstance(board.get('best_time'), list):
            board['best_time'] = []
        if not isinstance(board.get('least_moves'), list):
            board['least_moves'] = []
        self.new_time_rank = None
        self.new_moves_rank = None
        if not self.dev_mode:
            self.new_time_rank = self.get_rank(
                board['best_time'], time_taken
            )
            self.new_moves_rank = self.get_rank(
                board['least_moves'], self.moves
            )
            self.new_time_val = time_taken
            self.new_moves_val = self.moves
            self.name_input = ''
            self.ask_name = (
                self.new_time_rank is not None
                or self.new_moves_rank is not None
            )
        else:
            self.ask_name = False
        if self.current_level < len(LEVELS):
            self.current_level += 1
            if not self.dev_mode:
                self.data['unlocked_level'] = max(
                    self.data['unlocked_level'], self.current_level)
                self.data['current_level'] = self.current_level
                save_data(self.data)
            self.state = 'level_complete'
        else:
            if not self.dev_mode:
                self.data['current_level'] = self.current_level
                save_data(self.data)
            self.state = 'menu'

    def level_complete_loop(self):
        """Display completion info and handle leaderboard entry."""

        while self.state == 'level_complete':
            dt = self.clock.get_time()
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            entering_name = self.ask_name
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.KEYDOWN:
                    if entering_name:
                        if event.key == pygame.K_RETURN and self.name_input:
                            leaderboards = self.data.setdefault(
                                'leaderboard', {})
                            level_key = str(self.finished_level)
                            board = leaderboards.setdefault(
                                level_key,
                                {
                                    'best_time': [],
                                    'least_moves': []
                                },
                            )
                            if not isinstance(board.get('best_time'), list):
                                board['best_time'] = []
                            if not isinstance(board.get('least_moves'), list):
                                board['least_moves'] = []
                            if self.new_time_rank is not None:
                                board['best_time'].insert(
                                    self.new_time_rank, [
                                        self.name_input, self.new_time_val])
                                board['best_time'] = (
                                    board['best_time'][:MAX_RANKS]
                                )
                            if self.new_moves_rank is not None:
                                board['least_moves'].insert(
                                    self.new_moves_rank, [
                                        self.name_input, self.new_moves_val])
                                board['least_moves'] = (
                                    board['least_moves'][:MAX_RANKS]
                                )
                            save_data(self.data)
                            entering_name = False
                            self.ask_name = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.name_input = self.name_input[:-1]
                        else:
                            if (
                                event.unicode.isprintable()
                                and len(self.name_input) < 12
                            ):
                                self.name_input += event.unicode
                    else:
                        if event.key == pygame.K_SPACE:
                            self.start_level(self.current_level)
                            self.state = 'play'
                        if event.key == pygame.K_ESCAPE:
                            self.state = 'menu'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.menu_rect.collidepoint(event.pos):
                        self.state = 'menu'
            self.update_background(dt)
            self.draw_background()
            self.draw_text_center('Level Complete!', 180, self.large_font)
            if entering_name:
                self.draw_text_center(
                    'New leaderboard score! Enter name:', 260)
                self.draw_text_center(self.name_input + '|', 300)
            else:
                self.draw_text_center('Press SPACE for next level', 260)
                self.draw_text_center('Press ESC for menu', 300)
            self.draw_menu_button()
            pygame.display.flip()
            self.clock.tick(60)

    def toggle_fullscreen(self):
        """Switch between fullscreen and windowed mode."""

        fullscreen = not self.data['settings'].get('fullscreen')
        self.data['settings']['fullscreen'] = fullscreen
        save_data(self.data)
        if fullscreen:
            self.screen = pygame.display.set_mode(
                (self.width, self.height), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.width, self.height))

    def update_colors(self):
        """Apply current settings to colors and background style."""

        bg_key = self.data['settings'].get('background', 'Blue')
        if bg_key not in BACKGROUND_OPTIONS:
            bg_key = 'Blue'
            self.data['settings']['background'] = bg_key
        style_key = self.data['settings'].get('bg_style', 'Stars')
        if style_key not in BACKGROUND_STYLES:
            style_key = 'Stars'
            self.data['settings']['bg_style'] = style_key
        word_key = self.data['settings'].get('word_color', 'White')
        if word_key not in WORD_OPTIONS:
            word_key = 'White'
            self.data['settings']['word_color'] = word_key
        self.bg_color = BACKGROUND_OPTIONS.get(bg_key, MENU_BG)
        self.word_color = WORD_OPTIONS.get(word_key, (255, 255, 255))
        self.bg_style = style_key

        theme_key = self.data['settings'].get('theme', 'Numbers')
        if theme_key not in CARD_THEMES:
            theme_key = 'Numbers'
            self.data['settings']['theme'] = theme_key
        self.card_theme = CARD_THEMES[theme_key]
        self.init_background()

    def leaderboard_loop(self):
        """Render and navigate the leaderboard display."""

        while self.state == 'leaderboard':
            dt = self.clock.get_time()
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            self.back_rect = pygame.Rect(100, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.menu_rect.collidepoint(event.pos):
                        self.state = 'menu'
                    elif self.back_rect.collidepoint(event.pos):
                        self.state = 'leader_select'
            self.update_background(dt)
            self.draw_background()
            leaderboards = self.data.get('leaderboard', {})
            level_key = str(getattr(self, 'leader_level', 1))
            board = leaderboards.get(level_key, {})
            times = board.get('best_time', [])
            moves = board.get('least_moves', [])
            if not isinstance(times, list):
                times = []
            if not isinstance(moves, list):
                moves = []
            title = self.large_font.render(
                f'Level {level_key} Leaderboard', True, self.word_color)
            self.screen.blit(
                title, title.get_rect(
                    center=(
                        self.width // 2, 50)))
            header_t = self.font.render('Best Time (s)', True, self.word_color)
            header_m = self.font.render('Least Moves', True, self.word_color)
            self.screen.blit(
                header_t,
                header_t.get_rect(
                    center=(
                        self.width // 4,
                        100)))
            self.screen.blit(
                header_m,
                header_m.get_rect(
                    center=(
                        3 *
                        self.width //
                        4,
                        100)))
            y = 130
            max_len = min(max(len(times), len(moves)), MAX_RANKS)
            for i in range(max_len):
                if i < len(times):
                    name, val = times[i]
                    txt = self.font.render(
                        f'{i + 1}. {name} - {val}', True, self.word_color)
                    self.screen.blit(txt, txt.get_rect(midleft=(20, y)))
                if i < len(moves):
                    name, val = moves[i]
                    txt = self.font.render(
                        f'{i + 1}. {name} - {val}', True, self.word_color)
                    self.screen.blit(
                        txt, txt.get_rect(
                            midleft=(
                                self.width // 2 + 20, y)))
                y += 30
            self.draw_menu_button()
            self.draw_back_button()
            self.draw_dev_button()
            pygame.display.flip()
            self.clock.tick(60)

    def keypad_loop(self):
        """Show the keypad used to unlock dev mode."""

        buttons: List[Tuple[pygame.Rect, str]] = []
        padding = 10
        btn_w = 60
        btn_h = 40
        start_x = self.width // 2 - (btn_w * 3 + padding * 2) // 2
        start_y = self.height // 2 - (btn_h * 5 + padding * 4) // 2
        numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        long_w = int(btn_w * 1.5)
        while self.state == 'keypad':
            dt = self.clock.get_time()
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if self.menu_rect.collidepoint(mx, my):
                        self.state = self.prev_state
                        continue
                    for rect, label in buttons:
                        if rect.collidepoint(mx, my):
                            if label.isdigit():
                                self.keypad_input += label
                            elif label == 'Submit':
                                if self.keypad_input == '12345':
                                    self.saved_unlocked = (
                                        self.data['unlocked_level']
                                    )
                                    self.dev_mode = True
                                self.state = self.prev_state
                            elif label == 'Cancel':
                                self.state = self.prev_state
                            break
                if (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE
                ):
                    self.state = self.prev_state
            self.update_background(dt)
            self.draw_background()
            buttons = []
            idx = 0
            for row in range(3):
                for col in range(3):
                    x = start_x + col * (btn_w + padding)
                    y = start_y + row * (btn_h + padding)
                    rect = pygame.Rect(x, y, btn_w, btn_h)
                    buttons.append((rect, numbers[idx]))
                    pygame.draw.rect(self.screen, (150, 150, 150), rect)
                    text = self.font.render(numbers[idx], True, (0, 0, 0))
                    self.screen.blit(text, text.get_rect(center=rect.center))
                    idx += 1
            # row with 0
            zero_x = start_x + btn_w + padding
            zero_rect = pygame.Rect(
                zero_x, start_y + 3 * (btn_h + padding), btn_w, btn_h)
            buttons.append((zero_rect, '0'))
            pygame.draw.rect(self.screen, (150, 150, 150), zero_rect)
            txt0 = self.font.render('0', True, (0, 0, 0))
            self.screen.blit(txt0, txt0.get_rect(center=zero_rect.center))
            # submit and cancel
            submit_x = self.width // 2 - (2 * long_w + padding) // 2
            submit_rect = pygame.Rect(
                submit_x, start_y + 4 * (btn_h + padding), long_w, btn_h)
            buttons.append((submit_rect, 'Submit'))
            pygame.draw.rect(self.screen, (150, 150, 150), submit_rect)
            txts = self.font.render('Submit', True, (0, 0, 0))
            self.screen.blit(
                txts,
                txts.get_rect(center=submit_rect.center),
            )
            cancel_rect = pygame.Rect(
                submit_x + long_w + padding,
                start_y + 4 * (btn_h + padding),
                long_w,
                btn_h,
            )
            buttons.append((cancel_rect, 'Cancel'))
            pygame.draw.rect(self.screen, (150, 150, 150), cancel_rect)
            txtc = self.font.render('Cancel', True, (0, 0, 0))
            self.screen.blit(txtc, txtc.get_rect(center=cancel_rect.center))
            input_surf = self.font.render(
                self.keypad_input, True, (255, 255, 255))
            self.screen.blit(input_surf, (start_x, start_y - 40))
            self.draw_menu_button()
            pygame.display.flip()
            self.clock.tick(60)
