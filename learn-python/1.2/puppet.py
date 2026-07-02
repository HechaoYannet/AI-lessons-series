from __future__ import annotations

import math
import os
import queue
import random
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

from animation import (
    ACTION_ANIMS,
    PARTICLE_SPAWNERS,
    Animation,
    ParticleSystem,
    make_pet_frame_small,
    make_pet_frame_large,
)
from dialogue import DialogueSystem, ai_available, ai_chat_stream
from games import (
    ExplorationSystem,
    NumberGame,
    ReactionGame,
    stage_for_age,
    stage_name,
)

if os.name == "nt":
    import msvcrt


ESC = "\x1b"
RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"


def c(code: str) -> str:
    return f"{ESC}[{code}m"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def clear_screen() -> None:
    sys.stdout.write(f"{ESC}[2J{ESC}[H")


def hide_cursor() -> None:
    sys.stdout.write(f"{ESC}[?25l")


def show_cursor() -> None:
    sys.stdout.write(f"{ESC}[?25h")


def enter_alternate_screen() -> None:
    sys.stdout.write(f"{ESC}[?1049h")


def exit_alternate_screen() -> None:
    sys.stdout.write(f"{ESC}[?1049l")


def enable_windows_ansi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def terminal_size() -> tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(100, 32))
    return size.columns, size.lines


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _make_pet_frame(eyes: str, mouth: str, body_color: str, eye_color: str = "38;5;231") -> list[str]:
    """Build a standard pet frame."""
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


