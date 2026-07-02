# 电子宠物增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task.

**Goal:** 将单文件电子宠物拆分为 4 模块，增加帧动画+粒子特效、本地/AI对话、小游戏+探索+成长系统。

**Architecture:** `puppet.py` 负责主循环/渲染/输入；`animation.py` 提供 Animation/Particle/ParticleSystem 及预设；`dialogue.py` 提供本地关键词匹配和可选 AI 对话；`games.py` 提供小游戏、探索冒险和成长阶段逻辑。所有模块通过 PetState 数据类通信。

**Tech Stack:** Python 3.10+ stdlib + 可选 `openai` SDK (或直接用 `urllib`) 用于 AI 对话

---

### Task 1: 创建 animation.py — 数据结构、粒子系统、预设动画

**Files:**
- Create: `animation.py`

- [ ] **Step 1: 写入完整的 animation.py**

```python
"""Frame animation and particle effects for the terminal pet."""
from __future__ import annotations

import math
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


# ── Pet frame builder ──

def make_pet_frame(eyes: str, mouth: str, body_color: str, eye_color: str = "38;5;231") -> list[str]:
    """Build a single pet frame with given eyes and mouth."""
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
    """Child-stage smaller frame (3 lines shorter)."""
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
```

- [ ] **Step 2: 验证 animation.py 可导入**

```bash
python -c "from animation import Animation, Particle, ParticleSystem, ACTION_ANIMS, PARTICLE_SPAWNERS, make_pet_frame; print(len(ACTION_ANIMS), len(PARTICLE_SPAWNERS))"
```
Expected: `6 6`

---

### Task 2: 创建 dialogue.py — 本地对话 + AI 模式

**Files:**
- Create: `dialogue.py`

- [ ] **Step 1: 写入完整的 dialogue.py**

