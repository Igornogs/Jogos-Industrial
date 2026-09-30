import math
import random
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Set
from enum import Enum

try:
    import pygame
except ImportError:
    print("Este jogo precisa do Pygame.")
    print("Instale com: pip install pygame")
    sys.exit(1)

pygame.init()
pygame.mixer.init()

# ========== CONSTANTES ==========
WIDTH, HEIGHT = 1152, 648
FPS = 60
TITLE = "A PORTA — Terror Psicológico (Edição Gráfica HD)"
SAVE_FILE = Path("savegame.txt")

# ========== PALETA DE CORES ==========
class Colors:
    BLACK = (5, 7, 12)
    DARK = (15, 18, 26)
    BLUE_WALL = (28, 36, 52)
    WOOD_DARK = (60, 42, 30)
    WOOD_LIGHT = (110, 78, 55)
    MARBLE = (210, 215, 220)
    TILE_BLUE = (70, 90, 110)
    TILE_WHITE = (220, 225, 230)
    GREY_STEEL = (140, 148, 160)
    WHITE = (235, 238, 245)
    WARM_LIGHT = (255, 215, 130)
    RED = (210, 45, 45)
    GREEN = (45, 180, 85)
    CYAN = (90, 170, 190)
    YELLOW = (245, 220, 100)

# ========== FONTES ==========
class Fonts:
    SMALL = pygame.font.SysFont("consolas", 14)
    NORMAL = pygame.font.SysFont("consolas", 19)
    MID = pygame.font.SysFont("consolas", 24, bold=True)
    BIG = pygame.font.SysFont("consolas", 48, bold=True)

# ========== ENUMS ==========
class GameState(Enum):
    MENU = "menu"
    GAME = "game"
    PAUSED = "paused"
    SETTINGS = "settings"
    GAME_OVER = "game_over"
    ENDING = "ending"

class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

# ========== CLASSES DE UTILIDADE ==========
class Item:
    """Representa um item no inventário ou no mundo."""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return self.name == other.name
    
    def __hash__(self):
        return hash(self.name)
    
    def __repr__(self):
        return self.name

class Dialogue:
    """Gerencia diálogos na tela."""
    def __init__(self, text: str, duration: float = 4.5):
        self.text = text
        self.duration = duration
        self.timer = duration

class Message:
    """Gerencia mensagens de sistema."""
    def __init__(self, text: str, duration: float = 3.5):
        self.text = text
        self.duration = duration
        self.timer = duration

class InteractionZone:
    """Define uma zona de interação retangular."""
    def __init__(self, rect: pygame.Rect, callback=None, description: str = ""):
        self.rect = rect
        self.callback = callback
        self.description = description
    
    def contains(self, x: float, y: float) -> bool:
        return self.rect.collidepoint(x, y)