@dataclass
class PetState:
    name: str = "Nori"
    hunger: float = 26.0
    energy: float = 82.0
    joy: float = 74.0
    cleanliness: float = 87.0
    curiosity: float = 65.0
    affection: float = 70.0
    age: float = 0.0
    mood: str = "calm"
    message: str = "你好，我在这里。"
    message_timer: float = 0.0
    blink_timer: float = 0.0
    look_timer: float = 0.0
    bob_phase: float = 0.0
    petting_glow: float = 0.0
    sleepiness: float = 0.0
    hungry_ticks: float = 0.0
    dirty_ticks: float = 0.0
    fever: float = 0.0
    rename_buffer: str = ""
    renaming: bool = False
    last_action: str = "等待你的指令"
    last_action_at: float = 0.0

    # Animation / particles
    action_anim: Animation | None = None
    particle_sys: ParticleSystem | None = None

    # Dialogue
    dialogue: DialogueSystem | None = None
    chatting: bool = False
    chat_input: str = ""
    chat_reply: str = ""
    typing_progress: float = 0.0
    chat_scroll: int = 0
    chat_pending: bool = False
    chat_spin: float = 0.0
    chat_queue: object | None = None  # queue.Queue for streaming tokens
    chat_stream_thread: threading.Thread | None = None

    # Games
    reaction_game: ReactionGame | None = None
    number_game: NumberGame | None = None
    explore: ExplorationSystem | None = None

    # Growth
    current_stage: str = "幼年期"
    last_stage: str = "幼年期"

    def __post_init__(self) -> None:
        if self.particle_sys is None:
            self.particle_sys = ParticleSystem()
        if self.dialogue is None:
            self.dialogue = DialogueSystem()
        if self.reaction_game is None:
            self.reaction_game = ReactionGame()
        if self.number_game is None:
            self.number_game = NumberGame()
        if self.explore is None:
            self.explore = ExplorationSystem()

    def tick(self, dt: float) -> None:
        self.age += dt
        self.bob_phase += dt * (1.7 + self.energy / 100)
        self.blink_timer -= dt
        self.look_timer -= dt
        self.message_timer -= dt
        self.petting_glow = max(0.0, self.petting_glow - dt * 0.9)
        self.hunger = clamp(self.hunger + dt * 2.3, 0, 100)
        self.cleanliness = clamp(self.cleanliness - dt * 0.9, 0, 100)
        self.energy = clamp(self.energy - dt * 1.15, 0, 100)
        self.joy = clamp(self.joy - dt * (0.55 + (self.hunger / 180)), 0, 100)
        self.curiosity = clamp(self.curiosity - dt * 0.12, 0, 100)
        self.affection = clamp(self.affection - dt * 0.04, 0, 100)
        self.sleepiness = clamp((100 - self.energy) * 0.75, 0, 100)
        self.fever = clamp(self.fever - dt * 0.2, 0, 100)
        if self.hunger > 88:
            self.hungry_ticks += dt
        else:
            self.hungry_ticks = max(0.0, self.hungry_ticks - dt * 1.7)
        if self.cleanliness < 25:
            self.dirty_ticks += dt
        else:
            self.dirty_ticks = max(0.0, self.dirty_ticks - dt * 1.4)

        if self.hunger > 92:
            self.joy = clamp(self.joy - dt * 2.2, 0, 100)
        if self.energy < 18:
            self.joy = clamp(self.joy - dt * 1.0, 0, 100)
        if self.cleanliness < 18:
            self.affection = clamp(self.affection - dt * 0.9, 0, 100)

        # Update animation
        if self.action_anim is not None and not self.action_anim.done:
            self.action_anim.tick(dt)

        # Update particles
        if self.particle_sys is not None:
            self.particle_sys.tick(dt)

        # Update reaction game
        if self.reaction_game is not None and self.reaction_game.active:
            self.reaction_game.tick(dt)
            if self.reaction_game.active and self.reaction_game.target_visible:
                if self.reaction_game.reaction_time > 1.5:
                    msg = self.reaction_game.timeout()
                    self.message = msg

        # Update exploration
        if self.explore is not None:
            was_exploring = self.explore.exploring
            self.explore.tick(dt)
            if was_exploring and not self.explore.exploring and self.explore.result_msg:
                r = self.explore.result()
                self.message = r["msg"]
                if r["type"] == "tired":
                    self.energy = clamp(self.energy - 8, 0, 100)
                elif r["type"] != "none":
                    self.action(r["type"])

        # Update growth stage
        new_stage = stage_for_age(self.age)
        stage_str = stage_name(new_stage)
        if stage_str != self.current_stage:
            self.last_stage = self.current_stage
            self.current_stage = stage_str
            self.message = f"我长大了！进入{stage_str}！"

        # Chat typing effect
        if self.chat_reply and self.typing_progress < len(self.chat_reply):
            self.typing_progress += dt * random.uniform(8, 18)

        # Spinner for pending AI response
        if self.chat_pending:
            self.chat_spin += dt * 3.0

        self.update_mood()

    def update_mood(self) -> None:
        if self.energy < 15:
            self.mood = "sleepy"
            self.message = "zzZ... 眼皮有点沉。"
        elif self.hunger > 85:
            self.mood = "hungry"
            self.message = "肚子在敲鼓，求投喂。"
        elif self.cleanliness < 20:
            self.mood = "grimy"
            self.message = "我需要一点清爽护理。"
        elif self.joy > 80 and self.affection > 70:
            self.mood = "spark"
            self.message = "今天是发光的一天。"
        elif self.affection > 60 and self.hunger < 60:
            self.mood = "cozy"
            self.message = "你在，我就很安心。"
        else:
            self.mood = "calm"
            self.message = "我在慢慢呼吸，慢慢发亮。"

    def action(self, kind: str) -> None:
        if kind == "feed":
            self.hunger = clamp(self.hunger - random.uniform(18, 28), 0, 100)
            self.joy = clamp(self.joy + 6, 0, 100)
            self.affection = clamp(self.affection + 2, 0, 100)
            self.message = random.choice(["啊呜，暖暖的。", "谢谢，这口很灵。", "能量回来了。"])
            self.last_action = "喂食"
        elif kind == "play":
            self.joy = clamp(self.joy + random.uniform(12, 20), 0, 100)
            self.curiosity = clamp(self.curiosity + 10, 0, 100)
            self.energy = clamp(self.energy - 6, 0, 100)
            self.message = random.choice(["再来一次！", "这个我喜欢。", "像星星一样弹起来。"])
            self.last_action = "玩耍"
        elif kind == "clean":
            self.cleanliness = clamp(self.cleanliness + random.uniform(22, 34), 0, 100)
            self.affection = clamp(self.affection + 4, 0, 100)
            self.message = random.choice(["清爽模式启动。", "感觉像换了新皮肤。", "亮晶晶的，谢谢。"])
            self.last_action = "清洁"
        elif kind == "pet":
            self.affection = clamp(self.affection + random.uniform(10, 16), 0, 100)
            self.joy = clamp(self.joy + 8, 0, 100)
            self.petting_glow = 1.0
            self.message = random.choice(["呼噜，呼噜。", "贴贴时间。", "你摸得刚刚好。"])
            self.last_action = "抚摸"
        elif kind == "rest":
            self.energy = clamp(self.energy + random.uniform(18, 28), 0, 100)
            self.joy = clamp(self.joy + 2, 0, 100)
            self.message = random.choice(["我在充电。", "小憩一下，马上回来。", "睡眠是高级功能。"])
            self.last_action = "休息"
        elif kind == "spark":
            self.joy = clamp(self.joy + 4, 0, 100)
            self.curiosity = clamp(self.curiosity + 7, 0, 100)
            self.message = random.choice(["新鲜感+1。", "我看见了更远的光。", "哇，这里还有秘密。"])
            self.last_action = "惊喜"
        self.last_action_at = time.time()
        self.blink_timer = 0.2
        self.look_timer = 0.9
        self.petting_glow = max(self.petting_glow, 0.45)

        # Trigger animation and particles
        anim = ACTION_ANIMS.get(kind)
        if anim is not None:
            anim.reset()
            self.action_anim = anim
        spawner = PARTICLE_SPAWNERS.get(kind)
        if spawner is not None and self.particle_sys is not None:
            spawner(self.particle_sys, 0, 0)

        self.update_mood()

    def stats(self) -> dict[str, float]:
        return {
            "饥饿": self.hunger,
            "精力": self.energy,
            "快乐": self.joy,
            "清洁": self.cleanliness,
            "好奇": self.curiosity,
            "亲密": self.affection,
        }