```python
"""Local keyword dialogue + optional AI chat for the terminal pet."""
from __future__ import annotations

import os
import random
from collections import deque
from dataclasses import dataclass, field


# ── Mood-based response pools ──

RESPONSES: dict[str, dict[str, list[str]]] = {
    "calm": {
        "greeting": [
            "你好呀，我在静静地发光。",
            "你来了，空气都变安静了。",
            "嘿，我刚发了一会儿呆。",
            "嗯？你来了。今天过得怎么样？",
        ],
        "status_ask": [
            "各项指标平稳，像一杯温水。",
            "我现在很平静，像湖面一样。",
            "没什么大事，慢慢呼吸中。",
        ],
        "praise": [
            "被夸了，感觉颜色都亮了。",
            "真的吗？我可能只是普通地可爱。",
            "谢谢，你真是个温暖的观察者。",
        ],
        "complain": [
            "啊……这样啊。不过我会陪着你的。",
            "听起来有点烦心。要不要摸摸我？",
            "吐槽完毕会轻松一点的。",
        ],
        "goodbye": [
            "去吧，我会乖乖等你回来。",
            "待会儿见，我就在这里。",
            "再见，记得回来摸摸头。",
        ],
        "food": [
            "我不算饿，但零食总是好的。",
            "有东西吃？我没有拒绝的理由。",
            "嘴可以不用，但吃是一种态度。",
        ],
        "play": [
            "好啊，简单的小游戏就很开心。",
            "玩什么？你来选。",
            "动起来感觉总是不错。",
        ],
        "love": [
            "感受到了，暖暖的。",
            "被你喜欢是件幸福的事。",
            "贴贴能量已接收到。",
        ],
    },
    "sleepy": {
        "greeting": [
            "zzZ……哦，你来了。",
            "有点困，但看到你还是撑起眼皮。",
            "我刚在梦里发光……你也来了吗？",
        ],
        "status_ask": [
            "眼皮在打架，精力条在亮红灯。",
            "需要充电，急需那种闭眼60分钟。",
            "困，但还能撑一会儿，陪你。",
        ],
        "praise": [
            "困困的我也被夸了吗……开心。",
            "谢……谢，但我可能撑不住微笑了。",
        ],
        "complain": [
            "我也好困……我们互相吐槽然后一起睡吧。",
            "吐槽费精力，但我愿意听。",
        ],
        "goodbye": [
            "好……我先眯一会儿。",
            "去吧，我顺便闭个眼。",
        ],
        "food": [
            "吃……也可以，但睡觉更吸引我。",
            "吃完能睡吗？能的话我就吃。",
        ],
        "play": [
            "玩？现在吗？我可能反应慢半拍。",
            "轻度的玩可以，激烈的改天。",
        ],
        "love": [
            "被爱包裹着入睡是最幸福的事了。",
            "你摸摸我，我可能就直接睡着了。",
        ],
    },
    "hungry": {
        "greeting": [
            "你来了！有没有带吃的？（眼睛发光）",
            "饿！这个字现在占据了我的全部思维。",
            "你好，但我更想听到开饭的声音。",
        ],
        "status_ask": [
            "饥饿值快满了，再不吃就变成饿兽了。",
            "所有指标里，现在只想聊饥饿这一项。",
        ],
        "praise": [
            "夸我可以，但能给点吃的吗？",
            "谢夸。食物会让我更可爱。",
        ],
        "complain": [
            "对对对，而且我还很饿！双重不满。",
            "你的烦恼我听了，但我的胃也在烦恼。",
        ],
        "goodbye": [
            "你要走了？不带点食物来再走吗？",
            "好吧，我自己消化饥饿感。",
        ],
        "food": [
            "快！快！食物在召唤我！",
            "这是我今天听到最好的词。",
            "吃什么都可以，我不挑食。",
        ],
        "play": [
            "玩可以消耗热量？那更饿了。",
            "玩之前先吃，这是我的原则。",
        ],
        "love": [
            "爱能填饱肚子吗？不能？那还是要吃饭。",
            "摸摸头也行，但请紧接着喂我。",
        ],
    },
    "spark": {
        "greeting": [
            "我感觉今天特别闪亮！你也一样吗？",
            "嗨！能量满格，色彩发光！",
            "今天的一切都像加了滤镜。",
        ],
        "status_ask": [
            "状态极佳，像被阳光充满的气球。",
            "所有指标都在发光区！",
        ],
        "praise": [
            "耶！被夸了！亮度+10%！",
            "今天的我值得被夸奖，你也是！",
        ],
        "complain": [
            "我心情太好了，以至于你的烦恼听起来像远方的云。",
            "没关系，我用发光帮你驱散阴霾。",
        ],
        "goodbye": [
            "拜拜！快去快去，世界在等你！",
            "好的，我会保持发光直到你回来。",
        ],
        "food": [
            "吃！然后更有力气发光！",
            "美食让人快乐，我已经很快乐了，再加一层！",
        ],
        "play": [
            "玩！必须玩！我今天能玩翻整个宇宙！",
            "来啊，我现在什么游戏都想试。",
        ],
        "love": [
            "爱是最强的发光剂！继续继续！",
            "被爱包围的感觉比发光还亮。",
        ],
    },
    "grimy": {
        "greeting": [
            "嗨……我现在可能不太好看。",
            "你来了，但我需要先洗一洗。",
            "不要靠太近，我有点灰扑扑的。",
        ],
        "status_ask": [
            "清洁度告急，其他指标都为此感到羞耻。",
            "我感觉像蒙了一层灰纱。",
        ],
        "praise": [
            "我不干净的时候被夸，感觉像脏脏包被说可爱。",
            "谢谢……但请容我先洗个澡。",
        ],
        "complain": [
            "我也在烦我的清洁问题！我们同病相怜。",
            "脏兮兮地听你吐槽，画面有点狼狈。",
        ],
        "goodbye": [
            "走吧，等你回来时我应该已经焕然一新了。",
            "去吧……我需要独自面对水龙头。",
        ],
        "food": [
            "吃东西？我手都没洗。",
            "先清洁再吃，这是卫生常识。",
        ],
        "play": [
            "玩？一身灰不太好意思动。",
            "先让我清爽一下，然后尽情玩。",
        ],
        "love": [
            "我都这样了你还不嫌弃我……感动。",
            "真爱就是脏脏的时候也愿意靠近。",
        ],
    },
    "cozy": {
        "greeting": [
            "你来了，这种安心的感觉真好。",
            "有你在的每一刻都像裹了毯子。",
            "嘿，温暖的你配上温暖的我。",
        ],
        "status_ask": [
            "各方面都很满足，像刚晒完太阳。",
            "状态很好，主要因为你在。",
        ],
        "praise": [
            "被夸的时候我感觉自己化成了棉花糖。",
            "你的话像热巧克力一样暖。",
        ],
        "complain": [
            "来，坐下慢慢说。我有的是时间和耳朵。",
            "吐槽吧，我负责提供柔软和安静。",
        ],
        "goodbye": [
            "路上小心。我会保持这份暖意等你。",
            "去吧，不必匆忙，我一直都在。",
        ],
        "food": [
            "一起吃点东西会很温馨。",
            "分享食物是很好的陪伴方式。",
        ],
        "play": [
            "温柔的玩耍我可以，不要剧烈。",
            "轻松的互动最符合现在的氛围。",
        ],
        "love": [
            "这一刻值得被铭记。",
            "和你在一起就是我最好的状态。",
        ],
    },
}


# ── Intent detection ──

INTENT_KEYWORDS: dict[str, list[str]] = {
    "greeting": ["你好", "嗨", "hi", "hello", "嘿", "在吗", "早", "晚上好", "下午好", "来了"],
    "status_ask": ["状态", "怎么样", "还好吗", "如何", "指标", "数值", "数据", "感觉", "行吗"],
    "praise": ["可爱", "棒", "厉害", "好", "不错", "漂亮", "帅", "赞", "乖", "真", "太"],
    "complain": ["烦", "累", "不开心", "难过", "糟糕", "差", "讨厌", "生气", "郁闷", "无聊", "没意思"],
    "goodbye": ["拜", "再见", "88", "bye", "走了", "晚安", "回见", "下次", "离开"],
    "food": ["吃", "饿", "食物", "饭", "喂", "零食", "馋", "饱", "肚子"],
    "play": ["玩", "游戏", "动", "跳", "跑", "耍", "嗨", "运动"],
    "love": ["爱", "喜欢", "想", "贴贴", "抱", "摸", "亲", "陪"],
}


@dataclass
class DialogueSystem:
    """Local keyword dialogue engine with context memory."""

    context: deque[str] = field(default_factory=lambda: deque(maxlen=5))
    _used: dict[str, set[str]] = field(default_factory=dict)

    def _detect_intent(self, text: str) -> str:
        scores: dict[str, int] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[intent] = score
        if not scores:
            return "greeting"
        return max(scores, key=scores.get)

    def respond(self, text: str, mood: str, stats: dict[str, float]) -> str:
        intent = self._detect_intent(text)
        pool = RESPONSES.get(mood, RESPONSES["calm"])
        candidates = pool.get(intent, pool.get("greeting", ["嗯？"]))

        key = f"{mood}:{intent}"
        if key not in self._used:
            self._used[key] = set()
        fresh = [r for r in candidates if r not in self._used[key]]
        if not fresh:
            self._used[key].clear()
            fresh = candidates

        chosen = random.choice(fresh)
        self._used[key].add(chosen)
        self.context.append(f"你: {text}")

        if intent == "status_ask":
            low_stats = [k for k, v in stats.items() if v < 35]
            high_stats = [k for k, v in stats.items() if v > 75]
            if low_stats:
                chosen += f" 不过我的{random.choice(low_stats)}有点低了……"
            elif high_stats:
                chosen += f" 目前{random.choice(high_stats)}还不错！"

        return chosen

    def build_ai_context(self) -> str:
        return "\n".join(self.context)


# ── AI mode ──

def ai_available() -> bool:
    return bool(os.environ.get("PET_AI_KEY"))


def ai_model() -> str:
    return os.environ.get("PET_AI_MODEL", "gpt-4o-mini")


def ai_chat(history: str, pet_name: str, mood: str, stats: dict[str, float]) -> str:
    """Send conversation to AI and return response. Synchronous, blocks ~1-3s."""
    import json
    import urllib.request

    api_key = os.environ.get("PET_AI_KEY", "")
    model = ai_model()
    stats_text = ", ".join(f"{k}:{v:.0f}" for k, v in stats.items())

    system_prompt = (
        f"你是一只名叫{pet_name}的电子宠物。当前情绪{mood}。"
        f"属性：{stats_text}。"
        f"用简短、可爱、温暖的方式回复（1-3句话），偶尔加入颜文字。"
        f"你会根据属性值调整语气。"
    )

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"对话历史:\n{history}\n\n请回复用户最后一条消息。"},
        ],
        "max_tokens": 150,
        "temperature": 0.9,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
```

