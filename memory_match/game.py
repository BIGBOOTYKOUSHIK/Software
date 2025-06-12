import pygame
import json
import os
import random
from dataclasses import dataclass, field
from typing import Tuple, List, Optional
import math

SAVE_FILE = 'save.json'

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

DEFAULT_DATA = {
    'unlocked_level': 1,
    'leaderboard': {},
    'settings': {
        'music_volume': 0.5,
        'sfx_volume': 0.5,
        'theme': 'light',
        'timer_enabled': True,
        'fullscreen': False,
    }
}

CELEBRATIONS = [
    'Great!', 'Nice!', 'Well done!', 'Awesome!', 'Good job!'
]

def load_data() -> dict:
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_DATA.copy()

def save_data(data: dict):
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@dataclass
class Card:
    value: str
    rect: pygame.Rect
    is_face_up: bool = False
    is_matched: bool = False
    target: Optional[Tuple[int, int]] = None
    visible: bool = True

@dataclass
class MemoryMatchGame:
    width: int = 800
    height: int = 600
    data: dict = field(default_factory=load_data)

    def __post_init__(self):
        pygame.init()
        flags = pygame.FULLSCREEN if self.data['settings'].get('fullscreen') else 0
        self.screen = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption('Memory Match')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.large_font = pygame.font.SysFont(None, 72)
        self.state = 'menu'
        self.current_level = 1
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
        self.message: str = ''
        self.message_timer = 0

    def run(self):
        while True:
            if self.state == 'menu':
                self.menu_loop()
            elif self.state == 'play':
                self.play_loop()
            elif self.state == 'level_complete':
                self.level_complete_loop()
            elif self.state == 'quit':
                break
        pygame.quit()

    def draw_text_center(self, text: str, y: int, font=None):
        font = font or self.font
        surface = font.render(text, True, (255, 255, 255))
        rect = surface.get_rect(center=(self.width//2, y))
        self.screen.blit(surface, rect)

    # -------- Menu ---------
    def menu_loop(self):
        while self.state == 'menu':
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if self.play_rect.collidepoint(mx, my):
                        self.start_new_game()
                        self.state = 'play'
                    elif self.continue_rect.collidepoint(mx, my) and self.data['unlocked_level'] > 1:
                        self.current_level = self.data['unlocked_level']
                        self.start_level(self.current_level)
                        self.state = 'play'
                    elif self.exit_rect.collidepoint(mx, my):
                        self.state = 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
            self.screen.fill((0, 50, 100))
            self.draw_text_center('Memory Match', 100, self.large_font)
            self.play_rect = self.draw_button('Play', 250)
            cont_text = 'Continue' if self.data['unlocked_level'] > 1 else 'Continue (locked)'
            color = (255,255,255) if self.data['unlocked_level'] > 1 else (150,150,150)
            self.continue_rect = self.draw_button(cont_text, 320, color)
            self.exit_rect = self.draw_button('Exit', 390)
            pygame.display.flip()
            self.clock.tick(60)

    def draw_button(self, text: str, y: int, color=(255,255,255)) -> pygame.Rect:
        surface = self.font.render(text, True, color)
        rect = surface.get_rect(center=(self.width//2, y))
        self.screen.blit(surface, rect)
        return rect

    # -------- Gameplay ---------
    def start_new_game(self):
        self.current_level = 1
        self.start_level(self.current_level)

    def start_level(self, level: int):
        config = LEVELS[level-1]
        cols, rows = config['grid'][1], config['grid'][0]
        num_pairs = cols*rows//2
        values = list(range(num_pairs))*2
        random.shuffle(values)
        card_w = self.width//cols
        card_h = (self.height-100)//rows
        self.card_w = card_w - 10
        self.card_h = card_h - 10
        self.cards = []
        for r in range(rows):
            for c in range(cols):
                x = c*card_w + 5
                y = r*card_h + 50
                rect = pygame.Rect(x, y, card_w-10, card_h-10)
                value = str(values.pop())
                self.cards.append(Card(value=value, rect=rect))
        self.first_card = None
        self.second_card = None
        self.moves = 0
        self.time_limit = config['time']
        self.start_ticks = pygame.time.get_ticks()
        self.time_left = self.time_limit

    def play_loop(self):
        while self.state == 'play':
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()
            self.update_game(dt)
            self.draw_game()
            if self.check_complete():
                self.finish_level()
            elif self.time_left <= 0:
                self.state = 'menu'
            pygame.display.flip()

    def handle_click(self, pos: Tuple[int, int]):
        if self.flip_start or self.message_timer > 0:
            return
        for card in self.cards:
            if card.rect.collidepoint(pos) and not card.is_face_up and not card.is_matched:
                card.is_face_up = True
                if not self.first_card:
                    self.first_card = card
                elif not self.second_card and card != self.first_card:
                    self.second_card = card
                    self.moves += 1
                    self.flip_start = pygame.time.get_ticks()
                break

    def update_game(self, dt: int):
        self.update_timer()
        now = pygame.time.get_ticks()
        if self.first_card and self.second_card and self.flip_start:
            if now - self.flip_start >= 600:
                if self.first_card.value == self.second_card.value:
                    self.first_card.is_matched = True
                    self.second_card.is_matched = True
                    for card in (self.first_card, self.second_card):
                        card.target = (self.width + self.card_w, card.rect.centery)
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
        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000
        self.time_left = max(0, self.time_limit - int(elapsed))

    def draw_game(self):
        self.screen.fill((0, 0, 0))
        for card in self.cards:
            if not card.visible:
                continue
            color = (200, 200, 200)
            if card.is_face_up or card.is_matched:
                color = (50, 150, 50)
            pygame.draw.rect(self.screen, color, card.rect)
            if card.is_face_up or card.is_matched:
                val_surf = self.font.render(card.value, True, (0,0,0))
                val_rect = val_surf.get_rect(center=card.rect.center)
                self.screen.blit(val_surf, val_rect)
        self.draw_text_center(f'Time: {self.time_left}s', 20)
        self.draw_text_center(f'Moves: {self.moves}', 50)
        if self.message_timer > 0:
            msg_surf = self.large_font.render(self.message, True, (255, 215, 0))
            msg_rect = msg_surf.get_rect(center=(self.width//2, self.height//2))
            self.screen.blit(msg_surf, msg_rect)

    def check_complete(self) -> bool:
        return all(card.is_matched for card in self.cards)

    def finish_level(self):
        level_key = str(self.current_level)
        board = self.data.setdefault('leaderboard', {})
        entry = board.get(level_key, {'best_time': None, 'least_moves': None})
        if entry['best_time'] is None or self.time_left > 0 and self.time_left < entry['best_time']:
            entry['best_time'] = self.time_limit - self.time_left
        if entry['least_moves'] is None or self.moves < entry['least_moves']:
            entry['least_moves'] = self.moves
        board[level_key] = entry
        if self.current_level < len(LEVELS):
            self.current_level += 1
            self.data['unlocked_level'] = max(self.data['unlocked_level'], self.current_level)
            save_data(self.data)
            self.state = 'level_complete'
        else:
            save_data(self.data)
            self.state = 'menu'

    def level_complete_loop(self):
        while self.state == 'level_complete':
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.start_level(self.current_level)
                        self.state = 'play'
                    if event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
            self.screen.fill((0, 100, 0))
            self.draw_text_center('Level Complete!', 200, self.large_font)
            self.draw_text_center('Press SPACE for next level', 300)
            self.draw_text_center('Press ESC for menu', 350)
            pygame.display.flip()
            self.clock.tick(60)

    def toggle_fullscreen(self):
        fullscreen = not self.data['settings'].get('fullscreen')
        self.data['settings']['fullscreen'] = fullscreen
        save_data(self.data)
        if fullscreen:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.width, self.height))

