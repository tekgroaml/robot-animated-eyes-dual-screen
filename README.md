# Cyber Robot Animated Eyes — Single-HDMI SBS

![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![Graphics](https://img.shields.io/badge/graphics-Pygame%202-green) ![Canvas](https://img.shields.io/badge/canvas-960%C3%97480-purple)

[简体中文](README_CN.md)

Two expressive eyes rendered into **one window**. The left square is Screen A / left eye, the right square Screen B / right eye. The controller receives one HDMI signal and physically splits the side-by-side (SBS) image. There is no second connector or extended-desktop setup. Each eye is drawn separately, including asymmetric curiosity and a slight inter-eye blink delay.

![Software preview](docs/preview.png)

## Files

```text
robot-animated-eyes-dual-screen/
├── docs/
│   └── preview.png
├── tests/
│   └── test_motion.py
├── .gitignore
├── README.md
├── README_CN.md
├── config.py
├── main.py
├── requirements.txt
├── run.sh
└── setup.sh
```

## Wiring and first launch

1. With power off, connect Pi HDMI0 to the dual controller's single HDMI input. Pi 4/5 require micro-HDMI at the Pi end. Attach both panels to the board's A/B ribbon outputs in the labeled orientation.
2. Power the Pi and board with their specified regulated supplies. USB touch/data is optional for this demo; HDMI is not a panel power source.
3. Configure **960×480 at 100% desktop scaling** for dual 480×480 panels using the companion hardware setup repository. The board must support this timing and split mode. Keep the combined desktop unrotated.
4. From a desktop terminal on Raspberry Pi OS Bookworm/Bullseye or a configured Debian desktop:

```bash
chmod +x setup.sh run.sh
./setup.sh
# Install without launching:
./setup.sh --install-only
./run.sh
```

The installer uses Debian's Pygame/SDL package inside a `--system-site-packages` venv, avoiding PEP 668 global pip changes and native wheel compilation on Pi. If unavailable in the venv, pip falls back to `requirements.txt` (Pygame 2.6.1). Debian's installed Pygame can be an older 2.x release. Run as your desktop user, without sudo. A working Wayland/X11 desktop is required; direct DRM/console operation is not configured by these scripts.

For a development monitor or another panel size:

```bash
./run.sh --windowed
./run.sh --size 720 --fps 30       # Requires a 1440×720 SBS desktop
./run.sh --windowed --mouse --expression curious
./run.sh --display 1              # Select another physical SDL output, not eye B
```

Fullscreen refuses a desktop that does not match `2 × size` by `size`, to prevent a plausible-looking but incorrectly split image. The application does not program HDMI timings. A 720 setting requires a dual controller supporting 1440×720; the hardware guide's dual template targets 480 panels only.

## Controls and behavior

| Key | Action |
| --- | --- |
| `N`, `H`, `A`, `C` | Neutral, happy, angry, curious |
| Arrow keys | Look left, right, up, down; disable mouse tracking |
| Space | Center gaze; disable mouse tracking |
| `B` | Blink now; automatic blinking also continues |
| `M` | Toggle mouse tracking |
| Esc / `Q` | Exit |

Transitions use elapsed time and exponential interpolation rather than frame-dependent increments. Random saccades add small gaze changes; blinks follow a smooth closure curve. Mouse coordinates map to the local square under the pointer and drive both eyes, keeping the gaze coherent. `--seed N` gives repeatable animation; `--fps` caps frame rate.

Edit `config.py` for RGB colors (`PUPIL_COLOR`, `IRIS_COLOR`, `SCLERA_COLOR`), fractional `EYE_WIDTH` / `EYE_HEIGHT`, `IRIS_RADIUS`, `PUPIL_DILATION`, blink/saccade intervals and `TRANSITION_SPEED`. Geometry is normalized to one panel. Bright details fit inside a circular visible region. Iris content is clipped to the eye silhouette. The renderer uses CPU Pygame drawing and SDL presentation; no vendor GPU package, OpenGL binding, assets or network service is required.

## Headless validation

```bash
./run.sh --headless --frames 120 --seed 7 --expression angry --screenshot /tmp/eyes.png
```

The SDL dummy driver renders a bounded simulation without a desktop. A saved PNG confirms rendering, not real HDMI splitting, compositor scaling or hardware frame rate. Use `--frames N --screenshot PATH` with a real desktop for a bounded hardware run too. The dummy path uses fixed time steps for reproducibility.

## Cosplay and 3D-printed chassis

Measure the panel's active circle, glass outline, PCB, connector and cable bend radius separately. Model a removable bezel with clearance for glass and an unobstructed active aperture; test a paper template before printing. Keep opaque plastic outside the visible radius, add cable strain relief and ventilation, and isolate exposed electronics from conductive paint/fasteners. Mount A on the robot's left and B on its right, verifying the HDMI mapping before final assembly. Do not rotate the whole SBS output to compensate for mechanically inverted panels; rotate the individual eye surfaces in code if needed. Power off before handling ribbons, and follow the vendor's electrical and thermal limits.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Fullscreen size error | Set the desktop to 960×480 / 100% scale; use `--windowed` on a normal monitor. |
| Same image on both panels | Check that board firmware is in SBS split mode, not hardware mirroring. |
| Eyes swapped or cut at seam | Check A/B cables, exact canvas size, desktop overscan/scale and combined rotation. |
| No video device / Wayland error | Run inside the logged-in desktop; do not run the application with sudo or from plain SSH. |
| High CPU or low FPS | Try `--fps 30`, close composited effects/background apps, check Pi thermal throttling. |
| Pygame import failure | Rerun `./setup.sh --install-only` and use `./run.sh` to select the venv. |

## Integration boundary

`EyeMotion` owns time-based behavior; `render_eye` draws into one half of the canvas. An external robot controller can set `motion.expression`, `motion.target` or call `motion.blink()` in the main loop. Keep SDL calls on the main thread; feed external events through a bounded queue rather than blocking the frame loop. No remote control port is opened. Actual Pi frame rate and controller compatibility require hardware validation.

## Developer verification

```bash
python3 -m unittest discover -s tests -v
```

The 3 standard-library tests cover the core configuration, behavior or input/API boundary. The development verification used macOS, not Raspberry Pi hardware. Shell syntax and Python compilation were checked; the interactive demos were rendered where applicable. APT installation and the actual Pi boot/desktop still require on-device checks.

Older Bullseye images may provide Pygame 1.x. In that case setup installs SDL2/build prerequisites and builds the pinned Pygame 2 fallback if no wheel is available; allow extra installation time and disk space.
