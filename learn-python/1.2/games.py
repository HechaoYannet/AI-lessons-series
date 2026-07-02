"""Mini-games, exploration, and growth stages for the terminal pet."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto


ESC = "\x1b"
RESET = f"{ESC}[0m"


def c(code: str) -> str:
    return f"{ESC}[{code}m"


# ── Growth stages ──

class GrowthStage(Enum):
    CHILD = auto()
    ADULT = auto()
    MATURE = auto()


STAGE_THRESHOLDS = [
    (GrowthStage.CHILD, 0.0),
    (GrowthStage.ADULT, 30.0 * 60.0),
    (GrowthStage.MATURE, 120.0 * 60.0),
]


def stage_for_age(age: float) -> GrowthStage:
    current = GrowthStage.CHILD
    for stage, threshold in STAGE_THRESHOLDS:
        if age >= threshold:
            current = stage
    return current


def stage_name(stage: GrowthStage) -> str:
    return {GrowthStage.CHILD: "幼年期", GrowthStage.ADULT: "成长期", GrowthStage.MATURE: "成熟期"}[stage]


# ── Reaction game ──

@dataclass
class ReactionGame:
    active: bool = False
    target_visible: bool = False
    target_x: int = 0
    target_timer: float = 0.0
    reaction_time: float = 0.0
    result_message: str = ""

    def start(self) -> None:
        self.active = True
        self.target_visible = False
        self.result_message = ""
        self._schedule_target()

    def _schedule_target(self) -> None:
        self.target_visible = False
        self.target_timer = random.uniform(1.0, 3.5)

    def tick(self, dt: float) -> None:
        if not self.active:
            return
        if not self.target_visible:
            self.target_timer -= dt
            if self.target_timer <= 0:
                self.target_visible = True
                self.target_x = random.randint(5, 45)
                self.reaction_time = 0.0
        else:
            self.reaction_time += dt

    def hit(self) -> str | None:
        if not self.active or not self.target_visible:
            return None
        self.active = False
        t = self.reaction_time
        if t < 0.3:
            return f"超快！{t*1000:.0f}ms，快乐+15"
        elif t < 0.8:
            return f"不错！{t*1000:.0f}ms，快乐+9"
        elif t < 1.5:
            return f"还行，{t*1000:.0f}ms，快乐+4"
        else:
            return "太慢了……没有奖励。"

    def timeout(self) -> str:
        self.active = False
        self.result_message = "没来得及按……下次加油！"
        return self.result_message

    def render(self) -> str:
        if not self.active:
            return ""
        if self.target_visible:
            return f"\n{' ' * self.target_x}{c('38;5;213')}✦ ← 快按空格！{RESET}\n"
        return f"\n{' ' * 16}{c('38;5;246')}等待目标出现……{RESET}\n"


# ── Number guessing game ──

@dataclass
class NumberGame:
    active: bool = False
    target: int = 0
    guesses: list[int] = field(default_factory=list)
    max_guesses: int = 6
    result_message: str = ""

    def start(self) -> None:
        self.active = True
        self.target = random.randint(1, 100)
        self.guesses = []
        self.result_message = ""

    def guess(self, num: int) -> str:
        if not self.active:
            return ""
        self.guesses.append(num)
        if num == self.target:
            self.active = False
            bonus = max(0, (self.max_guesses - len(self.guesses)) * 4)
            self.result_message = f"猜对了！{len(self.guesses)}次，好奇+{bonus + 5:.0f}"
            return self.result_message
        if len(self.guesses) >= self.max_guesses:
            self.active = False
            self.result_message = f"没猜中……答案是{self.target}。"
            return self.result_message
        hint = "大了" if num > self.target else "小了"
        return f"{num}？{hint}！还剩{self.max_guesses - len(self.guesses)}次。"

    def render(self) -> str:
        if not self.active:
            return ""
        lines = [
            f"{c('38;5;214')}╭─ 猜数字游戏 ──────────╮{RESET}",
            f"{c('38;5;214')}│{RESET} 我想了一个 1-100 的数      ",
            f"{c('38;5;214')}│{RESET} 剩余次数: {self.max_guesses - len(self.guesses)}",
        ]
        if self.guesses:
            nums = ", ".join(map(str, self.guesses))
            lines.append(f"{c('38;5;214')}│{RESET} 已猜: {nums}")
        lines.append(f"{c('38;5;214')}╰────────────────────────╯{RESET}")
        return "\n".join(lines)


# ── Exploration system ──

EXPLORE_OUTCOMES = [
    ("发现了一颗发光的果子！", "feed"),
    ("在小路边找到了神秘的甜点。", "feed"),
    ("捡到一个会吱吱叫的玩具球。", "play"),
    ("草丛里藏着闪闪发亮的小石头。", "spark"),
    ("遇到了一只友善的小鸟，聊得很开心。", "spark"),
    ("日记本上多了一页有趣的故事碎片。", "spark"),
    ("外面很安静，什么也没发生。", "none"),
    ("走太远有点迷路了，有点累。", "tired"),
    ("被一阵花香包围，心情变好了。", "pet"),
]


@dataclass
class ExplorationSystem:
    exploring: bool = False
    start_time: float = 0.0
    duration: float = 0.0
    cooldown_until: float = 0.0
    cooldown_secs: float = 30.0
    result_msg: str = ""
    result_type: str = "none"
    path_progress: float = 0.0

    def start(self) -> str | None:
        now = time.time()
        if now < self.cooldown_until:
            remaining = int(self.cooldown_until - now)
            return f"还在冷却中……再等{remaining}秒吧。"
        self.exploring = True
        self.start_time = now
        self.duration = random.uniform(5.0, 15.0)
        self.result_msg = ""
        self.result_type = "none"
        self.path_progress = 0.0
        return None

    def tick(self, dt: float) -> None:
        if not self.exploring:
            return
        self.path_progress = min(1.0, (time.time() - self.start_time) / self.duration)
        if time.time() - self.start_time >= self.duration:
            self._finish()

    def _finish(self) -> None:
        self.exploring = False
        self.cooldown_until = time.time() + self.cooldown_secs
        outcome = random.choice(EXPLORE_OUTCOMES)
        self.result_msg = outcome[0]
        self.result_type = outcome[1]

    def result(self) -> dict:
        return {"type": self.result_type, "msg": self.result_msg}

    def render_path(self, width: int) -> str:
        if not self.exploring:
            return ""
        p = self.path_progress
        trail_len = min(width - 4, 40)
        chars = ["·", "•", "∘", "∗", "∴"]
        path = ""
        for i in range(trail_len):
            phase = i / max(trail_len, 1)
            if phase <= p:
                path += c("38;5;87") + random.choice(chars) + RESET
            else:
                path += " "
        return path