class TerminalPet:
    def __init__(self) -> None:
        self.pet = PetState()
        self.running = True
        self.last_frame = time.perf_counter()
        self.theme_seed = random.randint(0, 9999)
        self.help_visible = True

    def handle_key(self, key: str) -> None:
        if self.pet.renaming:
            if key in {"\r", "\n"}:
                if self.pet.rename_buffer.strip():
                    self.pet.name = self.pet.rename_buffer.strip()[:16]
                    self.pet.message = f"新名字已记录：{self.pet.name}。"
                self.pet.renaming = False
                self.pet.rename_buffer = ""
                self.help_visible = True
                return
            if key == "\x1b":
                self.pet.renaming = False
                self.pet.rename_buffer = ""
                self.help_visible = True
                return
            if key in {"\b", "\x7f"}:
                self.pet.rename_buffer = self.pet.rename_buffer[:-1]
            elif key.isprintable() and len(self.pet.rename_buffer) < 16:
                self.pet.rename_buffer += key
            return

        # Arrow key scrolling through chat history
        if key == "\x1b[A":  # up
            if self.pet.dialogue is not None and self.pet.dialogue.history:
                self.pet.chat_scroll = min(
                    self.pet.chat_scroll + 1,
                    len(self.pet.dialogue.history) - 1,
                )
            return
        if key == "\x1b[B":  # down
            if self.pet.chat_scroll > 0:
                self.pet.chat_scroll -= 1
            return

        # Chat / number game input mode
        if self.pet.chatting or (self.pet.number_game is not None and self.pet.number_game.active):
            if key in {"\r", "\n"}:
                user_input = self.pet.chat_input.strip()
                self.pet.chat_input = ""
                if not user_input:
                    self.pet.chat_reply = "（输入内容不能为空哦）"
                    self.pet.typing_progress = 0.0
                    return
                # Number game mode
                if self.pet.number_game is not None and self.pet.number_game.active:
                    try:
                        num = int(user_input)
                        result = self.pet.number_game.guess(num)
                        self.pet.chat_reply = result
                        self.pet.typing_progress = 0.0
                        if not self.pet.number_game.active:
                            self.pet.chatting = False
                            self.help_visible = True
                            if "对" in self.pet.number_game.result_message:
                                self.pet.action("spark")
                        return
                    except ValueError:
                        self.pet.chat_reply = "请输入数字！"
                        self.pet.typing_progress = 0.0
                        return
                # Chat mode
                stats = self.pet.stats()
                if ai_available():
                    self.pet.dialogue.context.append(f"你: {user_input}")
                    self.pet.chat_reply = ""
                    self.pet.typing_progress = 0.0
                    self.pet.chat_pending = True
                    self.pet.chat_spin = 0.0
                    history = self.pet.dialogue.build_ai_context()
                    self.pet.chat_queue = queue.Queue()
                    self.pet.chat_stream_thread = threading.Thread(
                        target=ai_chat_stream,
                        args=(history, self.pet.name, self.pet.mood, stats, self.pet.chat_queue),
                        daemon=True,
                    )
                    self.pet.chat_stream_thread.start()
                else:
                    reply = self.pet.dialogue.respond(user_input, self.pet.mood, stats)
                    self.pet.chat_reply = reply
                    self.pet.typing_progress = 0.0
                return
            if key == "\x1b":
                self.pet.chatting = False
                self.pet.chat_input = ""
                self.pet.chat_reply = ""
                self.pet.chat_pending = False
                self.pet.chat_queue = None
                if self.pet.number_game is not None:
                    self.pet.number_game.active = False
                self.pet.message = "已退出对话。"
                self.help_visible = True
                return
            if key in {"\b", "\x7f"}:
                self.pet.chat_input = self.pet.chat_input[:-1]
            elif key.isprintable() and len(self.pet.chat_input) < 60:
                self.pet.chat_input += key
            return

        # New action keys
        if key in {"t", "T"}:
            self.pet.chatting = not self.pet.chatting
            self.pet.chat_input = ""
            self.pet.chat_reply = ""
            self.pet.typing_progress = 0.0
            if self.pet.chatting:
                self.pet.message = "对话模式：输入文字回车发送，ESC 退出。"
                self.help_visible = False
            else:
                self.help_visible = True
            return
        if key in {"e", "E"}:
            err = self.pet.explore.start() if self.pet.explore else None
            self.pet.message = err if err else "我出门探索了，马上回来！"
            return
        if key in {"g", "G"}:
            if self.pet.number_game is not None and self.pet.number_game.active:
                self.pet.number_game.active = False
                self.pet.chatting = False
                self.pet.message = "已退出猜数字游戏。"
            elif self.pet.reaction_game is not None and self.pet.reaction_game.active:
                self.pet.reaction_game.active = False
                self.pet.message = "已退出反应测试。"
            else:
                self.pet.message = "游戏：按 1 反应测试，按 2 猜数字。按 g 退出当前游戏。"
            return
        if key == "1":
            if self.pet.reaction_game is not None:
                self.pet.reaction_game.start()
                self.pet.message = "反应测试！看到 ✦ 立刻按空格。"
            return
        if key == "2":
            if self.pet.number_game is not None:
                self.pet.number_game.start()
                self.pet.chatting = True
                self.pet.chat_input = ""
                self.pet.message = "猜数字开始！我想了 1-100 的数，输入数字猜。"
                self.help_visible = False
            return
        if key == " ":
            if self.pet.reaction_game is not None and self.pet.reaction_game.active:
                result = self.pet.reaction_game.hit()
                if result:
                    self.pet.message = result
                    self.pet.action("play")
            return

        # Original action keys
        if key in {"q", "Q", "\x03"}:
            self.running = False
        elif key in {"h", "H"}:
            self.help_visible = not self.help_visible
        elif key in {"f", "F"}:
            self.pet.action("feed")
        elif key in {"p", "P"}:
            self.pet.action("pet")
        elif key in {"c", "C"}:
            self.pet.action("clean")
        elif key in {"r", "R"}:
            self.pet.action("rest")
        elif key in {"x", "X"}:
            self.pet.action("play")
        elif key in {"n", "N"}:
            self.pet.renaming = True
            self.pet.rename_buffer = ""
            self.pet.message = "输入新名字，然后回车确认。"
            self.help_visible = False

    def read_input(self) -> None:
        if os.name != "nt":
            return
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in {"\x00", "\xe0"}:
                if msvcrt.kbhit():
                    ch2 = msvcrt.getwch()
                    # Arrow keys: up=H, down=P
                    if ch2 == "H":
                        self.handle_key("\x1b[A")  # up
                    elif ch2 == "P":
                        self.handle_key("\x1b[B")  # down
                continue
            self.handle_key(ch)

    def pet_frame(self, mood: str) -> list[str]:
        # Use action animation if active
        if self.pet.action_anim is not None and not self.pet.action_anim.done:
            return self.pet.action_anim.current

        # Growth-stage-aware idle frame
        stage = self.pet.current_stage
        body_color = {
            "幼年期": "38;5;159",
            "成长期": "38;5;87",
            "成熟期": "38;5;213",
        }.get(stage, "38;5;87")

        blink = self.pet.blink_timer > 0 or int(self.pet.age * 4) % 18 == 0
        eyes = "◕ ◕" if not blink else "─ ─"
        if mood == "sleepy":
            eyes = "˘ ˘"
        elif mood == "hungry":
            eyes = "• •"
        elif mood == "spark":
            eyes = "✦ ✦"
        mouth = {
            "sleepy": "﹏",
            "hungry": "﹏",
            "grimy": "﹍",
            "spark": "◡",
            "cozy": "▿",
        }.get(mood, "ᵔ")

        if stage == "幼年期":
            return make_pet_frame_small(eyes, mouth, body_color)
        elif stage == "成熟期":
            return make_pet_frame_large(eyes, mouth, body_color)
        else:
            wobble = math.sin(self.pet.bob_phase) * 1.2
            offset = 2 + int(round(wobble))
            aura = "" if self.pet.petting_glow < 0.1 else c("38;5;213") + "◌" * 6 + RESET
            frame = _make_pet_frame(eyes, mouth, body_color)
            if aura:
                frame.insert(0, f"{' ' * (offset + 3)}{aura}")
            return frame

    def meter(self, label: str, value: float, color: str, width: int = 20) -> str:
        filled = int(round(width * clamp(value / 100, 0, 1)))
        empty = width - filled
        return f"{label:<4} {c(color)}{'█' * filled}{RESET}{c('38;5;238')}{'░' * empty}{RESET} {value:5.1f}"

    def mood_color(self) -> str:
        return {
            "sleepy": "38;5;110",
            "hungry": "38;5;214",
            "grimy": "38;5;246",
            "spark": "38;5;213",
            "cozy": "38;5;123",
        }.get(self.pet.mood, "38;5;87")

    @staticmethod
    def _visible_len(text: str) -> int:
        import re
        return len(re.sub(re.escape(ESC) + r'\[[0-9;]*m', '', text))

    def render(self, width: int, height: int) -> str:
        lines: list[str] = []
        title_color = self.mood_color()
        gradient = ["38;5;45", "38;5;51", "38;5;87", "38;5;123", "38;5;159", "38;5;213"]
        top = c(gradient[self.theme_seed % len(gradient)]) + "╭" + "─" * max(10, width - 2) + "╮" + RESET
        bottom = c(gradient[(self.theme_seed + 2) % len(gradient)]) + "╰" + "─" * max(10, width - 2) + "╯" + RESET
        lines.append(top)
        header = f" {BOLD}{c(title_color)}{self.pet.name}{RESET}  {c('38;5;246')}|{RESET}  {c('38;5;159')}状态 {self.pet.mood}{RESET}  {c('38;5;246')}|{RESET}  {c('38;5;159')}时间 {now_text()}{RESET} "
        header_pad = max(0, width - 2 - self._visible_len(header))
        lines.append(f"{c('38;5;45')}│{RESET}{header}{' ' * header_pad}{c('38;5;45')}│{RESET}")

        pet_lines = self.pet_frame(self.pet.mood)
        max_body_width = max(self._visible_len(line) for line in pet_lines)

        info = [
            f"{c('38;5;246')}互动键{RESET}  f喂食 p抚摸 x玩耍 c清洁 r休息 t对话 e探索 g游戏 n改名 h帮助 q退出",
            f"{c('38;5;246')}消息{RESET}    {c(title_color)}{self.pet.message}{RESET}",
            f"{c('38;5;246')}最近动作{RESET} {self.pet.last_action}",
        ]

        # Inline overlays (game / explore / stage — stay in right panel)
        inline_extra: list[str] = []
        if self.pet.reaction_game is not None and self.pet.reaction_game.active:
            rendered = self.pet.reaction_game.render().strip()
            if rendered:
                inline_extra.append(rendered)
        if self.pet.number_game is not None and self.pet.number_game.active:
            for line in self.pet.number_game.render().strip().split("\n"):
                if line.strip():
                    inline_extra.append(line)
        if self.pet.explore is not None and self.pet.explore.exploring:
            path = self.pet.explore.render_path(width - 10)
            inline_extra.append(f"{c('38;5;87')}探索中{RESET}  {path}")
        if self.pet.current_stage and self.pet.current_stage != "成长期":
            inline_extra.append(f"{c('38;5;220')}阶段{RESET}    {self.pet.current_stage}")
        if inline_extra:
            info = info + inline_extra

        stat_lines = []
        colors = ["38;5;214", "38;5;123", "38;5;213", "38;5;45", "38;5;87", "38;5;159"]
        for (label, value), color in zip(self.pet.stats().items(), colors, strict=False):
            stat_lines.append(self.meter(label, value, color))

        # ── Main panel: pet (left) + info/stats (right) ──
        panel_width = max(width - 4, 20)
        total_rows = max(len(pet_lines), len(info) + len(stat_lines) + 2) + 2
        for i in range(total_rows):
            left = pet_lines[i] if i < len(pet_lines) else ""
            if self.pet.renaming and i == len(pet_lines) + 1:
                right = f"{c('38;5;246')}给我一个新名字：{RESET}{self.pet.rename_buffer}_"
            elif i < len(info):
                right = info[i]
            elif i - len(info) == 1:
                right = f"{c('38;5;246')}状态条{RESET}"
            elif 0 <= i - len(info) - 2 < len(stat_lines):
                right = stat_lines[i - len(info) - 2]
            else:
                right = ""
            left_vis = self._visible_len(left)
            left_pad = max_body_width - left_vis
            right_pad = max(0, panel_width - max_body_width - 3 - self._visible_len(right))
            combined = f"{c('38;5;45')}│{RESET} {left}{' ' * left_pad}  {right}{' ' * right_pad} {c('38;5;45')}│{RESET}"
            lines.append(combined)

        if self.help_visible:
            help_text_lines = [
                f"{c('38;5;246')}提示{RESET}  宠物会随时间变饿变累变脏；你可以通过操作影响它的情绪和外观。",
                f"{c('38;5;246')}玩法{RESET}  维持各项属性的平衡。t对话 e探索 g游戏。↑↓滚动聊天记录。",
            ]
            for text in help_text_lines:
                text_pad = max(0, width - 4 - self._visible_len(text))
                lines.append(f"{c('38;5;45')}│{RESET} {text}{' ' * text_pad} {c('38;5;45')}│{RESET}")

        lines.append(bottom)

        # ── Below main panel: chat history (full width) ──
        chat_lines: list[str] = []

        if self.pet.dialogue is not None and self.pet.dialogue.history and (self.pet.chatting or not self.help_visible):
            visible_rows = 5
            history = self.pet.dialogue.history
            total = len(history)
            start = max(0, total - visible_rows - self.pet.chat_scroll)
            end = total - self.pet.chat_scroll
            visible = history[start:end]

            chat_width = max(width - 4, 40)
            bar = "─" * (chat_width - 12)
            up_marker = "▼" if start > 0 else "─"
            dn_marker = "▲" if end < total else "─"
            chat_lines.append(
                f" {c('38;5;214')}╭─ 聊天记录 {up_marker}{bar}{dn_marker} ╮{RESET}"
            )
            if not visible:
                chat_lines.append(
                    f" {c('38;5;214')}│{RESET} (按 ↑↓ 滚动查看更早的消息)    {c('38;5;214')}│{RESET}"
                )
            for user_msg, pet_msg in visible:
                max_len = chat_width - 10
                u_disp = user_msg if len(user_msg) <= max_len else user_msg[:max_len - 1] + "…"
                p_disp = pet_msg if len(pet_msg) <= max_len else pet_msg[:max_len - 1] + "…"
                chat_lines.append(
                    f" {c('38;5;214')}│{RESET} {c('38;5;246')}你:{RESET} {u_disp}"
                )
                chat_lines.append(
                    f" {c('38;5;214')}│{RESET} {c('38;5;123')}{self.pet.name}:{RESET} {p_disp}"
                )
            chat_lines.append(
                f" {c('38;5;214')}╰{'─' * (chat_width - 2)}╯{RESET}"
            )

        # Chat input line
        if self.pet.chatting:
            input_text = self.pet.chat_input if self.pet.chat_input else ""
            # Show spinner while waiting for AI
            if self.pet.chat_pending:
                spin_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                idx = int(self.pet.chat_spin) % len(spin_chars)
                spinner = f"{c('38;5;214')}{spin_chars[idx]}{RESET}"
                chat_lines.append(f" {spinner} {c('38;5;214')}> {RESET}{input_text}_")
            else:
                chat_lines.append(f" {c('38;5;214')}> {RESET}{input_text}_")
            if self.pet.chat_reply:
                if self.pet.chat_pending:
                    # Streaming mode — show accumulated text directly
                    chat_lines.append(f"   {c('38;5;123')}{self.pet.chat_reply}{RESET}")
                else:
                    visible_r = self.pet.chat_reply[:int(self.pet.typing_progress)]
                    prefix = "[AI] " if ai_available() else ""
                    chat_lines.append(f"   {c('38;5;123')}{prefix}{visible_r}{RESET}")
            elif self.pet.chat_pending:
                chat_lines.append(f"   {c('38;5;214')}等待回复...{RESET}")

        # Pad chat_lines to their actual height to avoid flicker
        lines.extend(chat_lines)

        # Pad remaining space
        while len(lines) < height - 1:
            lines.append("")

        return "\n".join(lines)

    def _process_stream(self) -> None:
        """Consume available tokens from the streaming queue (non-blocking)."""
        q = self.pet.chat_queue
        if q is None:
            return
        try:
            while True:
                token = q.get_nowait()
                if token is None:
                    self.pet.chat_queue = None
                    self.pet.chat_pending = False
                    last_user = self.pet.dialogue.context[-1].replace("你: ", "")
                    self.pet.dialogue.history.append((last_user, self.pet.chat_reply))
                    break
                self.pet.chat_reply += token
        except queue.Empty:
            pass

    def frame(self) -> None:
        cols, rows = terminal_size()
        now = time.perf_counter()
        dt = min(0.08, now - self.last_frame)
        self.last_frame = now
        self.read_input()
        self.pet.tick(dt)

        self._process_stream()

        sys.stdout.write(f"{ESC}[H{ESC}[?7l")
        hide_cursor()
        output = self.render(cols, rows)
        sys.stdout.write(output)
        sys.stdout.write(f"{ESC}[J{ESC}[?7h")
        sys.stdout.flush()

    def run(self) -> None:
        enable_windows_ansi()
        enter_alternate_screen()
        clear_screen()
        hide_cursor()
        try:
            while self.running:
                self.frame()
                time.sleep(1 / 30)
        finally:
            show_cursor()
            exit_alternate_screen()
            sys.stdout.write(RESET + "\n")
            sys.stdout.flush()


def main() -> None:
    pet = TerminalPet()
    pet.run()


if __name__ == "__main__":
    main()
