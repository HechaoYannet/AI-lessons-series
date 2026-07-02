"""Local keyword dialogue + optional AI chat for the terminal pet."""
from __future__ import annotations

import os
import random
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
    "praise": ["可爱", "棒", "厉害", "不错", "漂亮", "帅", "赞", "乖", "真", "太"],
    "complain": ["烦", "累", "不开心", "难过", "糟糕", "差", "讨厌", "生气", "郁闷", "无聊", "没意思"],
    "goodbye": ["拜", "再见", "88", "bye", "走了", "晚安", "回见", "下次", "离开"],
    "food": ["吃", "饿", "食物", "饭", "喂", "零食", "馋", "饱", "肚子"],
    "play": ["玩", "游戏", "动", "跳", "跑", "耍", "嗨", "运动"],
    "love": ["爱", "喜欢", "想", "贴贴", "抱", "摸", "亲", "陪"],
}


@dataclass
class DialogueSystem:
    """Local keyword dialogue engine with context memory."""

    context: list[str] = field(default_factory=list)
    history: list[tuple[str, str]] = field(default_factory=list)
    _used: dict[str, set[str]] = field(default_factory=dict)

    def _context_limit(self) -> int:
        cfg = _load_config()
        return cfg.get("ai", {}).get("context_size", 50)

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
        # Trim context to configured limit
        limit = self._context_limit()
        if len(self.context) > limit:
            self.context = self.context[-limit:]
        # Store in displayable history
        self.history.append((text, chosen))

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


# ── AI config ──

def _load_config() -> dict:
    """Load config.json from the project directory (same dir as this file)."""
    import json

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.isfile(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def ai_available() -> bool:
    cfg = _load_config()
    return bool(cfg.get("ai", {}).get("api_key", ""))


def ai_model() -> str:
    cfg = _load_config()
    return cfg.get("ai", {}).get("model", "gpt-4o-mini")


def ai_base_url() -> str:
    cfg = _load_config()
    return cfg.get("ai", {}).get("base_url", "https://api.openai.com/v1")


def ai_chat(history: str, pet_name: str, mood: str, stats: dict[str, float]) -> str:
    """Send conversation to AI and return response. Synchronous, blocks ~1-3s."""
    import json
    import urllib.request

    cfg = _load_config()
    ai_cfg = cfg.get("ai", {})
    api_key = ai_cfg.get("api_key", "")
    model = ai_cfg.get("model", "gpt-4o-mini")
    base_url = ai_cfg.get("base_url", "https://api.openai.com/v1")
    max_tokens = ai_cfg.get("max_tokens", 150)
    temperature = ai_cfg.get("temperature", 0.9)
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
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()


def ai_chat_stream(history: str, pet_name: str, mood: str, stats: dict[str, float], token_queue) -> None:
    """Stream AI response tokens into token_queue. Puts None when done.

    Intended to be run in a background thread so the main loop stays responsive.
    """
    import json
    import urllib.request

    cfg = _load_config()
    ai_cfg = cfg.get("ai", {})
    api_key = ai_cfg.get("api_key", "")
    model = ai_cfg.get("model", "gpt-4o-mini")
    base_url = ai_cfg.get("base_url", "https://api.openai.com/v1")
    max_tokens = ai_cfg.get("max_tokens", 150)
    temperature = ai_cfg.get("temperature", 0.9)
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
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }).encode()

    try:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            for line in resp:
                line = line.decode("utf-8", errors="replace").strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            token_queue.put(content)
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        try:
            token_queue.put(f"（AI 响应失败：{e}）")
        except Exception:
            pass
    finally:
        try:
            token_queue.put(None)
        except Exception:
            pass
