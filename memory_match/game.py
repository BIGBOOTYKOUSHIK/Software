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
    'leaderboard': {
        'best_time': [
            ['AAA', 40], ['BBB', 45], ['CCC', 50], ['DDD', 55], ['EEE', 60],
            ['FFF', 65], ['GGG', 70], ['HHH', 75], ['III', 80], ['JJJ', 90]
        ],
        'least_moves': [
            ['AAA', 30], ['BBB', 32], ['CCC', 34], ['DDD', 36], ['EEE', 38],
            ['FFF', 40], ['GGG', 42], ['HHH', 44], ['III', 46], ['JJJ', 48]
        ]
    },
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
        self.dev_mode = False
        self.saved_unlocked = self.data.get('unlocked_level', 1)
        self.keypad_input = ''
        self.prev_state = None
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
            elif self.state == 'levels':
                self.levels_loop()
            elif self.state == 'play':
                self.play_loop()
            elif self.state == 'level_complete':
                self.level_complete_loop()
            elif self.state == 'leaderboard':
                self.leaderboard_loop()
            elif self.state == 'keypad':
                self.keypad_loop()
            elif self.state == 'quit':
                break
        pygame.quit()

    def draw_text_center(self, text: str, y: int, font=None):
        font = font or self.font
        surface = font.render(text, True, (255, 255, 255))
        rect = surface.get_rect(center=(self.width//2, y))
        self.screen.blit(surface, rect)

    def draw_menu_button(self):
        self.menu_rect = pygame.Rect(10, 10, 80, 30)
        pygame.draw.rect(self.screen, (80, 80, 80), self.menu_rect)
        txt = self.font.render('Menu', True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(center=self.menu_rect.center))

    def draw_dev_button(self):
        label = 'Normal' if self.dev_mode else 'Dev'
        self.dev_rect = pygame.Rect(self.width - 100, self.height - 40, 90, 30)
        pygame.draw.rect(self.screen, (80, 80, 80), self.dev_rect)
        txt = self.font.render(label, True, (0, 0, 0))
        self.screen.blit(txt, txt.get_rect(center=self.dev_rect.center))

    # -------- Menu ---------
    def menu_loop(self):
        while self.state == 'menu':
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
                    elif self.continue_rect.collidepoint(mx, my) and self.data['unlocked_level'] > 1:
                        self.current_level = self.data['unlocked_level']
                        self.start_level(self.current_level)
                        self.state = 'play'
                    elif self.leader_rect.collidepoint(mx, my):
                        self.state = 'leaderboard'
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
            self.screen.fill((0, 50, 100))
            self.draw_text_center('Memory Match', 100, self.large_font)
            self.play_rect = self.draw_button('Play', 240)
            self.levels_rect = self.draw_button('Levels', 280)
            cont_text = 'Continue' if self.data['unlocked_level'] > 1 else 'Continue (locked)'
            color = (255,255,255) if self.data['unlocked_level'] > 1 else (150,150,150)
            self.continue_rect = self.draw_button(cont_text, 320, color)
            self.leader_rect = self.draw_button('Leaderboards', 360)
            self.exit_rect = self.draw_button('Exit', 400)
            self.draw_menu_button()
            self.draw_dev_button()
            pygame.display.flip()
            self.clock.tick(60)

    def draw_button(self, text: str, y: int, color=(255,255,255)) -> pygame.Rect:
        surface = self.font.render(text, True, color)
        rect = surface.get_rect(center=(self.width//2, y))
        self.screen.blit(surface, rect)
        return rect

    def levels_loop(self):
        tile_w = 100
        tile_h = 60
        margin_x = (self.width - tile_w * 5) // 6
        margin_y = 40
        while self.state == 'levels':
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    for idx, rect in enumerate(self.level_rects):
                        if rect.collidepoint(mx, my):
                            level = idx + 1
                            if level <= self.data['unlocked_level'] or self.dev_mode:
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
            self.screen.fill((30, 30, 80))
            self.level_rects = []
            y_start = 100
            level = 1
            for row in range(2):
                x = margin_x
                for col in range(5):
                    rect = pygame.Rect(x, y_start + row * (tile_h + margin_y), tile_w, tile_h)
                    unlocked = level <= self.data['unlocked_level'] or self.dev_mode
                    color = (200, 200, 200) if unlocked else (100, 100, 100)
                    pygame.draw.rect(self.screen, color, rect)
                    text = self.font.render(str(level), True, (0,0,0))
                    text_rect = text.get_rect(center=rect.center)
                    self.screen.blit(text, text_rect)
                    self.level_rects.append(rect)
                    level += 1
                    x += tile_w + margin_x
            self.draw_menu_button()
            self.draw_dev_button()
            pygame.display.flip()
            self.clock.tick(60)

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
            self.draw_game()
            self.draw_menu_button()
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
            elif self.dev_mode:
                val_surf = self.font.render(card.value, True, (100,100,100))
                val_surf.set_alpha(80)
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

    def get_rank(self, table: List[List], value: int) -> Optional[int]:
        for i, (_, val) in enumerate(table):
            if value < val:
                return i
        if len(table) < 20:
            return len(table)
        return None

    def finish_level(self):
        time_taken = self.time_limit - self.time_left
        board = self.data.setdefault('leaderboard', {
            'best_time': [],
            'least_moves': []
        })
        if not isinstance(board, dict):
            board = {'best_time': [], 'least_moves': []}
            self.data['leaderboard'] = board
        board.setdefault('best_time', [])
        board.setdefault('least_moves', [])
        self.new_time_rank = None
        self.new_moves_rank = None
        if not self.dev_mode:
            self.new_time_rank = self.get_rank(board['best_time'], time_taken)
            self.new_moves_rank = self.get_rank(board['least_moves'], self.moves)
            self.new_time_val = time_taken
            self.new_moves_val = self.moves
            self.name_input = ''
            self.ask_name = self.new_time_rank is not None or self.new_moves_rank is not None
        else:
            self.ask_name = False
        if self.current_level < len(LEVELS):
            self.current_level += 1
            if not self.dev_mode:
                self.data['unlocked_level'] = max(self.data['unlocked_level'], self.current_level)
                save_data(self.data)
            self.state = 'level_complete'
        else:
            if not self.dev_mode:
                save_data(self.data)
            self.state = 'menu'

    def level_complete_loop(self):
        while self.state == 'level_complete':
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            entering_name = self.ask_name
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.KEYDOWN:
                    if entering_name:
                        if event.key == pygame.K_RETURN and self.name_input:
                            board = self.data.setdefault('leaderboard', {'best_time': [], 'least_moves': []})
                            if self.new_time_rank is not None:
                                board['best_time'].insert(self.new_time_rank, [self.name_input, self.new_time_val])
                                board['best_time'] = board['best_time'][:20]
                            if self.new_moves_rank is not None:
                                board['least_moves'].insert(self.new_moves_rank, [self.name_input, self.new_moves_val])
                                board['least_moves'] = board['least_moves'][:20]
                            save_data(self.data)
                            entering_name = False
                            self.ask_name = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.name_input = self.name_input[:-1]
                        else:
                            if event.unicode.isprintable() and len(self.name_input) < 12:
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
            self.screen.fill((0, 100, 0))
            self.draw_text_center('Level Complete!', 180, self.large_font)
            if entering_name:
                self.draw_text_center('New leaderboard score! Enter name:', 260)
                self.draw_text_center(self.name_input + '|', 300)
            else:
                self.draw_text_center('Press SPACE for next level', 260)
                self.draw_text_center('Press ESC for menu', 300)
            self.draw_menu_button()
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

    def leaderboard_loop(self):
        while self.state == 'leaderboard':
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
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
            self.screen.fill((40, 40, 60))
            board = self.data.get('leaderboard', {})
            times = board.get('best_time', [])
            moves = board.get('least_moves', [])
            title = self.large_font.render('Leaderboards', True, (255,255,255))
            self.screen.blit(title, title.get_rect(center=(self.width//2, 50)))
            header_t = self.font.render('Best Time (s)', True, (255,255,255))
            header_m = self.font.render('Least Moves', True, (255,255,255))
            self.screen.blit(header_t, header_t.get_rect(center=(self.width//4, 100)))
            self.screen.blit(header_m, header_m.get_rect(center=(3*self.width//4, 100)))
            y = 130
            max_len = max(len(times), len(moves))
            for i in range(max_len):
                if i < len(times):
                    name, val = times[i]
                    txt = self.font.render(f'{i+1}. {name} - {val}', True, (255,255,255))
                    self.screen.blit(txt, txt.get_rect(midleft=(20, y)))
                if i < len(moves):
                    name, val = moves[i]
                    txt = self.font.render(f'{i+1}. {name} - {val}', True, (255,255,255))
                    self.screen.blit(txt, txt.get_rect(midleft=(self.width//2 + 20, y)))
                y += 30
            self.draw_menu_button()
            self.draw_dev_button()
            pygame.display.flip()
            self.clock.tick(60)

    def keypad_loop(self):
        buttons: List[Tuple[pygame.Rect, str]] = []
        padding = 10
        btn_w = 60
        btn_h = 40
        start_x = self.width//2 - (btn_w*3 + padding*2)//2
        start_y = self.height//2 - (btn_h*5 + padding*4)//2
        numbers = ['1','2','3','4','5','6','7','8','9','0']
        long_w = int(btn_w * 1.5)
        while self.state == 'keypad':
            self.menu_rect = pygame.Rect(10, 10, 80, 30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.state = 'quit'
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx,my = event.pos
                    if self.menu_rect.collidepoint(mx, my):
                        self.state = self.prev_state
                        continue
                    for rect, label in buttons:
                        if rect.collidepoint(mx,my):
                            if label.isdigit():
                                self.keypad_input += label
                            elif label == 'Submit':
                                if self.keypad_input == '12345':
                                    self.saved_unlocked = self.data['unlocked_level']
                                    self.dev_mode = True
                                self.state = self.prev_state
                            elif label == 'Cancel':
                                self.state = self.prev_state
                            break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = self.prev_state
            self.screen.fill((0,0,0))
            buttons = []
            idx = 0
            for row in range(3):
                for col in range(3):
                    x = start_x + col*(btn_w+padding)
                    y = start_y + row*(btn_h+padding)
                    rect = pygame.Rect(x, y, btn_w, btn_h)
                    buttons.append((rect, numbers[idx]))
                    pygame.draw.rect(self.screen, (150,150,150), rect)
                    text = self.font.render(numbers[idx], True, (0,0,0))
                    self.screen.blit(text, text.get_rect(center=rect.center))
                    idx += 1
            # row with 0
            zero_x = start_x + btn_w + padding
            zero_rect = pygame.Rect(zero_x, start_y + 3*(btn_h+padding), btn_w, btn_h)
            buttons.append((zero_rect, '0'))
            pygame.draw.rect(self.screen, (150,150,150), zero_rect)
            txt0 = self.font.render('0', True, (0,0,0))
            self.screen.blit(txt0, txt0.get_rect(center=zero_rect.center))
            # submit and cancel
            submit_x = self.width//2 - (2*long_w + padding)//2
            submit_rect = pygame.Rect(submit_x, start_y + 4*(btn_h+padding), long_w, btn_h)
            buttons.append((submit_rect, 'Submit'))
            pygame.draw.rect(self.screen, (150,150,150), submit_rect)
            txts = self.font.render('Submit', True, (0,0,0))
            self.screen.blit(txts, txts.get_rect(center=submit_rect.center))
            cancel_rect = pygame.Rect(submit_x + long_w + padding, start_y + 4*(btn_h+padding), long_w, btn_h)
            buttons.append((cancel_rect, 'Cancel'))
            pygame.draw.rect(self.screen, (150,150,150), cancel_rect)
            txtc = self.font.render('Cancel', True, (0,0,0))
            self.screen.blit(txtc, txtc.get_rect(center=cancel_rect.center))
            input_surf = self.font.render(self.keypad_input, True, (255,255,255))
            self.screen.blit(input_surf, (start_x, start_y - 40))
            self.draw_menu_button()
            pygame.display.flip()
            self.clock.tick(60)

