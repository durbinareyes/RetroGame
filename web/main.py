#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEBULA SWARM
============
A fixed-screen retro arcade shooter inspired by the classic space shooters
of the 1980s. The name, graphics and enemies are all original.

Requirements : Python 3.10+ and pygame 2.x (pygame-ce recommended)
Run with     : python nebula_swarm.py

Everything (pixel-art sprites, synthesized sound effects, text) is generated
in code, so the game needs no external files. The only file it writes is
"highscore.json", saved next to this script.

The main loop is async-friendly (it yields with "await asyncio.sleep(0)"
every frame), so the same file also runs in a web browser through pygbag.
"""

import array
import asyncio
import json
import math
import os
import pathlib
import random
import sys

# Hide pygame's welcome message in the console (must be set before importing pygame).
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402  (imported after setting the environment variable)


# =============================================================================
# CONSTANTS (tweak these to change how the game looks and plays)
# =============================================================================

# ----- Screen and timing -----
SCREEN_W = 240                 # logical width in pixels (vertical arcade screen)
SCREEN_H = 320                 # logical height in pixels
FPS = 60                       # target frames per second
MAX_DT = 0.05                  # max seconds per frame (prevents big jumps)
WINDOW_TITLE = "NEBULA SWARM"

# ----- Retro palette (14 colors) -----
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 170)
DARK_GRAY = (70, 70, 90)
RED = (230, 40, 60)
ORANGE = (255, 140, 30)
YELLOW = (255, 225, 60)
GREEN = (60, 220, 100)
DARK_GREEN = (20, 120, 60)
CYAN = (70, 220, 240)
BLUE = (60, 100, 240)
NAVY = (25, 35, 110)
PURPLE = (170, 70, 230)
PINK = (255, 110, 190)

# Character -> color used by the pixel-art sprites ("." means transparent).
PALETTE = {
    "W": WHITE, "g": GRAY, "k": DARK_GRAY, "R": RED, "O": ORANGE,
    "Y": YELLOW, "G": GREEN, "D": DARK_GREEN, "C": CYAN, "B": BLUE,
    "N": NAVY, "P": PURPLE, "K": PINK,
}

# ----- Fonts (default pygame font, drawn without antialiasing) -----
FONT_SIZE_SMALL = 16
FONT_SIZE_MEDIUM = 24
FONT_SIZE_LARGE = 44

# ----- Player -----
PLAYER_SPEED = 120             # px/s
PLAYER_Y = SCREEN_H - 36       # vertical position of the ship's center
PLAYER_FIRE_COOLDOWN = 0.25    # seconds between shots while SPACE is held
PLAYER_MAX_BULLETS = 2         # player shots allowed on screen at once
PLAYER_BULLET_SPEED = 300      # px/s (upwards)
PLAYER_START_LIVES = 3
EXTRA_LIFE_SCORE = 20000       # one extra life when reaching this score
INVULNERABLE_TIME = 2.0        # seconds of invulnerability after respawning
PLAYER_HITBOX_SHRINK = 6       # hitbox is this many px smaller than the sprite
MAX_LIFE_ICONS = 6             # max life icons drawn in the HUD

# ----- Enemies: hit points and points (in formation / while diving) -----
DRONE_HP = 1
DRONE_POINTS_FORMATION = 50
DRONE_POINTS_DIVE = 100
ESCORT_HP = 1
ESCORT_POINTS_FORMATION = 80
ESCORT_POINTS_DIVE = 160
COMMANDER_HP = 2
COMMANDER_POINTS_FORMATION = 150
COMMANDER_POINTS_DIVE = 400

ENEMY_ANIM_INTERVAL = 0.4      # seconds between animation frames
ENEMY_HITBOX_SHRINK = 4        # hitbox is this many px smaller than the sprite
ENEMY_BULLET_SPEED = 150       # px/s (downwards)
ENEMY_BULLET_BASE_LIMIT = 6    # max enemy bullets = base + wave number,
ENEMY_BULLET_MAX_LIMIT = 12    # capped at this value
ENEMY_FIRE_MIN_GAP = 40        # enemies don't fire when this close above the player

# ----- Formation -----
FORMATION_COLS = 10
FORMATION_SPACING_X = 18
FORMATION_SPACING_Y = 16
FORMATION_TOP = 44             # y of the first row
FORMATION_LEFT = (SCREEN_W - (FORMATION_COLS - 1) * FORMATION_SPACING_X) / 2
FORMATION_SWAY_AMPLITUDE = 14  # px of side-to-side sway
FORMATION_SWAY_SPEED = 1.2     # radians per second
# Rows from top to bottom: (enemy type, how many). Each row is centered.
FORMATION_LAYOUT = (
    ("commander", 4),
    ("escort", 8),
    ("escort", 8),
    ("drone", 10),
    ("drone", 10),
)

# ----- Entry flight at the start of each wave -----
ENTRY_GROUP_SIZE = 8           # enemies per entry group
ENTRY_GROUP_DELAY = 1.4        # seconds between groups
ENTRY_MEMBER_DELAY = 0.12      # seconds between enemies of the same group
ENTRY_PATH_TIME = 2.2          # seconds to fly the entry curve
SETTLE_SPEED = 110             # px/s when sliding into the formation slot

# ----- Dive attacks -----
DIVE_INTERVAL_START = 3.0      # seconds between dive launches in wave 1
DIVE_INTERVAL_STEP = 0.2       # reduction per wave
DIVE_INTERVAL_MIN = 1.0        # never faster than this
DIVE_MIN_ENEMIES = 1
DIVE_MAX_ENEMIES = 3
DIVE_PATH_TIME = 2.6           # seconds for a dive in wave 1 (less = faster)
DIVE_SHOTS_MIN = 1
DIVE_SHOTS_MAX = 2
ENEMY_FIRE_CHANCE = 0.6        # chance each planned dive shot is fired (wave 1)
RETURN_SPEED = 90              # px/s when flying back to the formation

# ----- Difficulty progression -----
WAVE_DIFFICULTY_STEP = 1.10    # +10% dive speed and fire rate per wave,
DIFFICULTY_MAX_MULT = 1.8      # capped at +80% so it stays playable
WAVE_BONUS_PER_WAVE = 1000     # bonus = this x wave number

# ----- State timings -----
WAVE_INTRO_TIME = 2.0          # "WAVE N" message duration
DEATH_PAUSE = 2.0              # pause after the player explodes
GAME_OVER_INPUT_DELAY = 1.0    # ignore ENTER briefly on the game over screen
BLINK_SPEED = 2.5              # blinks per second for blinking text

# ----- Bullets -----
PLAYER_BULLET_SIZE = (2, 5)
ENEMY_BULLET_SIZE = (2, 5)
PLAYER_BULLET_COLOR = YELLOW
ENEMY_BULLET_COLOR = PINK
OWNER_PLAYER = "player"
OWNER_ENEMY = "enemy"

# ----- Particles -----
EXPLOSION_PARTICLES_MIN = 12
EXPLOSION_PARTICLES_MAX = 20
SPARK_PARTICLES = 5
PARTICLE_LIFE = 0.5            # seconds until a particle disappears
PARTICLE_SPEED_MIN = 25
PARTICLE_SPEED_MAX = 95
PARTICLE_DRAG = 2.0            # velocity loss per second
ENEMY_EXPLOSION_COLORS = {
    "drone": (GREEN, CYAN, WHITE, YELLOW),
    "escort": (PURPLE, PINK, YELLOW, WHITE),
    "commander": (BLUE, CYAN, YELLOW, WHITE),
}
PLAYER_EXPLOSION_COLORS = (WHITE, CYAN, RED, ORANGE, YELLOW)
SPARK_COLORS = (WHITE, YELLOW, ORANGE)

# ----- Starfield: (number of stars, speed px/s, color) per layer -----
STAR_LAYERS = (
    (40, 10, DARK_GRAY),
    (25, 25, GRAY),
    (12, 50, WHITE),
)

# ----- Sound -----
SAMPLE_RATE = 22050
SOUND_AMPLITUDE = 0.30         # 0..1, loudness of the generated waves
SOUND_VOLUME = 0.5             # 0..1, pygame volume of every sound

# ----- High score -----
HIGHSCORE_FILE = "highscore.json"


# =============================================================================
# PIXEL-ART SPRITES (each character is a color from PALETTE)
# =============================================================================

PLAYER_SPRITE = (
    "......W......",
    "......W......",
    ".....WCW.....",
    ".....WCW.....",
    "....WWCWW....",
    "R...WBBBW...R",
    "R..WWBBBWW..R",
    "W.WWWWBWWWW.W",
    "WWWWWWWWWWWWW",
    "WWW.RWWWR.WWW",
    "WW...RRR...WW",
    "W....O.O....W",
)

LIFE_ICON_SPRITE = (
    "...W...",
    "..WCW..",
    ".WWBWW.",
    "WWWWWWW",
    "W.RRR.W",
    "...O...",
)

DRONE_FRAME_1 = (
    "..C......C..",
    "...C....C...",
    "...GGGGGG...",
    "..GGGGGGGG..",
    ".GGWWGGWWGG.",
    ".GGWDGGWDGG.",
    "GGGGGGGGGGGG",
    "GDGGGGGGGGDG",
    "G.GD....DG.G",
    "G..G....G..G",
    "...GG..GG...",
    "............",
)

DRONE_FRAME_2 = (
    "...C....C...",
    "..C......C..",
    "...GGGGGG...",
    "..GGGGGGGG..",
    ".GGWWGGWWGG.",
    ".GGDWGGDWGG.",
    "GGGGGGGGGGGG",
    "GDGGGGGGGGDG",
    ".GGD....DGG.",
    "..G......G..",
    ".G........G.",
    "G..........G",
)

ESCORT_FRAME_1 = (
    ".....YY.....",
    "....PYYP....",
    "K..PPPPPP..K",
    "KK.PWPPWP.KK",
    "KKPPWPPWPPKK",
    "KKPPPPPPPPKK",
    ".KKPPPPPPKK.",
    "..K.PPPP.K..",
    "....P..P....",
    "...P....P...",
    "............",
    "............",
)

ESCORT_FRAME_2 = (
    ".....YY.....",
    "K...PYYP...K",
    "KK.PPPPPP.KK",
    "KKKPWPPWPKKK",
    ".KPPWPPWPPK.",
    "..PPPPPPPP..",
    "...PPPPPP...",
    "....PPPP....",
    "....P..P....",
    "....P..P....",
    "............",
    "............",
)

COMMANDER_FRAME_1 = (
    "..Y..YY..Y..",
    "..YYYYYYYY..",
    "...BBBBBB...",
    "..BCCBBCCB..",
    ".BBCWBBCWBB.",
    "BBBBBBBBBBBB",
    "BNBBBNNBBBNB",
    "BN.BBBBBB.NB",
    "B..BN..NB..B",
    "...B....B...",
    "..BB....BB..",
    "............",
)

COMMANDER_FRAME_2 = (
    "..Y..YY..Y..",
    "..YYYYYYYY..",
    "...BBBBBB...",
    "..BCCBBCCB..",
    ".BBWCBBWCBB.",
    "BBBBBBBBBBBB",
    "BNBBBNNBBBNB",
    "BN.BBBBBB.NB",
    ".B.BN..NB.B.",
    "..B......B..",
    "...BB..BB...",
    "............",
)

# After its first hit the Commander changes color: blue -> orange, navy -> red.
COMMANDER_HURT_RECOLOR = {"B": "O", "N": "R", "C": "Y"}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clamp(value, low, high):
    """Limit value to the range [low, high]."""
    return max(low, min(high, value))


def bezier_point(points, t):
    """Return the (x, y) point of a cubic Bezier curve at t (0..1)."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = points
    u = 1.0 - t
    a = u * u * u
    b = 3.0 * u * u * t
    c = 3.0 * u * t * t
    d = t * t * t
    return (a * x0 + b * x1 + c * x2 + d * x3,
            a * y0 + b * y1 + c * y2 + d * y3)