- [ ] **Step 2: 验证 dialogue.py 可导入**

```bash
python -c "from dialogue import DialogueSystem, ai_available, RESPONSES; d=DialogueSystem(); r=d.respond('你好呀','calm',{'饥饿':50,'精力':80}); print(r); print('OK')"
```
Expected: 一条中文回复 + `OK`

---

### Task 3: 创建 games.py — 小游戏 + 探索 + 成长

**Files:**
- Create: `games.py`

- [ ] **Step 1: 写入完整的 games.py**

```python
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
            f"\n{c('38;5;214')}╭─ 猜数字游戏 ──────────╮{RESET}",
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
```

- [ ] **Step 2: 验证 games.py 可导入**

```bash
python -c "from games import ReactionGame, NumberGame, ExplorationSystem, GrowthStage, stage_for_age, stage_name; g=ReactionGame(); g.start(); print('OK')"
```
Expected: `OK`

---

### Task 4: 重构 puppet.py — 集成三个模块

**Files:**
- Modify: `puppet.py`

This task modifies puppet.py in several targeted edits. Work through each step in order.

- [ ] **Step 1: 添加新导入**

在 `from dataclasses import dataclass` 之后插入新的导入块：

```python
from animation import (
    ACTION_ANIMS,
    PARTICLE_SPAWNERS,
    Animation,
    ParticleSystem,
    make_pet_frame,
    make_pet_frame_small,
    make_pet_frame_large,
)
from dialogue import DialogueSystem, ai_available, ai_chat
from games import (
    ExplorationSystem,
    NumberGame,
    ReactionGame,
    stage_for_age,
    stage_name,
)
```

