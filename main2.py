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

# ---------- Configurações de Tela e Motor ----------
WIDTH, HEIGHT = 1152, 648
FPS = 60
TITLE = "A PORTA — Terror Psicológico & Sobrevivência"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# ---------- Cores ----------
BLACK = (5, 7, 12)
DARK_BLUE = (12, 15, 24)
GREY = (90, 96, 108)
LIGHT_GREY = (160, 168, 180)
WHITE = (226, 229, 235)
WARM_GOLD = (220, 174, 112)
BLOOD_RED = (180, 40, 40)
CYAN = (92, 150, 165)
YELLOW = (240, 210, 110)

# ---------- Fontes ----------
FONT = pygame.font.SysFont("consolas", 20)
SMALL_FONT = pygame.font.SysFont("consolas", 15)
BIG_FONT = pygame.font.SysFont("consolas", 48, bold=True)
MID_FONT = pygame.font.SysFont("consolas", 26, bold=True)

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


def draw_wrapped_text(surface, text, rect, font=FONT, color=WHITE, line_gap=6):
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


def draw_panel(surface, rect, alpha=220, border_color=(80, 88, 105)):
    p = pygame.Surface(rect.size, pygame.SRCALPHA)
    p.fill((4, 6, 12, alpha))
    surface.blit(p, rect.topleft)
    pygame.draw.rect(surface, border_color, rect, 2, border_radius=4)


def apply_vignette(surface, strength=200):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cx, cy = WIDTH // 2, HEIGHT // 2
    for r in range(max(WIDTH, HEIGHT), 40, -32):
        alpha = int(strength * (1 - r / max(WIDTH, HEIGHT)))
        if alpha > 0:
            pygame.draw.ellipse(overlay, (0, 0, 0, alpha), (cx - r, cy - r, r * 2, r * 2), 32)
    surface.blit(overlay, (0, 0))


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, pos):
        return pygame.Vector2(pos.x - self.camera.x, pos.y - self.camera.y)

    def apply_rect(self, rect):
        return rect.move(-self.camera.x, -self.camera.y)

    def update(self, target):
        x = -target.x + int(WIDTH / 2)
        y = -target.y + int(HEIGHT / 2)
        # Limita o scroll até as bordas do mapa
        x = min(0, max(-(self.width - WIDTH), x))
        y = min(0, max(-(self.height - HEIGHT), y))
        self.camera = pygame.Rect(-x, -y, WIDTH, HEIGHT)


class Item:
    def __init__(self, name, x, y, item_id, description):
        self.name = name
        self.pos = pygame.Vector2(x, y)
        self.item_id = item_id
        self.description = description
        self.collected = False


