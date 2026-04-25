import pygame
from PIL import Image, ImageSequence
import os

class AnimatedBG:
    def __init__(self, gif_path, width, height):
        self.frames = []
        self.index = 0
        self.last_update = pygame.time.get_ticks()
        self.frame_delay = 60  # Adjust this to change GIF speed (ms)

        try:
            # Open the GIF using Pillow
            pil_gif = Image.open(gif_path)
            for frame in ImageSequence.Iterator(pil_gif):
                # Convert frame to Pygame compatible RGBA format
                frame = frame.convert('RGBA')
                data = frame.tobytes()
                size = frame.size
                surf = pygame.image.fromstring(data, size, 'RGBA')
                
                # Scale each frame to your screen size
                self.frames.append(pygame.transform.scale(surf, (width, height)))
        except Exception as e:
            print(f"Error loading GIF: {e}")

    def draw(self, screen):
        if not self.frames:
            return
        
        # Calculate when to show the next frame
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_delay:
            self.index = (self.index + 1) % len(self.frames)
            self.last_update = now
        
        screen.blit(self.frames[self.index], (0, 0))

class MenuButton:
    def __init__(self, image_path, x, y, width, height):
        # Load the button crop
        try:
            original = pygame.image.load(image_path).convert_alpha()
            self.base_img = pygame.transform.smoothscale(original, (width, height))
        except:
            # Fallback if image is missing
            self.base_img = pygame.Surface((width, height))
            self.base_img.fill((200, 0, 0))
            
        self.rect = self.base_img.get_rect(center=(x, y))
        
        # Animation state
        self.current_scale = 1.0
        self.target_scale = 1.0
        self.speed = 0.15

    def update(self, is_hovered):
        self.target_scale = 1.12 if is_hovered else 1.0
        # Smoothly zoom the button (Linear Interpolation)
        self.current_scale += (self.target_scale - self.current_scale) * self.speed

    def draw(self, screen):
        # Calculate the new 'zoomed' size
        z_w = int(self.rect.width * self.current_scale)
        z_h = int(self.rect.height * self.current_scale)
        
        # Scale and draw centered on the original position
        zoomed_img = pygame.transform.smoothscale(self.base_img, (z_w, z_h))
        zoomed_rect = zoomed_img.get_rect(center=self.rect.center)
        screen.blit(zoomed_img, zoomed_rect)

class MainMenu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # Initialize GIF Background (Make sure background.gif is in the folder)
        self.bg = AnimatedBG("assets/background.gif", width, height)

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
        # 1. Draw the GIF
        if self.bg:
            self.bg.draw(screen)
        else:
            screen.fill((30, 30, 50)) # Fallback if GIF fails

        # 2. Add a slight tint overlay (makes buttons pop against busy GIFs)
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 30)) 
        screen.blit(overlay, (0, 0))

        m_pos = pygame.mouse.get_pos()

        # 3. Update and draw your buttons
        for btn in [self.btn_start, self.btn_exit]:
            is_hover = btn.rect.collidepoint(m_pos)
            btn.update(is_hover)
            btn.draw(screen)

    def handle_click(self, pos):
        if self.btn_start.rect.collidepoint(pos):
            return "START"
        if self.btn_exit.rect.collidepoint(pos):
            return "QUIT"
        return None