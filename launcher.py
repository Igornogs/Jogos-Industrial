#!/usr/bin/env python3
"""
Launcher do jogo CLARA
Permite escolher versão e configurações antes de iniciar
"""

import pygame
import sys
import subprocess
from enum import Enum

class MenuState(Enum):
    MAIN = 1
    VERSION_SELECT = 2
    SETTINGS = 3
    DIFFICULTY = 4

class LauncherApp:
    """Menu launcher do jogo CLARA"""
    
    def __init__(self):
        pygame.init()
        
        self.screen = pygame.display.set_mode((900, 600))
        pygame.display.set_caption("CLARA - Launcher")
        self.clock = pygame.time.Clock()
        
        self.font_title = pygame.font.Font(None, 60)
        self.font_large = pygame.font.Font(None, 40)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)
        
        self.state = MenuState.MAIN
        self.selected = 0
        self.difficulty_selected = 0
        
        self.main_options = [
            ("Novo Jogo", "start"),
            ("Configurações", "settings"),
            ("Sair", "quit")
        ]
        
        self.version_options = [
            ("Versão Original", "original"),
            ("Versão Melhorada", "enhanced"),
            ("Voltar", "back")
        ]
        
        self.difficulty_options = [
            "Fácil",
            "Normal",
            "Difícil",
            "Pesadelo"
        ]
        
        self.settings_options = [
            ("Dificuldade", "difficulty"),
            ("Volume", "volume"),
            ("Idioma", "language"),
            ("Acessibilidade", "accessibility"),
            ("Voltar", "back")
        ]
        
        self.selected_version = None
        self.selected_difficulty = 1  # Normal
    
    def _draw_background(self):
        """Desenha fundo estilizado"""
        # Gradiente de preto a cinza
        for y in range(self.screen.get_height()):
            alpha = int(30 + (70 * y / self.screen.get_height()))
            color = (alpha, alpha, alpha)
            pygame.draw.line(self.screen, color, (0, y), (900, y))
    
    def _draw_text_centered(self, text, font, color, y):
        """Desenha texto centralizado"""
        text_surface = font.render(text, True, color)
        x = (self.screen.get_width() - text_surface.get_width()) // 2
        self.screen.blit(text_surface, (x, y))
        return text_surface
    
    def _draw_main_menu(self):
        """Menu principal"""
        self._draw_background()
        
        # Título
        title = self.font_title.render("CLARA", True, (200, 50, 50))
        x = (self.screen.get_width() - title.get_width()) // 2
        self.screen.blit(title, (x, 50))
        
        # Subtítulo
        subtitle = self.font_small.render(
            "Um Jogo de Horror Psicológico em Python",
            True, (150, 150, 150)
        )
        x = (self.screen.get_width() - subtitle.get_width()) // 2
        self.screen.blit(subtitle, (x, 120))
        
        # Opções
        for i, (text, _) in enumerate(self.main_options):
            color = (255, 255, 100) if i == self.selected else (200, 200, 200)
            option_text = self.font_large.render(text, True, color)
            x = (self.screen.get_width() - option_text.get_width()) // 2
            y = 220 + i * 100
            self.screen.blit(option_text, (x, y))
            
            # Seta indicadora
            if i == self.selected:
                arrow = self.font_large.render(">", True, (255, 255, 100))
                self.screen.blit(arrow, (x - 80, y))
    
    def _draw_version_select(self):
        """Menu de seleção de versão"""
        self._draw_background()
        
        title = self.font_large.render("Escolha a Versão", True, (200, 50, 50))
        x = (self.screen.get_width() - title.get_width()) // 2
        self.screen.blit(title, (x, 50))
        
        descriptions = [
            "Versão clássica com gameplay essencial",
            "Versão completa com áudio, gráficos e cinemáticas",
            ""
        ]
        
        for i, (text, _) in enumerate(self.version_options):
            color = (255, 255, 100) if i == self.selected else (200, 200, 200)
            option_text = self.font_large.render(text, True, color)
            x = (self.screen.get_width() - option_text.get_width()) // 2
            y = 150 + i * 100
            self.screen.blit(option_text, (x, y))
            
            # Descrição
            if i < len(descriptions) and descriptions[i]:
                desc = self.font_small.render(descriptions[i], True, (150, 150, 150))
                x_desc = (self.screen.get_width() - desc.get_width()) // 2
                self.screen.blit(desc, (x_desc, y + 40))
            
            if i == self.selected:
                arrow = self.font_large.render(">", True, (255, 255, 100))
                self.screen.blit(arrow, (x - 80, y))
    
    def _draw_difficulty_select(self):
        """Menu de seleção de dificuldade"""
        self._draw_background()
        
        title = self.font_large.render("Nível de Dificuldade", True, (200, 50, 50))
        x = (self.screen.get_width() - title.get_width()) // 2
        self.screen.blit(title, (x, 50))
        
        descriptions = [
            "Para explorar sem pressa",
            "Experiência equilibrada",
            "Desafio real",
            "Pesadelo puro"
        ]
        
        for i, difficulty in enumerate(self.difficulty_options):
            color = (255, 255, 100) if i == self.difficulty_selected else (200, 200, 200)
            option_text = self.font_large.render(difficulty, True, color)
            x = (self.screen.get_width() - option_text.get_width()) // 2
            y = 150 + i * 90
            self.screen.blit(option_text, (x, y))
            
            # Descrição
            desc = self.font_small.render(descriptions[i], True, (150, 150, 150))
            x_desc = (self.screen.get_width() - desc.get_width()) // 2
            self.screen.blit(desc, (x_desc, y + 40))
            
            if i == self.difficulty_selected:
                arrow = self.font_large.render(">", True, (255, 255, 100))
                self.screen.blit(arrow, (x - 80, y))
        
        # Instrução
        instruction = self.font_small.render(
            "ENTER: Confirmar | ESC: Voltar",
            True, (100, 100, 100)
        )
        x = (self.screen.get_width() - instruction.get_width()) // 2
        self.screen.blit(instruction, (x, 550))
    
    def _draw_settings_menu(self):
        """Menu de configurações"""
        self._draw_background()
        
        title = self.font_large.render("Configurações", True, (200, 50, 50))
        x = (self.screen.get_width() - title.get_width()) // 2
        self.screen.blit(title, (x, 50))
        
        for i, (text, _) in enumerate(self.settings_options):
            color = (255, 255, 100) if i == self.selected else (200, 200, 200)
            option_text = self.font_large.render(text, True, color)
            x = (self.screen.get_width() - option_text.get_width()) // 2
            y = 150 + i * 80
            self.screen.blit(option_text, (x, y))
            
            if i == self.selected:
                arrow = self.font_large.render(">", True, (255, 255, 100))
                self.screen.blit(arrow, (x - 80, y))
    
    def _handle_input(self):
        """Processa entrada do usuário"""
        keys = pygame.key.get_pressed()
        
        if self.state == MenuState.MAIN:
            if keys[pygame.K_UP]:
                self.selected = (self.selected - 1) % len(self.main_options)
            elif keys[pygame.K_DOWN]:
                self.selected = (self.selected + 1) % len(self.main_options)
            elif keys[pygame.K_RETURN]:
                action = self.main_options[self.selected][1]
                if action == "start":
                    self.state = MenuState.VERSION_SELECT
                    self.selected = 0
                elif action == "settings":
                    self.state = MenuState.SETTINGS
                    self.selected = 0
                elif action == "quit":
                    return False
        
        elif self.state == MenuState.VERSION_SELECT:
            if keys[pygame.K_UP]:
                self.selected = (self.selected - 1) % len(self.version_options)
            elif keys[pygame.K_DOWN]:
                self.selected = (self.selected + 1) % len(self.version_options)
            elif keys[pygame.K_RETURN]:
                action = self.version_options[self.selected][1]
                if action == "original":
                    return self._launch_game("clara_game.py")
                elif action == "enhanced":
                    return self._launch_game("clara_game_enhanced.py")
                elif action == "back":
                    self.state = MenuState.MAIN
                    self.selected = 0
        
        elif self.state == MenuState.SETTINGS:
            if keys[pygame.K_UP]:
                self.selected = (self.selected - 1) % len(self.settings_options)
            elif keys[pygame.K_DOWN]:
                self.selected = (self.selected + 1) % len(self.settings_options)
            elif keys[pygame.K_RETURN]:
                action = self.settings_options[self.selected][1]
                if action == "difficulty":
                    self.state = MenuState.DIFFICULTY
                    self.difficulty_selected = 1
                elif action == "back":
                    self.state = MenuState.MAIN
                    self.selected = 0
        
        elif self.state == MenuState.DIFFICULTY:
            if keys[pygame.K_UP]:
                self.difficulty_selected = (self.difficulty_selected - 1) % len(self.difficulty_options)
            elif keys[pygame.K_DOWN]:
                self.difficulty_selected = (self.difficulty_selected + 1) % len(self.difficulty_options)
            elif keys[pygame.K_RETURN]:
                # Salvar dificuldade em config
                self._save_difficulty(self.difficulty_selected)
                self.state = MenuState.SETTINGS
            elif keys[pygame.K_ESCAPE]:
                self.state = MenuState.SETTINGS
        
        if keys[pygame.K_ESCAPE]:
            if self.state == MenuState.VERSION_SELECT:
                self.state = MenuState.MAIN
                self.selected = 0
            elif self.state == MenuState.SETTINGS:
                self.state = MenuState.MAIN
                self.selected = 0
        
        return True
    
    def _launch_game(self, script):
        """Inicia o jogo"""
        try:
            pygame.quit()
            subprocess.run([sys.executable, script], check=True)
            return False  # Sair do launcher após jogar
        except Exception as e:
            print(f"Erro ao iniciar jogo: {e}")
            pygame.init()
            return True
    
    def _save_difficulty(self, difficulty_index):
        """Salva dificuldade escolhida"""
        difficulties = ["easy", "normal", "hard", "nightmare"]
        if 0 <= difficulty_index < len(difficulties):
            # Atualizar config.py
            try:
                with open("config.py", "r") as f:
                    content = f.read()
                
                old_line = 'CURRENT_DIFFICULTY = Difficulty.NORMAL'
                new_line = f'CURRENT_DIFFICULTY = Difficulty.{difficulties[difficulty_index].upper()}'
                
                content = content.replace(old_line, new_line)
                
                with open("config.py", "w") as f:
                    f.write(content)
            except:
                pass
    
    def run(self):
        """Loop principal do launcher"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            running = self._handle_input()
            
            self.screen.fill((0, 0, 0))
            
            if self.state == MenuState.MAIN:
                self._draw_main_menu()
            elif self.state == MenuState.VERSION_SELECT:
                self._draw_version_select()
            elif self.state == MenuState.SETTINGS:
                self._draw_settings_menu()
            elif self.state == MenuState.DIFFICULTY:
                self._draw_difficulty_select()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    launcher = LauncherApp()
    launcher.run()