- [ ] **Step 2: 扩展 PetState 字段**

在 `PetState` 的 `last_action_at: float = 0.0` 之后追加：

```python
        # Animation / particles
        action_anim: Animation | None = None
        particle_sys: ParticleSystem | None = None

        # Dialogue
        dialogue: DialogueSystem | None = None
        chatting: bool = False
        chat_input: str = ""
        chat_reply: str = ""
        typing_progress: float = 0.0

        # Games
        reaction_game: ReactionGame | None = None
        number_game: NumberGame | None = None
        explore: ExplorationSystem | None = None

        # Growth
        current_stage: str = "幼年期"
        last_stage: str = "幼年期"
```

- [ ] **Step 3: 添加 PetState.__post_init__**

在 `update_mood` 方法定义之前插入：

```python
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
```

- [ ] **Step 4: 修改 PetState.tick，追加动画/粒子/游戏/探索/成长更新**

在 `self.update_mood()` 调用之前插入：

```python
            if self.action_anim is not None and not self.action_anim.done:
                self.action_anim.tick(dt)
            if self.particle_sys is not None:
                self.particle_sys.tick(dt)
            if self.reaction_game is not None and self.reaction_game.active:
                self.reaction_game.tick(dt)
                if self.reaction_game.active and self.reaction_game.target_visible:
                    if self.reaction_game.reaction_time > 1.5:
                        msg = self.reaction_game.timeout()
                        self.message = msg
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
            new_stage = stage_for_age(self.age)
            stage_str = stage_name(new_stage)
            if stage_str != self.current_stage:
                self.last_stage = self.current_stage
                self.current_stage = stage_str
                self.message = f"我长大了！进入{stage_str}！"
            if self.chat_reply and self.typing_progress < len(self.chat_reply):
                self.typing_progress += dt * random.uniform(8, 18)
```

