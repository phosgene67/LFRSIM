# PIDsim - Line Follower Robot Simulation and Arena Designer

PIDsim is a desktop simulation project for learning and experimenting with PID-controlled line following robots.
It combines three things in one app:

1. A visual robot simulation (Pygame).
2. A track/arena editor to draw custom paths.
3. A live PID tuner with telemetry plotting.

The project is intentionally modular so other developers (and other AI models) can extend it safely.

## What This Project Does

- Simulates a line follower robot moving on a 2D arena.
- Uses an 8-sensor style virtual array to detect track position error.
- Applies a PID controller to convert error into steering correction.
- Allows real-time tuning of `KP`, `KI`, and `KD` during runtime.
- Stores tuned PID values to a bounded log and reloads them on startup.
- Lets users design custom tracks with line/circle/curve/eraser tools.
- Supports runtime controls: start, pause, manual placement, reset, and live graph.
- Shows a 4-panel real-time telemetry dashboard for deeper PID understanding.

## How It Works (High-Level)

At runtime the app cycles through three modes:

1. `MENU`: Start/Quit screen.
2. `SIMULATION`: Robot follows the track while UI controls are active.
3. `EDIT`: Arena editor where the user draws/edits the map.

Core simulation loop (simplified):

1. Read events (mouse input, mode switches, tuner input).
2. If in simulation and running, compute robot step.
3. Update telemetry plot if enabled.
4. Render arena + robot + side panels.
5. Repeat at configured FPS.

## PID Control Logic (How the Robot Steers)

The controller output is:

$$
u = K_p e + K_i \int e\,dt + K_d \frac{de}{dt}
$$

Where:

- $e$ is line position error computed from active sensor weights.
- $K_p$ handles immediate correction.
- $K_i$ removes steady-state bias (with windup guard).
- $K_d$ dampens oscillation by reacting to error slope.

Implementation details in this project:

- 8 virtual sensors are projected in front of the robot.
- Active sensors are those over dark pixels (`r < 100`).
- Error is the mean of predefined sensor weights.
- Steering change is clamped to keep behavior stable.
- Integral memory is clamped to reduce runaway accumulation.

## Main Features

- Real-time robot simulation in a split arena + side-panel layout.
- Live PID tuning:
	- Left-click to select `KP`, `KI`, or `KD` row.
	- Mouse wheel to increase/decrease selected gain.
- Runtime control panel:
	- Start/Resume
	- Pause
	- Manual placement mode
	- Open telemetry graph
- Dropdown actions inside simulation:
	- Edit arena
	- Reset robot
- Arena editor tools:
	- Line
	- Circle
	- Curve
	- Eraser brush
- Persistent custom map saved to `arenas/custom_map.png`.
- Persistent PID tuning history in `pid_tuning.log`.
- Bounded PID tuning log retention (keeps latest entries to control storage growth).
- Advanced telemetry dashboard (`OPEN GRAPH`) with four synchronized plots:
	- Error `e(t)` vs time
	- Control signal `u(t)` vs time
	- Separate PID terms: `P-term`, `I-term`, `D-term`
	- Robot lateral offset vs track center (physical motion view)
- Learning-oriented live diagnostics in graphs:
	- Control signal hints for possible oscillation or sluggish response
	- PID component hints for potential integral windup (`I-term`) and derivative noise (`D-term`)
	- Lateral motion stability hint from RMS offset
- Zoomed telemetry time scale for visibility (short moving window, currently 4 seconds).

## Architecture Overview

### Module Boundaries

- `main_pro.py`: Orchestrator and runtime state machine.
- `pid.py`: Pure PID control math and controller memory.
- `editor_engine.py`: Arena editing toolset and editor UI.
- `interfaceStatic.py`: Current main menu implementation (static background image).
- `interface.py`: Alternative/legacy animated menu implementation (GIF background).

### Runtime Data Flow

1. `main_pro.py` creates config/layout and initializes modules.
2. `Robot` (in `main_pro.py`) requests corrections from `PIDController` (`pid.py`).
3. `LiveTuner` updates controller gains and writes tuning history.
4. `ArenaEditor` draws onto the arena surface and saves map snapshots.
5. `TelemetryPlotter` receives robot error history and refreshes Matplotlib graph.
6. `TelemetryPlotter` also receives control signal, P/I/D components, and lateral offset for synchronized analysis.

## File-by-File Documentation

### `main_pro.py`
Main entry point and application coordinator.

Responsibilities:

- Defines global `Config` and responsive layout calculations.
- Loads and saves PID gains (`pid_tuning.log`).
- Owns UI classes for runtime control:
	- `Button`
	- `ControlPanel`
	- `LiveTuner`
	- `DropdownMenu`
- Defines simulation classes:
	- `Robot`
	- `TelemetryPlotter`
- Streams multi-channel telemetry (`error`, `control`, `P`, `I`, `D`, lateral offset) into the graph window.
- Runs the app mode state machine (`MENU`, `SIMULATION`, `EDIT`).

Why it exists:

- This file centralizes app flow, event dispatch, and render loop so all modules can stay focused and reusable.

