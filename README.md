# NEBULA SWARM

A retro, fixed-screen arcade space shooter written in Python + pygame.
Everything (graphics, sound effects, text) is generated in code — no image,
font or sound files are needed.

## What's in this folder

| File | What it is |
|---|---|
| `nebula_swarm.py` | The whole game (this is the file you run) |
| `requirements.txt` | The one library the game needs (`pygame-ce`) |
| `web/main.py` | An identical copy of the game, named the way the web builder expects |
| `README.md` | These instructions |

The game creates `highscore.json` next to `nebula_swarm.py` the first time a record is set.

---

## 1. Install (one time only)

### Windows
1. Download Python 3.10 or newer from <https://www.python.org/downloads/>.
2. Run the installer and **tick "Add python.exe to PATH"** on the first screen, then click *Install Now*.
3. Open **Command Prompt** (press the Windows key, type `cmd`, press Enter) and run:
   ```
   py -m pip install pygame-ce
   ```

### Mac
1. Download Python 3.10 or newer from <https://www.python.org/downloads/> and run the installer.
2. Open **Terminal** (Cmd + Space, type `Terminal`, press Enter) and run:
   ```
   python3 -m pip install pygame-ce
   ```

> Already have the classic `pygame` installed? The game works with it too — don't install both at once.

---

## 2. Open the project and run the game

1. Unzip `NebulaSwarm.zip` somewhere easy, such as your Desktop.
2. Open a terminal **inside the folder**:
   - **Windows:** open the `NebulaSwarm` folder in File Explorer, click the address bar, type `cmd` and press Enter.
   - **Mac:** right-click the `NebulaSwarm` folder → *New Terminal at Folder*
     (if you don't see it, open Terminal, type `cd ` with a space, drag the folder into the window and press Enter).
3. Run:
   - **Windows:** `py nebula_swarm.py`
   - **Mac:** `python3 nebula_swarm.py`

To edit the game, open the folder in any code editor (VS Code is free: <https://code.visualstudio.com>),
open `nebula_swarm.py`, change something, save, and run it again.

### Controls
| Key | Action |
|---|---|
| ← → or A / D | Move |
| SPACE | Fire (hold for auto-fire) |
| ENTER | Start / continue |
| P | Pause |
| M | Sound on / off |
| ESC | Back to title (on the title screen: quit) |

---

## 3. Tuning the difficulty

All settings are UPPERCASE constants at the top of `nebula_swarm.py`. The most useful ones:

| Constant | Default | Effect |
|---|---|---|
| `PLAYER_START_LIVES` | 3 | Lives at the start |
| `PLAYER_SPEED` | 120 | Ship speed (px/s) |
| `PLAYER_FIRE_COOLDOWN` | 0.25 | Seconds between shots |
| `PLAYER_MAX_BULLETS` | 2 | Your shots on screen at once |
| `INVULNERABLE_TIME` | 2.0 | Protection after respawning |
| `EXTRA_LIFE_SCORE` | 20000 | Score for the bonus life |
| `DIVE_INTERVAL_START` / `DIVE_INTERVAL_MIN` | 3.0 / 1.0 | How often enemies dive |
| `DIVE_MAX_ENEMIES` | 3 | Enemies per dive attack |
| `DIVE_PATH_TIME` | 2.6 | Dive duration (lower = faster dives) |
| `ENEMY_FIRE_CHANCE` | 0.6 | Chance each planned enemy shot is fired |
| `ENEMY_BULLET_SPEED` | 150 | Enemy bullet speed |
| `ENEMY_BULLET_MAX_LIMIT` | 12 | Max enemy bullets on screen |
| `WAVE_DIFFICULTY_STEP` / `DIFFICULTY_MAX_MULT` | 1.10 / 1.8 | How much harder each wave gets, and the cap |

---

## 4. Publishing the game

### Option A — Play in the browser on itch.io (recommended)
Anyone can play from a link, on computer or phone, with nothing to install.

1. Install the web builder (one time):
   - Windows: `py -m pip install pygbag`
   - Mac: `python3 -m pip install pygbag`
2. If you changed the game, copy the new `nebula_swarm.py` over `web/main.py` (same code, different name).
3. From the `NebulaSwarm` folder, test it locally:
   - Windows: `py -m pygbag web`  · Mac: `python3 -m pygbag web`
   - Open <http://localhost:8000> in your browser and click to start. Press Ctrl + C in the terminal to stop.
4. Build the upload file:
   - Windows: `py -m pygbag --archive web`  · Mac: `python3 -m pygbag --archive web`
   - This creates `web/build/web.zip`.
5. Upload to itch.io:
   1. Create a free account at <https://itch.io> → your avatar menu → **Upload new project**.
   2. Title: *Nebula Swarm*. **Kind of project: HTML**.
   3. Upload `web.zip` and tick **"This file will be played in the browser"**.
   4. Embed options: viewport about **480 × 640** (a 2× scale of the game), and turn on the fullscreen button.
   5. Add a description, cover image and screenshots, set **Visibility** to *Public*, then **Save**.

Notes: the first load in the browser takes a few seconds; sound starts after the player clicks the game;
the high score may not be kept between browser visits.

### Option B — A downloadable app (Windows .exe / Mac .app)
Players can double-click it without installing Python.

1. Install PyInstaller: `py -m pip install pyinstaller` (Windows) or `python3 -m pip install pyinstaller` (Mac).
2. Build **on each system you want to support** (a Windows PC makes the .exe; a Mac makes the .app):
   - **Windows:** `py -m PyInstaller --onefile --windowed --name NebulaSwarm nebula_swarm.py`
     → result: `dist\NebulaSwarm.exe`
   - **Mac:** `python3 -m PyInstaller --windowed --name NebulaSwarm nebula_swarm.py`
     → result: `dist/NebulaSwarm.app`
3. Zip the result and share it, or upload it to itch.io as a **Downloadable** project (Windows/Mac tags),
   or attach it to a GitHub Release.

Notes: because the app isn't code-signed, Windows SmartScreen may show "Windows protected your PC"
(players click *More info → Run anyway*), and on Mac players right-click the app → *Open* the first time.

### Option C — Share the source
Zip the `NebulaSwarm` folder and send it, or put it on GitHub. The other person follows sections 1 and 2.