def make_sprite(rows, recolor=None):
    """Turn a list of strings into a pygame Surface with transparency."""
    width = len(rows[0])
    height = len(rows)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == ".":
                continue
            if recolor and char in recolor:
                char = recolor[char]
            surface.set_at((x, y), PALETTE[char])
    return surface.convert_alpha()


def build_sprites():
    """Create every sprite once, after the display has been opened."""
    return {
        "player": make_sprite(PLAYER_SPRITE),
        "life": make_sprite(LIFE_ICON_SPRITE),
        "drone": [make_sprite(DRONE_FRAME_1), make_sprite(DRONE_FRAME_2)],
        "escort": [make_sprite(ESCORT_FRAME_1), make_sprite(ESCORT_FRAME_2)],
        "commander": [make_sprite(COMMANDER_FRAME_1),
                      make_sprite(COMMANDER_FRAME_2)],
        "commander_hurt": [make_sprite(COMMANDER_FRAME_1, COMMANDER_HURT_RECOLOR),
                           make_sprite(COMMANDER_FRAME_2, COMMANDER_HURT_RECOLOR)],
    }


def get_base_dir():
    """Folder where highscore.json lives (next to the script or the .exe)."""
    if getattr(sys, "frozen", False):
        # Packaged with PyInstaller: use the folder of the executable.
        return pathlib.Path(sys.executable).resolve().parent
    try:
        return pathlib.Path(__file__).resolve().parent
    except NameError:
        return pathlib.Path.cwd()


