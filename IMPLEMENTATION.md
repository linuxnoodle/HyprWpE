# HyprWpE: Architectural Mapping & Implementation Dynamics

This document details the architectural differences and mapping between the native Windows Wallpaper Engine (WE) and the Linux/Wayland port **HyprWpE**.

## 1. High-Level Architecture

| Component | Original Wallpaper Engine (Windows) | HyprWpE Port (Linux/Wayland) |
| :--- | :--- | :--- |
| **GUI / Control** | Native C++ Windows UI, system tray icon, communicating via IPC with the rendering engine. | Python GTK4 application (`gui.py`), saving state to YAML configs and spawning bash processes. |
| **Window Layering** | Windows Hooks / Desktop Window Manager (DWM) worker threads (draws behind icons). | `gtk4-layer-shell` Protocol (Wayland native) + `mpvpaper`. Draws on the background compositor layer. |
| **Asset Storage** | Proprietary `.pkg` (RePKG format) archives and custom `.tex` texture formats. | Python scripts leveraging the official `RePKG.exe` (run via the `.NET` runtime) to extract `.pkg` and flawlessly decode proprietary `.tex` textures to standard `.png` / `.jpg`. |

## 2. Rendering Engines by Wallpaper Type

Wallpaper Engine handles different wallpaper types by dispatching them to specialized internal engines. HyprWpE mimics this by dispatching to specialized open-source tools and Python scripts.

### A. Video Wallpapers
- **Original Engine:** Uses Media Foundation or a custom video renderer integrated into its DirectX loop. Applies playback rate, mute, and scaling natively.
- **HyprWpE:** Uses **`mpvpaper`**, an efficient video player designed specifically to act as a Wayland background. Settings from the GUI (speed, audio, scale) are passed as `mpv` flags (e.g., `--speed=1.0`, `--no-audio`, `--video-aspect-method=stretch`).

### B. Web Wallpapers
- **Original Engine:** Embeds a CEF (Chromium Embedded Framework) view. Interacts directly with JavaScript via the `window.wallpaperPropertyListener` API.
- **HyprWpE:** Uses **`web_viewer.py`**, which spawns a `WebKitGTK` web view inside a `gtk4-layer-shell` window. Currently provides a visual representation of the web wallpaper, though complex two-way IPC property injection (via JS callbacks) is limited.

### C. Scene Wallpapers (2D/3D)
- **Original Engine:** A proprietary DirectX/OpenGL scene graph engine. It dynamically reads `scene.json`, loads `.tex` textures, runs custom GLSL shaders, and handles complex particle systems and physics.
- **HyprWpE:** Uses **`linux-wallpaperengine`**, a native port of Wallpaper Engine for Linux, to render scene wallpapers. It handles complex particle systems, 3D models, shaders, and video textures natively on the GPU without relying on HTML compositing or fragile WebGL hacks.

## 3. Configuration and State Management

### State Synchronization
- **Original Engine:** Uses internal databases and `.json` configs to track monitors and which wallpaper is active on which screen.
- **HyprWpE:** Uses a file-based state mechanism. `managers/monitor_manager.py` queries `hyprctl monitors` to detect screens. State is saved into two primary files in `~/.config/HyprWpE/`:
  - `wallpapers.yaml`: Maps monitor names (e.g., `DP-1`) to Wallpaper IDs.
  - `properties.yaml`: Stores playback parameters (volume, speed) and global configurations like panel margins.

### Process Lifecycle
- **Original Engine:** Long-running monolithic service (`wallpaper32.exe`/`wallpaper64.exe`).
- **HyprWpE:** Process-based architecture via `HyprWpE.sh`. Each monitor's wallpaper runs as a detached Unix process. The script handles unpacking dependencies to a `/tmp` directory and spawns the correct backend (`mpvpaper`, `web_viewer.py`, or `linux-wallpaperengine`). When a wallpaper is stopped, `HyprWpE.sh` kills the specific PID associated with that screen.

## 4. Current Limitations & Forward Roadmap

- **Scene Features:** Currently, `scene_viewer.py` focuses on 2D image layers. Advanced proprietary systems like particle emitters, complex skeletal animations, and interactive physics present in WE are not fully emulated.
- **JavaScript Interaction:** Web properties customized in the WE UI are not yet dynamically injected into the `WebKitGTK` instances.
- **Extraction Overhead:** Unpacking `.pkg` and converting `.tex` files to standard PNGs on the fly incurs initial loading time not present in the native engine.
