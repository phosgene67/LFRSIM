import pygame
import math
import os

class EditorButton:
    def __init__(self, x, y, w, h, text, color=(210, 210, 210)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.font = pygame.font.SysFont("Arial", 14, bold=True)

    def draw(self, screen, is_active=False):
        draw_color = (255, 255, 150) if is_active else self.color
        pygame.draw.rect(screen, draw_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, (30, 30, 30), self.rect, 1, border_radius=5)
        label = self.font.render(self.text, True, (0, 0, 0))
        screen.blit(label, (self.rect.x + (self.rect.w - label.get_width())//2, 
                            self.rect.y + (self.rect.h - label.get_height())//2))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class ArenaEditor:
    def __init__(self, arena_width, height, track_width, ui_x, ui_width):
        self.width = arena_width
        self.height = height
        self.track_width = track_width
        self.ui_x = ui_x
        self.ui_width = ui_width
        self.ui_padding = max(10, int(self.height * 0.015))
        self.active_tool = "Line"
        self.tools = ["Line", "Circle", "Curve", "Eraser"]
        self.panel_button_w = self.ui_width - (2 * self.ui_padding)
        self.panel_button_h = max(36, int(self.height * 0.05))
        self.panel_gap = max(8, int(self.height * 0.012))
        self.tools_top = int(self.height * 0.42)
        self.tool_buttons = [
            EditorButton(
                self.ui_x + self.ui_padding,
                self.tools_top + (i * (self.panel_button_h + self.panel_gap)),
                self.panel_button_w,
                self.panel_button_h,
                t,
            )
            for i, t in enumerate(self.tools)
        ]
        clear_y = self.height - ((self.panel_button_h + self.ui_padding) * 2) - self.panel_gap
        self.clear_btn = EditorButton(
            self.ui_x + self.ui_padding,
            clear_y,
            self.panel_button_w,
            self.panel_button_h,
            "CLEAR ALL",
            (255, 170, 170),
        )
        save_y = self.height - self.panel_button_h - self.ui_padding
        self.save_btn = EditorButton(
            self.ui_x + self.ui_padding,
            save_y,
            self.panel_button_w,
            self.panel_button_h,
            "SAVE & EXIT",
            (100, 255, 100),
        )
        self.start_pos = None

    def handle_event(self, event, arena_surf):
        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, btn in enumerate(self.tool_buttons):
                if btn.is_clicked(event.pos):
                    self.active_tool = self.tools[i]
                    return None
            if self.clear_btn.is_clicked(event.pos):
                arena_surf.fill((255, 255, 255))
                self.start_pos = None
                return None
            if self.save_btn.is_clicked(event.pos):
                return "SAVE"
            if event.pos[0] < self.width:
                self.start_pos = event.pos
                # For Eraser, we start acting immediately
                if self.active_tool == "Eraser":
                    pygame.draw.circle(arena_surf, (255, 255, 255), event.pos, self.track_width)

        if event.type == pygame.MOUSEMOTION and self.start_pos:
            # Upgrade: Continuous Eraser Brush
            if self.active_tool == "Eraser" and event.pos[0] < self.width:
                pygame.draw.circle(arena_surf, (255, 255, 255), event.pos, self.track_width)

        if event.type == pygame.MOUSEBUTTONUP:
            if self.start_pos and self.active_tool != "Eraser":
                self.draw_shape(arena_surf, event.pos, is_preview=False)
            self.start_pos = None
        return None

    def draw_shape(self, surface, current_pos, is_preview=True):
        if not self.start_pos: return
        color = (0, 0, 0)
        thickness = self.track_width
        
        if self.active_tool == "Line":
            pygame.draw.line(surface, color, self.start_pos, current_pos, thickness)
            pygame.draw.circle(surface, color, self.start_pos, thickness // 2)
            pygame.draw.circle(surface, color, current_pos, thickness // 2)
        elif self.active_tool == "Circle":
            radius = int(math.hypot(current_pos[0]-self.start_pos[0], current_pos[1]-self.start_pos[1]))
            pygame.draw.circle(surface, color, self.start_pos, radius, thickness)
        elif self.active_tool == "Curve":
            rect = pygame.Rect(0, 0, abs(current_pos[0]-self.start_pos[0])*2, abs(current_pos[1]-self.start_pos[1])*2)
            rect.center = self.start_pos
            pygame.draw.arc(surface, color, rect, 0, math.pi, thickness)

    def draw_ui(self, screen, m_pos):
        pygame.draw.rect(screen, (200, 200, 200), (self.ui_x, 0, self.ui_width, self.height))
        header_font = pygame.font.SysFont("Arial", 20, bold=True)
        header_x = self.ui_x + self.ui_padding
        header_y = self.tools_top - 40
        screen.blit(header_font.render("EDITOR TOOLS", True, (0, 0, 0)), (header_x, header_y))
        for btn in self.tool_buttons:
            btn.draw(screen, is_active=(btn.text == self.active_tool))
        self.clear_btn.draw(screen)
        self.save_btn.draw(screen)
        
        # Cursor Preview for Eraser
        if self.active_tool == "Eraser" and m_pos[0] < self.width:
            pygame.draw.circle(screen, (100, 100, 100), m_pos, self.track_width, 1)

    def save_map(self, surface):
        os.makedirs("arenas", exist_ok=True)
        pygame.image.save(surface, "arenas/custom_map.png")