def load_highscore(path):
    """Read the high score; return 0 if the file is missing or corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            data = data.get("highscore", 0)
        return max(0, int(data))
    except (OSError, ValueError, TypeError):
        return 0


def save_highscore(path, value):
    """Save the high score; return False (and keep playing) if it fails."""
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"highscore": int(value)}, file)
        return True
    except (OSError, ValueError):
        return False


def entry_path(group_index, end_point):
    """Bezier control points for an entry group (4 patterns, alternating)."""
    side = group_index % 4
    if side in (0, 1):
        # From the top: sweep down the screen and loop back up.
        points = [(70, -16), (10, 190), (190, 230)]
    else:
        # From the side: come in low and curve up.
        points = [(-16, 210), (150, 270), (200, 40)]
    if side in (1, 3):
        # Mirror the pattern horizontally.
        points = [(SCREEN_W - x, y) for x, y in points]
    return (points[0], points[1], points[2], end_point)


# =============================================================================
# SOUND
# =============================================================================

def prepare_audio():
    """Request a simple audio format before pygame.init(). Returns success."""
    try:
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
        return True
    except Exception:
        return False  # no mixer module: SoundManager will stay silent


class SoundManager:
    """Synthesizes the sound effects in code and plays them safely.

    If audio is not available, every method silently does nothing.
    """

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.sounds = {}
        self.rate = SAMPLE_RATE
        self.channels = 1
        # A broad except is intentional: any audio problem (no device, no mixer
        # module, unsupported format) must leave the game running in silence.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
            mixer_info = pygame.mixer.get_init()
            if not mixer_info:
                return
            frequency, size, channels = mixer_info
            if size != -16:
                return  # unexpected sample format: stay silent
            self.rate = frequency
            self.channels = max(1, channels)
            self.sounds = {
                "shoot": self._make_sound(self._tone(1400, 300, 0.12)),
                "enemy_explode": self._make_sound(self._noise(0.30, 2, 1.5)),
                "player_explode": self._make_sound(self._noise(0.90, 6, 1.2)),
                "wave_start": self._make_sound(
                    self._melody((523, 659, 784, 1047), 0.09)),
                "extra_life": self._make_sound(
                    self._melody((784, 988, 1175, 1568, 1175, 1568), 0.07)),
            }
            self.enabled = True
        except Exception:
            self.enabled = False
            self.sounds = {}

    # ----- Wave generators (return lists of floats between -1 and 1) -----

    def _tone(self, freq_start, freq_end, duration):
        """Square wave that slides from freq_start to freq_end and fades out."""
        count = max(1, int(self.rate * duration))
        samples = []
        phase = 0.0
        for i in range(count):
            t = i / count
            frequency = freq_start + (freq_end - freq_start) * t
            phase += frequency / self.rate
            value = 1.0 if (phase % 1.0) < 0.5 else -1.0
            samples.append(value * (1.0 - t))
        return samples

    def _noise(self, duration, hold, decay_power):
        """White noise that fades out. A bigger 'hold' sounds deeper."""
        count = max(1, int(self.rate * duration))
        samples = []
        value = 0.0
        for i in range(count):
            if i % hold == 0:
                value = random.uniform(-1.0, 1.0)
            envelope = (1.0 - i / count) ** decay_power
            samples.append(value * envelope)
        return samples

    def _melody(self, notes, note_duration):
        """Short square-wave jingle, one short note after another."""
        samples = []
        for frequency in notes:
            samples.extend(self._tone(frequency, frequency, note_duration))
        return samples

    def _make_sound(self, samples):
        """Convert float samples into a pygame Sound (16-bit signed)."""
        data = array.array("h")
        amplitude = 32767 * SOUND_AMPLITUDE
        for sample in samples:
            value = int(clamp(sample, -1.0, 1.0) * amplitude)
            for _ in range(self.channels):
                data.append(value)
        sound = pygame.mixer.Sound(buffer=data.tobytes())
        sound.set_volume(SOUND_VOLUME)
        return sound

    # ----- Public methods -----

    def play(self, name):
        """Play a sound by name (does nothing when muted or without audio)."""
        if not self.enabled or self.muted:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            sound.play()
        except Exception:
            self.enabled = False  # audio broke mid-game: continue in silence

    def toggle_mute(self):
        self.muted = not self.muted


# =============================================================================
# BACKGROUND
# =============================================================================

class Starfield:
    """Three layers of stars moving at different speeds (parallax)."""

    def __init__(self):
        self.layers = []
        for count, speed, color in STAR_LAYERS:
            stars = [[random.uniform(0, SCREEN_W), random.uniform(0, SCREEN_H)]
                     for _ in range(count)]
            self.layers.append((stars, speed, color))

    def update(self, dt):
        for stars, speed, _color in self.layers:
            for star in stars:
                star[1] += speed * dt
                if star[1] >= SCREEN_H:
                    star[1] -= SCREEN_H
                    star[0] = random.uniform(0, SCREEN_W)

    def draw(self, surface):
        last_layer = len(self.layers) - 1
        for index, (stars, _speed, color) in enumerate(self.layers):
            height = 2 if index == last_layer else 1  # fastest stars look streaked
            for x, y in stars:
                surface.fill(color, (int(x), int(y), 1, height))


# =============================================================================
# GAME OBJECTS
# =============================================================================

class Particle:
    """A small square of an explosion that flies outwards and fades."""

    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life = PARTICLE_LIFE
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        slowdown = max(0.0, 1.0 - PARTICLE_DRAG * dt)
        self.vx *= slowdown
        self.vy *= slowdown
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surface):
        # "Fade" in retro style: shrink, then switch to a dark color.
        size = 2 if self.life > PARTICLE_LIFE * 0.5 else 1
        color = self.color if self.life > PARTICLE_LIFE * 0.25 else DARK_GRAY
        surface.fill(color, (int(self.x), int(self.y), size, size))


class Bullet:
    """A shot. 'owner' says whether it belongs to the player or an enemy."""

    def __init__(self, x, y, vy, owner):
        self.x = x
        self.y = y
        self.vy = vy
        self.owner = owner
        self.alive = True
        if owner == OWNER_PLAYER:
            self.width, self.height = PLAYER_BULLET_SIZE
            self.color = PLAYER_BULLET_COLOR
        else:
            self.width, self.height = ENEMY_BULLET_SIZE
            self.color = ENEMY_BULLET_COLOR

    def update(self, dt):
        self.y += self.vy * dt
        if self.y < -10 or self.y > SCREEN_H + 10:
            self.alive = False

    def rect(self):
        return pygame.Rect(int(self.x - self.width / 2),
                           int(self.y - self.height / 2),
                           self.width, self.height)

    def draw(self, surface):
        surface.fill(self.color, self.rect())


class Player:
    """The player's ship at the bottom of the screen."""

    def __init__(self, sprite):
        self.sprite = sprite
        self.width = sprite.get_width()
        self.height = sprite.get_height()
        self.reset()

    def reset(self):
        self.x = SCREEN_W / 2
        self.y = PLAYER_Y
        self.cooldown = 0.0
        self.invulnerable = 0.0
        self.alive = True

    def update(self, dt, keys):
        direction = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction += 1
        self.x += direction * PLAYER_SPEED * dt
        half = self.width / 2
        self.x = clamp(self.x, half, SCREEN_W - half)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)

    def can_fire(self, bullets_on_screen):
        return (self.alive and self.cooldown <= 0
                and bullets_on_screen < PLAYER_MAX_BULLETS)

    def fire(self):
        self.cooldown = PLAYER_FIRE_COOLDOWN
        return Bullet(self.x, self.y - self.height / 2, -PLAYER_BULLET_SPEED,
                      OWNER_PLAYER)

    def is_vulnerable(self):
        return self.alive and self.invulnerable <= 0

    def rect(self):
        rect = pygame.Rect(0, 0, self.width, self.height)
        rect.center = (int(round(self.x)), int(round(self.y)))
        return rect

    def hitbox(self):
        return self.rect().inflate(-PLAYER_HITBOX_SHRINK, -PLAYER_HITBOX_SHRINK)

    def draw(self, surface):
        if not self.alive:
            return
        # Blink while invulnerable.
        if self.invulnerable > 0 and int(self.invulnerable * 10) % 2 == 1:
            return
        surface.blit(self.sprite, self.rect())