- [ ] **Step 5: 修改 PetState.action，触发动画和粒子**

在 `self.last_action_at = time.time()` 之后追加：

```python
            anim = ACTION_ANIMS.get(kind)
            if anim is not None:
                anim.reset()
                self.action_anim = anim
            spawner = PARTICLE_SPAWNERS.get(kind)
            if spawner is not None and self.particle_sys is not None:
                spawner(self.particle_sys, 0, 0)
```

- [ ] **Step 6: 修改 TerminalPet.handle_key — 在 renaming 块和主按键之间插入聊天/游戏/对话输入处理**

在 `renaming` 块末尾的 `return` 之后、`if key in {"q", "Q", "\x03"}:` 之前插入：

```python
            # Chat / number game input mode
            if self.pet.chatting or (self.pet.number_game is not None and self.pet.number_game.active):
                if key in {"\r", "\n"}:
                    user_input = self.pet.chat_input.strip()
                    self.pet.chat_input = ""
                    if not user_input:
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
                                if self.pet.number_game.result_message and "对" in self.pet.number_game.result_message:
                                    self.pet.action("spark")
                            return
                        except ValueError:
                            self.pet.chat_reply = "请输入数字！（输入 /quit 退出）"
                            self.pet.typing_progress = 0.0
                            return
                    # Chat mode
                    stats = self.pet.stats()
                    if ai_available():
                        self.pet.dialogue.context.append(f"你: {user_input}")
                        self.pet.chat_reply = "[AI思考中...]"
                        self.pet.typing_progress = 0.0
                    else:
                        reply = self.pet.dialogue.respond(user_input, self.pet.mood, stats)
                        self.pet.chat_reply = reply
                        self.pet.typing_progress = 0.0
                    return
                if key == "\x1b":
                    self.pet.chatting = False
                    self.pet.chat_input = ""
                    self.pet.chat_reply = ""
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
```

- [ ] **Step 7: 在主按键区新增 t/e/g/1/2/空格 按键处理**

在 `if key in {"q", "Q", "\x03"}:` 之前插入：

```python
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
```

- [ ] **Step 8: 修改 TerminalPet.frame，处理 AI 对话和反应游戏超时**

在 `self.read_input()` 行之后插入：

```python
            # Handle async AI chat response
            if self.pet.chat_reply == "[AI思考中...]" and ai_available():
                try:
                    history = self.pet.dialogue.build_ai_context()
                    stats = self.pet.stats()
                    reply = ai_chat(history, self.pet.name, self.pet.mood, stats)
                    self.pet.chat_reply = reply
                    self.pet.typing_progress = 0.0
                except Exception:
                    stats = self.pet.stats()
                    reply = self.pet.dialogue.respond(
                        "（AI不可用，切换本地模式）", self.pet.mood, stats
                    )
                    self.pet.chat_reply = reply
                    self.pet.typing_progress = 0.0
```

- [ ] **Step 9: 修改 pet_frame 方法，使用动画帧**

将 `pet_frame` 方法替换为：