### `pid.py`
Standalone PID controller implementation.

Responsibilities:

- Stores gain parameters (`kp`, `ki`, `kd`).
- Stores controller state (`prev_error`, `integral`).
- Computes control output from error and timestep.
- Prevents integral windup with clamping.
- Exposes last computed terms (`last_p_term`, `last_i_term`, `last_d_term`, `last_output`) for live telemetry.
- Provides `reset()` to clear controller memory.

Why it exists:

- Keeps control math isolated from UI and simulation rendering.
- Easy to unit test and reuse in other projects.

### `editor_engine.py`
Arena editing engine and editor-side UI controls.

Responsibilities:

- Tool selection UI (`Line`, `Circle`, `Curve`, `Eraser`).
- Mouse interaction handling for drawing.
- Shape rendering logic and eraser brush behavior.
- Save arena to `arenas/custom_map.png`.

Why it exists:

- Separates map-authoring logic from simulation logic.
- Makes editor behavior easier to extend with new tools later.

### `interfaceStatic.py`
Main menu with static background image (`assets/main_menu.png`).

Responsibilities:

- Draws menu background and button hover animation.
- Handles start/quit click detection.
- Provides a clean UI entry point used by `main_pro.py`.

Why it exists:

- Keeps menu rendering decoupled from simulation runtime.
- Current production menu module used by the app.

### `interface.py`
Alternative/legacy menu implementation with animated GIF background.

Responsibilities:

- Loads GIF frames with Pillow.
- Animates background using frame delay updates.
- Draws same style Start/Quit buttons.

Why it exists:

- Preserved as an alternative style implementation and reference.
- Useful if contributors want animated menu behavior.

### `tempCodeRunnerFile.py`
Temporary file generated by VS Code in some run/debug workflows.

Why it exists:

- Not a core project module.
- Safe to ignore for architecture and feature development.

### `arenas/`
Holds saved track maps.

- `custom_map.png`: Last saved user-defined arena loaded at startup if present.

### `assets/`
Holds visual assets used by menu and robot rendering.

Observed assets:

- `main_menu.png` (static menu background)
- `background.gif` (animated menu background option)
- `btn_start.png`
- `btn_exit.png`
- `button.png`
- `robot.png`

### Generated Runtime File: `pid_tuning.log`
Appends timestamped PID values whenever live tuning changes.

Why it exists:

- Provides persistent tuning history.
- Last valid entry is loaded on next startup.
- Log is auto-trimmed so history stays bounded (latest entries are kept).

## Dependencies

Required Python packages:

- `pygame`
- `numpy`
- `matplotlib`
- `Pillow`

Suggested install command:

```bash
pip install pygame numpy matplotlib pillow
```

## How To Run

From project root:

```bash
python main_pro.py
```

## Basic Usage Guide

1. Launch app and click `START`.
2. Use `START/RESUME` in side panel to run robot.
3. Tune PID:
	 - Left-click `KP`, `KI`, or `KD` row.
	 - Scroll wheel up/down to adjust.
4. Toggle `MANUAL POS` to place robot by clicking inside arena.
5. Open telemetry graph with `OPEN GRAPH`.
6. Read the four telemetry panels:
	- Error plot for tracking deviation trend
	- Control plot for controller aggressiveness
	- P/I/D plot for term-level tuning insight
	- Lateral offset plot for physical movement around track center
7. Watch the status text in graph panels for quick tuning hints.
8. Use top-left 3-dot menu in arena to:
	 - Enter editor
	 - Reset robot
9. In editor mode, draw track and click `SAVE & EXIT`.

## Contribution Notes (For Humans and AI Models)

If you are extending this project, follow these boundaries:

- Put PID math changes in `pid.py`.
- Put arena drawing/edit changes in `editor_engine.py`.
- Keep app state transitions and event routing in `main_pro.py`.
- Keep menu visual work in `interfaceStatic.py` (or `interface.py` if intentionally switching).

Recommended safe extension points:

- Add new editor tools in `ArenaEditor.tools` and `draw_shape`.
- Add new control panel actions in `ControlPanel`.
- Add advanced tuner modes in `LiveTuner` (fine/coarse, reset-to-default, profiles).
- Add richer telemetry metrics in `TelemetryPlotter`.
- Tune analysis thresholds in `TelemetryPlotter` if your arena/speed profile differs.

## Known Limitations

- Physics is intentionally simple (kinematic steering, not full dynamics).
- Error detection depends on pixel thresholding and drawn track quality.
- No automated tests yet for PID/controller or editor tools.
- `interface.py` and `interfaceStatic.py` overlap in responsibility; one is currently active.
- Telemetry diagnostics are heuristic guides, not formal control-theory guarantees.

## Suggested Next Improvements

- Add unit tests for `PIDController` math and reset behavior.
- Add a `requirements.txt` and optional `pyproject.toml`.
- Add config persistence for window size and robot parameters.
- Add keyboard shortcuts for simulation and editor tools.
- Add CI checks (lint + tests) to support easier collaboration.

