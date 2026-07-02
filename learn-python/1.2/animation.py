"""Frame animation and particle effects for the terminal pet."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

ESC = "\x1b"
RESET = f"{ESC}[0m"


def c(code: str) -> str:
    return f"{ESC}[{code}m"


@dataclass
class Animation:
    """A sequence of ASCII art frames."""
    frames: list[list[str]]
    fps: float = 8.0
    loop: bool = False
    _timer: float = 0.0
    _index: int = 0
    _done: bool = False

    @property
    def current(self) -> list[str]:
        return self.frames[self._index]

    @property
    def done(self) -> bool:
        return self._done and not self.loop

    def tick(self, dt: float) -> None:
        if self.done:
            return
        self._timer += dt
        frame_dur = 1.0 / self.fps
        if self._timer >= frame_dur:
            self._timer -= frame_dur
            self._index += 1
            if self._index >= len(self.frames):
                if self.loop:
                    self._index = 0
                else:
                    self._index = len(self.frames) - 1
                    self._done = True

    def reset(self) -> None:
        self._timer = 0.0
        self._index = 0
        self._done = False


@dataclass
class Particle:
    """A single floating particle in terminal space."""
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    char: str
    color: str

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def alpha(self) -> float:
        return self.life / self.max_life


class ParticleSystem:
    """Manages a pool of particles."""

    def __init__(self, max_particles: int = 30) -> None:
        self.max_particles = max_particles
        self.particles: list[Particle] = []

    def spawn(
        self,
        x: float,
        y: float,
        char: str,
        color: str,
        count: int = 6,
        spread: float = 3.0,
        life: float = 1.5,
        vy_boost: float = -2.0,
    ) -> None:
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                self.particles.pop(0)
            self.particles.append(
                Particle(
                    x=x + random.uniform(-spread * 0.5, spread * 0.5),
                    y=y + random.uniform(-0.3, 0.3),
                    vx=random.uniform(-spread, spread),
                    vy=random.uniform(-spread, spread) + vy_boost,
                    life=life + random.uniform(0, 0.5),
                    max_life=life + 0.5,
                    char=char,
                    color=color,
                )
            )

    def tick(self, dt: float) -> None:
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
        self.particles = [p for p in self.particles if p.alive]

    def render_at(self, offset_x: int, offset_y: int) -> dict[tuple[int, int], str]:
        """Return dict of (col, row) -> colored char for particles."""
        result: dict[tuple[int, int], str] = {}
        for p in self.particles:
            px = int(round(p.x + offset_x))
            py = int(round(p.y + offset_y))
            if (px, py) not in result and p.alpha > 0.3:
                result[(px, py)] = c(p.color) + p.char + RESET
        return result


# ── Pet frame builders ──

def make_pet_frame(eyes: str, mouth: str, body_color: str, eye_color: str = "38;5;231") -> list[str]:
    """Build a standard-sized pet frame."""
    bc = body_color
    ec = eye_color
    return [
        f"{c(bc)}╭────────────╮{RESET}",
        f"{c(bc)}│   ░░░░░░   │{RESET}",
        f"{c(bc)}│ ░░▓▓▓▓▓▓░░ │{RESET}",
        f"{c(bc)}│░▓▓ {c(ec)}{eyes}{RESET}{c(bc)} ▓▓░│{RESET}",
        f"{c(bc)}│░▓▓  {c(ec)}{mouth}{RESET}{c(bc)}  ▓▓░│{RESET}",
        f"{c(bc)}│░▓▓▓▓▓▓▓▓▓▓▓░│{RESET}",
        f"{c(bc)}│  ░░╱  ╲░░  │{RESET}",
        f"{c(bc)}╰────────────╯{RESET}",
    ]


def make_pet_frame_small(eyes: str, mouth: str, body_color: str) -> list[str]:
    """Child-stage smaller frame."""
    bc = body_color
    return [
        f"{c(bc)} ╭──────────╮ {RESET}",
        f"{c(bc)} │ ░░▓▓▓▓░░ │ {RESET}",
        f"{c(bc)} │░▓ {eyes} ▓░│ {RESET}",
        f"{c(bc)} │░▓  {mouth}  ▓░│ {RESET}",
        f"{c(bc)} ╰──────────╯ {RESET}",
    ]


def make_pet_frame_large(eyes: str, mouth: str, body_color: str) -> list[str]:
    """Mature-stage larger frame with crown."""
    bc = body_color
    return [
        f"{c('38;5;220')}    ♛ ♛ ♛    {RESET}",
        f"{c(bc)}╭──────────────╮{RESET}",
        f"{c(bc)}│   ░░░░░░░░   │{RESET}",
        f"{c(bc)}│ ░░▓▓▓▓▓▓▓▓░░ │{RESET}",
        f"{c(bc)}│░▓▓  {eyes}  ▓▓░│{RESET}",
        f"{c(bc)}│░▓▓   {mouth}   ▓▓░│{RESET}",
        f"{c(bc)}│░▓▓▓▓▓▓▓▓▓▓▓▓▓░│{RESET}",
        f"{c(bc)}│   ░░╱   ╲░░   │{RESET}",
        f"{c(bc)}╰──────────────╯{RESET}",
    ]


# ── Action animation presets ──

FEED_ANIM = Animation(
    frames=[
        make_pet_frame("◕ ◕", "﹏", "38;5;45"),
        make_pet_frame("◕ ◕", "o", "38;5;45"),
        make_pet_frame("^ ^", "o", "38;5;45"),
        make_pet_frame("^ ^", "ᵔ", "38;5;45"),
        make_pet_frame("◕ ◕", "ᵔ", "38;5;45"),
    ],
    fps=6.0,
)

PLAY_ANIM = Animation(
    frames=[
        make_pet_frame("✦ ✦", "◡", "38;5;213"),
        make_pet_frame("✧ ✧", "◡", "38;5;219"),
        make_pet_frame("✦ ✦", "◡", "38;5;213"),
        make_pet_frame("✧ ✧", "◡", "38;5;219"),
        make_pet_frame("✦ ✦", "◡", "38;5;213"),
    ],
    fps=7.0,
)

CLEAN_ANIM = Animation(
    frames=[
        make_pet_frame("˘ ˘", "﹍", "38;5;87"),
        make_pet_frame("^ ^", "﹍", "38;5;87"),
        make_pet_frame("^ ^", "ᵔ", "38;5;87"),
        make_pet_frame("◕ ◕", "▿", "38;5;87"),
        make_pet_frame("◕ ◕", "▿", "38;5;87"),
    ],
    fps=6.0,
)

PET_ANIM = Animation(
    frames=[
        make_pet_frame("◕ ◕", "ᵔ", "38;5;123"),
        make_pet_frame("^ ^", "◡", "38;5;123"),
        make_pet_frame("− −", "▿", "38;5;123"),
        make_pet_frame("^ ^", "◡", "38;5;123"),
        make_pet_frame("◕ ◕", "ᵔ", "38;5;123"),
    ],
    fps=7.0,
)

REST_ANIM = Animation(
    frames=[
        make_pet_frame("˘ ˘", "﹏", "38;5;110"),
        make_pet_frame("− −", "﹏", "38;5;110"),
        make_pet_frame("˘ ˘", "﹏", "38;5;110"),
        make_pet_frame("− −", "﹏", "38;5;110"),
    ],
    fps=4.0,
)

SPARK_ANIM = Animation(
    frames=[
        make_pet_frame("✦ ✦", "◡", "38;5;213"),
        make_pet_frame("✧ ✧", "◡", "38;5;219"),
        make_pet_frame("✦ ✦", "◡", "38;5;213"),
        make_pet_frame("✧ ✧", "◡", "38;5;219"),
        make_pet_frame("✦ ✦", "◡", "38;5;213"),
    ],
    fps=6.0,
)

ACTION_ANIMS: dict[str, Animation] = {
    "feed": FEED_ANIM,
    "play": PLAY_ANIM,
    "clean": CLEAN_ANIM,
    "pet": PET_ANIM,
    "rest": REST_ANIM,
    "spark": SPARK_ANIM,
}


# ── Particle spawner presets ──

def spawn_feed_particles(ps: ParticleSystem, cx: float, cy: float) -> None:
    ps.spawn(cx + 6, cy + 3, "◆", "38;5;214", count=8, spread=4.0, life=1.2, vy_boost=-3.0)
    ps.spawn(cx + 6, cy + 3, "•", "38;5;221", count=5, spread=3.0, life=1.0, vy_boost=-2.5)


def spawn_play_particles(ps: ParticleSystem, cx: float, cy: float) -> None:
    ps.spawn(cx + 6, cy + 1, "✦", "38;5;213", count=10, spread=5.0, life=1.5, vy_boost=-2.0)


def spawn_clean_particles(ps: ParticleSystem, cx: float, cy: float) -> None:
    ps.spawn(cx + 6, cy + 4, "💧", "38;5;87", count=6, spread=3.5, life=1.3, vy_boost=-1.5)


def spawn_pet_particles(ps: ParticleSystem, cx: float, cy: float) -> None:
    ps.spawn(cx + 6, cy + 2, "❤", "38;5;204", count=6, spread=2.5, life=2.0, vy_boost=-1.8)


def spawn_rest_particles(ps: ParticleSystem, cx: float, cy: float) -> None:
    ps.spawn(cx + 6, cy + 1, "💤", "38;5;110", count=4, spread=2.0, life=2.5, vy_boost=-0.8)


def spawn_spark_particles(ps: ParticleSystem, cx: float, cy: float) -> None:
    ps.spawn(cx + 6, cy + 2, "✨", "38;5;219", count=10, spread=5.0, life=1.8, vy_boost=-2.5)


PARTICLE_SPAWNERS = {
    "feed": spawn_feed_particles,
    "play": spawn_play_particles,
    "clean": spawn_clean_particles,
    "pet": spawn_pet_particles,
    "rest": spawn_rest_particles,
    "spark": spawn_spark_particles,
}
