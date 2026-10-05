import pygame
import sys
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import random
import math
import time

from audio_manager import AudioManager, MusicTransitioner
from save_manager import SaveManager
from graphics_engine import GraphicsEngine, ParticleEffect
from cinematics import CinematicController

# ============================================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================================

pygame.init()

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GRAY = (30, 30, 30)
RED = (200, 50, 50)
YELLOW = (255, 255, 100)
BLUE = (100, 150, 200)
GREEN = (100, 200, 100)
DARK_RED = (100, 20, 20)

# ============================================================================
# ENUMS E ESTRUTURAS
# ============================================================================

class GameState(Enum):
    """Estados do jogo"""
    MENU = 0
    INTRO_CINEMATIC = 1
    EXPLORING = 2
    HIDING = 3
    CHASED = 4
    FOUND_CLUE = 5
    SCARE_CINEMATIC = 6
    FINAL_CHOICE = 7
    ENDING_TELL = 8
    ENDING_SILENT = 9
    PAUSED = 10

@dataclass
class Clue:
    """Estrutura de pistas"""
    id: int
    name: str
    location: Tuple[int, int]
    text: str
    room: str
    importance: int  # 1-5 (quanto maior, mais importante para revelar)
    found: bool = False

# ============================================================================
# PERSONAGENS MELHORADOS
# ============================================================================

class Character(pygame.sprite.Sprite):
    """Classe base para personagens"""
    
    def __init__(self, x: float, y: float, width: int, height: int, color: Tuple[int, int, int]):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.color = color
        
        self.image = pygame.Surface((width, height))
        self.rect = self.image.get_rect()
        self.rect.x = int(x)
        self.rect.y = int(y)
        
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.speed = 0
    
    def update(self):
        """Atualiza posição"""
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

class Clara(Character):
    """Protagonista - Clara"""
    
    def __init__(self, x: int, y: int):
        super().__init__(x, y, 25, 35, YELLOW)
        self.speed = 4.5
        self.fear_level = 0.0
        self.is_hiding = False
        self.hiding_location = None
        self.footstep_timer = 0
    
    def update(self):
        """Atualiza Clara"""
        super().update()
        
        # Aumentar medo gradualmente
        if not self.is_hiding:
            self.fear_level = min(100, self.fear_level + 0.3)
        else:
            self.fear_level = max(0, self.fear_level - 0.5)
        
        # Efeito visual de medo (mudança de cor)
        fear_intensity = self.fear_level / 100
        r = int(255 * (0.5 + fear_intensity * 0.5))
        g = int(255 * (1 - fear_intensity * 0.3))
        b = int(255 * (1 - fear_intensity * 0.5))
        
        self.image.fill((r, g, b))
        
        # Desenhar olhos
        pygame.draw.circle(self.image, WHITE, (8, 12), 2)
        pygame.draw.circle(self.image, WHITE, (17, 12), 2)
        
        # Footstep particles
        self.footstep_timer += 1
        if self.velocity_x != 0 or self.velocity_y != 0:
            if self.footstep_timer > 15:
                self.footstep_timer = 0
    
    def move(self, keys):
        """Controla movimento"""
        self.velocity_x = 0
        self.velocity_y = 0
        
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.velocity_y = -self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.velocity_y = self.speed
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.velocity_x = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity_x = self.speed
    
    def hide(self):
        """Se esconde"""
        self.is_hiding = True
        self.fear_level = max(0, self.fear_level - 30)

class Stepfather(Character):
    """Antagonista - O padrasto"""
    
    def __init__(self, x: int, y: int):
        super().__init__(x, y, 30, 40, RED)
        self.speed = 3.2
        self.is_chasing = False
        self.message_timer = 0
        self.detection_range = 300
        self.last_known_position = None
        self.patrol_target = None
    
    def update(self):
        """Atualiza padrasto"""
        super().update()
        
        if self.message_timer > 0:
            self.message_timer -= 1
        
        # Desenhar corpo
        self.image.fill(self.color)
        
        # Desenhar rosto agressivo
        pygame.draw.circle(self.image, WHITE, (10, 10), 3)
        pygame.draw.circle(self.image, WHITE, (20, 10), 3)
        pygame.draw.rect(self.image, DARK_RED, (8, 15, 14, 10))
    
    def chase(self, clara_pos: Optional[Tuple[int, int]]):
        """Persegue Clara"""
        if clara_pos is None:
            return
        
        dx = clara_pos[0] - self.x
        dy = clara_pos[1] - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > 0:
            self.velocity_x = (dx / distance) * self.speed
            self.velocity_y = (dy / distance) * self.speed
            self.last_known_position = clara_pos

