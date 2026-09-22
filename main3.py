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
TITLE = "A PORTA — Terror Psicológico & Sobrevivência"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# ---------- Cores ----------
BLACK = (5, 7, 12)
DARK = (12, 15, 24)
BLUE = (19, 28, 43)
GREY = (90, 96, 108)
WHITE = (226, 229, 235)
WARM = (220, 174, 112)
RED = (200, 40, 40)
GREEN = (40, 180, 80)
CYAN = (92, 150, 165)
YELLOW = (240, 210, 110)

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


def panel(surface, rect, alpha=220, border_color=(80, 88, 105)):
    p = pygame.Surface(rect.size, pygame.SRCALPHA)
    p.fill((4, 6, 12, alpha))
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
        self.current_room = 0  # Permite ter várias salas por fase
        self.stage_time = 0.0
        self.tension = 0.0

        self.message = ""
        self.message_timer = 0
        self.dialogue = None
        self.dialogue_timer = 0
        self.objective = ""

        self.inventory = []  # Sistema de inventário
        self.flags = set()

        self.player = pygame.Vector2(120, 480)
        self.player_dir = "RIGHT"
        self.walk_cycle = 0.0
        self.is_moving = False
        self.speed = 190
        self.hidden = False

        # Perseguidor
        self.stalker_pos = pygame.Vector2(-100, -100)
        self.stalker_active = False
        self.stalker_speed = 135

        # Puzzle do Cofre/Senha
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
            self.message = "FASE 2 — O APARTAMENTO"
            self.objective = "A porta do quarto exige uma SENHA de 4 dígitos. Procure as pistas pelas salas."
            self.say("A porta está trancada por uma fechadura digital. Onde deixei a senha?")
        elif self.stage == 3:
            self.message = "FASE 3 — SUBSOLO & PARANOIA"
            self.objective = "Ligue o FUSÍVEL na sala de máquinas e use o CARTÃO DE ACESSO na porta final."
            self.say("Escutei passos pesados! Preciso restaurar a energia e pegar o cartão para escapar.")
            self.stalker_pos = pygame.Vector2(950, 400)
            self.stalker_active = True
        elif self.stage == 4:
            self.message = "FASE 4 — O LABIRINTO MENTAL"
            self.objective = "Colete os 4 FRAGMENTOS DE MEMÓRIA escondidos no labirinto para libertar a mente."
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

        # Movimentação do Personagem
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

            # Limites de Tela
            self.player.x = max(45, min(WIDTH - 45, self.player.x))
            self.player.y = max(130, min(HEIGHT - 65, self.player.y))

        # Lógica de Inteligência do Perseguidor (Fase 3)
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
            # Trocar de sala (Rua principal <-> Beco)
            if self.current_room == 0:
                if 420 < x < 540 and y < 200:
                    self.current_room = 1  # Entra no beco
                    self.player = pygame.Vector2(550, 520)
                    self.say("Você entrou em um beco escuro e úmido.")
                elif x > 950 and y > 380:
                    if "Corta-Vergalhão" in self.inventory:
                        self.say("Você cortou a corrente da grade e abriu o caminho!")
                        self.complete_stage()
                    else:
                        self.say("O portão está trancado com corrente pesada. Preciso de um Corta-Vergalhão!")

            elif self.current_room == 1:  # Sala do Beco
                if x < 150 and y > 450:
                    self.current_room = 0  # Volta para a rua
                    self.player = pygame.Vector2(480, 240)
                elif 700 < x < 850 and y < 300 and "Corta-Vergalhão" not in self.inventory:
                    self.inventory.append("Corta-Vergalhão")
                    self.say("Você encontrou o CORTA-VERGALHÃO caido atrás da lixeira!")
                    self.objective = "Volte para a rua principal e use a ferramenta no portão trancado."

        # ---------- FASE 2 ----------
        elif self.stage == 2:
            # Transição entre Salas: 0=Sala Principal, 1=Banheiro, 2=Cozinha
            if self.current_room == 0:
                if 120 < x < 240 and y < 220:
                    self.current_room = 1  # Banheiro
                    self.player = pygame.Vector2(550, 500)
                elif 750 < x < 870 and y < 220:
                    self.current_room = 2  # Cozinha
                    self.player = pygame.Vector2(150, 500)
                elif 450 < x < 600 and y < 220:
                    self.entering_pin = True  # Tentar digitar a senha da porta do quarto

            elif self.current_room == 1:  # Banheiro
                if y > 520:
                    self.current_room = 0
                    self.player = pygame.Vector2(180, 260)
                elif 450 < x < 600 and y < 280 and "Bilhete 1" not in self.flags:
                    self.flags.add("Bilhete 1")
                    self.say("No espelho do banheiro há escrito em batom: 'Primeiros dígitos: 4 8'")

            elif self.current_room == 2:  # Cozinha
                if x < 100:
                    self.current_room = 0
                    self.player = pygame.Vector2(810, 260)
                elif 650 < x < 800 and y < 280 and "Bilhete 2" not in self.flags:
                    self.flags.add("Bilhete 2")
                    self.say("Um papel preso na geladeira diz: 'Últimos dígitos: 2 1'")

        # ---------- FASE 3 ----------
        elif self.stage == 3:
            # Sala 0: Corredor / Sala 1: Sala de Energia
            if self.current_room == 0:
                if 150 < x < 280 and y > 380:
                    self.hidden = not self.hidden
                    if self.hidden:
                        self.say("Você se escondeu no armário! O perseguidor não te vê aqui.")
                    else:
                        self.say("Você saiu do armário.")
                elif 800 < x < 900 and y < 220:
                    self.current_room = 1  # Entrar na Sala de Energia
                    self.player = pygame.Vector2(200, 480)
                elif x > 950 and y > 380:
                    if "Energia Ligada" in self.flags and "Cartão de Acesso" in self.inventory:
                        self.say("Passou o cartão e a porta blindada se abriu!")
                        self.complete_stage()
                    elif "Energia Ligada" not in self.flags:
                        self.say("A porta eletrônica está sem energia! Ache o Fusível e ligue a chave de força.")
                    else:
                        self.say("A energia voltou, mas a porta exige um CARTÃO DE ACESSO!")

            elif self.current_room == 1:  # Sala de Energia
                if x < 120:
                    self.current_room = 0
                    self.player = pygame.Vector2(850, 260)
                elif 300 < x < 450 and y < 250 and "Fusível" not in self.inventory:
                    self.inventory.append("Fusível")
                    self.say("Você encontrou um FUSÍVEL DE ALTA VOLTAGEM!")
                elif 700 < x < 850 and y < 250:
                    if "Fusível" in self.inventory and "Energia Ligada" not in self.flags:
                        self.flags.add("Energia Ligada")
                        self.say("Você colocou o fusível e religou o painel! A energia voltou!")
                        if "Cartão de Acesso" not in self.inventory:
                            self.inventory.append("Cartão de Acesso")
                            self.say("GAVETA DESTRANCADA! Você pegou o CARTÃO DE ACESSO!")

        # ---------- FASE 4 ----------
        elif self.stage == 4:
            zones = [
                (pygame.Rect(80, 150, 180, 140), "Espelho Quebrado", "Fragmento 1: Encarar a realidade sem distorções."),
                (pygame.Rect(380, 140, 180, 150), "Diário Antigo", "Fragmento 2: Palavras gravadas que nunca foram ouvidas."),
                (pygame.Rect(700, 140, 180, 150), "Chave de Fenda", "Fragmento 3: A ferramenta do próprio destino."),
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
        pygame.draw.ellipse(screen, (0, 0, 0, 150), (x - 16, y + 10, 32, 10))

        # Pernas
        leg_offset = math.cos(self.walk_cycle) * 5 if self.is_moving else 0
        pygame.draw.line(screen, (40, 45, 55), (x - 5, y + 8), (x - 5 + leg_offset, y + 22), 4)
        pygame.draw.line(screen, (40, 45, 55), (x + 5, y + 8), (x + 5 - leg_offset, y + 22), 4)

        # Corpo e Cabeça
        pygame.draw.rect(screen, (58, 68, 84), (x - 11, y - 22 + int(bob), 22, 32), border_radius=4)
        pygame.draw.circle(screen, (215, 185, 160), (x, y - 30 + int(bob)), 9)

        # Cabelo e Olhos por Direção
        if self.player_dir == "DOWN":
            pygame.draw.circle(screen, (35, 25, 20), (x, y - 33 + int(bob)), 9)
            pygame.draw.circle(screen, (215, 185, 160), (x, y - 29 + int(bob)), 7)
            pygame.draw.rect(screen, (20, 20, 20), (x - 4, y - 30 + int(bob), 3, 3))
            pygame.draw.rect(screen, (20, 20, 20), (x + 1, y - 30 + int(bob), 3, 3))
        elif self.player_dir == "UP":
            pygame.draw.circle(screen, (35, 25, 20), (x, y - 31 + int(bob)), 10)
        elif self.player_dir == "LEFT":
            pygame.draw.circle(screen, (35, 25, 20), (x + 2, y - 32 + int(bob)), 9)
            pygame.draw.rect(screen, (20, 20, 20), (x - 5, y - 30 + int(bob), 3, 3))
        elif self.player_dir == "RIGHT":
            pygame.draw.circle(screen, (35, 25, 20), (x - 2, y - 32 + int(bob)), 9)
            pygame.draw.rect(screen, (20, 20, 20), (x + 3, y - 30 + int(bob), 3, 3))

        # Feixe da Lanterna
        light_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        angle = 0 if self.player_dir == "RIGHT" else 180 if self.player_dir == "LEFT" else 90 if self.player_dir == "DOWN" else 270
        rad = math.radians(angle)
        p1 = (x, y - 10)
        p2 = (x + math.cos(rad - 0.35) * 190, y - 10 + math.sin(rad - 0.35) * 190)
        p3 = (x + math.cos(rad + 0.35) * 190, y - 10 + math.sin(rad + 0.35) * 190)
        pygame.draw.polygon(light_surface, (255, 240, 200, 35), [p1, p2, p3])
        screen.blit(light_surface, (0, 0))

    def draw_stalker(self):
        if not self.stalker_active or self.current_room != 0:
            return

        sx, sy = int(self.stalker_pos.x), int(self.stalker_pos.y)
        pygame.draw.ellipse(screen, (0, 0, 0), (sx - 20, sy + 15, 40, 12))
        pygame.draw.rect(screen, (10, 12, 18), (sx - 14, sy - 45, 28, 60), border_radius=5)
        pygame.draw.circle(screen, (8, 9, 12), (sx, y_head := sy - 54), 13)

        pulse = math.sin(self.stage_time * 8) * 20
        eye_color = (min(255, int(200 + pulse)), 20, 20)
        pygame.draw.circle(screen, eye_color, (sx - 4, y_head - 2), 3)
        pygame.draw.circle(screen, eye_color, (sx + 4, y_head - 2), 3)

    # ---------- DESENHO DAS FASES ----------
    def draw_stage1(self):
        screen.fill((8, 10, 16))

        if self.current_room == 0:  # Rua Principal
            pygame.draw.rect(screen, (22, 26, 34), (0, 320, WIDTH, 328))
            pygame.draw.rect(screen, (14, 18, 24), (0, 470, WIDTH, 178))

            # Beco Interativo
            pygame.draw.rect(screen, (5, 5, 8), (430, 140, 100, 180))
            draw_text(screen, "BECO [E]", (445, 110), SMALL, YELLOW)

            # Portão Trancado no Final
            pygame.draw.rect(screen, (40, 40, 50), (980, 330, 80, 150))
            for x_bar in range(985, 1060, 10):
                pygame.draw.line(screen, (120, 120, 130), (x_bar, 330), (x_bar, 480), 3)
            draw_text(screen, "PORTÃO TRANCADO", (940, 300), SMALL, RED if "Corta-Vergalhão" not in self.inventory else GREEN)

        elif self.current_room == 1:  # Beco Escuro
            pygame.draw.rect(screen, (15, 16, 22), (100, 100, 952, 480))
            draw_text(screen, " SAÍDA DO BECO [S]", (110, 540), SMALL, CYAN)

            # Lixeira com Item
            pygame.draw.rect(screen, (35, 45, 40), (740, 220, 110, 80))
            if "Corta-Vergalhão" not in self.inventory:
                pygame.draw.rect(screen, RED, (770, 200, 30, 15))
                draw_text(screen, "[E] CORTA-VERGALHÃO", (710, 175), SMALL, YELLOW)

        self.draw_player()

    def draw_stage2(self):
        screen.fill((12, 13, 18))

        if self.current_room == 0:  # Sala Principal
            pygame.draw.rect(screen, (25, 26, 32), (60, 110, 1032, 480))

            # Portas
            pygame.draw.rect(screen, (15, 20, 30), (130, 120, 90, 130))
            draw_text(screen, "BANHEIRO", (135, 95), SMALL, CYAN)

            pygame.draw.rect(screen, (15, 20, 30), (760, 120, 90, 130))
            draw_text(screen, "COZINHA", (770, 95), SMALL, CYAN)

            # Porta com Fechadura Digital
            pygame.draw.rect(screen, (30, 10, 10), (470, 120, 110, 130))
            pygame.draw.rect(screen, RED, (515, 160, 20, 30))
            draw_text(screen, "QUARTO (SENHA)", (455, 95), SMALL, RED)

        elif self.current_room == 1:  # Banheiro
            screen.fill((10, 15, 20))
            pygame.draw.rect(screen, (70, 75, 85), (460, 160, 140, 110), 3)
            draw_text(screen, "ESPELHO [E]", (480, 135), SMALL, YELLOW)
            draw_text(screen, "VOLTAR [S]", (530, 560), SMALL, CYAN)

        elif self.current_room == 2:  # Cozinha
            screen.fill((18, 15, 12))
            pygame.draw.rect(screen, (200, 200, 210), (670, 160, 100, 140))
            draw_text(screen, "GELADEIRA [E]", (665, 135), SMALL, YELLOW)
            draw_text(screen, "VOLTAR [A]", (50, 300), SMALL, CYAN)

        self.draw_player()

    def draw_stage3(self):
        screen.fill((6, 8, 12))

        if self.current_room == 0:  # Corredor Principal
            pygame.draw.polygon(screen, (28, 30, 38), [(0, 140), (WIDTH, 140), (940, 600), (200, 600)])

            # Armário
            pygame.draw.rect(screen, (45, 35, 30), (160, 360, 110, 180))
            draw_text(screen, "ARMÁRIO [E]", (160, 330), SMALL, CYAN)

            # Sala de Força
            pygame.draw.rect(screen, (20, 25, 35), (800, 120, 90, 120))
            draw_text(screen, "ENERGIA", (810, 95), SMALL, YELLOW)

            # Porta Final
            pygame.draw.rect(screen, (15, 12, 10), (950, 200, 100, 200))
            draw_text(screen, "SAÍDA BLINDADA", (930, 170), SMALL, RED if "Energia Ligada" not in self.flags else GREEN)

            self.draw_stalker()

        elif self.current_room == 1:  # Sala de Energia
            screen.fill((10, 10, 15))
            draw_text(screen, "VOLTAR [A]", (20, 300), SMALL, CYAN)

            # Mesa com Fusível
            pygame.draw.rect(screen, (40, 40, 50), (320, 200, 100, 60))
            if "Fusível" not in self.inventory:
                pygame.draw.circle(screen, YELLOW, (370, 220), 8)
                draw_text(screen, "[E] FUSÍVEL", (330, 175), SMALL, YELLOW)

            # Painel Elétrico
            pygame.draw.rect(screen, (60, 60, 70), (720, 180, 110, 120))
            status_color = GREEN if "Energia Ligada" in self.flags else RED
            pygame.draw.circle(screen, status_color, (775, 210), 10)
            draw_text(screen, "[E] RELIGAR ENERGIA", (690, 150), SMALL, YELLOW)

        self.draw_player()

    def draw_stage4(self):
        screen.fill((8, 10, 15))

        rects = [
            (pygame.Rect(80, 150, 180, 140), "ESPELHO", "Espelho Quebrado"),
            (pygame.Rect(380, 140, 180, 150), "DIÁRIO", "Diário Antigo"),
            (pygame.Rect(700, 140, 180, 150), "FERRAMENTA", "Chave de Fenda"),
            (pygame.Rect(440, 390, 260, 150), "LUZ DA VERDADE", "Luz da Verdade"),
        ]

        for rect, label, tag in rects:
            has = tag in self.inventory
            color = (50, 80, 60) if has else (35, 38, 48)
            pygame.draw.rect(screen, color, rect, border_radius=6)
            pygame.draw.rect(screen, WARM if has else GREY, rect, 2, border_radius=6)
            draw_text(screen, label, rect.center, MID, WHITE if has else GREY, True)

        # Porta Final
        pygame.draw.rect(screen, (25, 20, 18), (965, 350, 130, 220), border_radius=4)
        pygame.draw.rect(screen, WARM if len(self.inventory) >= 4 else GREY, (965, 350, 130, 220), 4, border_radius=4)
        draw_text(screen, "LIBERTAÇÃO", (970, 320), SMALL, WARM if len(self.inventory) >= 4 else GREY)

        self.draw_player()

    def draw_pin_pad(self):
        panel(screen, pygame.Rect(376, 150, 400, 340), 245)
        draw_text(screen, "FECHADURA DIGITAL", (576, 180), MID, WHITE, True)
        draw_text(screen, "DIGITE A SENHA DE 4 DÍGITOS:", (576, 230), SMALL, GREY, True)

        # Exibição do PIN
        display_code = self.pin_input + "_" * (4 - len(self.pin_input))
        draw_text(screen, display_code, (576, 280), BIG, WARM, True)

        draw_text(screen, "Use o teclado numérico do seu computador", (576, 370), SMALL, CYAN, True)
        draw_text(screen, "[ENTER] Confirmar  •  [ESC] Cancelar", (576, 420), SMALL, GREY, True)

    def draw_game(self):
        if self.stage == 1:
            self.draw_stage1()
        elif self.stage == 2:
            self.draw_stage2()
        elif self.stage == 3:
            self.draw_stage3()
        elif self.stage == 4:
            self.draw_stage4()

        vignette(screen, int(140 + self.tension * 70))

        # Painel do Objetivo
        panel(screen, pygame.Rect(15, 15, 520, 60), 200)
        draw_text(screen, f"FASE {self.stage}/4 — {self.objective}", (25, 35), SMALL, WARM)

        # INVENTÁRIO HUD
        panel(screen, pygame.Rect(15, HEIGHT - 55, 600, 40), 200)
        inv_str = "INVENTÁRIO: " + (" | ".join(self.inventory) if self.inventory else "Vazio")
        draw_text(screen, inv_str, (25, HEIGHT - 43), SMALL, CYAN)

        # Diálogo
        if self.dialogue_timer > 0 and self.dialogue:
            r = pygame.Rect(110, 480, 932, 90)
            panel(screen, r, 240)
            wrapped(screen, self.dialogue, pygame.Rect(135, 500, 880, 55), FONT, WHITE)

        # Fechadura Digital
        if self.entering_pin:
            self.draw_pin_pad()

        # Pausa
        if self.paused:
            panel(screen, pygame.Rect(390, 190, 370, 240), 245)
            draw_text(screen, "PAUSADO", (575, 230), BIG, WHITE, True)
            draw_text(screen, "ESC — Continuar", (575, 310), FONT, GREY, True)
            draw_text(screen, "M — Menu Principal", (575, 350), FONT, GREY, True)

    def handle_game(self, event):
        if self.entering_pin:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.entering_pin = False
                    self.pin_input = ""
                elif event.key == pygame.K_RETURN:
                    if self.pin_input == self.correct_pin:
                        self.entering_pin = False
                        self.say("SENHA CORRETA! A porta do quarto destrancou.")
                        self.complete_stage()
                    else:
                        self.say("SENHA INCORRETA! Procure as pistas nos cômodos.")
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
        draw_text(screen, "O perseguidor te alcançou na escuridão.", (WIDTH // 2, 300), FONT, GREY, True)
        draw_text(screen, "Pressione [ENTER] para recomeçar esta fase", (WIDTH // 2, 420), SMALL, WHITE, True)

    def handle_game_over(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.setup_stage()
            self.state = "game"

    def draw_menu(self):
        screen.fill((5, 7, 12))
        draw_text(screen, "A PORTA", (100, 120), BIG, WHITE)
        draw_text(screen, "um terror psicológico sobre limites e sobrevivência", (105, 180), FONT, GREY)

        options = ["1  NOVO JOGO", "2  CONTINUAR", "3  CONFIGURAÇÕES", "ESC  SAIR"]
        y = 290
        for item in options:
            draw_text(screen, item, (110, y), FONT, WHITE if y < 400 else GREY)
            y += 48

    def draw_settings(self):
        screen.fill((7, 9, 15))
        draw_text(screen, "CONFIGURAÇÕES", (90, 100), BIG)
        draw_text(screen, f"VOLUME DOS EFEITOS: {self.settings['volume']}%", (100, 230), MID)
        draw_text(screen, "← / → Ajustar volume", (100, 285), FONT, GREY)
        draw_text(screen, "ESC Voltar ao Menu", (100, 340), FONT, GREY)

    def draw_ending(self):
        screen.fill((210, 215, 212))
        pygame.draw.rect(screen, (240, 242, 238), (120, 85, 912, 480), border_radius=8)

        draw_text(screen, "VOCÊ SUPEROU A PORTA", (576, 150), MID, (35, 40, 45), True)
        draw_text(screen, "Algumas portas precisam ser abertas.", (576, 230), FONT, (55, 60, 65), True)
        draw_text(screen, "Outras... precisam ser trancadas para sempre.", (576, 270), FONT, (55, 60, 65), True)

        draw_text(screen, "Se você ou alguém que você conhece estiver enfrentando assédio ou perseguição:", (576, 370), SMALL, (80, 85, 90), True)
        draw_text(screen, "Procure ajuda com pessoas de confiança e autoridades regionais. Seus limites importam.", (576, 400), SMALL, (80, 85, 90), True)

        draw_text(screen, "Pressione [ENTER] para voltar ao menu principal", (576, 500), SMALL, GREY, True)

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