# ========== GERENCIADOR DE SAVE/LOAD ==========
class SaveManager:
    @staticmethod
    def save_game(stage: int):
        try:
            SAVE_FILE.write_text(str(stage), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def load_game() -> int:
        try:
            return max(1, min(4, int(SAVE_FILE.read_text(encoding="utf-8").strip())))
        except Exception:
            return 1

# ========== DESENHO E RENDERING ==========
class Renderer:
    @staticmethod
    def draw_text(surface, text: str, pos: Tuple, font=None, color=Colors.WHITE, center: bool = False):
        if font is None:
            font = Fonts.NORMAL
        img = font.render(text, True, color)
        rect = img.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        surface.blit(img, rect)

    @staticmethod
    def wrapped_text(surface, text: str, rect: pygame.Rect, font=None, color=Colors.WHITE, line_gap: int = 5):
        if font is None:
            font = Fonts.NORMAL
        words = text.split()
        lines, line = [], ""
        
        for word in words:
            test = (line + " " + word).strip()
            if font.size(test)[0] <= rect.width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        
        y = rect.top
        for ln in lines:
            Renderer.draw_text(surface, ln, (rect.left, y), font, color)
            y += font.get_height() + line_gap

    @staticmethod
    def draw_panel(surface, rect: pygame.Rect, alpha: int = 220, border_color: Tuple = (80, 90, 110)):
        p = pygame.Surface(rect.size, pygame.SRCALPHA)
        p.fill((5, 8, 15, alpha))
        surface.blit(p, rect.topleft)
        pygame.draw.rect(surface, border_color, rect, 1)

    @staticmethod
    def draw_vignette(surface, strength: int = 210):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cx, cy = WIDTH // 2, HEIGHT // 2
        for r in range(max(WIDTH, HEIGHT), 40, -32):
            alpha = int(strength * (1 - r / max(WIDTH, HEIGHT)))
            if alpha > 0:
                pygame.draw.ellipse(overlay, (0, 0, 0, alpha), (cx - r, cy - r, r * 2, r * 2), 32)
        surface.blit(overlay, (0, 0))

# ========== ENTIDADES ==========
class Player:
    """Representa o jogador."""
    def __init__(self, x: float, y: float):
        self.pos = pygame.Vector2(x, y)
        self.direction = Direction.RIGHT
        self.is_moving = False
        self.walk_cycle = 0.0
        self.speed = 190
        self.hidden = False
    
    def update(self, dt: float, keys):
        move = pygame.Vector2(0, 0)
        
        if not self.hidden:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                move.x -= 1
                self.direction = Direction.LEFT
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                move.x += 1
                self.direction = Direction.RIGHT
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                move.y -= 1
                self.direction = Direction.UP
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                move.y += 1
                self.direction = Direction.DOWN

            if move.length_squared() > 0:
                move = move.normalize()
                boost = 1.45 if keys[pygame.K_LSHIFT] else 1.0
                self.pos += move * self.speed * boost * dt
                self.is_moving = True
                self.walk_cycle += dt * (10 * boost)
            else:
                self.is_moving = False
                self.walk_cycle = 0

            # Limites da tela
            self.pos.x = max(45, min(WIDTH - 45, self.pos.x))
            self.pos.y = max(160, min(HEIGHT - 65, self.pos.y))
    
    def toggle_hide(self):
        self.hidden = not self.hidden
    
    def draw(self, surface):
        if self.hidden:
            return

        x, y = int(self.pos.x), int(self.pos.y)
        bob = math.sin(self.walk_cycle) * 3 if self.is_moving else 0

        # Sombra
        pygame.draw.ellipse(surface, (0, 0, 0, 160), (x - 18, y + 10, 36, 12))

        # Pernas
        leg = math.cos(self.walk_cycle) * 6 if self.is_moving else 0
        pygame.draw.line(surface, (30, 35, 45), (x - 6, y + 8), (x - 6 + leg, y + 24), 5)
        pygame.draw.line(surface, (30, 35, 45), (x + 6, y + 8), (x + 6 - leg, y + 24), 5)

        # Jaqueta
        pygame.draw.rect(surface, (50, 65, 85), (x - 12, y - 22 + int(bob), 24, 32), border_radius=4)
        pygame.draw.rect(surface, (190, 150, 120), (x - 10, y - 20 + int(bob), 20, 12))

        # Cabeça e Cabelo
        pygame.draw.circle(surface, (220, 185, 155), (x, y - 30 + int(bob)), 10)
        pygame.draw.circle(surface, (40, 30, 25), (x, y - 34 + int(bob)), 10)

        # Olhos
        if self.direction == Direction.RIGHT:
            pygame.draw.circle(surface, Colors.WHITE, (x + 4, y - 30 + int(bob)), 3)
            pygame.draw.circle(surface, Colors.BLACK, (x + 5, y - 30 + int(bob)), 1)
        elif self.direction == Direction.LEFT:
            pygame.draw.circle(surface, Colors.WHITE, (x - 4, y - 30 + int(bob)), 3)
            pygame.draw.circle(surface, Colors.BLACK, (x - 5, y - 30 + int(bob)), 1)

        # Lanterna
        self._draw_flashlight(surface, x, y, int(bob))
    
    def _draw_flashlight(self, surface, x: int, y: int, bob: int):
        light_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        
        angles = {
            Direction.RIGHT: 0,
            Direction.LEFT: 180,
            Direction.DOWN: 90,
            Direction.UP: 270
        }
        angle = angles.get(self.direction, 0)
        rad = math.radians(angle)
        
        p1 = (x, y - 10)
        p2 = (x + math.cos(rad - 0.4) * 220, y - 10 + math.sin(rad - 0.4) * 220)
        p3 = (x + math.cos(rad + 0.4) * 220, y - 10 + math.sin(rad + 0.4) * 220)
        
        pygame.draw.polygon(light_surface, (255, 235, 170, 45), [p1, p2, p3])
        surface.blit(light_surface, (0, 0))

class Stalker:
    """Representa a entidade inimiga."""
    def __init__(self, x: float, y: float):
        self.pos = pygame.Vector2(x, y)
        self.speed = 135
        self.active = False
    
    def update(self, dt: float, player_pos: pygame.Vector2, is_player_hidden: bool, stage_time: float):
        if not self.active or is_player_hidden:
            self.pos.x += math.sin(stage_time * 2.5) * 60 * dt
        else:
            target_dir = player_pos - self.pos
            if target_dir.length_squared() > 0:
                target_dir = target_dir.normalize()
                self.pos += target_dir * self.speed * dt
    
    def is_colliding_with_player(self, player_pos: pygame.Vector2) -> bool:
        return self.pos.distance_to(player_pos) < 32
    
    def draw(self, surface):
        if not self.active:
            return

        sx, sy = int(self.pos.x), int(self.pos.y)
        
        pygame.draw.ellipse(surface, (0, 0, 0, 180), (sx - 22, sy + 15, 44, 14))
        pygame.draw.rect(surface, (10, 12, 18), (sx - 15, sy - 48, 30, 62), border_radius=6)
        pygame.draw.circle(surface, (6, 8, 12), (sx, sy - 58), 14)

        # Olhos que pulsam
        y_head = sy - 58
        pulse = math.sin(pygame.time.get_ticks() / 100) * 30
        eye_color = (min(255, int(220 + pulse)), 30, 30)
        pygame.draw.circle(surface, eye_color, (sx - 5, y_head - 2), 3)
        pygame.draw.circle(surface, eye_color, (sx + 5, y_head - 2), 3)

# ========== DESENHADORES DE CENAS ==========
class SceneDrawer:
    """Classe abstrata para desenhar cenas."""
    
    @staticmethod
    def draw_stage1_main_street(surface):
        """Desenha a rua principal da Fase 1."""
        surface.fill((6, 8, 12))
        
        # Parede de Tijolos
        pygame.draw.rect(surface, (22, 26, 35), (0, 0, WIDTH, 340))
        for y_line in range(0, 340, 20):
            pygame.draw.line(surface, (18, 20, 28), (0, y_line), (WIDTH, y_line), 1)
        
        # Asfalto e Calçada
        pygame.draw.rect(surface, (45, 48, 55), (0, 340, WIDTH, 40))
        pygame.draw.rect(surface, (20, 22, 28), (0, 380, WIDTH, 268))
        
        # Faixa de Pedestre
        for x_faixa in range(100, 900, 120):
            pygame.draw.rect(surface, (80, 85, 95), (x_faixa, 440, 70, 12))
        
        # Bueiro
        pygame.draw.ellipse(surface, (10, 10, 12), (300, 500, 50, 20))
        
        # Postes de Luz
        for post_x in [150, 750]:
            pygame.draw.rect(surface, (70, 75, 85), (post_x, 100, 8, 240))
            pygame.draw.circle(surface, Colors.WARM_LIGHT, (post_x + 4, 100), 12)
            
            # Brilho do poste
            light = pygame.Surface((200, 200), pygame.SRCALPHA)
            pygame.draw.circle(light, (255, 220, 130, 25), (100, 100), 100)
            surface.blit(light, (post_x - 96, 200))
        
        # Entrada do Beco
        pygame.draw.rect(surface, (5, 6, 10), (430, 140, 110, 200))
        Renderer.draw_text(surface, "BECO [E]", (450, 110), Fonts.SMALL, Colors.YELLOW)
    
    @staticmethod
    def draw_stage1_alley(surface):
        """Desenha o beco da Fase 1."""
        surface.fill((6, 8, 12))
        pygame.draw.rect(surface, (12, 14, 18), (80, 80, 992, 500))
        Renderer.draw_text(surface, "SAÍDA DA RUA [S]", (90, 550), Fonts.SMALL, Colors.CYAN)
        
        # Pichação
        Renderer.draw_text(surface, "NÃO HÁ SAÍDA", (250, 150), Fonts.MID, (60, 25, 25))
        
        # Caixotes de Madeira
        pygame.draw.rect(surface, Colors.WOOD_DARK, (700, 230, 80, 70))
        pygame.draw.rect(surface, Colors.WOOD_LIGHT, (700, 230, 80, 70), 2)
        pygame.draw.rect(surface, Colors.WOOD_DARK, (770, 250, 60, 50))
    
    @staticmethod
    def draw_stage2_living_room(surface):
        """Desenha a sala de estar da Fase 2."""
        surface.fill((6, 8, 12))
        
        # Paredes
        pygame.draw.rect(surface, Colors.BLUE_WALL, (0, 0, WIDTH, HEIGHT))
        
        # Piso de Madeira
        for y_wood in range(160, HEIGHT, 40):
            pygame.draw.line(surface, Colors.WOOD_LIGHT, (0, y_wood), (WIDTH, y_wood), 2)
    
    @staticmethod
    def draw_stage3_basement(surface):
        """Desenha o subsolo industrial da Fase 3."""
        surface.fill((6, 8, 12))
        
        # Paredes de Metal
        pygame.draw.rect(surface, Colors.GREY_STEEL, (0, 0, WIDTH, HEIGHT))
        
        # Grade de Ventilação
        for x in range(0, WIDTH, 30):
            pygame.draw.line(surface, (100, 105, 115), (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 30):
            pygame.draw.line(surface, (100, 105, 115), (0, y), (WIDTH, y), 1)
    
    @staticmethod
    def draw_stage4_labyrinth(surface):
        """Desenha o labirinto mental da Fase 4."""
        surface.fill((6, 8, 12))
        
        # Névoa e ambiente onírico
        noise_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(50):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            pygame.draw.circle(noise_surface, (100, 100, 120, 30), (x, y), random.randint(10, 50))
        surface.blit(noise_surface, (0, 0))

# ========== SISTEMA DE INTERAÇÃO ==========
class InteractionSystem:
    """Gerencia interações em cada fase."""
    
    def __init__(self):
        self.zones: List[InteractionZone] = []
    
    def add_zone(self, zone: InteractionZone):
        self.zones.append(zone)
    
    def clear_zones(self):
        self.zones.clear()
    
    def check_interaction(self, x: float, y: float) -> Optional[InteractionZone]:
        for zone in self.zones:
            if zone.contains(x, y):
                return zone
        return None

# ========== JOGO PRINCIPAL ==========
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        
        self.state = GameState.MENU
        self.running = True
        
        # Estado do Jogo
        self.stage = 1
        self.current_room = 0
        self.stage_time = 0.0
        self.tension = 0.0
        
        # Mensagens e Diálogos
        self.message: Optional[Message] = None
        self.dialogue: Optional[Dialogue] = None
        self.objective = ""
        
        # Inventário e Flags
        self.inventory: List[Item] = []
        self.flags: Set[str] = set()
        
        # Entidades
        self.player = Player(120, 480)
        self.stalker = Stalker(-100, -100)
        
        # Sistema de Interação
        self.interaction_system = InteractionSystem()
        
        # PIN (Fase 2)
        self.pin_input = ""
        self.correct_pin = "4821"
        self.entering_pin = False
        
        # Configurações
        self.paused = False
        self.settings = {"volume": 70}
    
    def new_game(self):
        """Inicia um novo jogo."""
        self.stage = 1
        self.setup_stage()
        self.state = GameState.GAME
        SaveManager.save_game(1)
    
    def continue_game(self):
        """Carrega um jogo salvo."""
        self.stage = SaveManager.load_game()
        self.setup_stage()
        self.state = GameState.GAME
    
    def setup_stage(self):
        """Configura uma nova fase."""
        self.stage_time = 0
        self.current_room = 0
        self.tension = 0.1 * self.stage
        self.inventory.clear()
        self.flags.clear()
        self.player = Player(120, 480)
        self.interaction_system.clear_zones()
        
        if self.stage == 1:
            self._setup_stage1()
        elif self.stage == 2:
            self._setup_stage2()
        elif self.stage == 3:
            self._setup_stage3()
        elif self.stage == 4:
            self._setup_stage4()
    
    def _setup_stage1(self):
        """Configura Fase 1 - A Rua Bloqueada."""
        self.show_message("FASE 1 — A RUA BLOQUEADA")
        self.objective = "O portão da rua está trancado. Encontre um Corta-Vergalhão no beco."
        self.say("O caminho principal está bloqueado... Preciso achar uma ferramenta no beco escuro.")
    
    def _setup_stage2(self):
        """Configura Fase 2 - O Apartamento Detalhado."""
        self.show_message("FASE 2 — O APARTAMENTO DETALHADO")
        self.objective = "A porta do quarto exige SENHA. Procure dicas nas salas (Banheiro / Cozinha)."
        self.say("A porta está trancada por uma fechadura digital. Onde deixei a senha?")
    
    def _setup_stage3(self):
        """Configura Fase 3 - Subsolo Industrial."""
        self.show_message("FASE 3 — SUBSOLO INDUSTRIAL")
        self.objective = "Ligue o FUSÍVEL no painel de energia e pegue o CARTÃO para abrir a porta blindada."
        self.say("Ouço passos pesados! Preciso religar a energia e pegar o cartão para escapar.")
        self.stalker = Stalker(950, 400)
        self.stalker.active = True
    
    def _setup_stage4(self):
        """Configura Fase 4 - O Labirinto Mental."""
        self.show_message("FASE 4 — O LABIRINTO MENTAL")
        self.objective = "Colete os 4 FRAGMENTOS DE MEMÓRIA escondidos para abrir a porta da libertação."
        self.say("Este lugar parece um pesadelo sem fim. Preciso achar minhas memórias.")
    
    def show_message(self, text: str, duration: float = 3.5):
        """Exibe uma mensagem de sistema."""
        self.message = Message(text, duration)
    
    def say(self, text: str, duration: float = 4.5):
        """Faz o personagem falar um diálogo."""
        self.dialogue = Dialogue(text, duration)
    
    def add_item(self, item_name: str, description: str = ""):
        """Adiciona um item ao inventário."""
        item = Item(item_name, description)
        if item not in self.inventory:
            self.inventory.append(item)
            return True
        return False
    
    def has_item(self, item_name: str) -> bool:
        """Verifica se tem um item no inventário."""
        return any(item.name == item_name for item in self.inventory)
    
    def complete_stage(self):
        """Completa a fase atual."""
        if self.stage < 4:
            self.stage += 1
            SaveManager.save_game(self.stage)
            self.setup_stage()
        else:
            self.state = GameState.ENDING
    
    def game_over(self):
        """Ativa game over."""
        self.state = GameState.GAME_OVER
    
    def handle_menu(self, event):
        """Processa eventos do menu."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.new_game()
            elif event.key == pygame.K_2:
                self.continue_game()
            elif event.key == pygame.K_3:
                self.state = GameState.SETTINGS
            elif event.key == pygame.K_ESCAPE:
                self.running = False
    
    def handle_settings(self, event):
        """Processa eventos das configurações."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.settings["volume"] = max(0, self.settings["volume"] - 10)
            elif event.key == pygame.K_RIGHT:
                self.settings["volume"] = min(100, self.settings["volume"] + 10)
            elif event.key == pygame.K_ESCAPE:
                self.state = GameState.MENU
    
    def handle_game(self, event):
        """Processa eventos do jogo."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
            elif event.key == pygame.K_e and self.state == GameState.GAME:
                self.interact()
    
    def interact(self):
        """Processa interações do jogador."""
        px, py = self.player.pos.x, self.player.pos.y
        zone = self.interaction_system.check_interaction(px, py)
        
        if zone and zone.callback:
            zone.callback()
    
    def update(self, dt: float):
        """Atualiza o estado do jogo."""
        if self.state != GameState.GAME or self.paused:
            return
        
        self.stage_time += dt
        
        # Atualizar mensagens
        if self.message:
            self.message.timer -= dt
            if self.message.timer <= 0:
                self.message = None
        
        # Atualizar diálogos
        if self.dialogue:
            self.dialogue.timer -= dt
            if self.dialogue.timer <= 0:
                self.dialogue = None
        
        # Atualizar jogador e stalker
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        self.stalker.update(dt, self.player.pos, self.player.hidden, self.stage_time)
        
        # Verificar colisão com stalker
        if self.stalker.active and self.stalker.is_colliding_with_player(self.player.pos):
            self.game_over()
    
    def draw(self):
        """Desenha o jogo."""
        self.screen.fill(Colors.BLACK)
        
        # Desenhar cena apropriada
        if self.stage == 1:
            if self.current_room == 0:
                SceneDrawer.draw_stage1_main_street(self.screen)
            else:
                SceneDrawer.draw_stage1_alley(self.screen)
        elif self.stage == 2:
            SceneDrawer.draw_stage2_living_room(self.screen)
        elif self.stage == 3:
            SceneDrawer.draw_stage3_basement(self.screen)
        elif self.stage == 4:
            SceneDrawer.draw_stage4_labyrinth(self.screen)
        
        # Desenhar entidades
        self.player.draw(self.screen)
        self.stalker.draw(self.screen)
        
        # Desenhar UI
        self._draw_ui()
        
        # Efeito vignette
        Renderer.draw_vignette(self.screen, int(200 - self.tension * 10))
        
        pygame.display.flip()
    
    def _draw_ui(self):
        """Desenha a interface do usuário."""
        # Mensagem de sistema
        if self.message:
            Renderer.draw_text(self.screen, self.message.text, (WIDTH // 2, 30), Fonts.BIG, Colors.YELLOW, center=True)
        
        # Diálogo
        if self.dialogue:
            panel_rect = pygame.Rect(50, HEIGHT - 120, WIDTH - 100, 100)
            Renderer.draw_panel(self.screen, panel_rect)
            Renderer.wrapped_text(self.screen, self.dialogue.text, pygame.Rect(70, HEIGHT - 100, WIDTH - 140, 80), Fonts.NORMAL, Colors.WHITE)
        
        # Objetivo
        Renderer.draw_text(self.screen, f"Objetivo: {self.objective}", (20, HEIGHT - 30), Fonts.SMALL, Colors.CYAN)
        
        # Inventário
        inv_text = " | ".join([str(item) for item in self.inventory]) if self.inventory else "Vazio"
        Renderer.draw_text(self.screen, f"Inventário: {inv_text}", (20, HEIGHT - 50), Fonts.SMALL, Colors.GREEN)
    
    def draw_menu(self):
        """Desenha o menu principal."""
        self.screen.fill(Colors.BLACK)
        Renderer.draw_text(self.screen, "A PORTA", (WIDTH // 2, 80), Fonts.BIG, Colors.RED, center=True)
        Renderer.draw_text(self.screen, "Terror Psicológico", (WIDTH // 2, 150), Fonts.MID, Colors.CYAN, center=True)
        
        Renderer.draw_text(self.screen, "1 - NOVO JOGO", (WIDTH // 2, 250), Fonts.NORMAL, Colors.WHITE, center=True)
        Renderer.draw_text(self.screen, "2 - CONTINUAR", (WIDTH // 2, 300), Fonts.NORMAL, Colors.WHITE, center=True)
        Renderer.draw_text(self.screen, "3 - CONFIGURAÇÕES", (WIDTH // 2, 350), Fonts.NORMAL, Colors.WHITE, center=True)
        Renderer.draw_text(self.screen, "ESC - SAIR", (WIDTH // 2, 400), Fonts.NORMAL, Colors.RED, center=True)
        
        Renderer.draw_vignette(self.screen, 150)
        pygame.display.flip()
    
    def draw_settings(self):
        """Desenha a tela de configurações."""
        self.screen.fill(Colors.BLACK)
        Renderer.draw_text(self.screen, "CONFIGURAÇÕES", (WIDTH // 2, 100), Fonts.BIG, Colors.YELLOW, center=True)
        
        volume = self.settings["volume"]
        Renderer.draw_text(self.screen, f"Volume: {volume}%", (WIDTH // 2, 250), Fonts.MID, Colors.WHITE, center=True)
        Renderer.draw_text(self.screen, "← ESQUERDA | DIREITA →", (WIDTH // 2, 320), Fonts.NORMAL, Colors.CYAN, center=True)
        Renderer.draw_text(self.screen, "ESC - VOLTAR", (WIDTH // 2, 400), Fonts.NORMAL, Colors.RED, center=True)
        
        pygame.display.flip()
    
    def draw_game_over(self):
        """Desenha a tela de game over."""
        self.screen.fill(Colors.BLACK)
        Renderer.draw_text(self.screen, "GAME OVER", (WIDTH // 2, 200), Fonts.BIG, Colors.RED, center=True)
        Renderer.draw_text(self.screen, "Você foi alcançado...", (WIDTH // 2, 300), Fonts.MID, Colors.CYAN, center=True)
        Renderer.draw_text(self.screen, "Pressione ESC para retornar ao menu", (WIDTH // 2, 400), Fonts.NORMAL, Colors.WHITE, center=True)
        
        Renderer.draw_vignette(self.screen, 200)
        pygame.display.flip()
    
    def draw_ending(self):
        """Desenha a tela de finalização."""
        self.screen.fill(Colors.BLACK)
        Renderer.draw_text(self.screen, "VOCÊ ESCAPOU!", (WIDTH // 2, 200), Fonts.BIG, Colors.GREEN, center=True)
        Renderer.draw_text(self.screen, "A PORTA foi deixada para trás...", (WIDTH // 2, 300), Fonts.MID, Colors.CYAN, center=True)
        Renderer.draw_text(self.screen, "Pressione ESC para retornar ao menu", (WIDTH // 2, 400), Fonts.NORMAL, Colors.WHITE, center=True)
        
        pygame.display.flip()
    
    def run(self):
        """Loop principal do jogo."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if self.state == GameState.MENU:
                    self.handle_menu(event)
                elif self.state == GameState.GAME:
                    self.handle_game(event)
                elif self.state == GameState.SETTINGS:
                    self.handle_settings(event)
                elif self.state == GameState.GAME_OVER:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU
                elif self.state == GameState.ENDING:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = GameState.MENU
            
            self.update(dt)
            
            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.GAME:
                self.draw()
            elif self.state == GameState.SETTINGS:
                self.draw_settings()
            elif self.state == GameState.GAME_OVER:
                self.draw_game_over()
            elif self.state == GameState.ENDING:
                self.draw_ending()
        
        pygame.quit()
        sys.exit()

# ========== PONTO DE ENTRADA ==========
if __name__ == "__main__":
    game = Game()
    game.run()