# ============================================================================
# SISTEMA DE CÔMODOS
# ============================================================================

class Room:
    """Representa um cômodo da casa"""
    
    def __init__(self, name: str, x: int, y: int, width: int, height: int, 
                 description: str, connections: Dict[str, str] = None):
        self.name = name
        self.description = description
        self.rect = pygame.Rect(x, y, width, height)
        self.connections = connections or {}
        self.clues: List[Clue] = []
        self.hiding_spots: List[Tuple[int, int]] = []
        self.visited = False
        self.is_dark = False
        self.ambient_light = 1.0
    
    def contains_point(self, x: int, y: int) -> bool:
        """Verifica se ponto está no cômodo"""
        return self.rect.collidepoint(x, y)

# ============================================================================
# JOGO MELHORADO
# ============================================================================

class ClaraGameEnhanced:
    """Versão melhorada do jogo Clara"""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("CLARA - Horror Psicológico")
        self.clock = pygame.time.Clock()
        
        # Sistemas
        self.audio = AudioManager()
        self.music_transitioner = MusicTransitioner(self.audio)
        self.save_manager = SaveManager()
        self.graphics = GraphicsEngine(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.cinematics = CinematicController(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Fontes
        self.font_tiny = pygame.font.Font(None, 16)
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_large = pygame.font.Font(None, 50)
        
        # Estado do jogo
        self.state = GameState.MENU
        self.paused = False
        self.time_played = 0
        
        # Personagens
        self.clara = Clara(100, 100)
        self.stepfather = Stepfather(1000, 600)
        
        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.clara)
        self.all_sprites.add(self.stepfather)
        
        # Cômodos
        self.current_room_name = "quarto"
        self._create_enhanced_rooms()
        self._setup_expanded_clues()
        
        # Lógica de jogo
        self.chase_started = False
        self.chase_timer = 0
        self.clues_collected = 0
        self.clues_found: List[int] = []
        self.dialogue = ""
        self.dialogue_timer = 0
        self.fear_history: List[float] = []
        
        # Mensagens do padrasto
        self.stepfather_messages = [
            "Clara...",
            "Onde você está?",
            "Não precisa ter medo...",
            "Você prometeu não contar...",
            "Venha aqui...",
            "Você sabe que precisa obedecer...",
            "Ninguém vai acreditar em você..."
        ]
        
        # Menu
        self.menu_selection = 0
        self.menu_options = ["Novo Jogo", "Carregar Jogo", "Configurações", "Sair"]
    
    def _create_enhanced_rooms(self):
        """Cria estrutura expandida da casa"""
        self.rooms = {
            "quarto": Room("Seu Quarto", 50, 50, 350, 280,
                          "Seu refúgio... ou era.",
                          {"down": "corredor"}),
            
            "corredor_principal": Room("Corredor Principal", 50, 350, 1200, 150,
                                      "Um caminho que conecta tudo.",
                                      {"up": "quarto", "left": "sala", 
                                       "right": "cozinha", "down": "escada"}),
            
            "sala": Room("Sala de Estar", 50, 520, 380, 300,
                        "Onde tudo parecia normal.",
                        {"right": "corredor_principal"}),
            
            "cozinha": Room("Cozinha", 870, 520, 380, 300,
                           "Onde tudo começou.",
                           {"left": "corredor_principal"}),
            
            "escada": Room("Escada para o 2º Andar", 50, 530, 200, 250,
                          "Suba se ousar.",
                          {"up": "corredor_principal", "down": "sotao"}),
            
            "sotao": Room("Sótão", 700, 50, 400, 280,
                         "O segredo está aqui.",
                         {"up": "escada"}),
        }
        
        # Adicionar spots de esconder
        self.rooms["quarto"].hiding_spots = [
            (150, 150),  # Debaixo da cama
            (300, 220),  # Guarda-roupa
        ]
        self.rooms["sala"].hiding_spots = [
            (120, 620),  # Atrás do sofá
            (350, 700),  # Cortinas
        ]
        self.rooms["cozinha"].hiding_spots = [
            (900, 650),  # Armário
            (1100, 700),  # Embaixo da mesa
        ]
        self.rooms["sotao"].hiding_spots = [
            (800, 150),  # Baú antigo
            (950, 250),  # Espaço entre caixas
        ]
    
    def _setup_expanded_clues(self):
        """Configura sistema expandido de pistas"""
        clues = [
            # Quarto
            Clue(1, "Bilhete Antigo", (150, 100), 
                 "\"Não conte para ninguém.\"\nLetra de criança, mas a caligrafia tremida.", "quarto", 1),
            
            Clue(2, "Desenho Infantil", (200, 150),
                 "Uma criança atrás de uma porta.\nDo outro lado, uma figura sombria.", "quarto", 2),
            
            Clue(3, "Caixa de Segredos", (250, 200),
                 "Dentro: cartas antigas, fotografias com cantos rasgados.", "quarto", 3),
            
            # Cozinha
            Clue(4, "Segundo Bilhete", (950, 580),
                 "\"Ele sabe quando você está sozinha.\"", "cozinha", 1),
            
            Clue(5, "Celular Antigo", (1050, 650),
                 "Mensagens recuperadas:\n\"Você precisa contar.\"\n\"Não foi culpa sua.\"", "cozinha", 4),
            
            # Sala
            Clue(6, "Fotografia Familiar", (120, 600),
                 "Clara, sua mãe... e ele.\nSeu padrasto.\nA data: 8 anos atrás.", "sala", 5),
            
            Clue(7, "Diário Escondido", (300, 700),
                 "Páginas e páginas de medo documentado.\nDatas. Detalhes. Segredos.", "sala", 4),
            
            # Sótão
            Clue(8, "Caixa de Memórias", (800, 150),
                 "Pertences antigos. Roupas de criança.\nUma escova de cabelo. Flores secas.", "sotao", 3),
            
            Clue(9, "Carta Final", (950, 200),
                 "\"Querida Clara, quando você ler isto...\"\nA carta de sua mãe. Inacabada.", "sotao", 5),
        ]
        
        # Distribuir pistas
        for clue in clues:
            self.rooms[clue.room].clues.append(clue)
        
        self.all_clues = clues
    
    def _get_current_room(self) -> Room:
        """Retorna cômodo atual"""
        for room in self.rooms.values():
            if room.contains_point(self.clara.rect.centerx, self.clara.rect.centery):
                return room
        return self.rooms[self.current_room_name]
    
    def _check_collision_with_walls(self):
        """Limita movimento aos cômodos"""
        current_room = self._get_current_room()
        
        if self.clara.rect.left < current_room.rect.left:
            self.clara.rect.left = current_room.rect.left
            self.clara.x = self.clara.rect.x
        if self.clara.rect.right > current_room.rect.right:
            self.clara.rect.right = current_room.rect.right
            self.clara.x = self.clara.rect.x
        if self.clara.rect.top < current_room.rect.top:
            self.clara.rect.top = current_room.rect.top
            self.clara.y = self.clara.rect.y
        if self.clara.rect.bottom > current_room.rect.bottom:
            self.clara.rect.bottom = current_room.rect.bottom
            self.clara.y = self.clara.rect.y
    
    def _check_clue_collision(self):
        """Verifica colisão com pistas"""
        current_room = self._get_current_room()
        
        for clue in current_room.clues:
            if not clue.found:
                dx = self.clara.rect.centerx - clue.location[0]
                dy = self.clara.rect.centery - clue.location[1]
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance < 40:
                    clue.found = True
                    self.clues_found.append(clue.id)
                    self.clues_collected += 1
                    
                    self.state = GameState.FOUND_CLUE
                    self.dialogue = f"{clue.name}\n\n{clue.text}"
                    self.dialogue_timer = 200
                    
                    # Efeito visual
                    self.graphics.particle_system.emit(
                        ParticleEffect.LIGHT_PULSE,
                        clue.location[0], clue.location[1], 10
                    )
                    
                    self.audio.play_sfx("clue_found")
                    break
    
    def _start_chase(self):
        """Inicia perseguição"""
        if not self.chase_started:
            self.chase_started = True
            self.state = GameState.SCARE_CINEMATIC
            self.stepfather.is_chasing = True
            self.stepfather.rect.x = 1100
            self.stepfather.rect.y = 300
            
            self.cinematics.play_scare_cinematic()
            self.audio.play_sfx("scare")
    
    def _check_caught(self) -> bool:
        """Verifica se foi pego"""
        if self.clara.is_hiding:
            return False
        
        distance = math.sqrt(
            (self.clara.rect.centerx - self.stepfather.rect.centerx)**2 +
            (self.clara.rect.centery - self.stepfather.rect.centery)**2
        )
        return distance < 50
    
    def _handle_menu_state(self):
        """Tela de menu"""
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_UP]:
            self.menu_selection = (self.menu_selection - 1) % len(self.menu_options)
        elif keys[pygame.K_DOWN]:
            self.menu_selection = (self.menu_selection + 1) % len(self.menu_options)
        elif keys[pygame.K_RETURN]:
            if self.menu_selection == 0:  # Novo Jogo
                self.state = GameState.INTRO_CINEMATIC
                self.cinematics.play_intro_cinematic()
                self.audio.play_music("intro", fade_in=1000)
            elif self.menu_selection == 3:  # Sair
                return False
        
        return True
    
    def _handle_intro_cinematic_state(self):
        """Cinemática de introdução"""
        self.cinematics.update()
        
        if self.cinematics.playing:
            return
        
        # Transição para exploração
        self.state = GameState.EXPLORING
        self.audio.play_music("exploring", loops=-1, fade_in=500)
        self.dialogue = "Relógio: 03:17 | Procure pelas pistas..."
        self.dialogue_timer = 120
    
    def _handle_exploring_state(self):
        """Estado de exploração"""
        keys = pygame.key.get_pressed()
        self.clara.move(keys)
        
        # Mecânica de perseguição
        if self.clues_collected >= 2 and not self.chase_started:
            self._start_chase()
        
        self._check_collision_with_walls()
        self._check_clue_collision()
        
        # Checar esconderijos
        hiding_nearby = False
        for spot in self._get_current_room().hiding_spots:
            dx = self.clara.rect.centerx - spot[0]
            dy = self.clara.rect.centery - spot[1]
            distance = math.sqrt(dx**2 + dy**2)
            if distance < 40:
                hiding_nearby = True
                self.dialogue = "ESPAÇO: Se esconder"
                if keys[pygame.K_SPACE]:
                    self.clara.hide()
                    self.state = GameState.HIDING
                    self.dialogue = "Você está escondida. ESPAÇO para sair."
                    self.dialogue_timer = 200
                break
        
        if not hiding_nearby:
            self.dialogue = ""
        
        # Atualizar música
        self.music_transitioner.update_tension(self.clara.fear_level)
    
    def _handle_hiding_state(self):
        """Estado escondido"""
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_SPACE]:
            self.clara.is_hiding = False
            self.state = GameState.EXPLORING
    
    def _handle_chased_state(self):
        """Estado de perseguição"""
        keys = pygame.key.get_pressed()
        self.clara.move(keys)
        
        # Perseguir
        if not self.clara.is_hiding:
            self.stepfather.chase((self.clara.rect.centerx, self.clara.rect.centery))
        else:
            self.stepfather.chase(None)
        
        self.chase_timer += 1
        
        # Mensagens ocasionais
        if self.chase_timer % 120 == 0 and self.chase_timer > 0:
            self.dialogue = random.choice(self.stepfather_messages)
            self.dialogue_timer = 80
            self.audio.play_sfx("scare")
        
        # Verificar se foi pego
        if self._check_caught():
            self.state = GameState.FINAL_CHOICE
            self.stepfather.velocity_x = 0
            self.stepfather.velocity_y = 0
            self.dialogue = ""
        
        self._check_collision_with_walls()
        self.graphics.particle_system.emit(ParticleEffect.FEAR_AURA,
                                          self.clara.x, self.clara.y, 3)
    
    def _handle_scare_cinematic_state(self):
        """Cinemática de susto"""
        self.cinematics.update()
        
        if not self.cinematics.playing:
            self.state = GameState.CHASED
            self.dialogue = "CORRA!"
            self.dialogue_timer = 80
    
    def _handle_found_clue_state(self):
        """Estado de encontrar pista"""
        if self.dialogue_timer <= 0:
            self.state = GameState.EXPLORING
    
    def _handle_final_choice_state(self):
        """Tela de escolha final"""
        keys = pygame.key.get_pressed()
        
        self.dialogue = "Você conseguiu escapar...\n\nE agora?\nE: CONTAR | S: SILÊNCIO"
        
        if keys[pygame.K_e]:
            self.state = GameState.ENDING_TELL
            self.dialogue_timer = 300
            self.audio.stop_music(fade_out=1000)
        elif keys[pygame.K_s]:
            self.state = GameState.ENDING_SILENT
            self.dialogue_timer = 300
            self.audio.stop_music(fade_out=1000)
    
    def _handle_ending_tell(self):
        """Final: Clara conta"""
        if self.dialogue_timer > 200:
            self.dialogue = "Clara procura ajuda..."
            self.graphics.particle_system.emit(ParticleEffect.LIGHT_PULSE,
                                              self.clara.x, self.clara.y, 5)
        elif self.dialogue_timer > 100:
            self.dialogue = "Ela finalmente revela o segredo."
        else:
            self.dialogue = "\"Alguns segredos não protegem ninguém.\nEles protegem quem está fazendo mal.\"\n\nPressione ESC para sair"
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            return False
        return True
    
    def _handle_ending_silent(self):
        """Final: Clara fica em silêncio"""
        if self.dialogue_timer > 200:
            self.dialogue = "Clara volta para seu quarto."
            self.graphics.particle_system.emit(ParticleEffect.DUST,
                                              self.clara.x, self.clara.y, 3)
        elif self.dialogue_timer > 100:
            self.dialogue = "O silêncio continua..."
        else:
            self.dialogue = "Nada muda.\nPressione ESC para sair"
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            return False
        return True
    
    def _draw_menu(self):
        """Desenha menu principal"""
        title = self.font_large.render("CLARA", True, RED)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        
        subtitle = self.font_small.render("Um Jogo de Horror Psicológico", True, WHITE)
        self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 180))
        
        for i, option in enumerate(self.menu_options):
            color = YELLOW if i == self.menu_selection else WHITE
            text = self.font_medium.render(option, True, color)
            y = 350 + i * 80
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
    
    def _draw_hud(self):
        """Desenha interface"""
        # Medo
        medo_text = self.font_small.render(f"Medo: {int(self.clara.fear_level)}%", True, RED)
        self.screen.blit(medo_text, (10, 10))
        
        # Pistas
        pistas_text = self.font_small.render(f"Pistas: {self.clues_collected}/{len(self.all_clues)}", 
                                             True, YELLOW)
        self.screen.blit(pistas_text, (10, 35))
        
        # Cômodo
        room_text = self.font_small.render(f"Local: {self._get_current_room().name}", True, BLUE)
        self.screen.blit(room_text, (10, 60))
        
        # Tempo
        minutes = self.time_played // 3600
        seconds = (self.time_played // 60) % 60
        time_text = self.font_tiny.render(f"Tempo: {minutes:02d}:{seconds:02d}", True, BLUE)
        self.screen.blit(time_text, (10, 85))
        
        # Diálogo
        if self.dialogue:
            lines = self.dialogue.split('\n')
            for i, line in enumerate(lines):
                dialogue_text = self.font_small.render(line, True, WHITE)
                self.screen.blit(dialogue_text, (20, SCREEN_HEIGHT - 150 + i * 25))
        
        # Controles (canto superior direito)
        controls = ["WASD: Mover", "ESPAÇO: Interagir", "P: Pausar", "ESC: Menu"]
        for i, ctrl in enumerate(controls):
            ctrl_text = self.font_tiny.render(ctrl, True, BLUE)
            self.screen.blit(ctrl_text, (SCREEN_WIDTH - 180, 10 + i * 20))
    
    def _draw_rooms(self):
        """Desenha cômodos"""
        for room in self.rooms.values():
            is_current = room.contains_point(self.clara.rect.centerx, self.clara.rect.centery)
            
            self.graphics.draw_room_enhanced(self.screen, room.rect, room.name, 
                                            room.is_dark)
            
            # Desenhar pistas
            for clue in room.clues:
                self.graphics.draw_clue_indicator(self.screen, clue.location[0],
                                                 clue.location[1], clue.found)
            
            # Desenhar esconderijos
            for spot in room.hiding_spots:
                nearby = math.sqrt((self.clara.rect.centerx - spot[0])**2 +
                                  (self.clara.rect.centery - spot[1])**2) < 60
                self.graphics.draw_hiding_spot(self.screen, spot[0], spot[1], nearby)
    
    def _draw_game(self):
        """Desenha cena de jogo"""
        self._draw_rooms()
        self.all_sprites.draw(self.screen)
        self.graphics.particle_system.draw(self.screen)
        
        # Efeito de vignette quanto mais medo
        vignette_intensity = self.clara.fear_level / 200
        if vignette_intensity > 0:
            self.graphics.draw_vignette(self.screen, vignette_intensity)
        
        self._draw_hud()
    
    def run(self):
        """Loop principal"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state in [GameState.ENDING_TELL, GameState.ENDING_SILENT]:
                            self.state = GameState.MENU
                            self.cinematics.current_cinematic = None
                            self.__init__()
                        elif self.state != GameState.MENU:
                            self.state = GameState.PAUSED
                    elif event.key == pygame.K_p:
                        if self.state != GameState.MENU:
                            self.paused = not self.paused
            
            # Atualizar lógica
            if not self.paused and self.state != GameState.MENU:
                self.time_played += 1
                self.graphics.particle_system.update()
                self.cinematics.update()
                
                if self.dialogue_timer > 0:
                    self.dialogue_timer -= 1
            
            keys = pygame.key.get_pressed()
            
            # Máquina de estados
            if self.state == GameState.MENU:
                if not self._handle_menu_state():
                    running = False
            elif self.state == GameState.INTRO_CINEMATIC:
                self._handle_intro_cinematic_state()
            elif self.state == GameState.EXPLORING:
                self._handle_exploring_state()
            elif self.state == GameState.HIDING:
                self._handle_hiding_state()
            elif self.state == GameState.CHASED:
                self._handle_chased_state()
            elif self.state == GameState.SCARE_CINEMATIC:
                self._handle_scare_cinematic_state()
            elif self.state == GameState.FOUND_CLUE:
                self._handle_found_clue_state()
            elif self.state == GameState.FINAL_CHOICE:
                self._handle_final_choice_state()
            elif self.state == GameState.ENDING_TELL:
                if not self._handle_ending_tell():
                    self.state = GameState.MENU
            elif self.state == GameState.ENDING_SILENT:
                if not self._handle_ending_silent():
                    self.state = GameState.MENU
            
            # Atualizar sprites
            self.all_sprites.update()
            
            # Renderizar
            self.screen.fill(BLACK)
            
            if self.state == GameState.MENU:
                self._draw_menu()
            elif self.state in [GameState.ENDING_TELL, GameState.ENDING_SILENT]:
                self._draw_game()
            elif self.state not in [GameState.INTRO_CINEMATIC]:
                self._draw_game()
            
            # Desenhar cinemáticas
            self.cinematics.draw(self.screen)
            
            # Fade
            self.graphics.update_fade()
            self.graphics.draw_fade(self.screen)
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

# ============================================================================
# EXECUTAR
# ============================================================================

if __name__ == "__main__":
    game = ClaraGameEnhanced()
    game.run()