class Enemy:
    """A single alien. Moves between four states."""

    ENTERING = "ENTERING"
    IN_FORMATION = "IN_FORMATION"
    DIVING = "DIVING"
    RETURNING = "RETURNING"

    STATS = {
        "drone": (DRONE_HP, DRONE_POINTS_FORMATION, DRONE_POINTS_DIVE),
        "escort": (ESCORT_HP, ESCORT_POINTS_FORMATION, ESCORT_POINTS_DIVE),
        "commander": (COMMANDER_HP, COMMANDER_POINTS_FORMATION,
                      COMMANDER_POINTS_DIVE),
    }

    def __init__(self, kind, row, col, sprites):
        self.kind = kind
        self.row = row
        self.col = col
        self.hp, self.points_formation, self.points_dive = Enemy.STATS[kind]
        self.frames = sprites[kind]
        self.hurt_frames = sprites.get(kind + "_hurt", self.frames)
        self.hurt = False
        self.width = self.frames[0].get_width()
        self.height = self.frames[0].get_height()
        self.x = -100.0
        self.y = -100.0
        self.state = Enemy.ENTERING
        self.alive = True
        self.visible = False          # hidden until its entry flight begins
        self.delay = 0.0              # seconds to wait before entering
        self.settling = False         # True after the entry curve ends
        self.path = None
        self.path_t = 0.0
        self.path_time = 1.0
        self.shots = []               # path progress values where it fires
        self.frame = 0
        self.anim_timer = random.uniform(0, ENEMY_ANIM_INTERVAL)

    # ----- State changes -----

    def start_entry(self, path, delay):
        self.state = Enemy.ENTERING
        self.path = path
        self.path_t = 0.0
        self.path_time = ENTRY_PATH_TIME
        self.delay = delay
        self.visible = False
        self.settling = False
        self.x, self.y = path[0]

    def start_dive(self, target_x, speed_mult, fire_chance):
        self.state = Enemy.DIVING
        side = -1 if self.x < SCREEN_W / 2 else 1  # small loop outwards first
        p0 = (self.x, self.y)
        p1 = (self.x + side * 40, self.y - 36)
        p2 = (clamp(target_x + random.uniform(-40, 40), 10, SCREEN_W - 10),
              SCREEN_H * 0.55)
        p3 = (clamp(target_x + random.uniform(-50, 50), 10, SCREEN_W - 10),
              SCREEN_H + 16)
        self.path = (p0, p1, p2, p3)
        self.path_t = 0.0
        self.path_time = DIVE_PATH_TIME / speed_mult
        planned = random.randint(DIVE_SHOTS_MIN, DIVE_SHOTS_MAX)
        self.shots = sorted(random.uniform(0.25, 0.6) for _ in range(planned)
                            if random.random() < fire_chance)

    # ----- Per-frame logic -----

    def move_towards(self, target_x, target_y, step):
        """Move up to 'step' px towards a point. Return True on arrival."""
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)
        if distance <= step:
            self.x, self.y = target_x, target_y
            return True
        self.x += dx / distance * step
        self.y += dy / distance * step
        return False

    def update(self, dt, formation):
        """Update movement. Returns True if the enemy wants to fire now."""
        self.anim_timer += dt
        if self.anim_timer >= ENEMY_ANIM_INTERVAL:
            self.anim_timer -= ENEMY_ANIM_INTERVAL
            self.frame = 1 - self.frame

        slot_x, slot_y = formation.slot_position(self.row, self.col)
        wants_to_fire = False

        if self.state == Enemy.ENTERING:
            if self.delay > 0:
                self.delay -= dt
                if self.delay > 0:
                    return False
            self.visible = True
            if not self.settling:
                self.path_t = min(1.0, self.path_t + dt / self.path_time)
                self.x, self.y = bezier_point(self.path, self.path_t)
                if self.path_t >= 1.0:
                    self.settling = True
            elif self.move_towards(slot_x, slot_y, SETTLE_SPEED * dt):
                self.state = Enemy.IN_FORMATION

        elif self.state == Enemy.IN_FORMATION:
            self.x, self.y = slot_x, slot_y

        elif self.state == Enemy.DIVING:
            self.path_t += dt / self.path_time
            if self.shots and self.path_t >= self.shots[0]:
                self.shots.pop(0)
                wants_to_fire = True
            if self.path_t >= 1.0:
                # Left the screen at the bottom: reappear at the top.
                self.state = Enemy.RETURNING
                self.x = slot_x
                self.y = -float(self.height)
                self.shots = []
            else:
                self.x, self.y = bezier_point(self.path, self.path_t)

        elif self.state == Enemy.RETURNING:
            if self.move_towards(slot_x, slot_y, RETURN_SPEED * dt):
                self.state = Enemy.IN_FORMATION

        return wants_to_fire

    # ----- Damage and score -----

    def hit(self):
        """Take one hit. Returns True if the enemy is destroyed."""
        self.hp -= 1
        if self.hp <= 0:
            return True
        self.hurt = True
        return False

    def points(self):
        if self.state == Enemy.DIVING:
            return self.points_dive
        return self.points_formation

    def explosion_colors(self):
        if self.hurt:
            return (ORANGE, RED, YELLOW, WHITE)
        return ENEMY_EXPLOSION_COLORS[self.kind]

    # ----- Collision and drawing -----

    def rect(self):
        rect = pygame.Rect(0, 0, self.width, self.height)
        rect.center = (int(round(self.x)), int(round(self.y)))
        return rect

    def hitbox(self):
        return self.rect().inflate(-ENEMY_HITBOX_SHRINK, -ENEMY_HITBOX_SHRINK)

    def draw(self, surface):
        if not self.visible:
            return
        frames = self.hurt_frames if self.hurt else self.frames
        surface.blit(frames[self.frame], self.rect())


