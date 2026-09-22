import math
import random
import sys
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Este jogo precisa do Pygame.")
    print("Instale com: pip install pygame")
    sys.exit(1)

pygame.init()
pygame.mixer.init()

# ---------- Configurações Gerais ----------
WIDTH, HEIGHT = 1152, 648
FPS = 60
TITLE = "A PORTA — Terror Psicológico (Edição Gráfica HD)"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# ---------- Paleta de Cores Avançada ----------
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

# ---------- Fontes ----------
FONT = pygame.font.SysFont("consolas", 19)
SMALL = pygame.font.SysFont("consolas", 14)
BIG = pygame.font.SysFont("consolas", 48, bold=True)
MID = pygame.font.SysFont("consolas", 24, bold=True)

SAVE_FILE = Path("savegame.txt")


def save_game(stage):
    try:
        SAVE_FILE.write_text(str(stage), encoding="utf-8")
    except OSError:
        pass


def load_game():
    try:
        return max(1, min(4, int(SAVE_FILE.read_text(encoding="utf-8").strip())))
    except Exception:
        return 1


def draw_text(surface, text, pos, font=FONT, color=WHITE, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(img, rect)


def wrapped(surface, text, rect, font=FONT, color=WHITE, line_gap=5):
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
        draw_text(surface, ln, (rect.left, y), font, color)
        y += font.get_height() + line_gap


def panel(surface, rect, alpha=220, border_color=(80, 90, 110)):
    p = pygame.Surface(rect.size, pygame.SRCALPHA)
    p.fill((5, 8, 15, alpha))
    surface.blit(p, rect.topleft)
    pygame.draw.rect(surface, border_color, rect, 1)


def vignette(surface, strength=210):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cx, cy = WIDTH // 2, HEIGHT // 2
    for r in range(max(WIDTH, HEIGHT), 40, -32):
        alpha = int(strength * (1 - r / max(WIDTH, HEIGHT)))
        if alpha > 0:
            pygame.draw.ellipse(overlay, (0, 0, 0, alpha), (cx - r, cy - r, r * 2, r * 2), 32)
    surface.blit(overlay, (0, 0))


class Game:
    def __init__(self):
        self.running = True
        self.state = "menu"
        self.stage = 1
        self.current_room = 0
        self.stage_time = 0.0
        self.tension = 0.0

        self.message = ""
        self.message_timer = 0
        self.dialogue = None
        self.dialogue_timer = 0
        self.objective = ""

        self.inventory = []
        self.flags = set()

        self.player = pygame.Vector2(120, 480)
        self.player_dir = "RIGHT"
        self.walk_cycle = 0.0
        self.is_moving = False
        self.speed = 190
        self.hidden = False

        self.stalker_pos = pygame.Vector2(-100, -100)
        self.stalker_active = False
        self.stalker_speed = 135

        self.pin_input = ""
        self.correct_pin = "4821"
        self.entering_pin = False

        self.paused = False
        self.settings = {"volume": 70}

    def new_game(self):
        self.stage = 1
        self.setup_stage()
        self.state = "game"
        save_game(1)

    def continue_game(self):
        self.stage = load_game()
        self.setup_stage()
        self.state = "game"

    def setup_stage(self):
        self.stage_time = 0
        self.current_room = 0
        self.tension = 0.1 * self.stage
        self.inventory.clear()
        self.flags.clear()
        self.player = pygame.Vector2(120, 480)
        self.player_dir = "RIGHT"
        self.hidden = False
        self.stalker_active = False
        self.entering_pin = False
        self.pin_input = ""

        if self.stage == 1:
            self.message = "FASE 1 — A RUA BLOQUEADA"
            self.objective = "O portão da rua está trancado. Encontre um Corta-Vergalhão no beco."
            self.say("O caminho principal está bloqueado... Preciso achar uma ferramenta no beco escuro.")
        elif self.stage == 2:
            self.message = "FASE 2 — O APARTAMENTO DETALHADO"
            self.objective = "A porta do quarto exige SENHA. Procure dicas nas salas (Banheiro / Cozinha)."
            self.say("A porta está trancada por uma fechadura digital. Onde deixei a senha?")
        elif self.stage == 3:
            self.message = "FASE 3 — SUBSOLO INDUSTRIAL"
            self.objective = "Ligue o FUSÍVEL no painel de energia e pegue o CARTÃO para abrir a porta blindada."
            self.say("Ouço passos pesados! Preciso religar a energia e pegar o cartão para escapar.")
            self.stalker_pos = pygame.Vector2(950, 400)
            self.stalker_active = True
        elif self.stage == 4:
            self.message = "FASE 4 — O LABIRINTO MENTAL"
            self.objective = "Colete os 4 FRAGMENTOS DE MEMÓRIA escondidos para abrir a porta da libertação."
            self.say("Este lugar parece um pesadelo sem fim. Preciso achar minhas memórias.")

        self.message_timer = 3.5

    def say(self, text, seconds=4.5):
        self.dialogue = text
        self.dialogue_timer = seconds

    def complete_stage(self):
        if self.stage < 4:
            self.stage += 1
            save_game(self.stage)
            self.setup_stage()
        else:
            self.state = "ending"

    def game_over(self):
        self.state = "game_over"

    def handle_menu(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.new_game()
            elif event.key == pygame.K_2:
                self.continue_game()
            elif event.key == pygame.K_3:
                self.state = "settings"
            elif event.key == pygame.K_ESCAPE:
                self.running = False

    def handle_settings(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.settings["volume"] = max(0, self.settings["volume"] - 10)
            elif event.key == pygame.K_RIGHT:
                self.settings["volume"] = min(100, self.settings["volume"] + 10)
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"

    def update(self, dt):
        if self.state != "game" or self.paused or self.entering_pin:
            return

        self.stage_time += dt
        self.message_timer = max(0, self.message_timer - dt)
        self.dialogue_timer = max(0, self.dialogue_timer - dt)

        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)

        if not self.hidden:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                move.x -= 1
                self.player_dir = "LEFT"
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                move.x += 1
                self.player_dir = "RIGHT"
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                move.y -= 1
                self.player_dir = "UP"
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                move.y += 1
                self.player_dir = "DOWN"

            if move.length_squared() > 0:
                move = move.normalize()
                boost = 1.45 if keys[pygame.K_LSHIFT] else 1.0
                self.player += move * self.speed * boost * dt
                self.is_moving = True
                self.walk_cycle += dt * (10 * boost)
            else:
                self.is_moving = False
                self.walk_cycle = 0

            self.player.x = max(45, min(WIDTH - 45, self.player.x))
            self.player.y = max(160, min(HEIGHT - 65, self.player.y))

        if self.stage == 3 and self.stalker_active:
            if not self.hidden:
                target = pygame.Vector2(self.player.x, self.player.y)
                dir_vector = target - self.stalker_pos
                if dir_vector.length_squared() > 0:
                    dir_vector = dir_vector.normalize()
                    self.stalker_pos += dir_vector * self.stalker_speed * dt

                if self.stalker_pos.distance_to(self.player) < 32:
                    self.game_over()
            else:
                self.stalker_pos.x += math.sin(self.stage_time * 2.5) * 60 * dt

    def interact(self):
        x, y = self.player.x, self.player.y

        # ---------- FASE 1 ----------
        if self.stage == 1:
            if self.current_room == 0:
                if 420 < x < 540 and y < 220:
                    self.current_room = 1
                    self.player = pygame.Vector2(550, 520)
                    self.say("Você entrou em um beco escuro e úmido entre os prédios.")
                elif x > 930 and y > 380:
                    if "Corta-Vergalhão" in self.inventory:
                        self.say("Você cortou as correntes e abriu o portão!")
                        self.complete_stage()
                    else:
                        self.say("O portão está trancado com uma corrente grossa. Preciso do Corta-Vergalhão!")

            elif self.current_room == 1:
                if x < 150 and y > 480:
                    self.current_room = 0
                    self.player = pygame.Vector2(480, 260)
                elif 700 < x < 850 and y < 320 and "Corta-Vergalhão" not in self.inventory:
                    self.inventory.append("Corta-Vergalhão")
                    self.say("Você achou o CORTA-VERGALHÃO caído entre as caixas de madeira!")
                    self.objective = "Volte para a rua principal e use o Corta-Vergalhão no portão."

        # ---------- FASE 2 ----------
        elif self.stage == 2:
            if self.current_room == 0:  # Sala de Estar
                if 100 < x < 220 and y < 250:
                    self.current_room = 1  # Banheiro
                    self.player = pygame.Vector2(550, 520)
                elif 780 < x < 900 and y < 250:
                    self.current_room = 2  # Cozinha
                    self.player = pygame.Vector2(150, 520)
                elif 450 < x < 600 and y < 250:
                    self.entering_pin = True

            elif self.current_room == 1:  # Banheiro
                if y > 530:
                    self.current_room = 0
                    self.player = pygame.Vector2(160, 280)
                elif 450 < x < 600 and y < 280 and "Bilhete 1" not in self.flags:
                    self.flags.add("Bilhete 1")
                    self.say("No espelho do banheiro há escrito em batom vermelho: 'Primeiros dígitos: 4 8'")

            elif self.current_room == 2:  # Cozinha
                if x < 120:
                    self.current_room = 0
                    self.player = pygame.Vector2(840, 280)
                elif 650 < x < 820 and y < 280 and "Bilhete 2" not in self.flags:
                    self.flags.add("Bilhete 2")
                    self.say("Um bilhete preso na geladeira diz: 'Últimos dígitos: 2 1'")

        # ---------- FASE 3 ----------
        elif self.stage == 3:
            if self.current_room == 0:
                if 140 < x < 280 and y > 380:
                    self.hidden = not self.hidden
                    if self.hidden:
                        self.say("Você se escondeu no armário metálico! Aguarde o perigo passar.")
                    else:
                        self.say("Você saiu do armário.")
                elif 780 < x < 890 and y < 250:
                    self.current_room = 1
                    self.player = pygame.Vector2(200, 480)
                elif x > 930 and y > 380:
                    if "Energia Ligada" in self.flags and "Cartão de Acesso" in self.inventory:
                        self.say("Cartão aceito! A porta blindada se destrancou!")
                        self.complete_stage()
                    elif "Energia Ligada" not in self.flags:
                        self.say("O painel da porta está apagado. Falta energia no subsolo!")
                    else:
                        self.say("A energia voltou, mas a porta exige o CARTÃO DE ACESSO!")

            elif self.current_room == 1:
                if x < 120:
                    self.current_room = 0
                    self.player = pygame.Vector2(830, 280)
                elif 280 < x < 440 and y < 280 and "Fusível" not in self.inventory:
                    self.inventory.append("Fusível")
                    self.say("Você pegou o FUSÍVEL INDUSTRIAL em cima da bancada de trabalho!")
                elif 700 < x < 850 and y < 280:
                    if "Fusível" in self.inventory and "Energia Ligada" not in self.flags:
                        self.flags.add("Energia Ligada")
                        self.say("Você instalou o fusível e puxou a alavanca! A luz voltou ao subsolo!")
                        if "Cartão de Acesso" not in self.inventory:
                            self.inventory.append("Cartão de Acesso")
                            self.say("GAVETA AUTOMÁTICA ABRIU! Você obteve o CARTÃO DE ACESSO!")

        # ---------- FASE 4 ----------
        elif self.stage == 4:
            zones = [
                (pygame.Rect(80, 160, 180, 140), "Espelho Quebrado", "Fragmento 1: Encarar a realidade sem distorções."),
                (pygame.Rect(380, 150, 180, 150), "Diário Antigo", "Fragmento 2: Palavras gravadas que nunca foram ouvidas."),
                (pygame.Rect(700, 150, 180, 150), "Chave de Fenda", "Fragmento 3: A ferramenta do próprio destino."),
                (pygame.Rect(440, 390, 260, 150), "Luz da Verdade", "Fragmento 4: O medo perde o poder na luz."),
            ]
            for rect, item, text in zones:
                if rect.collidepoint(x, y) and item not in self.inventory:
                    self.inventory.append(item)
                    self.say(text)
                    self.objective = f"Fragmentos coletados: {len(self.inventory)}/4"
            if len(self.inventory) >= 4 and x > 930 and y > 380:
                self.complete_stage()

    def draw_player(self):
        if self.hidden:
            return

        x, y = int(self.player.x), int(self.player.y)
        bob = math.sin(self.walk_cycle) * 3 if self.is_moving else 0

        # Sombra
        pygame.draw.ellipse(screen, (0, 0, 0, 160), (x - 18, y + 10, 36, 12))

        # Pernas
        leg = math.cos(self.walk_cycle) * 6 if self.is_moving else 0
        pygame.draw.line(screen, (30, 35, 45), (x - 6, y + 8), (x - 6 + leg, y + 24), 5)
        pygame.draw.line(screen, (30, 35, 45), (x + 6, y + 8), (x + 6 - leg, y + 24), 5)

        # Jaqueta
        pygame.draw.rect(screen, (50, 65, 85), (x - 12, y - 22 + int(bob), 24, 32), border_radius=4)
        pygame.draw.rect(screen, (190, 150, 120), (x - 10, y - 20 + int(bob), 20, 12))  # Camisa interna

        # Cabeça e Cabelo
        pygame.draw.circle(screen, (220, 185, 155), (x, y - 30 + int(bob)), 10)
        pygame.draw.circle(screen, (40, 30, 25), (x, y - 34 + int(bob)), 10)  # Cabelo

        # Olhos
        if self.player_dir == "RIGHT":
            pygame.draw.circle(screen, WHITE, (x + 4, y - 30 + int(bob)), 3)
            pygame.draw.circle(screen, BLACK, (x + 5, y - 30 + int(bob)), 1)
        elif self.player_dir == "LEFT":
            pygame.draw.circle(screen, WHITE, (x - 4, y - 30 + int(bob)), 3)
            pygame.draw.circle(screen, BLACK, (x - 5, y - 30 + int(bob)), 1)

        # Lanterna
        light_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        angle = 0 if self.player_dir == "RIGHT" else 180 if self.player_dir == "LEFT" else 90 if self.player_dir == "DOWN" else 270
        rad = math.radians(angle)
        p1 = (x, y - 10)
        p2 = (x + math.cos(rad - 0.4) * 220, y - 10 + math.sin(rad - 0.4) * 220)
        p3 = (x + math.cos(rad + 0.4) * 220, y - 10 + math.sin(rad + 0.4) * 220)
        pygame.draw.polygon(light_surface, (255, 235, 170, 45), [p1, p2, p3])
        screen.blit(light_surface, (0, 0))

    def draw_stalker(self):
        if not self.stalker_active or self.current_room != 0:
            return

        sx, sy = int(self.stalker_pos.x), int(self.stalker_pos.y)
        pygame.draw.ellipse(screen, (0, 0, 0, 180), (sx - 22, sy + 15, 44, 14))
        pygame.draw.rect(screen, (10, 12, 18), (sx - 15, sy - 48, 30, 62), border_radius=6)
        pygame.draw.circle(screen, (6, 8, 12), (sx, y_head := sy - 58), 14)

        pulse = math.sin(self.stage_time * 9) * 30
        eye_color = (min(255, int(220 + pulse)), 30, 30)
        pygame.draw.circle(screen, eye_color, (sx - 5, y_head - 2), 3)
        pygame.draw.circle(screen, eye_color, (sx + 5, y_head - 2), 3)

    # ==========================================
    # DETALHAMENTO DOS CENÁRIOS E MÓVEIS
    # ==========================================

    def draw_stage1(self):
        screen.fill((6, 8, 12))

        if self.current_room == 0:  # Rua Principal
            # Parede de Tijolos dos Prédios
            pygame.draw.rect(screen, (22, 26, 35), (0, 0, WIDTH, 340))
            for y_line in range(0, 340, 20):
                pygame.draw.line(screen, (18, 20, 28), (0, y_line), (WIDTH, y_line), 1)

            # Asfalto e Calçada
            pygame.draw.rect(screen, (45, 48, 55), (0, 340, WIDTH, 40))  # Calçada
            pygame.draw.rect(screen, (20, 22, 28), (0, 380, WIDTH, 268))  # Asfalto

            # Faixa de Pedestre e Bueiro
            for x_fainxa in range(100, 900, 120):
                pygame.draw.rect(screen, (80, 85, 95), (x_fainxa, 440, 70, 12))
            pygame.draw.ellipse(screen, (10, 10, 12), (300, 500, 50, 20))

            # Postes de Luz Iluminando a Rua
            for post_x in [150, 750]:
                pygame.draw.rect(screen, (70, 75, 85), (post_x, 100, 8, 240))
                pygame.draw.circle(screen, WARM_LIGHT, (post_x + 4, 100), 12)
                # Brilho do Poste
                light = pygame.Surface((200, 200), pygame.SRCALPHA)
                pygame.draw.circle(light, (255, 220, 130, 25), (100, 100), 100)
                screen.blit(light, (post_x - 96, 200))

            # Entrada do Beco
            pygame.draw.rect(screen, (5, 6, 10), (430, 140, 110, 200))
            draw_text(screen, "BECO [E]", (450, 110), SMALL, YELLOW)

            # Portão de Ferro Trancado
            pygame.draw.rect(screen, (35, 38, 45), (960, 320, 90, 160))
            for xb in range(965, 1050, 12):
                pygame.draw.line(screen, (110, 115, 125), (xb, 320), (xb, 480), 3)
            # Corrente no Portão
            chain_color = RED if "Corta-Vergalhão" not in self.inventory else GREEN
            pygame.draw.circle(screen, chain_color, (1005, 400), 12, 4)
            draw_text(screen, "PORTÃO CORTADO" if "Corta-Vergalhão" in self.inventory else "PORTÃO TRANCADO", (920, 290), SMALL, chain_color)

        elif self.current_room == 1:  # Beco Escuro
            pygame.draw.rect(screen, (12, 14, 18), (80, 80, 992, 500))
            draw_text(screen, "SAÍDA DA RUA [S]", (90, 550), SMALL, CYAN)

            # Pichação e Tijolos no Beco
            draw_text(screen, "NÃO HÁ SAÍDA", (250, 150), MID, (60, 25, 25))

            # Caixotes de Madeira e Lixeira metálica
            pygame.draw.rect(screen, WOOD_DARK, (700, 230, 80, 70))
            pygame.draw.rect(screen, WOOD_LIGHT, (700, 230, 80, 70), 2)
            pygame.draw.rect(screen, WOOD_DARK, (770, 250, 60, 50))

            if "Corta-Vergalhão" not in self.inventory:
                pygame.draw.rect(screen, RED, (720, 210, 35, 16), border_radius=3)
                draw_text(screen, "[E] CORTA-VERGALHÃO", (680, 185), SMALL, YELLOW)

        self.draw_player()

    def draw_stage2(self):
        screen.fill((10, 12, 16))

        if self.current_room == 0:  # Sala de Estar Realista
            # Piso de Madeira
            pygame.draw.rect(screen, BLUE_WALL, (50, 80, 1052, 220))  # Parede
            pygame.draw.rect(screen, WOOD_DARK, (50, 300, 1052, 300))  # Piso

            # Linhas do Piso de Madeira
            for y_wood in range(300, 600, 25):
                pygame.draw.line(screen, (45, 30, 20), (50, y_wood), (1102, y_wood), 1)

            # Sofá Retrô
            pygame.draw.rect(screen, (100, 45, 40), (280, 340, 220, 80), border_radius=8)  # Encosto
            pygame.draw.rect(screen, (120, 55, 50), (270, 380, 240, 50), border_radius=6)  # Assento
            pygame.draw.rect(screen, (80, 35, 30), (260, 370, 20, 60))  # Braço
            pygame.draw.rect(screen, (80, 35, 30), (500, 370, 20, 60))

            # Estante de Livros e TV Antiga
            pygame.draw.rect(screen, WOOD_LIGHT, (620, 220, 140, 180))
            pygame.draw.rect(screen, (20, 20, 25), (640, 240, 100, 70), border_radius=4)  # TV
            pygame.draw.rect(screen, CYAN, (650, 250, 80, 50))  # Estática da Tela
            # Livros nas Prateleiras
            colors_books = [RED, GREEN, YELLOW, CYAN]
            for i, col in enumerate(colors_books):
                pygame.draw.rect(screen, col, (635 + (i * 12), 330, 10, 35))

            # Tapete Central
            pygame.draw.ellipse(screen, (140, 110, 80), (320, 460, 400, 100))

            # Portas da Sala
            pygame.draw.rect(screen, WOOD_LIGHT, (120, 130, 90, 170), border_radius=4)
            draw_text(screen, "BANHEIRO", (125, 100), SMALL, CYAN)

            pygame.draw.rect(screen, WOOD_LIGHT, (800, 130, 90, 170), border_radius=4)
            draw_text(screen, "COZINHA", (810, 100), SMALL, CYAN)

            # Porta Principal do Quarto (Com Teclado)
            pygame.draw.rect(screen, (30, 15, 15), (460, 130, 110, 170), border_radius=4)
            pygame.draw.rect(screen, RED if "Senha" not in self.flags else GREEN, (510, 180, 16, 25))
            draw_text(screen, "QUARTO (SENHA)", (445, 100), SMALL, RED)

        elif self.current_room == 1:  # Banheiro Realista
            # Paredes de Azulejo
            pygame.draw.rect(screen, TILE_BLUE, (80, 80, 992, 240))
            pygame.draw.rect(screen, TILE_WHITE, (80, 320, 992, 260))

            # Linhas de Azulejo
            for x_tile in range(80, 1072, 35):
                pygame.draw.line(screen, (60, 80, 100), (x_tile, 80), (x_tile, 320), 1)

            # Espelho Ilustrado com Luz Integrada
            pygame.draw.rect(screen, MARBLE, (470, 120, 140, 110), border_radius=6)
            pygame.draw.rect(screen, (180, 220, 240), (480, 130, 120, 90))
            draw_text(screen, "ESPELHO [E]", (490, 95), SMALL, YELLOW)

            # Pia / Lavatório
            pygame.draw.rect(screen, WHITE, (460, 230, 160, 60), border_radius=8)
            pygame.draw.rect(screen, GREY_STEEL, (530, 205, 20, 25))  # Torneira

            # Vaso Sanitário
            pygame.draw.rect(screen, WHITE, (200, 240, 70, 80), border_radius=10)
            pygame.draw.rect(screen, WHITE, (190, 190, 90, 60), border_radius=4)  # Caixa d'água

            # Box do Chuveiro (Vidro)
            glass = pygame.Surface((180, 260), pygame.SRCALPHA)
            glass.fill((150, 210, 230, 60))
            screen.blit(glass, (800, 100))
            pygame.draw.rect(screen, GREY_STEEL, (800, 100, 180, 260), 3)

            draw_text(screen, "VOLTAR [S]", (530, 550), SMALL, CYAN)

        elif self.current_room == 2:  # Cozinha Completa e Detalhada
            # Paredes e Piso Xadrez
            pygame.draw.rect(screen, (40, 48, 58), (80, 80, 992, 220))  # Parede Superior

            # Piso Xadrez
            for x_q in range(80, 1072, 50):
                for y_q in range(300, 580, 50):
                    col = (210, 215, 220) if (x_q // 50 + y_q // 50) % 2 == 0 else (40, 45, 55)
                    pygame.draw.rect(screen, col, (x_q, y_q, 50, 50))

            # Armários Suspensos e Micro-ondas
            pygame.draw.rect(screen, WOOD_DARK, (200, 100, 400, 80))
            pygame.draw.rect(screen, WOOD_LIGHT, (200, 100, 400, 80), 2)
            pygame.draw.rect(screen, (30, 30, 35), (420, 120, 70, 45))  # Micro-ondas

            # Balcão de Mármore com Pia e Fogão
            pygame.draw.rect(screen, MARBLE, (200, 220, 450, 20))  # Pedra de Mármore
            pygame.draw.rect(screen, WOOD_DARK, (200, 240, 450, 80))  # Balcão Inferior

            # Fogão com bocas e Forno
            pygame.draw.rect(screen, (20, 20, 25), (220, 210, 90, 110))
            for bx in [235, 275]:
                for by in [220, 240]:
                    pygame.draw.circle(screen, (80, 85, 95), (bx, by), 8)

            # Geladeira Inox Realista
            pygame.draw.rect(screen, GREY_STEEL, (680, 140, 130, 180), border_radius=6)
            pygame.draw.line(screen, (90, 95, 105), (680, 210), (810, 210), 3)  # Divisória Congelador
            pygame.draw.rect(screen, (40, 45, 55), (695, 230, 10, 40), border_radius=2)  # Puxador
            pygame.draw.rect(screen, (40, 45, 55), (695, 160, 10, 30), border_radius=2)
            draw_text(screen, "GELADEIRA [E]", (685, 110), SMALL, YELLOW)

            # Mesa de Jantar com Fruteira
            pygame.draw.rect(screen, WOOD_LIGHT, (860, 380, 150, 90), border_radius=4)
            pygame.draw.ellipse(screen, RED, (920, 405, 30, 18))  # Fruteira

            draw_text(screen, "VOLTAR [A]", (90, 300), SMALL, CYAN)

        self.draw_player()

    def draw_stage3(self):
        screen.fill((5, 6, 10))

        if self.current_room == 0:  # Corredor Industrial Subsolo
            pygame.draw.rect(screen, (20, 24, 32), (0, 120, WIDTH, 200))  # Parede Metal
            pygame.draw.rect(screen, (12, 14, 18), (0, 320, WIDTH, 328))  # Chão Concreto

            # Tubulações de Vapor no Teto
            pygame.draw.line(screen, GREY_STEEL, (0, 135), (WIDTH, 135), 8)
            pygame.draw.line(screen, (100, 110, 120), (0, 155), (WIDTH, 155), 6)

            # Armário Industrial para Esconder
            pygame.draw.rect(screen, (50, 58, 70), (160, 330, 110, 180), border_radius=4)
            pygame.draw.rect(screen, (25, 30, 40), (170, 340, 40, 150))
            pygame.draw.rect(screen, (25, 30, 40), (220, 340, 40, 150))
            draw_text(screen, "ARMÁRIO [E]", (165, 300), SMALL, CYAN)

            # Entrada Sala de Energia
            pygame.draw.rect(screen, (15, 18, 25), (780, 140, 90, 180))
            draw_text(screen, "ENERGIA", (790, 110), SMALL, YELLOW)

            # Porta Blindada
            pygame.draw.rect(screen, (35, 30, 28), (950, 180, 110, 220), border_radius=4)
            pygame.draw.circle(screen, GREEN if "Energia Ligada" in self.flags else RED, (1005, 230), 12)
            draw_text(screen, "SAÍDA BLINDADA", (930, 150), SMALL, GREEN if "Energia Ligada" in self.flags else RED)

            self.draw_stalker()

        elif self.current_room == 1:  # Sala de Geradores
            screen.fill((8, 10, 14))

            # Gerador Principal Gigante
            pygame.draw.rect(screen, (30, 35, 45), (250, 160, 220, 180), border_radius=8)
            pygame.draw.rect(screen, GREY_STEEL, (280, 190, 160, 120))
            draw_text(screen, "BANCADA COM FUSÍVEL", (260, 130), SMALL, YELLOW)

            if "Fusível" not in self.inventory:
                pygame.draw.circle(screen, YELLOW, (360, 250), 10)
                draw_text(screen, "[E] PEGAR FUSÍVEL", (295, 220), SMALL, YELLOW)

            # Painel Elétrico de Alta Voltagem
            pygame.draw.rect(screen, (50, 55, 65), (710, 150, 130, 190), border_radius=6)
            st_color = GREEN if "Energia Ligada" in self.flags else RED
            pygame.draw.circle(screen, st_color, (775, 200), 14)
            draw_text(screen, "[E] RELIGAR PAINEL", (680, 115), SMALL, YELLOW)

            draw_text(screen, "VOLTAR [A]", (30, 300), SMALL, CYAN)

        self.draw_player()

    def draw_stage4(self):
        screen.fill((8, 10, 15))

        rects = [
            (pygame.Rect(80, 160, 180, 140), "ESPELHO", "Espelho Quebrado"),
            (pygame.Rect(380, 150, 180, 150), "DIÁRIO", "Diário Antigo"),
            (pygame.Rect(700, 150, 180, 150), "FERRAMENTA", "Chave de Fenda"),
            (pygame.Rect(440, 390, 260, 150), "LUZ DA VERDADE", "Luz da Verdade"),
        ]

        for rect, label, tag in rects:
            has = tag in self.inventory
            color = (50, 85, 65) if has else (32, 36, 46)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, WARM_LIGHT if has else GREY_STEEL, rect, 2, border_radius=8)
            draw_text(screen, label, rect.center, MID, WHITE if has else GREY_STEEL, True)

        pygame.draw.rect(screen, (25, 20, 18), (965, 350, 130, 220), border_radius=4)
        pygame.draw.rect(screen, WARM_LIGHT if len(self.inventory) >= 4 else GREY_STEEL, (965, 350, 130, 220), 4, border_radius=4)
        draw_text(screen, "LIBERTAÇÃO", (970, 320), SMALL, WARM_LIGHT if len(self.inventory) >= 4 else GREY_STEEL)

        self.draw_player()

    def draw_pin_pad(self):
        panel(screen, pygame.Rect(376, 150, 400, 340), 245)
        draw_text(screen, "FECHADURA DIGITAL", (576, 180), MID, WHITE, True)
        draw_text(screen, "DIGITE A SENHA DE 4 DÍGITOS:", (576, 230), SMALL, GREY_STEEL, True)

        display_code = self.pin_input + "_" * (4 - len(self.pin_input))
        draw_text(screen, display_code, (576, 280), BIG, WARM_LIGHT, True)

        draw_text(screen, "Use o teclado numérico do teclado", (576, 370), SMALL, CYAN, True)
        draw_text(screen, "[ENTER] Confirmar  •  [ESC] Cancelar", (576, 420), SMALL, GREY_STEEL, True)

    def draw_game(self):
        if self.stage == 1:
            self.draw_stage1()
        elif self.stage == 2:
            self.draw_stage2()
        elif self.stage == 3:
            self.draw_stage3()
        elif self.stage == 4:
            self.draw_stage4()

        vignette(screen, int(130 + self.tension * 70))

        # HUD do Objetivo
        panel(screen, pygame.Rect(15, 15, 580, 60), 210)
        draw_text(screen, f"FASE {self.stage}/4 — {self.objective}", (25, 35), SMALL, WARM_LIGHT)

        # HUD do Inventário
        panel(screen, pygame.Rect(15, HEIGHT - 55, 650, 40), 210)
        inv_str = "INVENTÁRIO: " + (" | ".join(self.inventory) if self.inventory else "Vazio")
        draw_text(screen, inv_str, (25, HEIGHT - 43), SMALL, CYAN)

        # Diálogos
        if self.dialogue_timer > 0 and self.dialogue:
            r = pygame.Rect(110, 480, 932, 90)
            panel(screen, r, 240)
            wrapped(screen, self.dialogue, pygame.Rect(135, 500, 880, 55), FONT, WHITE)

        if self.entering_pin:
            self.draw_pin_pad()

        if self.paused:
            panel(screen, pygame.Rect(390, 190, 370, 240), 245)
            draw_text(screen, "PAUSADO", (575, 230), BIG, WHITE, True)
            draw_text(screen, "ESC — Continuar", (575, 310), FONT, GREY_STEEL, True)
            draw_text(screen, "M — Menu Principal", (575, 350), FONT, GREY_STEEL, True)

    def handle_game(self, event):
        if self.entering_pin:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.entering_pin = False
                    self.pin_input = ""
                elif event.key == pygame.K_RETURN:
                    if self.pin_input == self.correct_pin:
                        self.entering_pin = False
                        self.say("SENHA CORRETA! A porta do quarto foi destrancada.")
                        self.complete_stage()
                    else:
                        self.say("SENHA INCORRETA! Procure as pistas no banheiro e na cozinha.")
                        self.pin_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.pin_input = self.pin_input[:-1]
                elif event.unicode.isdigit() and len(self.pin_input) < 4:
                    self.pin_input += event.unicode
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
                return
            if self.paused:
                if event.key == pygame.K_m:
                    self.state = "menu"
                    self.paused = False
                return
            if event.key == pygame.K_e:
                self.interact()

    def draw_game_over(self):
        screen.fill((15, 5, 5))
        draw_text(screen, "VOCÊ FOI PEGA", (WIDTH // 2, 220), BIG, RED, True)
        draw_text(screen, "O perseguidor te alcançou na escuridão.", (WIDTH // 2, 300), FONT, GREY_STEEL, True)
        draw_text(screen, "Pressione [ENTER] para recomeçar esta fase", (WIDTH // 2, 420), SMALL, WHITE, True)

    def handle_game_over(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.setup_stage()
            self.state = "game"

    def draw_menu(self):
        screen.fill((5, 7, 12))
        draw_text(screen, "A PORTA", (100, 120), BIG, WHITE)
        draw_text(screen, "um terror psicológico sobre limites e sobrevivência", (105, 180), FONT, GREY_STEEL)

        options = ["1  NOVO JOGO", "2  CONTINUAR", "3  CONFIGURAÇÕES", "ESC  SAIR"]
        y = 290
        for item in options:
            draw_text(screen, item, (110, y), FONT, WHITE if y < 400 else GREY_STEEL)
            y += 48

    def draw_settings(self):
        screen.fill((7, 9, 15))
        draw_text(screen, "CONFIGURAÇÕES", (90, 100), BIG)
        draw_text(screen, f"VOLUME DOS EFEITOS: {self.settings['volume']}%", (100, 230), MID)
        draw_text(screen, "← / → Ajustar volume", (100, 285), FONT, GREY_STEEL)
        draw_text(screen, "ESC Voltar ao Menu", (100, 340), FONT, GREY_STEEL)

    def draw_ending(self):
        screen.fill((210, 215, 212))
        pygame.draw.rect(screen, (240, 242, 238), (120, 85, 912, 480), border_radius=8)

        draw_text(screen, "VOCÊ SUPEROU A PORTA", (576, 150), MID, (35, 40, 45), True)
        draw_text(screen, "Algumas portas precisam ser abertas.", (576, 230), FONT, (55, 60, 65), True)
        draw_text(screen, "Outras... precisam ser trancadas para sempre.", (576, 270), FONT, (55, 60, 65), True)

        draw_text(screen, "Se você ou alguém que você conhece estiver enfrentando assédio ou perseguição:", (576, 370), SMALL, (80, 85, 90), True)
        draw_text(screen, "Procure ajuda com pessoas de confiança e autoridades regionais. Seus limites importam.", (576, 400), SMALL, (80, 85, 90), True)

        draw_text(screen, "Pressione [ENTER] para voltar ao menu principal", (576, 500), SMALL, GREY_STEEL, True)

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "game":
            self.draw_game()
        elif self.state == "game_over":
            self.draw_game_over()
        elif self.state == "ending":
            self.draw_ending()

    def run(self):
        while self.running:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.state == "menu":
                    self.handle_menu(event)
                elif self.state == "settings":
                    self.handle_settings(event)
                elif self.state == "game":
                    self.handle_game(event)
                elif self.state == "game_over":
                    self.handle_game_over(event)
                elif self.state == "ending":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                        self.state = "menu"

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()