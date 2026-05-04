import pygame
import sys
import math
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import os
from dataclasses import dataclass
from collections import deque

# Modular Imports
from pid import PIDController
from editor_engine import ArenaEditor
from interface import MainMenu

# ==========================================
# 1. CONFIGURATION
# ==========================================
class Config:
    # Balanced default ratio: 16:10 works well on laptops and desktops.
    WIDTH, HEIGHT = 1200, 750
    SIDEBAR_RATIO = 0.20
    MIN_SIDEBAR_WIDTH = 230
    ARENA_WIDTH = 0
    TRACK_WIDTH = 20
    FPS = 60
    KP, KI, KD = 0.12, 0.0001, 2.8 
    MAX_SPEED = 2.5
    MIN_SPEED = 1.2
    BORDER_COLOR = (40, 40, 40)
    TELEMETRY_WINDOW_SEC = 4

    @classmethod
    def recalculate(cls):
        sidebar = max(cls.MIN_SIDEBAR_WIDTH, int(cls.WIDTH * cls.SIDEBAR_RATIO))
        sidebar = min(sidebar, cls.WIDTH - 240)
        cls.ARENA_WIDTH = cls.WIDTH - sidebar


Config.recalculate()

PID_LOG_FILE = os.path.join(os.path.dirname(__file__), "pid_tuning.log")
PID_LOG_MAX_ENTRIES = 500


