import pygame
import os

class StaticBG:
    def __init__(self, image_path, width, height):
        self.width = width
        self.height = height
        try:
            # Load the static background image
            original = pygame.image.load(image_path).convert()
            # Scale it to fit the window perfectly
            self.image = pygame.transform.smoothscale(original, (width, height))
        except Exception as e:
            print(f"Error loading background image: {e}")
            self.image = pygame.Surface((width, height))
            self.image.fill((40, 40, 60)) # Dark blue fallback

    def draw(self, screen):
        screen.blit(self.image, (0, 0))

class MenuButton:
    def __init__(self, image_path, x, y, width, height):
        try:
            original = pygame.image.load(image_path).convert_alpha()
            self.base_img = pygame.transform.smoothscale(original, (width, height))
        except:
            # Fallback if image is missing
            self.base_img = pygame.Surface((width, height))
            self.base_img.fill((200, 50, 50))

        self.rect = self.base_img.get_rect(center=(x, y))
        self.current_scale = 1.0
        self.target_scale = 1.0
        self.speed = 0.15

    def update(self, is_hovered):
        self.target_scale = 1.12 if is_hovered else 1.0
        self.current_scale += (self.target_scale - self.current_scale) * self.speed

    def draw(self, screen):
        # Calculate zoomed dimensions
        z_w = int(self.rect.width * self.current_scale)
        z_h = int(self.rect.height * self.current_scale)
        zoomed_img = pygame.transform.smoothscale(self.base_img, (z_w, z_h))
        zoomed_rect = zoomed_img.get_rect(center=self.rect.center)
        screen.blit(zoomed_img, zoomed_rect)

class MainMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # Load the static main_menu.png
        self.bg = StaticBG("assets/main_menu.png", width, height)

        # Keep menu proportional so changing width/height in main config updates this screen too.
        btn_w = int(self.width * 0.34)
        btn_h = int(self.height * 0.24)
        self.btn_start = MenuButton(
            "assets/btn_start.png",
            x=int(self.width * 0.50),
            y=int(self.height * 0.66),
            width=btn_w,
            height=btn_h,
        )
        self.btn_exit = MenuButton(
            "assets/btn_exit.png",
            x=int(self.width * 0.55),
            y=int(self.height * 0.82),
            width=btn_w,
            height=btn_h,
        )

    def draw(self, screen):
        self.bg.draw(screen)

        # Subtle dark overlay to make UI pop
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 30)) 
        screen.blit(overlay, (0, 0))

        m_pos = pygame.mouse.get_pos()
        for btn in [self.btn_start, self.btn_exit]:
            btn.update(btn.rect.collidepoint(m_pos))
            btn.draw(screen)

    def handle_click(self, pos):
        if self.btn_start.rect.collidepoint(pos): return "START"
        if self.btn_exit.rect.collidepoint(pos): return "QUIT"
        return None