class Game:
    def __init__(self):
        self.running = True
        self.state = "menu"
        self.stage = 1
        self.stage_time = 0.0

        # Sistema de Câmera e Mundo
        self.world_size = pygame.Vector2(2300, 750)
        self.camera = Camera(int(self.world_size.x), int(self.world_size.y))

        # Mensagens e HUD
        self.message = ""
        self.message_timer = 0
        self.dialogue = None
        self.dialogue_timer = 0
        self.objective = ""

        # Inventário e Progresso
        self.inventory = []
        self.show_inventory = False
        self.flags = set()
        self.interactive_items = []

        # Atributos do Jogador
        self.player = pygame.Vector2(120, 480)
        self.player_dir = "RIGHT"
        self.walk_cycle = 0.0
        self.is_moving = False
        self.speed = 180
        self.stamina = 100.0
        self.hidden = False
        self.flashlight_battery = 100.0

        # Puzzles & Códigos
        self.safe_code = str(random.randint(1000, 9999))
        self.entered_code = ""
        self.in_safe_ui = False

        # Perseguidor Inteligente
        self.stalker_pos = pygame.Vector2(-100, -100)
        self.stalker_active = False
        self.stalker_speed = 135
        self.stalker_state = "PATROL"  # PATROL, CHASE
        self.stalker_target = pygame.Vector2(0, 0)

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
        self.inventory.clear()
        self.flags.clear()
        self.interactive_items.clear()
        self.hidden = False
        self.stalker_active = False
        self.flashlight_battery = 100.0
        self.stamina = 100.0
        self.in_safe_ui = False

        if self.stage == 1:
            self.world_size = pygame.Vector2(2300, 750)
            self.player = pygame.Vector2(120, 520)
            self.message = "FASE 1 — RUA ESCURA"
            self.objective = "Explore a rua, encontre a bateria para a lanterna e a chave de casa."
            self.say("Está escuro demais aqui fora... preciso achar algo para iluminar meu caminho.")

            # Itens espalhados na Fase 1
            self.interactive_items.append(Item("Bateria", 650, 530, "battery", "Sua lanterna precisa de pilhas para funcionar."))
            self.interactive_items.append(Item("Chaveiro de Casa", 1450, 510, "house_key", "A chave da porta principal da sua residência."))
            self.interactive_items.append(Item("Bilhete Estranho", 950, 520, "note_1", "Diz: 'Eu sei por onde você anda.'"))

        elif self.stage == 2:
            self.world_size = pygame.Vector2(1600, 750)
            self.player = pygame.Vector2(150, 480)
            self.message = "FASE 2 — O APARTAMENTO"
            self.objective = "Encontre a anotação da senha para abrir o cofre e pegar a chave do quarto."
            self.say("Sensação estranha... Parece que alguém mexeu nas minhas coisas.")

            self.interactive_items.append(Item("Anotação da Senha", 720, 260, "code_note", f"Senha do Cofre anotada: {self.safe_code}"))
            self.interactive_items.append(Item("Pilhas Extras", 1200, 480, "battery", "Recarrega a iluminação da lanterna."))

        elif self.stage == 3:
            self.world_size = pygame.Vector2(2100, 850)
            self.player = pygame.Vector2(150, 450)
            self.message = "FASE 3 — LABIRINTO MENTAL"
            self.objective = "Cuidado com o Perseguidor! Encontre 2 fusíveis para ligar a porta elétrica e fugir."
            self.say("ELE ESTÁ AQUI! Se eu correr, ele vai ouvir meus passos!")

            self.interactive_items.append(Item("Fusível A", 850, 220, "fuse_1", "Primeiro componente elétrico da porta."))
            self.interactive_items.append(Item("Fusível B", 1750, 680, "fuse_2", "Segundo componente elétrico da porta."))

            self.stalker_pos = pygame.Vector2(1800, 300)
            self.stalker_active = True
            self.stalker_target = pygame.Vector2(1000, 300)

        elif self.stage == 4:
            self.world_size = pygame.Vector2(1800, 750)
            self.player = pygame.Vector2(150, 450)
            self.message = "FASE 4 — CONFRONTAÇÃO FINAL"
            self.objective = "Colete os 4 fragmentos espalhados para encarar a porta final."
            self.say("O medo não pode me controlar. Preciso juntar minhas memórias.")

            self.interactive_items.append(Item("Fragmento da Verdade", 450, 220, "frag_1", "Lembrança de superação."))
            self.interactive_items.append(Item("Fragmento da Coragem", 900, 580, "frag_2", "Lembrança de impor limites."))
            self.interactive_items.append(Item("Fragmento da Razão", 1350, 220, "frag_3", "Lembrança de buscar apoio."))
            self.interactive_items.append(Item("Fragmento da Paz", 1650, 580, "frag_4", "Você não está sozinha."))

        self.camera = Camera(int(self.world_size.x), int(self.world_size.y))
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
        if self.state != "game" or self.paused:
            return

        self.stage_time += dt
        self.message_timer = max(0, self.message_timer - dt)
        self.dialogue_timer = max(0, self.dialogue_timer - dt)

        # Atualiza Câmera
        self.camera.update(self.player)

        # Bateria da Lanterna
        if "battery_equipped" in self.flags or self.stage > 1:
            self.flashlight_battery = max(0.0, self.flashlight_battery - dt * 0.8)

        # Movimentação e Input
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)

        if not self.hidden and not self.in_safe_ui:
            is_running = keys[pygame.K_LSHIFT] and self.stamina > 5

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
                speed_mult = 1.6 if is_running else 1.0
                self.player += move * self.speed * speed_mult * dt
                self.is_moving = True
                self.walk_cycle += dt * (10 * speed_mult)

                if is_running:
                    self.stamina = max(0.0, self.stamina - dt * 25)
                else:
                    self.stamina = min(100.0, self.stamina + dt * 15)
            else:
                self.is_moving = False
                self.walk_cycle = 0
                self.stamina = min(100.0, self.stamina + dt * 20)

            # Limites do Mapa
            self.player.x = max(40, min(self.world_size.x - 40, self.player.x))
            self.player.y = max(130, min(self.world_size.y - 60, self.player.y))

        # Lógica da IA do Perseguidor na Fase 3
        if self.stage == 3 and self.stalker_active:
            self.update_stalker_ai(dt)

    def update_stalker_ai(self, dt):
        dist_to_player = self.stalker_pos.distance_to(self.player)

        # Perseguidor escuta se o jogador estiver correndo perto dele
        is_running = self.is_moving and pygame.key.get_pressed()[pygame.K_LSHIFT]

        if not self.hidden:
            if dist_to_player < 380 or (is_running and dist_to_player < 600):
                self.stalker_state = "CHASE"
                self.stalker_target = pygame.Vector2(self.player.x, self.player.y)
            else:
                self.stalker_state = "PATROL"
        else:
            self.stalker_state = "PATROL"

        # Movimento do Perseguidor
        if self.stalker_state == "PATROL":
            if self.stalker_pos.distance_to(self.stalker_target) < 30:
                # Troca ponto de patrulha
                self.stalker_target = pygame.Vector2(random.randint(200, 1900), random.randint(200, 700))
            spd = self.stalker_speed * 0.6
        else:
            spd = self.stalker_speed * 1.15

        dir_vec = (self.stalker_target - self.stalker_pos)
        if dir_vec.length_squared() > 0:
            dir_vec = dir_vec.normalize()
            self.stalker_pos += dir_vec * spd * dt

        # Colisão fatal com o jogador
        if not self.hidden and self.stalker_pos.distance_to(self.player) < 30:
            self.game_over()

    def interact(self):
        # 1. Coletar Itens Próximos
        for item in self.interactive_items:
            if not item.collected and self.player.distance_to(item.pos) < 60:
                item.collected = True
                self.inventory.append(item)
                self.say(f"Coletado: {item.name}. ({item.description})")

                if item.item_id == "battery":
                    self.flags.add("battery_equipped")
                    self.flashlight_battery = 100.0

                return

        x, y = self.player.x, self.player.y

        # Interações por Fase
        if self.stage == 1:
            if x > 2100 and y > 450:
                if any(i.item_id == "house_key" for i in self.inventory):
                    self.say("Você destranca a porta da sua casa e entra rapidamente!")
                    self.complete_stage()
                else:
                    self.say("A porta está trancada! Preciso encontrar o Chaveiro de Casa na rua.")

        elif self.stage == 2:
            # Cofre na Sala (X: 1000, Y: 250)
            if 950 < x < 1080 and y < 310:
                self.in_safe_ui = True
                self.entered_code = ""

            # Porta para o quarto
            elif x > 1400 and y > 420:
                if "bedroom_key" in self.flags:
                    self.complete_stage()
                else:
                    self.say("A porta do quarto está trancada com um segredo no cofre da sala!")

        elif self.stage == 3:
            # Armário de Esconder
            if 350 < x < 500 and y < 320:
                self.hidden = not self.hidden
                if self.hidden:
                    self.say("Você se escondeu no armário. Fique em silêncio...")
                else:
                    self.say("Você saiu do armário.")

            # Painel Elétrico da Porta
            elif x > 1950 and y > 400:
                fuses = [i for i in self.inventory if "fuse" in i.item_id]
                if len(fuses) >= 2:
                    self.say("Você inseriu os 2 fusíveis! A porta elétrica abriu!")
                    self.complete_stage()
                else:
                    self.say(f"Painel desativado! Faltam {2 - len(fuses)} fusível(is) no labirinto.")

        elif self.stage == 4:
            if x > 1650 and y > 400:
                frags = [i for i in self.inventory if "frag" in i.item_id]
                if len(frags) >= 4:
                    self.complete_stage()
                else:
                    self.say(f"A porta da mente exige todos os 4 fragmentos. Você tem {len(frags)}/4.")

    def draw_player(self):
        if self.hidden:
            return

        screen_pos = self.camera.apply(self.player)
        x, y = int(screen_pos.x), int(screen_pos.y)
        bob = math.sin(self.walk_cycle) * 3 if self.is_moving else 0

        # Sombra
        pygame.draw.ellipse(screen, (0, 0, 0, 140), (x - 16, y + 10, 32, 10))

        # Indicador de Som de Passos ao Correr
        if self.is_moving and pygame.key.get_pressed()[pygame.K_LSHIFT]:
            pulse_r = int(25 + math.sin(self.stage_time * 15) * 10)
            pygame.draw.circle(screen, (200, 50, 50, 80), (x, y + 5), pulse_r, 1)

        # Pernas
        leg_offset = math.cos(self.walk_cycle) * 5 if self.is_moving else 0
        pygame.draw.line(screen, (40, 45, 55), (x - 5, y + 8), (x - 5 + leg_offset, y + 22), 4)
        pygame.draw.line(screen, (40, 45, 55), (x + 5, y + 8), (x + 5 - leg_offset, y + 22), 4)

        # Corpo
        pygame.draw.rect(screen, (58, 68, 84), (x - 11, y - 22 + int(bob), 22, 32), border_radius=4)

        # Cabeça
        pygame.draw.circle(screen, (215, 185, 160), (x, y - 30 + int(bob)), 9)

        # Detalhes Direcionais
        if self.player_dir == "DOWN":
            pygame.draw.circle(screen, (35, 25, 20), (x, y - 33 + int(bob)), 9)
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

        # Lanterna
        if self.flashlight_battery > 0:
            self.draw_flashlight(x, y + int(bob))

    def draw_flashlight(self, x, y):
        light_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        alpha = int(40 * (self.flashlight_battery / 100.0))
        cone_color = (255, 240, 190, max(10, alpha))

        angle = 0
        if self.player_dir == "RIGHT": angle = 0
        elif self.player_dir == "LEFT": angle = 180
        elif self.player_dir == "DOWN": angle = 90
        elif self.player_dir == "UP": angle = 270

        rad = math.radians(angle)
        dist = 220
        p1 = (x, y - 10)
        p2 = (x + math.cos(rad - 0.4) * dist, y - 10 + math.sin(rad - 0.4) * dist)
        p3 = (x + math.cos(rad + 0.4) * dist, y - 10 + math.sin(rad + 0.4) * dist)

        pygame.draw.polygon(light_surface, cone_color, [p1, p2, p3])
        screen.blit(light_surface, (0, 0))

    def draw_stalker(self):
        if not self.stalker_active:
            return

        screen_pos = self.camera.apply(self.stalker_pos)
        sx, sy = int(screen_pos.x), int(screen_pos.y)

        # Sombra
        pygame.draw.ellipse(screen, (0, 0, 0), (sx - 22, sy + 15, 44, 12))

        # Corpo
        pygame.draw.rect(screen, (10, 12, 18), (sx - 15, sy - 48, 30, 62), border_radius=5)
        pygame.draw.circle(screen, (8, 9, 12), (sx, y_head := sy - 56), 14)

        # Olhos
        pulse = math.sin(self.stage_time * 10) * 35
        eye_color = (min(255, int(220 + pulse)), 30, 30)
        pygame.draw.circle(screen, eye_color, (sx - 5, y_head - 2), 3)
        pygame.draw.circle(screen, eye_color, (sx + 5, y_head - 2), 3)

    def draw_items(self):
        for item in self.interactive_items:
            if not item.collected:
                sp = self.camera.apply(item.pos)
                if -50 < sp.x < WIDTH + 50 and -50 < sp.y < HEIGHT + 50:
                    pygame.draw.circle(screen, YELLOW, (int(sp.x), int(sp.y)), 6)
                    pygame.draw.circle(screen, WARM_GOLD, (int(sp.x), int(sp.y)), 12, 1)

                    if self.player.distance_to(item.pos) < 60:
                        draw_text(screen, f"[E] {item.name}", (int(sp.x) - 40, int(sp.y) - 30), SMALL_FONT, YELLOW)

    def draw_stage1(self):
        screen.fill((8, 10, 16))

        # Rua Expandida
        r_street = self.camera.apply_rect(pygame.Rect(0, 350, int(self.world_size.x), 400))
        pygame.draw.rect(screen, (20, 24, 32), r_street)

        # Postes de Luz
        for px in range(200, int(self.world_size.x), 400):
            sp = self.camera.apply(pygame.Vector2(px, 350))
            pygame.draw.rect(screen, (40, 45, 55), (sp.x, sp.y - 180, 8, 180))
            pygame.draw.circle(screen, WARM_GOLD, (sp.x + 4, sp.y - 185), 18)

        # Casa Final
        r_house = self.camera.apply_rect(pygame.Rect(2050, 320, 180, 230))
        pygame.draw.rect(screen, (35, 28, 25), r_house)
        draw_text(screen, "SUA CASA", (r_house.x + 40, r_house.y - 25), SMALL_FONT, WARM_GOLD)

        self.draw_items()
        self.draw_player()

    def draw_stage2(self):
        screen.fill((12, 13, 18))

        # Paredes dos Cômodos do Apartamento
        r_apt = self.camera.apply_rect(pygame.Rect(80, 100, 1450, 550))
        pygame.draw.rect(screen, (24, 25, 32), r_apt)
        pygame.draw.rect(screen, (50, 55, 65), r_apt, 4)

        # Divisórias de Cômodos
        r_wall1 = self.camera.apply_rect(pygame.Rect(550, 100, 10, 380))
        r_wall2 = self.camera.apply_rect(pygame.Rect(1050, 250, 10, 400))
        pygame.draw.rect(screen, (50, 55, 65), r_wall1)
        pygame.draw.rect(screen, (50, 55, 65), r_wall2)

        # Cofre
        r_safe = self.camera.apply_rect(pygame.Rect(980, 140, 60, 60))
        pygame.draw.rect(screen, (60, 65, 75), r_safe)
        draw_text(screen, "COFRE", (r_safe.x, r_safe.y - 20), SMALL_FONT, YELLOW)

        self.draw_items()
        self.draw_player()

        # UI Interativa do Cofre
        if self.in_safe_ui:
            draw_panel(screen, pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 120, 360, 240))
            draw_text(screen, "DIGITE A SENHA DO COFRE", (WIDTH // 2, HEIGHT // 2 - 80), SMALL_FONT, WHITE, True)
            draw_text(screen, self.entered_code + "_" if len(self.entered_code) < 4 else self.entered_code, (WIDTH // 2, HEIGHT // 2 - 20), MID_FONT, YELLOW, True)
            draw_text(screen, "Use o teclado numérico para digitar", (WIDTH // 2, HEIGHT // 2 + 40), SMALL_FONT, GREY, True)
            draw_text(screen, "[ESC] Fechar", (WIDTH // 2, HEIGHT // 2 + 75), SMALL_FONT, GREY, True)

    def draw_stage3(self):
        screen.fill((5, 6, 10))

        # Estrutura do Labirinto
        r_lab = self.camera.apply_rect(pygame.Rect(80, 80, 1950, 700))
        pygame.draw.rect(screen, (20, 22, 28), r_lab)
        pygame.draw.rect(screen, (60, 40, 40), r_lab, 4)

        # Armário
        r_arm = self.camera.apply_rect(pygame.Rect(380, 120, 100, 150))
        pygame.draw.rect(screen, (50, 40, 35), r_arm)
        draw_text(screen, "ARMÁRIO", (r_arm.x + 10, r_arm.y - 20), SMALL_FONT, CYAN)

        # Painel Elétrico de Saída
        r_exit = self.camera.apply_rect(pygame.Rect(1920, 420, 80, 160))
        pygame.draw.rect(screen, (40, 60, 40), r_exit)
        draw_text(screen, "PORTA SAÍDA", (r_exit.x - 15, r_exit.y - 20), SMALL_FONT, BLOOD_RED)

        self.draw_items()
        self.draw_stalker()
        self.draw_player()

    def draw_stage4(self):
        screen.fill((8, 8, 14))

        # Ilhas do Vazio Mental
        rects = [
            (pygame.Rect(100, 150, 400, 300), "VERDADE"),
            (pygame.Rect(650, 400, 400, 300), "CORAGEM"),
            (pygame.Rect(1150, 150, 400, 300), "RAZÃO"),
            (pygame.Rect(1500, 400, 250, 300), "LIBERTAÇÃO"),
        ]

        for rect, label in rects:
            r_sp = self.camera.apply_rect(rect)
            pygame.draw.rect(screen, (25, 28, 38), r_sp, border_radius=8)
            pygame.draw.rect(screen, GREY, r_sp, 2, border_radius=8)
            draw_text(screen, label, (r_sp.centerx, r_sp.top + 20), SMALL_FONT, GREY, True)

        self.draw_items()
        self.draw_player()

    def draw_inventory_ui(self):
        draw_panel(screen, pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 180, 500, 360), alpha=245)
        draw_text(screen, "INVENTÁRIO DO JOGADOR", (WIDTH // 2, HEIGHT // 2 - 150), MID_FONT, WARM_GOLD, True)

        if not self.inventory:
            draw_text(screen, "Seu inventário está vazio.", (WIDTH // 2, HEIGHT // 2), FONT, GREY, True)
        else:
            y = HEIGHT // 2 - 90
            for item in self.inventory:
                draw_text(screen, f"• {item.name}", (WIDTH // 2 - 210, y), FONT, WHITE)
                draw_text(screen, item.description, (WIDTH // 2 - 210, y + 22), SMALL_FONT, GREY)
                y += 55

        draw_text(screen, "Pressione [I] para fechar", (WIDTH // 2, HEIGHT // 2 + 140), SMALL_FONT, CYAN, True)

    def draw_hud(self):
        # Barra Superior de Status
        draw_panel(screen, pygame.Rect(15, 15, 520, 75), 210)
        draw_text(screen, f"FASE {self.stage}/4", (28, 22), SMALL_FONT, GREY)
        draw_text(screen, f"OBJETIVO: {self.objective}", (28, 42), SMALL_FONT, WARM_GOLD)

        # Barra de Stamina
        pygame.draw.rect(screen, (40, 45, 55), (28, 65, 180, 10))
        pygame.draw.rect(screen, CYAN, (28, 65, int(180 * (self.stamina / 100.0)), 10))

        # Bateria da Lanterna
        pygame.draw.rect(screen, (40, 45, 55), (230, 65, 180, 10))
        pygame.draw.rect(screen, YELLOW, (230, 65, int(180 * (self.flashlight_battery / 100.0)), 10))
        draw_text(screen, "LANTERNA", (230, 50), SMALL_FONT, GREY)

        # Botão de Inventário
        draw_text(screen, "[I] Inventário", (425, 60), SMALL_FONT, CYAN)

        # Diálogo do Personagem
        if self.dialogue_timer > 0 and self.dialogue:
            r = pygame.Rect(110, 520, 932, 90)
            draw_panel(screen, r, 240)
            draw_wrapped_text(screen, self.dialogue, pygame.Rect(135, 540, 880, 55), FONT, WHITE)

    def draw_game(self):
        if self.stage == 1: self.draw_stage1()
        elif self.stage == 2: self.draw_stage2()
        elif self.stage == 3: self.draw_stage3()
        elif self.stage == 4: self.draw_stage4()

        apply_vignette(screen, 190)
        self.draw_hud()

        if self.show_inventory:
            self.draw_inventory_ui()

        if self.paused:
            draw_panel(screen, pygame.Rect(390, 190, 370, 260), 245)
            draw_text(screen, "PAUSADO", (575, 230), BIG_FONT, WHITE, True)
            draw_text(screen, "ESC — Continuar", (575, 310), FONT, GREY, True)
            draw_text(screen, "M — Menu Principal", (575, 350), FONT, GREY, True)

    def handle_game(self, event):
        if event.type == pygame.KEYDOWN:
            if self.in_safe_ui:
                if event.key == pygame.K_ESCAPE:
                    self.in_safe_ui = False
                elif event.key == pygame.K_BACKSPACE:
                    self.entered_code = self.entered_code[:-1]
                elif event.unicode.isdigit() and len(self.entered_code) < 4:
                    self.entered_code += event.unicode
                    if self.entered_code == self.safe_code:
                        self.in_safe_ui = False
                        self.flags.add("bedroom_key")
                        self.inventory.append(Item("Chave do Quarto", 0, 0, "bedroom_key", "Encontrada dentro do cofre."))
                        self.say("Cofre aberto! Você pegou a Chave do Quarto!")
                    elif len(self.entered_code) == 4:
                        self.say("Senha incorreta! Procure a anotação no apartamento.")
                        self.entered_code = ""
                return

            if event.key == pygame.K_i:
                self.show_inventory = not self.show_inventory
                return

            if event.key == pygame.K_ESCAPE:
                self.paused = not self.paused
                return

            if event.key == pygame.K_e:
                self.interact()

    def draw_game_over(self):
        screen.fill((15, 5, 5))
        draw_text(screen, "VOCÊ FOI CAPTURADA", (WIDTH // 2, 220), BIG_FONT, BLOOD_RED, True)
        draw_text(screen, "O medo encurtou seus passos.", (WIDTH // 2, 300), FONT, GREY, True)
        draw_text(screen, "Pressione [ENTER] para tentar novamente", (WIDTH // 2, 420), SMALL_FONT, WHITE, True)

    def handle_game_over(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.setup_stage()
            self.state = "game"

    def draw_menu(self):
        screen.fill((5, 7, 12))
        draw_text(screen, "A PORTA", (100, 120), BIG_FONT, WHITE)
        draw_text(screen, "Edição Expandida de Sobrevivência & Exploração", (105, 180), FONT, GREY)

        options = [
            "1  NOVO JOGO",
            "2  CONTINUAR",
            "3  CONFIGURAÇÕES",
            "ESC  SAIR",
        ]
        y = 290
        for item in options:
            draw_text(screen, item, (110, y), FONT, WHITE if y < 400 else GREY)
            y += 48

        draw_text(screen, "Controles: WASD (Mover) • SHIFT (Correr) • E (Interagir/Coletar) • I (Inventário)", (105, 570), SMALL_FONT, CYAN)

    def draw_settings(self):
        screen.fill((7, 9, 15))
        draw_text(screen, "CONFIGURAÇÕES", (90, 100), BIG_FONT)
        draw_text(screen, f"VOLUME DOS EFEITOS: {self.settings['volume']}%", (100, 230), MID_FONT)
        draw_text(screen, "← / → Ajustar volume", (100, 285), FONT, GREY)
        draw_text(screen, "ESC Voltar ao Menu", (100, 340), FONT, GREY)

    def draw_ending(self):
        screen.fill((210, 215, 212))
        pygame.draw.rect(screen, (240, 242, 238), (120, 85, 912, 480), border_radius=8)

        draw_text(screen, "VOCÊ VENCEU O MEDO", (576, 150), MID_FONT, (35, 40, 45), True)
        draw_text(screen, "A porta final se abriu para um novo começo.", (576, 230), FONT, (55, 60, 65), True)
        draw_text(screen, "Seus limites importam. Busque sempre apoio e proteção.", (576, 320), SMALL_FONT, (80, 85, 90), True)
        draw_text(screen, "Pressione [ENTER] para voltar ao menu", (576, 500), SMALL_FONT, GREY, True)

    def draw(self):
        if self.state == "menu": self.draw_menu()
        elif self.state == "settings": self.draw_settings()
        elif self.state == "game": self.draw_game()
        elif self.state == "game_over": self.draw_game_over()
        elif self.state == "ending": self.draw_ending()

    def run(self):
        while self.running:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.state == "menu": self.handle_menu(event)
                elif self.state == "settings": self.handle_settings(event)
                elif self.state == "game": self.handle_game(event)
                elif self.state == "game_over": self.handle_game_over(event)
                elif self.state == "ending":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                        self.state = "menu"

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    Game().run()