class Formation:
    """Grid positions of the swarm and its side-to-side sway."""

    def __init__(self):
        self.time = 0.0

    def reset(self):
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def sway_offset(self):
        return math.sin(self.time * FORMATION_SWAY_SPEED) * FORMATION_SWAY_AMPLITUDE

    @staticmethod
    def base_position(row, col):
        """Slot position without the sway (used as entry target)."""
        return (FORMATION_LEFT + col * FORMATION_SPACING_X,
                FORMATION_TOP + row * FORMATION_SPACING_Y)

    def slot_position(self, row, col):
        x, y = Formation.base_position(row, col)
        return (x + self.sway_offset(), y)

    @staticmethod
    def slots():
        """List of (kind, row, col) for the whole formation, top row first."""
        result = []
        for row, (kind, count) in enumerate(FORMATION_LAYOUT):
            count = min(count, FORMATION_COLS)
            first_col = (FORMATION_COLS - count) // 2
            for i in range(count):
                result.append((kind, row, first_col + i))
        return result


# =============================================================================
# GAME
# =============================================================================

class Game:
    """Main loop, state machine, score, lives and waves."""

    TITLE = "TITLE"
    WAVE_START = "WAVE_START"
    PLAYING = "PLAYING"
    DEATH = "DEATH"
    PAUSED = "PAUSED"
    GAME_OVER = "GAME_OVER"

    ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)

    def __init__(self):
        # Ask for a simple audio format before pygame.init() opens the mixer.
        prepare_audio()
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED)
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.Font(None, FONT_SIZE_SMALL)
        self.font_medium = pygame.font.Font(None, FONT_SIZE_MEDIUM)
        self.font_large = pygame.font.Font(None, FONT_SIZE_LARGE)

        self.sprites = build_sprites()
        self.sound = SoundManager()
        self.starfield = Starfield()
        self.formation = Formation()
        self.player = Player(self.sprites["player"])

        self.highscore_path = get_base_dir() / HIGHSCORE_FILE
        self.highscore = load_highscore(self.highscore_path)

        self.running = True
        self.state = Game.TITLE
        self.state_timer = 0.0
        self.paused_from = Game.PLAYING
        self.blink_timer = 0.0
        self.reset_game()

    # ----- Game setup -----

    def reset_game(self):
        """Put every value back to the start of a new game."""
        self.score = 0
        self.lives = PLAYER_START_LIVES
        self.wave = 0
        self.extra_life_given = False
        self.new_record = False
        self.last_bonus = 0
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.attacks_enabled = False
        self.dive_timer = DIVE_INTERVAL_START
        self.formation.reset()
        self.player.reset()

    def start_game(self):
        self.reset_game()
        self.start_wave(1)

    def start_wave(self, number):
        """Create the swarm for a new wave and show 'WAVE N'."""
        self.wave = number
        self.bullets = []
        self.formation.reset()
        self.enemies = []
        for index, (kind, row, col) in enumerate(Formation.slots()):
            group = index // ENTRY_GROUP_SIZE
            member = index % ENTRY_GROUP_SIZE
            enemy = Enemy(kind, row, col, self.sprites)
            path = entry_path(group, Formation.base_position(row, col))
            delay = group * ENTRY_GROUP_DELAY + member * ENTRY_MEMBER_DELAY
            enemy.start_entry(path, delay)
            self.enemies.append(enemy)
        self.attacks_enabled = False
        self.dive_timer = self.dive_interval()
        self.set_state(Game.WAVE_START)
        self.sound.play("wave_start")

    def set_state(self, new_state):
        self.state = new_state
        self.state_timer = 0.0

    def go_to_title(self):
        self.update_highscore()
        self.reset_game()
        self.set_state(Game.TITLE)

    # ----- Difficulty -----

    def difficulty_mult(self):
        return min(WAVE_DIFFICULTY_STEP ** max(0, self.wave - 1), DIFFICULTY_MAX_MULT)

    def dive_interval(self):
        return max(DIVE_INTERVAL_MIN,
                   DIVE_INTERVAL_START - DIVE_INTERVAL_STEP * max(0, self.wave - 1))

    def enemy_bullet_limit(self):
        return min(ENEMY_BULLET_BASE_LIMIT + self.wave, ENEMY_BULLET_MAX_LIMIT)

    def fire_chance(self):
        return min(1.0, ENEMY_FIRE_CHANCE * self.difficulty_mult())

    # ----- Score and high score -----

    def add_score(self, points):
        self.score += points
        if not self.extra_life_given and self.score >= EXTRA_LIFE_SCORE:
            self.extra_life_given = True
            self.lives += 1
            self.sound.play("extra_life")

    def update_highscore(self):
        """Store a new record (if any) in memory and on disk."""
        if self.score > self.highscore:
            self.highscore = self.score
            self.new_record = True
            save_highscore(self.highscore_path, self.highscore)

    # ----- Input -----

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                self.on_key(event.key)
                if not self.running:
                    return

    def on_key(self, key):
        if key == pygame.K_m:
            self.sound.toggle_mute()
            return

        if self.state == Game.TITLE:
            if key == pygame.K_ESCAPE:
                self.running = False
            elif key in Game.ENTER_KEYS:
                self.start_game()

        elif self.state == Game.GAME_OVER:
            if key == pygame.K_ESCAPE:
                self.go_to_title()
            elif key in Game.ENTER_KEYS and self.state_timer >= GAME_OVER_INPUT_DELAY:
                self.go_to_title()

        else:  # WAVE_START, PLAYING, DEATH, PAUSED
            if key == pygame.K_ESCAPE:
                self.go_to_title()
            elif key == pygame.K_p:
                self.toggle_pause()
            elif key in Game.ENTER_KEYS and self.state == Game.PAUSED:
                self.toggle_pause()

    def toggle_pause(self):
        # The state timer is not reset, so timers continue where they stopped.
        if self.state == Game.PAUSED:
            self.state = self.paused_from
        else:
            self.paused_from = self.state
            self.state = Game.PAUSED

    # ----- Update -----

    def update(self, dt):
        if self.state == Game.PAUSED:
            return  # everything frozen

        self.state_timer += dt
        self.blink_timer += dt
        self.starfield.update(dt)
        self.update_particles(dt)

        if self.state == Game.TITLE:
            return

        if self.state == Game.WAVE_START:
            self.update_player(dt)
            self.update_bullets(dt)
            if self.state_timer >= WAVE_INTRO_TIME:
                self.set_state(Game.PLAYING)

        elif self.state == Game.PLAYING:
            self.update_player(dt)
            self.update_world(dt, allow_dives=True)
            self.handle_collisions()
            self.cleanup()
            if not self.enemies:
                self.wave_cleared()

        elif self.state == Game.DEATH:
            self.update_world(dt, allow_dives=False)
            self.handle_collisions()
            self.cleanup()
            if self.state_timer >= DEATH_PAUSE:
                self.after_death()

        elif self.state == Game.GAME_OVER:
            self.update_world(dt, allow_dives=False)
            self.cleanup()

    def update_player(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        if keys[pygame.K_SPACE] and self.player.can_fire(
                self.count_bullets(OWNER_PLAYER)):
            self.bullets.append(self.player.fire())
            self.sound.play("shoot")

    def update_world(self, dt, allow_dives):
        """Move the formation, enemies and bullets."""
        self.formation.update(dt)

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if enemy.update(dt, self.formation):
                self.enemy_fire(enemy)

        # Enemies only attack once the whole swarm is in formation.
        if not self.attacks_enabled:
            if self.enemies and all(e.state == Enemy.IN_FORMATION
                                    for e in self.enemies if e.alive):
                self.attacks_enabled = True
                self.dive_timer = self.dive_interval()
        elif allow_dives:
            self.dive_timer -= dt
            if self.dive_timer <= 0:
                self.launch_dives()
                self.dive_timer = self.dive_interval()

        self.update_bullets(dt)

    def update_bullets(self, dt):
        for bullet in self.bullets:
            bullet.update(dt)

    def update_particles(self, dt):
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def count_bullets(self, owner):
        return sum(1 for b in self.bullets if b.alive and b.owner == owner)

    def enemy_fire(self, enemy):
        if enemy.y > PLAYER_Y - ENEMY_FIRE_MIN_GAP:
            return  # too close to the player: unfair shot
        if self.count_bullets(OWNER_ENEMY) >= self.enemy_bullet_limit():
            return
        self.bullets.append(Bullet(enemy.x, enemy.y + enemy.height / 2,
                                   ENEMY_BULLET_SPEED, OWNER_ENEMY))

    def launch_dives(self):
        candidates = [e for e in self.enemies
                      if e.alive and e.state == Enemy.IN_FORMATION]
        if not candidates:
            return
        count = random.randint(DIVE_MIN_ENEMIES,
                               max(DIVE_MIN_ENEMIES,
                                   min(DIVE_MAX_ENEMIES, len(candidates))))
        count = min(count, len(candidates))
        for enemy in random.sample(candidates, count):
            enemy.start_dive(self.player.x, self.difficulty_mult(),
                             self.fire_chance())

    # ----- Collisions -----

    def handle_collisions(self):
        # 1) Player bullets against enemies.
        for bullet in self.bullets:
            if not bullet.alive or bullet.owner != OWNER_PLAYER:
                continue
            bullet_rect = bullet.rect()
            for enemy in self.enemies:
                if (enemy.alive and enemy.visible
                        and bullet_rect.colliderect(enemy.hitbox())):
                    bullet.alive = False
                    self.damage_enemy(enemy)
                    break

        if self.state != Game.PLAYING or not self.player.is_vulnerable():
            return
        player_box = self.player.hitbox()

        # 2) Enemy bullets against the player.
        for bullet in self.bullets:
            if (bullet.alive and bullet.owner == OWNER_ENEMY
                    and bullet.rect().colliderect(player_box)):
                bullet.alive = False
                self.kill_player()
                return

        # 3) Diving enemies crashing into the player (both are destroyed).
        for enemy in self.enemies:
            if (enemy.alive and enemy.state == Enemy.DIVING
                    and enemy.hitbox().colliderect(player_box)):
                self.destroy_enemy(enemy)
                self.kill_player()
                return

    def damage_enemy(self, enemy):
        if enemy.hit():
            self.destroy_enemy(enemy)
        else:
            self.spawn_particles(enemy.x, enemy.y, SPARK_COLORS, SPARK_PARTICLES)

    def destroy_enemy(self, enemy):
        enemy.alive = False
        self.add_score(enemy.points())
        self.spawn_particles(enemy.x, enemy.y, enemy.explosion_colors())
        self.sound.play("enemy_explode")

    def kill_player(self):
        self.player.alive = False
        self.lives -= 1
        self.spawn_particles(self.player.x, self.player.y,
                             PLAYER_EXPLOSION_COLORS, EXPLOSION_PARTICLES_MAX)
        self.sound.play("player_explode")
        self.set_state(Game.DEATH)

    def spawn_particles(self, x, y, colors, count=None):
        if count is None:
            count = random.randint(EXPLOSION_PARTICLES_MIN, EXPLOSION_PARTICLES_MAX)
        for _ in range(count):
            self.particles.append(Particle(x, y, random.choice(colors)))

    def cleanup(self):
        """Remove dead objects (never done while iterating the lists)."""
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]

    # ----- Wave and life transitions -----

    def wave_cleared(self):
        bonus = WAVE_BONUS_PER_WAVE * self.wave
        self.add_score(bonus)
        self.last_bonus = bonus
        self.start_wave(self.wave + 1)

    def after_death(self):
        if self.lives > 0:
            self.player.reset()
            self.player.invulnerable = INVULNERABLE_TIME
            self.bullets = [b for b in self.bullets if b.owner == OWNER_PLAYER]
            self.set_state(Game.PLAYING)
        else:
            self.game_over()

    def game_over(self):
        self.new_record = False
        self.update_highscore()
        self.set_state(Game.GAME_OVER)

    # ----- Drawing -----

    def blink_on(self):
        return int(self.blink_timer * BLINK_SPEED * 2) % 2 == 0

    def draw_text(self, text, font, color, x, y, align="center"):
        surface = font.render(text, False, color)
        rect = surface.get_rect()
        if align == "left":
            rect.topleft = (int(x), int(y))
        elif align == "right":
            rect.topright = (int(x), int(y))
        else:
            rect.midtop = (int(x), int(y))
        self.screen.blit(surface, rect)

    def draw(self):
        self.screen.fill(BLACK)
        self.starfield.draw(self.screen)

        if self.state == Game.TITLE:
            self.draw_title()
        else:
            for enemy in self.enemies:
                enemy.draw(self.screen)
            for bullet in self.bullets:
                bullet.draw(self.screen)
            if self.state != Game.GAME_OVER:
                self.player.draw(self.screen)
            for particle in self.particles:
                particle.draw(self.screen)
            self.draw_hud()
            self.draw_overlay()

        pygame.display.flip()

    def draw_title(self):
        center = SCREEN_W / 2
        self.draw_text("NEBULA", self.font_large, CYAN, center, 34)
        self.draw_text("SWARM", self.font_large, PINK, center, 66)
        self.draw_text(f"HIGH SCORE  {self.highscore}", self.font_small,
                       YELLOW, center, 108)

        # Score table with the enemy sprites.
        frame = int(self.blink_timer / ENEMY_ANIM_INTERVAL) % 2
        rows = (
            ("commander", COMMANDER_POINTS_FORMATION, COMMANDER_POINTS_DIVE),
            ("escort", ESCORT_POINTS_FORMATION, ESCORT_POINTS_DIVE),
            ("drone", DRONE_POINTS_FORMATION, DRONE_POINTS_DIVE),
        )
        y = 132
        for kind, points, dive_points in rows:
            self.screen.blit(self.sprites[kind][frame], (46, y))
            self.draw_text(f"{points:>3} PTS   DIVE {dive_points}",
                           self.font_small, WHITE, 66, y + 1, "left")
            y += 18

        if self.blink_on():
            self.draw_text("PRESS ENTER", self.font_medium, WHITE, center, 198)

        controls = (
            "ARROWS / A D   MOVE",
            "SPACE   FIRE",
            "P   PAUSE      M   SOUND",
            "ESC   QUIT",
        )
        y = 236
        for line in controls:
            self.draw_text(line, self.font_small, GRAY, center, y)
            y += 14

    def draw_hud(self):
        # Top: score (left) and high score (center).
        self.draw_text("SCORE", self.font_small, RED, 4, 2, "left")
        self.draw_text(str(self.score), self.font_small, WHITE, 4, 13, "left")
        self.draw_text("HIGH", self.font_small, RED, SCREEN_W / 2, 2)
        self.draw_text(str(max(self.highscore, self.score)), self.font_small,
                       WHITE, SCREEN_W / 2, 13)

        # Bottom: lives (left) and wave (right).
        icon = self.sprites["life"]
        for i in range(clamp(self.lives, 0, MAX_LIFE_ICONS)):
            self.screen.blit(icon, (4 + i * (icon.get_width() + 3), SCREEN_H - 11))
        self.draw_text(f"WAVE {self.wave}", self.font_small, CYAN,
                       SCREEN_W - 4, SCREEN_H - 13, "right")
        if self.sound.muted:
            self.draw_text("SOUND OFF", self.font_small, DARK_GRAY,
                           SCREEN_W / 2, SCREEN_H - 13)

    def draw_overlay(self):
        center = SCREEN_W / 2
        if self.state == Game.WAVE_START:
            self.draw_text(f"WAVE {self.wave}", self.font_medium, YELLOW, center, 140)
            if self.last_bonus > 0:
                self.draw_text(f"BONUS +{self.last_bonus}", self.font_small,
                               GREEN, center, 166)

        elif self.state == Game.PAUSED:
            self.draw_text("PAUSED", self.font_medium, WHITE, center, 140)
            self.draw_text("PRESS P TO CONTINUE", self.font_small, GRAY, center, 166)

        elif self.state == Game.GAME_OVER:
            self.draw_text("GAME OVER", self.font_large, RED, center, 118)
            self.draw_text(f"SCORE  {self.score}", self.font_medium, WHITE,
                           center, 160)
            if self.new_record and self.blink_on():
                self.draw_text("NEW HIGH SCORE!", self.font_medium, YELLOW,
                               center, 184)
            if self.state_timer >= GAME_OVER_INPUT_DELAY:
                self.draw_text("PRESS ENTER", self.font_small, GRAY, center, 214)

    # ----- Main loop -----

    async def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, MAX_DT)
            self.handle_events()
            if not self.running:
                break
            self.update(dt)
            self.draw()
            await asyncio.sleep(0)  # lets the browser breathe when run with pygbag
        self.shutdown()

    def shutdown(self):
        self.update_highscore()  # keep a record even if the window was closed
        pygame.quit()


# =============================================================================
# ENTRY POINT
# =============================================================================

async def main_async():
    game = Game()
    await game.run()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