def trim_pid_log(max_entries=PID_LOG_MAX_ENTRIES):
    if max_entries <= 0 or not os.path.exists(PID_LOG_FILE):
        return

    kept_lines = deque(maxlen=max_entries)
    total_lines = 0

    try:
        with open(PID_LOG_FILE, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                kept_lines.append(line)
                total_lines += 1

        if total_lines > max_entries:
            with open(PID_LOG_FILE, "w", encoding="utf-8") as f:
                for line in kept_lines:
                    f.write(f"{line}\n")
    except Exception as e:
        print(f"Could not trim PID log: {e}")


def load_pid_gains():
    if not os.path.exists(PID_LOG_FILE):
        return
    try:
        loaded = False
        with open(PID_LOG_FILE, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) != 4:
                    continue
                try:
                    Config.KP = float(parts[1])
                    Config.KI = float(parts[2])
                    Config.KD = float(parts[3])
                    loaded = True
                except ValueError:
                    continue
        if loaded:
            trim_pid_log()
    except Exception as e:
        print(f"Could not load PID settings: {e}")


def save_pid_gains(kp, ki, kd):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(PID_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{timestamp},{float(kp):.6f},{float(ki):.8f},{float(kd):.6f}\n")
        trim_pid_log()
    except Exception as e:
        print(f"Could not save PID settings: {e}")


@dataclass
class Layout:
    arena_rect: pygame.Rect
    side_rect: pygame.Rect
    tuner_rect: pygame.Rect
    controls_rect: pygame.Rect
    panel_padding: int

    @classmethod
    def from_config(cls):
        pad = max(10, int(Config.HEIGHT * 0.015))
        arena_rect = pygame.Rect(0, 0, Config.ARENA_WIDTH, Config.HEIGHT)
        side_rect = pygame.Rect(Config.ARENA_WIDTH, 0, Config.WIDTH - Config.ARENA_WIDTH, Config.HEIGHT)

        panel_x = side_rect.x + pad
        panel_w = side_rect.width - (2 * pad)
        tuner_h = int(Config.HEIGHT * 0.38)
        tuner_rect = pygame.Rect(panel_x, pad, panel_w, tuner_h)

        controls_y = tuner_rect.bottom + pad
        controls_h = Config.HEIGHT - controls_y - pad
        controls_rect = pygame.Rect(panel_x, controls_y, panel_w, controls_h)
        return cls(arena_rect, side_rect, tuner_rect, controls_rect, pad)

# ==========================================
# 2. UI & CONTROL CLASSES
# ==========================================
class Button:
    def __init__(self, x, y, w, h, text, color=(210, 210, 210)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.font = pygame.font.SysFont("Arial", 12, bold=True)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)
        pygame.draw.rect(screen, (30, 30, 30), self.rect, 1, border_radius=5)
        label = self.font.render(self.text, True, (0, 0, 0))
        screen.blit(label, (self.rect.x + (self.rect.w - label.get_width())//2, 
                            self.rect.y + (self.rect.h - label.get_height())//2))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class ControlPanel:
    def __init__(self, layout):
        self.rect = layout.controls_rect
        btn_w = self.rect.width - (2 * layout.panel_padding)
        btn_h = max(32, int(Config.HEIGHT * 0.047))
        gap = max(8, int(Config.HEIGHT * 0.012))
        btn_x = self.rect.x + layout.panel_padding
        start_y = self.rect.y + max(18, int(Config.HEIGHT * 0.026))

        self.btn_start = Button(btn_x, start_y, btn_w, btn_h, "START/RESUME", (100, 255, 100))
        self.btn_pause = Button(btn_x, start_y + (btn_h + gap), btn_w, btn_h, "PAUSE", (255, 200, 100))
        self.btn_manual = Button(btn_x, start_y + ((btn_h + gap) * 2), btn_w, btn_h, "MANUAL POS", (150, 150, 255))
        self.btn_graph = Button(btn_x, start_y + ((btn_h + gap) * 3), btn_w, btn_h, "OPEN GRAPH", (255, 150, 255))
        
        self.sim_status = "IDLE" 
        self.manual_mode = False
        self.graph_active = False

    def draw(self, screen):
        pygame.draw.rect(screen, (245, 245, 245), self.rect, border_radius=10)
        pygame.draw.rect(screen, (60, 60, 60), self.rect, 2, border_radius=10)
        self.btn_start.draw(screen)
        self.btn_pause.draw(screen)
        self.btn_manual.draw(screen)
        self.btn_graph.draw(screen)
        
        font = pygame.font.SysFont("Arial", 14, bold=True)
        color = (0, 150, 0) if self.sim_status == "RUNNING" else (150, 0, 0)
        status_lbl = font.render(f"STATUS: {self.sim_status}", True, color)
        screen.blit(status_lbl, (self.rect.x + 12, self.rect.bottom - 30))

    def handle_click(self, pos):
        if self.btn_start.is_clicked(pos):
            self.sim_status = "RUNNING"
            self.manual_mode = False
        elif self.btn_pause.is_clicked(pos):
            self.sim_status = "PAUSED"
        elif self.btn_manual.is_clicked(pos):
            self.manual_mode = not self.manual_mode
            if self.manual_mode: self.sim_status = "PAUSED"
        elif self.btn_graph.is_clicked(pos):
            self.graph_active = True
            return "OPEN_GRAPH"
        return None

class LiveTuner:
    def __init__(self, robot, layout):
        self.robot = robot
        self.panel_rect = layout.tuner_rect
        self.params = ["KP", "KI", "KD"]
        self.steps = {"KP": 0.01, "KI": 0.00001, "KD": 0.01}
        self.selected_param = "KP"
        self.row_rects = {}

        row_top = self.panel_rect.y + max(46, int(Config.HEIGHT * 0.062))
        row_step = max(55, int(self.panel_rect.height * 0.28))
        row_h = max(36, int(self.panel_rect.height * 0.16))
        row_x = self.panel_rect.x + layout.panel_padding
        row_w = self.panel_rect.width - (2 * layout.panel_padding)

        for i, p in enumerate(self.params):
            y_pos = row_top + (i * row_step)
            self.row_rects[p] = pygame.Rect(row_x, y_pos, row_w, row_h)

    def _adjust_param(self, param, direction):
        step = self.steps[param]
        if param == "KP":
            self.robot.brain.kp = max(0.0, self.robot.brain.kp + (step * direction))
        elif param == "KI":
            self.robot.brain.ki = max(0.0, self.robot.brain.ki + (step * direction))
        elif param == "KD":
            self.robot.brain.kd = max(0.0, self.robot.brain.kd + (step * direction))
        save_pid_gains(self.robot.brain.kp, self.robot.brain.ki, self.robot.brain.kd)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for param, rect in self.row_rects.items():
                    if rect.collidepoint(event.pos):
                        self.selected_param = param
                        return
            elif event.button == 4 and self.panel_rect.collidepoint(event.pos):
                self._adjust_param(self.selected_param, 1)
            elif event.button == 5 and self.panel_rect.collidepoint(event.pos):
                self._adjust_param(self.selected_param, -1)
        elif event.type == pygame.MOUSEWHEEL:
            if self.panel_rect.collidepoint(pygame.mouse.get_pos()):
                direction = 1 if event.y > 0 else -1
                if direction != 0:
                    self._adjust_param(self.selected_param, direction)

    def draw(self, screen):
        pygame.draw.rect(screen, (245, 245, 245), self.panel_rect, border_radius=10)
        pygame.draw.rect(screen, (60, 60, 60), self.panel_rect, 2, border_radius=10)
        font = pygame.font.SysFont("Arial", 18, bold=True)
        screen.blit(font.render("PID TUNER", True, (0, 0, 0)), (self.panel_rect.x + 12, self.panel_rect.y + 12))
        v_font = pygame.font.SysFont("Courier", 14, bold=True)
        row_top = self.panel_rect.y + max(46, int(Config.HEIGHT * 0.062))
        row_step = max(55, int(self.panel_rect.height * 0.28))

        values = {
            "KP": f"KP: {self.robot.brain.kp:.3f}",
            "KI": f"KI: {self.robot.brain.ki:.5f}",
            "KD": f"KD: {self.robot.brain.kd:.2f}",
        }
        colors = {
            "KP": (200, 0, 0),
            "KI": (0, 150, 0),
            "KD": (0, 0, 200),
        }

        for i, param in enumerate(self.params):
            rect = self.row_rects[param]
            if param == self.selected_param:
                pygame.draw.rect(screen, (220, 235, 255), rect, border_radius=6)
                pygame.draw.rect(screen, (70, 120, 200), rect, 2, border_radius=6)
            else:
                pygame.draw.rect(screen, (238, 238, 238), rect, border_radius=6)
                pygame.draw.rect(screen, (170, 170, 170), rect, 1, border_radius=6)
            label = v_font.render(values[param], True, colors[param])
            screen.blit(label, (rect.x + 10, rect.y + (rect.height - label.get_height()) // 2))

        hint_font = pygame.font.SysFont("Arial", 12, bold=False)
        hint = hint_font.render("Left click to select, mouse wheel to adjust", True, (70, 70, 70))
        screen.blit(hint, (self.panel_rect.x + 12, self.panel_rect.bottom - 22))

# ==========================================
# 3. ROBOT & TELEMETRY
# ==========================================
class TelemetryPlotter:
    def __init__(self):
        plt.ion() 
        self.fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
        self.ax_error = axes[0][0]
        self.ax_control = axes[0][1]
        self.ax_components = axes[1][0]
        self.ax_offset = axes[1][1]

        self.err_line, = self.ax_error.plot([], [], 'r-', linewidth=2, label='Error e(t)')
        self.ctrl_line, = self.ax_control.plot([], [], 'b-', linewidth=2, label='Control u(t)')
        self.p_line, = self.ax_components.plot([], [], color='#d62728', linewidth=1.8, label='P-term')
        self.i_line, = self.ax_components.plot([], [], color='#2ca02c', linewidth=1.8, label='I-term')
        self.d_line, = self.ax_components.plot([], [], color='#1f77b4', linewidth=1.8, label='D-term')
        self.offset_line, = self.ax_offset.plot([], [], color='#9467bd', linewidth=2, label='Lateral offset')
        self.zero_line, = self.ax_offset.plot([], [], 'k--', linewidth=1, alpha=0.6, label='Track center')

        self.ax_error.set_title("Real-time PID Telemetry")
        self.ax_error.set_ylabel("Error e(t)")
        self.ax_error.grid(True)
        self.ax_error.legend(loc="upper right")

        self.ax_control.set_title("Control Signal")
        self.ax_control.set_ylabel("Control u(t)")
        self.ax_control.grid(True)
        self.ax_control.legend(loc="upper right")
        self.ctrl_status_text = self.ax_control.text(0.01, 0.90, "", transform=self.ax_control.transAxes, fontsize=9)

        self.ax_components.set_title("PID Components")
        self.ax_components.set_xlabel("Time (s)")
        self.ax_components.set_ylabel("Term value")
        self.ax_components.grid(True)
        self.ax_components.legend(loc="upper right")
        self.comp_status_text = self.ax_components.text(0.01, 0.90, "", transform=self.ax_components.transAxes, fontsize=9)

        self.ax_offset.set_title("Robot Lateral Offset")
        self.ax_offset.set_xlabel("Time (s)")
        self.ax_offset.set_ylabel("Offset (px)")
        self.ax_offset.grid(True)
        self.ax_offset.legend(loc="upper right")
        self.offset_status_text = self.ax_offset.text(0.01, 0.90, "", transform=self.ax_offset.transAxes, fontsize=9)

        self.fig.tight_layout()
        plt.show(block=False)

    def _set_dynamic_ylim(self, axis, values, min_span=0.05, pad_ratio=0.20):
        if not values:
            return
        v_min = min(values)
        v_max = max(values)
        span = v_max - v_min
        if span < min_span:
            center = (v_min + v_max) * 0.5
            half = min_span * 0.5
            axis.set_ylim(center - half, center + half)
        else:
            pad = span * pad_ratio
            axis.set_ylim(v_min - pad, v_max + pad)

    def _analyze_response(self, controls):
        if len(controls) < 20:
            return "Control analysis: collecting data"

        window = controls[-80:] if len(controls) > 80 else controls
        amplitude = max(window) - min(window)
        mean_abs = float(np.mean(np.abs(window)))
        zero_crossings = sum(
            1 for i in range(1, len(window))
            if (window[i - 1] <= 0 < window[i]) or (window[i - 1] >= 0 > window[i])
        )

        if amplitude > 0.20 and zero_crossings > 10:
            return "Possible oscillation: Kp/Kd may be too high"
        if mean_abs < 0.025:
            return "Possible sluggish response: consider increasing Kp"
        return "Control effort looks stable"

    def _analyze_components(self, i_terms, d_terms):
        if len(i_terms) < 20 or len(d_terms) < 20:
            return "Component analysis: collecting data"

        i_window = i_terms[-120:] if len(i_terms) > 120 else i_terms
        d_window = d_terms[-120:] if len(d_terms) > 120 else d_terms

        i_growth = i_window[-1] - i_window[0]
        d_abs = [abs(v) for v in d_window]
        d_mean = float(np.mean(d_abs))
        d_std = float(np.std(d_window))

        if i_growth > 0.08 and i_window[-1] > 0.12:
            return "I-term rising: possible integral windup"
        if d_std > max(0.03, d_mean * 1.25):
            return "D-term noisy: derivative may be too sensitive"
        return "PID components look balanced"

    def _analyze_offset(self, offsets):
        if len(offsets) < 20:
            return "Offset analysis: collecting data"

        window = offsets[-120:] if len(offsets) > 120 else offsets
        rms = float(np.sqrt(np.mean(np.square(window))))
        if rms > 14:
            return "Large lateral motion: tracking is unstable"
        if rms < 3.0:
            return "Lateral tracking is tight"
        return "Lateral tracking is moderate"

    def update(self, times, errors, controls, p_terms, i_terms, d_terms, offsets):
        if not times or len(times) < 2:
            return

        n = min(len(times), len(errors), len(controls), len(p_terms), len(i_terms), len(d_terms), len(offsets))
        if n < 2:
            return

        t = times[-n:]
        e = errors[-n:]
        u = controls[-n:]
        p = p_terms[-n:]
        i = i_terms[-n:]
        d = d_terms[-n:]
        off = offsets[-n:]

        self.err_line.set_data(t, e)
        self.ctrl_line.set_data(t, u)
        self.p_line.set_data(t, p)
        self.i_line.set_data(t, i)
        self.d_line.set_data(t, d)
        self.offset_line.set_data(t, off)
        self.zero_line.set_data(t, [0.0] * n)

        for ax in [self.ax_error, self.ax_control, self.ax_components, self.ax_offset]:
            ax.set_xlim(max(0, t[-1] - Config.TELEMETRY_WINDOW_SEC), t[-1] + 0.5)

        self._set_dynamic_ylim(self.ax_error, e, min_span=0.5)
        self._set_dynamic_ylim(self.ax_control, u, min_span=0.05)
        combined_terms = p + i + d
        self._set_dynamic_ylim(self.ax_components, combined_terms, min_span=0.08)
        self._set_dynamic_ylim(self.ax_offset, off + [0.0], min_span=6.0)

        self.ctrl_status_text.set_text(self._analyze_response(u))
        self.comp_status_text.set_text(self._analyze_components(i, d))
        self.offset_status_text.set_text(self._analyze_offset(off))

        try:
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        except:
            pass 

class Robot:
    def __init__(self, x, y, angle):
        self.start_pos = (x, y)
        self.start_angle = angle
        self.sensor_offsets = np.array([-35, -25, -15, -5, 5, 15, 25, 35])
        self.weights = np.array([-15, -10, -5, -2, 2, 5, 10, 15])
        self.max_history = 4000
        self.brain = PIDController(Config.KP, Config.KI, Config.KD)
        self.reset()
        try:
            self.img = pygame.image.load(os.path.join(os.path.dirname(__file__), "assets", "robot.png")).convert_alpha()   #try => do this --- except => if try fails , then do this ;
            self.img = pygame.transform.scale(self.img, (50, 45))
        except: 
            self.img = None

    def reset(self):
        self.pos = np.array([float(self.start_pos[0]), float(self.start_pos[1])])
        self.angle = self.start_angle
        self.state, self.search_angle, self.collision_cooldown = "FOLLOWING", 0, 0
        self.history_error, self.history_time = [], []
        self.history_control = []
        self.history_p_term, self.history_i_term, self.history_d_term = [], [], []
        self.history_lateral_offset = []

    def _trim_histories(self):
        if len(self.history_time) <= self.max_history:
            return
        overflow = len(self.history_time) - self.max_history
        del self.history_time[:overflow]
        del self.history_error[:overflow]
        del self.history_control[:overflow]
        del self.history_p_term[:overflow]
        del self.history_i_term[:overflow]
        del self.history_d_term[:overflow]
        del self.history_lateral_offset[:overflow]

    def get_sensor_positions(self):
        fwd = np.array([math.cos(self.angle), math.sin(self.angle)])
        right = np.array([-math.sin(self.angle), math.cos(self.angle)])
        front = self.pos + (fwd * 25)
        return (front + (self.sensor_offsets[:, np.newaxis] * right)).astype(int)

    def step(self, arena_surf):
        if self.collision_cooldown > 0:
            self.collision_cooldown -= 1
            self.angle += 0.12
            self.pos += np.array([math.cos(self.angle), math.sin(self.angle)]) * Config.MIN_SPEED
        else:
            s_pos = self.get_sensor_positions()
            active = [i for i, (px, py) in enumerate(s_pos) if 0 <= px < Config.ARENA_WIDTH and 0 <= py < Config.HEIGHT and arena_surf.get_at((px, py)).r < 100]
            if not active:
                self.state = "SEARCHING"
                self.search_angle += 0.06
                self.angle += math.sin(self.search_angle) * 0.15
                speed = Config.MIN_SPEED
            else:
                self.state = "FOLLOWING"
                self.search_angle = 0
                err = np.mean(self.weights[active])
                control = max(min(self.brain.calculate(err), 0.15), -0.15)
                lateral_offset = float(np.mean(self.sensor_offsets[active]))
                self.angle += control
                speed = Config.MAX_SPEED - (abs(err) * 0.1)
                self.history_error.append(err)
                self.history_time.append(pygame.time.get_ticks() / 1000.0)
                self.history_control.append(control)
                self.history_p_term.append(self.brain.last_p_term)
                self.history_i_term.append(self.brain.last_i_term)
                self.history_d_term.append(self.brain.last_d_term)
                self.history_lateral_offset.append(lateral_offset)
                self._trim_histories()
            self.pos += np.array([math.cos(self.angle), math.sin(self.angle)]) * speed

    def draw(self, screen, arena_surf):
        if self.img:
            rot = pygame.transform.rotate(self.img, -math.degrees(self.angle))
            screen.blit(rot, rot.get_rect(center=(int(self.pos[0]), int(self.pos[1]))))
        for px, py in self.get_sensor_positions():
            try:
                active = arena_surf.get_at((px, py)).r < 100
                pygame.draw.circle(screen, (0,255,0) if active else (180,180,180), (px, py), 4)
            except: pass

class DropdownMenu:
    def __init__(self):
        self.is_open = False
        self.dots_rect = pygame.Rect(Config.ARENA_WIDTH - 40, 10, 30, 30)
        self.edit_btn = Button(Config.ARENA_WIDTH - 150, 45, 140, 35, "Edit Arena", (255, 255, 255))
        self.reset_btn = Button(Config.ARENA_WIDTH - 150, 85, 140, 35, "Reset Robot", (255, 255, 255))

    def draw(self, screen):
        for i in range(3):
            pygame.draw.circle(screen, (50, 50, 50), (self.dots_rect.centerx, self.dots_rect.y + 7 + (i * 8)), 3)
        if self.is_open:
            self.edit_btn.draw(screen)
            self.reset_btn.draw(screen)

    def handle_click(self, pos):
        if self.dots_rect.collidepoint(pos):
            self.is_open = not self.is_open
            return None
        if self.is_open:
            if self.edit_btn.is_clicked(pos): return "EDIT"
            if self.reset_btn.is_clicked(pos): return "RESET"
        self.is_open = False
        return None

# ==========================================
# 4. MAIN RUNTIME
# ==========================================
def main():
    # 1. Initialize Pygame & Screen
    pygame.init()
    Config.recalculate()
    load_pid_gains()
    layout = Layout.from_config()
    screen = pygame.display.set_mode((Config.WIDTH, Config.HEIGHT))
    pygame.display.set_caption("LFR SIM ")
    
    # 2. Setup Arena Surface
    arena_surf = pygame.Surface((Config.ARENA_WIDTH, Config.HEIGHT))
    arena_surf.fill((255, 255, 255))
    
    if os.path.exists("arenas/custom_map.png"):
        try:
            loaded_map = pygame.image.load("arenas/custom_map.png").convert()
            arena_surf = pygame.transform.smoothscale(loaded_map, (Config.ARENA_WIDTH, Config.HEIGHT))
        except:
            print("Could not load custom_map.png, starting with blank arena.")

    # 3. Initialize Modules
    robot_start_y = min(layout.arena_rect.height - 40, int(layout.arena_rect.height * 0.85))
    robot = Robot(150, robot_start_y, -math.pi/2)
    tuner = LiveTuner(robot, layout)
    controls = ControlPanel(layout)
    menu_ui = MainMenu(Config.WIDTH, Config.HEIGHT)
    dropdown = DropdownMenu()
    editor = ArenaEditor(
        Config.ARENA_WIDTH,
        Config.HEIGHT,
        Config.TRACK_WIDTH,
        ui_x=layout.side_rect.x,
        ui_width=layout.side_rect.width,
    )
    
    plotter = None 
    mode = "MENU"
    clock = pygame.time.Clock()

    # 4. Main Application Loop
    while True:
        m_pos = pygame.mouse.get_pos()

        # If the graph window was closed manually, allow reopening it.
        if plotter is not None and not plt.fignum_exists(plotter.fig.number):
            plotter = None
        
        for event in pygame.event.get():
            # Standard Quit Logic
            if event.type == pygame.QUIT:
                if plotter: plt.close('all')
                pygame.quit()
                sys.exit()

            # --- MODE: MAIN MENU ---
            if mode == "MENU":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    selection = menu_ui.handle_click(event.pos)
                    if selection == "START": 
                        mode = "SIMULATION"
                    if selection == "QUIT": 
                        pygame.quit()
                        sys.exit()

            # --- MODE: ARENA EDITOR ---
            elif mode == "EDIT":
                res = editor.handle_event(event, arena_surf)
                if res == "SAVE":
                    editor.save_map(arena_surf)
                    mode = "SIMULATION"
            
            # --- MODE: SIMULATION ---
            elif mode == "SIMULATION":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = dropdown.handle_click(event.pos)
                    
                    if action == "EDIT": 
                        mode = "EDIT"
                        controls.sim_status = "PAUSED"
                    elif action == "RESET": 
                        robot.reset()
                    
                    elif not dropdown.is_open:
                        ctrl_action = controls.handle_click(event.pos)
                        tuner.handle_event(event)
                        
                        if ctrl_action == "OPEN_GRAPH" and plotter is None:
                            plotter = TelemetryPlotter()
                        
                        if controls.manual_mode and event.pos[0] < Config.ARENA_WIDTH:
                            robot.pos = np.array([float(event.pos[0]), float(event.pos[1])])

        # 5. Logic Updates
        if mode == "SIMULATION" and controls.sim_status == "RUNNING":
            robot.step(arena_surf)
            
            if plotter and pygame.time.get_ticks() % 15 == 0:
                plotter.update(
                    robot.history_time,
                    robot.history_error,
                    robot.history_control,
                    robot.history_p_term,
                    robot.history_i_term,
                    robot.history_d_term,
                    robot.history_lateral_offset,
                )

        # 6. Final Rendering Pass
        screen.fill((230, 230, 230)) 
        
        if mode == "MENU":
            menu_ui.draw(screen)
            
        elif mode == "EDIT":
            temp_view = arena_surf.copy()
            editor.draw_shape(temp_view, m_pos)
            screen.blit(temp_view, (0, 0))
            editor.draw_ui(screen, m_pos)
            
        elif mode == "SIMULATION":
            screen.blit(arena_surf, (0, 0))
            robot.draw(screen, arena_surf)
            tuner.draw(screen)
            controls.draw(screen)
            dropdown.draw(screen)
            
            if controls.manual_mode:
                overlay = pygame.Surface((Config.ARENA_WIDTH, Config.HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 100, 255, 25))
                screen.blit(overlay, (0,0))
                f = pygame.font.SysFont("Arial", 16, bold=True)
                msg = f.render("MANUAL PLACEMENT ACTIVE - CLICK ON TRACK", True, (0, 80, 200))
                screen.blit(msg, (20, 20))

        if mode != "MENU":
            b_col = (255, 50, 50) if mode == "EDIT" else Config.BORDER_COLOR
            pygame.draw.rect(screen, b_col, (0, 0, Config.ARENA_WIDTH, Config.HEIGHT), 6)
        
        pygame.display.flip()
        clock.tick(Config.FPS)

if __name__ == "__main__":
    main()