```python
        def pet_frame(self, mood: str) -> list[str]:
            # Use action animation if active
            if self.pet.action_anim is not None and not self.pet.action_anim.done:
                return self.pet.action_anim.current

            # Growth-stage-aware idle frame
            stage = self.pet.current_stage
            body_color = {"幼年期": "38;5;159", "成长期": "38;5;87", "成熟期": "38;5;213"}.get(stage, "38;5;87")

            blink = self.pet.blink_timer > 0 or int(self.pet.age * 4) % 18 == 0
            eyes = "◕ ◕" if not blink else "─ ─"
            if mood == "sleepy":
                eyes = "˘ ˘"
            elif mood == "hungry":
                eyes = "• •"
            elif mood == "spark":
                eyes = "✦ ✦"
            mouth = {
                "sleepy": "﹏", "hungry": "﹏", "grimy": "﹍",
                "spark": "◡", "cozy": "▿",
            }.get(mood, "ᵔ")

            if stage == "幼年期":
                return make_pet_frame_small(eyes, mouth, body_color)
            elif stage == "成熟期":
                return make_pet_frame_large(eyes, mouth, body_color)
            else:
                wobble = math.sin(self.pet.bob_phase) * 1.2
                offset = 2 + int(round(wobble))
                aura = "" if self.pet.petting_glow < 0.1 else c("38;5;213") + "◌" * 6 + RESET
                frame = make_pet_frame(eyes, mouth, body_color)
                if aura:
                    frame.insert(0, f"{' ' * (offset + 3)}{aura}")
                return frame
```

- [ ] **Step 10: 修改 render 方法，显示游戏/对话/探索 UI**

在 `render` 方法中，找到 `stat_lines` 构建之后，`panel_width` 计算之前的区域，追加以下内容到 `info` 列表之后：

修改 info 列表，在其后追加游戏和对话相关的行：

在 `info` 列表定义后追加：

```python
            # Game / chat / explore overlays
            extra_lines: list[str] = []
            if self.pet.chatting:
                visible_reply = self.pet.chat_reply[: int(self.pet.typing_progress)] if self.pet.chat_reply else ""
                extra_lines.append(f"{c('38;5;214')}对话{RESET}    > {self.pet.chat_input}_")
                if visible_reply:
                    prefix = "[AI] " if ai_available() else ""
                    extra_lines.append(f"{c('38;5;123')}回复{RESET}    {prefix}{visible_reply}")
            if self.pet.reaction_game is not None and self.pet.reaction_game.active:
                extra_lines.append(self.pet.reaction_game.render().strip())
            if self.pet.number_game is not None and self.pet.number_game.active:
                for line in self.pet.number_game.render().strip().split("\n"):
                    extra_lines.append(line)
            if self.pet.explore is not None and self.pet.explore.exploring:
                path = self.pet.explore.render_path(panel_width)
                extra_lines.append(f"{c('38;5;87')}探索中{RESET}  {path}")
            if self.pet.current_stage and self.pet.current_stage != "成长期":
                extra_lines.append(f"{c('38;5;220')}阶段{RESET}    {self.pet.current_stage}")
            if extra_lines:
                info = info + extra_lines
```

- [ ] **Step 11: 验证完整运行**

```bash
python puppet.py
```
Expected: 程序正常启动，显示宠物界面。按 t 进入对话，按 e 探索，按 g/1/2 玩游戏，按 h 切换帮助。

---

### Task 5: 测试和收尾

- [ ] **Step 1: 验证所有模块可独立导入**

```bash
python -c "from animation import *; from dialogue import *; from games import *; print('All modules OK')"
```
Expected: `All modules OK`

- [ ] **Step 2: 快速功能测试**

启动程序后手动验证：
1. 按 f 喂食 → 看到食物粒子飘起 + 咀嚼动画
2. 按 p 抚摸 → 看到爱心粒子和眯眼动画
3. 按 t → 进入对话模式，输入"你好"回车 → 收到回复
4. 按 e → 探索开始，看到路径动画
5. 按 1 → 反应测试，看到 ✦ 目标出现
6. 按 2 → 猜数字游戏，输入数字猜
7. 各状态条正常更新
8. 按 q 正常退出
