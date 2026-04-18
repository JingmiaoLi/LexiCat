import json
import random
import re
import base64
import io
from pathlib import Path

from PIL import Image, ImageOps
import streamlit as st
import gtts
import streamlit.components.v1 as components


# =========================
# 配置
# =========================

# =========================
# 🌍 语言系统
# =========================
TEXT = {
    "correct_feedback": {
        "EN": [
            "Purrfect! 🐾 You earned a fish!",
            "Nice job! Kitty is happy 😺",
            "Yay! Another fish collected 🐟"
        ],
        "中文": [
            "答对啦！小喵开心地吃掉了一颗喵粮！",
            "太棒啦！又收获一颗喵粮～",
        ]
    },

    "wrong_feedback": {
        "EN": [
            "It's okay, let's take it slow, meo🐱",
            "That was just a tiny mistake, meow. Let's keep going~",
            "I'm right here with you🐱. Let's try again together, okay?",
            "A true hero isn't afraid to start over, meow. Let's go again!",
            "I won't cry, meow! We'll earn those fish back in no time~"
        ],
        "中文": [
            "没关系喵🐱，我们再慢慢来就好",
            "刚刚只是小失误喵🐱，我们继续加油～",
            "小喵陪着你呢❤️，一起再试试看好不好",
            "英雄不怕从头再来喵💪，我们继续冲～",
            "小喵才不哭🥺呢，马上又能赚到喵粮～",
            ]
    },

    "food_lost": {
        "EN": [
            "Oops... you lost {drop} fish 🥺 but we can earn them back!",
            "{drop} fish slipped away 🐟 but don't worry!"
        ],
        "中文": [
            "哎呀喵🥺 掉了 {drop} 颗喵粮，不过我们可以再赚回来。",
            "喵呜…掉了 {drop} 颗喵粮，不过不用担心～"
        ]
    },

    "rule_0": {
        "EN": "Everything feels calm today... keep it up 🐾",
        "中文": "小喵今天很安心喵～继续保持就好啦。"
    },

    "rule_1": {
        "EN": "Careful... 1 mistake so far!",
        "中文": "要小心一点点喵～现在已经答错 1 次啦。"
    },

    "rule_2": {
        "EN": "Uh-oh... Our fish may swim away if we make 1 more mistake🥺",
        "中文": "喵粮开始有点不安了喵🥺 再错 1 次可能会掉几颗喔"
    },

    "rule_3": {
        "EN": "Let's slow down and try again 🐾",
        "中文": "我们慢慢来喵～"
    },

    "title": {
        "EN": "LexiCat",
        "中文": "喵喵单词屋"
    },
    "pet_status_line_default": {
        "EN": "Come learn with me... I've been waiting for you 🐾",
        "中文": "快来陪我学单词吧，我在等你喔～"
    },
    "rule_status_line_default": {
        "EN": "Everything feels calm today... keep it up 🐾",
        "中文": "小喵今天很安心喵～继续保持就好啦。"
    },
    "progress_label": {
        "EN": "Today's Progress",
        "中文": "今日喂喵进度"
    },
    "food_label": {
        "EN": "Fish Collected",
        "中文": "喵粮数"
    },
    "sleep_done": {
        "EN": "🎉 All done today! Kitty is sleeping now.",
        "中文": "🎉 今天的小任务完成啦！小喵已经睡着了。"
    },
    "new_day": {
        "EN": "Start New Day",
        "中文": "开始新一天"
    },
    "pet_status_title": {
        "EN": "Kitty Status",
        "中文": "小喵今天的状态"
    }
}

def t(key):
    return TEXT[key][st.session_state.get("lang", "EN")]

def t_choice(key):
    return random.choice(TEXT[key][st.session_state.get("lang", "EN")])


BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data/processed/unit1_parsed.json"
ASSETS_DIR = BASE_DIR / "assets"

HUNGRY_CAT = ASSETS_DIR / "hungry_cat.png"
HAPPY_CAT = ASSETS_DIR / "happy_cat.png"
SLEEPING_CAT = ASSETS_DIR / "sleeping_cat.png"
BACKGROUND_IMG = ASSETS_DIR / "background_small.png"
FISH_IMG = ASSETS_DIR / "fish2.png"

DAILY_GOAL = 10
APP_TITLE = "LexiCat"


# =========================
# 数据加载
# =========================
@st.cache_data
def load_words(path: str | Path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到数据文件: {p}")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned = []
    for item in data:
        if item.get("id") and item.get("word"):
            cleaned.append(item)
    return cleaned


# =========================
# 图片工具
# =========================
@st.cache_data
def load_fish_variants(path: str | Path):
    p = Path(path)
    if not p.exists():
        return None, None

    fish = Image.open(p).convert("RGBA")

    fish_done = fish.copy()

    gray_rgb = ImageOps.grayscale(fish).convert("RGBA")
    alpha = fish.getchannel("A")
    fish_gray = gray_rgb.copy()
    fish_gray.putalpha(alpha)

    return fish_done, fish_gray


def pil_to_base64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# =========================
# 题目工具
# =========================
def capitalize_if_sentence_start(sentence: str, word: str) -> str:
    if sentence.strip().startswith("______"):
        return word.capitalize()
    return word


def build_options(correct_word: str, all_words: list, sentence: str, n_options: int = 4):
    pool = [w["word"] for w in all_words if w["word"] != correct_word]
    distractors = random.sample(pool, k=min(n_options - 1, len(pool)))
    options = distractors + [correct_word]
    options = [capitalize_if_sentence_start(sentence, opt) for opt in options]
    random.shuffle(options)
    return options


def blank_word_in_sentence(sentence: str, word: str) -> str:
    if not sentence or not word:
        return sentence

    pattern = re.compile(re.escape(word), re.IGNORECASE)

    if pattern.search(sentence):
        return pattern.sub("______", sentence, count=1)

    return f"______  {sentence}"


# =========================
# 状态初始化
# =========================
def init_state(words):
    defaults = {
        "show_review": False,
        "answered": False,
        "cat_food": 0,
        "today_done": 0,
        "wrong_attempts_current_q": 0,
        "total_wrong_today": 0,
        "food_lost": False,
        "last_drop": 0,
        "sleeping": False,
        "checked": False,
        "selected_option": None,
        "wrong_ids": [],
        "done_ids": [],
        "last_result": None,
        "last_selected_option": None,
        "selected_answer": None,
        "correct_answer": None,
        "pet_status_line": t("pet_status_line_default"),
        "rule_status_line": t("rule_status_line_default"),
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "current_q" not in st.session_state:
        st.session_state.current_q = pick_next_question(words)


# =========================
# 文案工具
# =========================
def get_pet_message(done, goal, sleeping):
    lang = st.session_state.get("lang", "EN")

    if lang == "EN":
        if sleeping:
            return "I'm full now... time to sleep 💤"
        if done == 0:
            return "I'm hungry... can I have my first fish? 🥺"
        remain = goal - done
        if remain <= 0:
            return "I'm full and happy!"
        if remain == 1:
            return "Just 1 more fish!"
        return f"{remain} more fish to go!"

    else:
        if sleeping:
            return "今天已经吃到 10 颗喵粮啦，我要抱着小被子睡觉啦～"
        if done == 0:
            return "我今天还没吃到喵粮，想先吃第一颗🥺"
        remain = goal - done
        if remain <= 0:
            return "今天已经吃得很满足啦～"
        if remain == 1:
            return "再喂我 1 颗喵粮，我就吃饱啦！"
        return f"今天目标是 10 颗喵粮，再喂我 {remain} 颗就够啦～"

def get_pet_result_message(last_result):
    lang = st.session_state.get("lang", "EN")

    if last_result is True:
        if lang == "EN":
            return random.choice([
                "Purrfect! 🐾",
                "Nice job! 😺",
                "You got it!",
            ])
        else:
            return random.choice([
                "太棒啦🎊！我又吃到一颗喵粮～",
                "答对啦😊，我现在更开心了！",
            ])

    if last_result is False:
        if lang == "EN":
            return random.choice([
                "Almost there! Try again 🐾",
                "Oops! Try once more 😺",
            ])
        else:
            return random.choice([
                "没关系，我们再试一次好不好？",
                "差一点点，我陪你再看看～",
            ])

    return "Let's learn!" if lang == "EN" else "快来陪我学单词吧～"

def get_wrong_count_message(total_wrong: int) -> str:
    if total_wrong == 0:
        return t("rule_0")
    elif total_wrong == 1:
        return t("rule_1")
    elif total_wrong == 2:
        return t("rule_2")
    else:
        return t("rule_3")

def get_recovery_message():
    return t_choice("wrong_feedback")


# =========================
# 鼓励语（小喵语气）
# =========================
TAILS = ["喵～", "喵！", "喵呜～", "喵～🐾", "喵！✨"]


def get_encourage_message():
    lang = st.session_state.get("lang", "EN")

    if lang == "EN":
        return random.choice([
            "Almost there! 🐾",
            "Try again, you got this!",
            "So close! One more try!",
        ])
    else:
        base = random.choice([
            "差一点点就对啦，我们再try一次好不好",
            "没关系，这题小喵陪你一起再看看",
            "已经很接近答案啦，再想一下就成功啦",
        ])
        return "🐾 " + base + random.choice(TAILS)

def get_wrong_hint_message(q):
    lang = st.session_state.get("lang", "EN")
    attempts = st.session_state.get("wrong_attempts_current_q", 0)
    example_zh = q.get("example_zh", "")

    if attempts < 2:
        return None

    if example_zh:
        if lang == "EN":
            return f"Hint: \"{example_zh}\" 🤫"
        else:
            return f"『{example_zh}』…嘘🤫 喵～"

    return None

def get_cat_image(done: int, goal: int, sleeping: bool) -> Path:
    if sleeping and SLEEPING_CAT.exists():
        return SLEEPING_CAT
    if done == 0 and HUNGRY_CAT.exists():
        return HUNGRY_CAT
    if HAPPY_CAT.exists():
        return HAPPY_CAT
    return HUNGRY_CAT


# =========================
# 出题逻辑
# =========================
def pick_next_question(words):
    wrong_ids = st.session_state.get("wrong_ids", [])

    if wrong_ids:
        wrong_pool = [w for w in words if w["id"] in wrong_ids]
        q = random.choice(wrong_pool) if wrong_pool else random.choice(words)
    else:
        q = random.choice(words)

    q = q.copy()
    q["question_sentence"] = blank_word_in_sentence(q.get("example_en", ""), q.get("word", ""))
    q["options"] = build_options(q["word"], words, q["question_sentence"])
    return q


def go_next(words):
    if st.session_state.get("food_lost", False):
        st.session_state.rule_status_line = get_recovery_message()

    st.session_state.current_q = pick_next_question(words)
    st.session_state.checked = False
    st.session_state.answered = False
    st.session_state.selected_option = None
    st.session_state.last_selected_option = None
    st.session_state.last_result = None
    st.session_state.show_review = False
    st.session_state.selected_answer = None
    st.session_state.correct_answer = None
    st.session_state.wrong_attempts_current_q = 0
    st.session_state.food_lost = False


def try_again():
    if st.session_state.get("food_lost", False):
        st.session_state.rule_status_line = get_recovery_message()

    st.session_state.selected_option = None
    st.session_state.last_selected_option = None
    st.session_state.answered = False
    st.session_state.checked = False
    st.session_state.last_result = None
    st.session_state.show_review = False
    st.session_state.selected_answer = None
    st.session_state.correct_answer = None
    st.session_state.food_lost = False


# =========================
# 判题逻辑
# =========================
def check_answer(words, choice: str):
    q = st.session_state.current_q

    if not choice or st.session_state.answered:
        return

    st.session_state.selected_answer = choice
    st.session_state.correct_answer = q["word"]
    st.session_state.selected_option = choice
    st.session_state.last_selected_option = choice
    st.session_state.checked = True
    st.session_state.answered = True

    if choice.lower() == q["word"].lower():
        st.session_state.last_result = True
        st.session_state.wrong_attempts_current_q = 0
        st.session_state.food_lost = False
        st.session_state.pet_status_line = get_pet_result_message(True)
        st.session_state.rule_status_line = get_wrong_count_message(st.session_state.total_wrong_today)

        if q["id"] not in st.session_state.done_ids:
            st.session_state.done_ids.append(q["id"])
            st.session_state.cat_food += 1
            st.session_state.today_done += 1

        if q["id"] in st.session_state.wrong_ids:
            st.session_state.wrong_ids.remove(q["id"])

        if st.session_state.today_done >= DAILY_GOAL:
            st.session_state.sleeping = True

    else:
        st.session_state.last_result = False
        st.session_state.wrong_attempts_current_q += 1
        st.session_state.total_wrong_today += 1
        st.session_state.food_lost = False
        st.session_state.pet_status_line = get_pet_result_message(False)

        if q["id"] not in st.session_state.wrong_ids:
            st.session_state.wrong_ids.append(q["id"])

        if st.session_state.total_wrong_today >= 3:
            drop = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
            drop = min(drop, st.session_state.today_done)

            st.session_state.cat_food = max(0, st.session_state.cat_food - drop)
            st.session_state.today_done = max(0, st.session_state.today_done - drop)

            if len(st.session_state.done_ids) >= drop:
                st.session_state.done_ids = st.session_state.done_ids[:-drop]
            else:
                st.session_state.done_ids = []

            st.session_state.total_wrong_today = 0
            st.session_state.food_lost = True
            st.session_state.last_drop = drop
            st.session_state.rule_status_line = t("rule_3")
            
            st.rerun()
        else:
            st.session_state.rule_status_line = get_wrong_count_message(st.session_state.total_wrong_today)


# =========================
# 样式
# =========================
def render_css():
    bg_base64 = ""
    if BACKGROUND_IMG.exists():
        with open(BACKGROUND_IMG, "rb") as f:
            bg_base64 = base64.b64encode(f.read()).decode()

    bg_css = (
        f'background: url("data:image/png;base64,{bg_base64}") center center / cover no-repeat;'
        if bg_base64
        else "background: linear-gradient(180deg, #fdf8f2, #f6efe6);"
    )

    st.markdown(
        f"""
        <style>
        .stApp {{
            position: relative;
            {bg_css}
        }}
        /* ❌ 先全部注释掉 */
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(255,255,255,0.32);
            pointer-events: none;
            z-index: 0;
        }}
        /* ❌ 先全部注释掉 */

        [data-testid="stAppViewContainer"] {{
            position: relative;
            z-index: 10;
        }}

         .block-container {{
            padding-top: 0.8rem !important;
            padding-bottom: 0.8rem;
            max-width: 980px;
        }}

        [data-testid="stHeader"],
        header[data-testid="stHeader"],
        [data-testid="stToolbar"] {{
            background: transparent !important;
        }}

       

        div[data-testid="stVerticalBlock"] {{
            gap: 0.38rem !important;
        }}

        div[data-testid="element-container"] {{
            margin-bottom: 0 !important;
        }}

        .status-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #6a5240;
            margin-bottom: 0.3rem;
        }}

        .status-text {{
            font-size: 0.98rem;
            color: #7a6758;
            line-height: 1.5;
            margin-bottom: 0rem;
        }}

        .status-hint {{
            font-size: 0.88rem;
            color: #b7a79a;
            margin-top: 0rem;
            line-height: 1.4;
            font-style: italic;
        }}

        .rule-text {{
            font-size: 0.9rem;
            color: #9a806a;
            line-height: 1.5;
            margin-top: 0.1rem;
            padding-left: 10px;
            border-left: 3px solid rgba(242, 199, 110, 0.6);
        }}

        .stats-wrap {{
            background: rgba(255,255,255,0.78);
            border: 1px solid #efe4d7;
            border-radius: 20px;
            padding: 14px 16px;
            box-shadow: 0 5px 16px rgba(0,0,0,0.03);
            backdrop-filter: blur(6px);
        }}

        .mini-label {{
            font-size: 0.9rem;
            color: #8b7b6d;
            margin-bottom: 0.2rem;
        }}

        .big-progress {{
            font-size: 1.6rem;
            font-weight: 800;
            color: #6b4f3b;
            line-height: 1.1;
            margin-bottom: 0.6rem;
        }}

        .question-box {{
            background: rgba(255,255,255,0.92);
            border: 1px solid #f0ece6;
            border-radius: 20px;
            padding: 10px 18px;
            box-shadow: 0 5px 16px rgba(0,0,0,0.04);
            margin-top: 4px;
            margin-bottom: 16px;
            backdrop-filter: blur(6px);
        }}

        .question-text {{
            font-size: 1.35rem;
            font-weight: 700;
            color: #3d3a4b;
            line-height: 1.4;
        }}

        div[data-testid="stExpander"] {{
            background: rgba(255,255,255,0.62);
            border: 1px solid #eadfce;
            border-radius: 14px;
            overflow: hidden;
            backdrop-filter: blur(4px);
            margin-bottom: 0.55rem;
        }}

        div[data-testid="stExpander"] details {{
            background: transparent;
        }}

        div[data-testid="stExpander"] summary {{
            padding: 2px 6px;
        }}

        div.stButton {{
            margin-bottom: 0 !important;
        }}

        div.stButton > button {{
            width: 100%;
            border-radius: 14px;
            border: 1px solid rgba(235, 224, 210, 0.9);
            background: rgba(255, 255, 255, 0.76);
            color: #4b3d31;
            padding: 0.62rem 1rem;
            font-size: 0.98rem;
            font-weight: 600;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0,0,0,0.025);
            backdrop-filter: blur(6px);
            transition: all 0.12s ease;
        }}

        div.stButton > button:hover {{
            border-color: #d9c4aa;
            background: rgba(255, 255, 255, 0.9);
            transform: translateY(-1px);
        }}

        div.stButton > button:focus {{
            outline: none;
            box-shadow: 0 0 0 0.15rem rgba(217, 196, 170, 0.2);
        }}

        div.stButton > button:disabled {{
            opacity: 1 !important;
            color: #4b3d31 !important;
            background: rgba(255, 255, 255, 0.82) !important;
            border: 1px solid rgba(220, 205, 188, 0.95) !important;
            box-shadow: 0 3px 10px rgba(0,0,0,0.02) !important;
            cursor: default !important;
        }}

        .review-card {{
            background: linear-gradient(
                135deg,
                rgba(255, 253, 248, 0.94) 0%,
                rgba(255, 248, 239, 0.94) 100%
            );
            border: 1px solid rgba(243, 230, 216, 0.95);
            border-radius: 22px;
            padding: 18px 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.04);
            margin-top: 10px;
            backdrop-filter: blur(6px);
        }}

        div[data-testid="stProgress"] {{
            margin-top: 6px;
        }}

        .option-card {{
            width: 100%;
            border-radius: 14px;
            padding: 0.4rem 1rem;
            font-size: 0.98rem;
            font-weight: 600;
            text-align: center;
            box-sizing: border-box;
            margin-bottom: 0.2rem;
            border: 1px solid rgba(235, 224, 210, 0.9);
            backdrop-filter: blur(6px);
        }}

        .option-card.normal {{
            background: rgba(255, 255, 255, 0.76);
            color: #4b3d31;
        }}

        .option-card.correct {{
            background: rgba(92, 150, 255, 0.92);
            border: 1px solid #4c8fff;
            color: #ffffff;
        }}

        .option-card.wrong {{
            background: rgba(255, 116, 116, 0.92);
            border: 1px solid #ff6f6f;
            color: #ffffff;
        }}

        .option-card.dim {{
            background: rgba(255, 255, 255, 0.56);
            border: 1px solid rgba(228, 218, 206, 0.82);
            color: #9c948a;
        }}

        .fish-row-wrap {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 4px 0 12px 0;
            flex-wrap: nowrap;
            overflow-x: hidden;
        }}

        .fish-paw {{
            font-size: 1.1rem;
            line-height: 1;
            flex: 0 0 auto;
            margin-right: 2px;
        }}

        .fish-row {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: nowrap;
            white-space: nowrap;
        }}

        .fish-row img {{
            width: 34px;
            height: auto;
            display: block;
            flex: 0 0 auto;
        }}

        .feedback-slot {{
            min-height: 48px;
            margin-top: 10px;
            margin-bottom: 4px;
        }}

        .feedback-card {{
            border-radius: 18px;
            padding: 8px 18px;
            border: 1px solid #e7eadf;
            background: rgba(244, 252, 242, 0.82);
            color: #219653;
            font-size: 1.0rem;
            font-weight: 700;
            line-height: 1.5;
            backdrop-filter: blur(4px);
        }}

        .feedback-card.error {{
            border: 1px solid #f1d4d4;
            background: rgba(255, 244, 244, 0.85);
            color: #d64545;
        }}

        .feedback-card.neutral {{
            border: 1px solid transparent;
            background: transparent;
            color: transparent;
            box-shadow: none;
        }}

        .feedback-paw {{
            margin-right: 8px;
        }}

        .hint-card {{
            border-radius: 16px;
            padding: 8px 16px;
            border: 1px solid rgba(173, 204, 255, 0.9);
            background: rgba(235, 244, 255, 0.88);
            color: #2f6fb3;
            font-size: 0.98rem;
            font-weight: 600;
            line-height: 1.5;
            margin-top: 4px;
            margin-bottom: 6px;
            backdrop-filter: blur(4px);
        }}

        /* 压缩 error 和 hint 之间距离 */
        div[data-testid="stAlert"] {{
            margin-bottom: 2px !important;   /* 原来很大 */
        }}

        .action-buttons {{
            margin-top: 6px;
            padding-top: 4px;
        }}

        h1 {{
            margin-top: 0rem !important;
            margin-bottom: 0.2rem !important;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# 选项按钮
# =========================
def render_option_buttons(options, words):
    selected = st.session_state.get("selected_answer")
    correct = st.session_state.get("correct_answer")
    answered = st.session_state.answered
    last_result = st.session_state.last_result

    if not answered:
        for idx, option in enumerate(options):
            if st.button(
                option,
                key=f"option_btn_{st.session_state.current_q['id']}_{idx}",
                use_container_width=True,
            ):
                check_answer(words, option)
                st.rerun()
        return

    if last_result is True:
        for option in options:
            card_class = "correct" if option == correct else "dim"
            st.markdown(
                f"<div class='option-card {card_class}'>{option}</div>",
                unsafe_allow_html=True,
            )
        return

    for option in options:
        card_class = "wrong" if option == selected else "normal"
        st.markdown(
            f"<div class='option-card {card_class}'>{option}</div>",
            unsafe_allow_html=True,
        )


# =========================
# 鱼进度条
# =========================
def render_fish_progress():
    done = st.session_state.today_done

    fish_done, fish_gray = load_fish_variants(FISH_IMG)

    if fish_done is None or fish_gray is None:
        fish_html = "".join("🐟" if i < done else "⚪" for i in range(DAILY_GOAL))
        st.markdown(
            f"""
            <div class="fish-row-wrap">
                <div class="fish-paw">🐾</div>
                <div class="fish-row">{fish_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    fish_done_b64 = pil_to_base64(fish_done)
    fish_gray_b64 = pil_to_base64(fish_gray)

    fish_imgs_html = ""
    for i in range(DAILY_GOAL):
        img_b64 = fish_done_b64 if i < done else fish_gray_b64
        fish_imgs_html += f'<img src="data:image/png;base64,{img_b64}" />'

    st.markdown(
        f"""
        <div class="fish-row-wrap">
            <div class="fish-paw">🐾</div>
            <div class="fish-row">
                {fish_imgs_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# 创建发音按钮
# =========================
def build_audio_button_html(audio_id: str, size: int = 46) -> str:
    icon_size = int(size * 0.44)
    radius = int(size * 0.32)

    return f"""
    <button
        onclick="document.getElementById('{audio_id}').play()"
        title="listen"
        style="
            width:{size}px;
            height:{size}px;
            border:none;
            border-radius:{radius}px;
            background: linear-gradient(180deg, #fffdf9 0%, #fdf4ea 100%);
            box-shadow: 0 4px 12px rgba(91, 70, 54, 0.10);
            display:flex;
            align-items:center;
            justify-content:center;
            cursor:pointer;
            transition: all 0.15s ease;
            flex-shrink:0;
        "
        onmouseover="this.style.transform='translateY(-1px) scale(1.04)'; this.style.boxShadow='0 6px 16px rgba(91,70,54,0.14)'"
        onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 4px 12px rgba(91,70,54,0.10)'"
    >
        <svg width="{icon_size}" height="{icon_size}" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 9.5V14.5C5 14.7761 5.22386 15 5.5 15H8.1C8.21046 15 8.31761 15.0366 8.405 15.1041L12.6875 18.4097C13.0165 18.6636 13.5 18.429 13.5 18.0139V5.9861C13.5 5.57098 13.0165 5.33637 12.6875 5.59028L8.405 8.89594C8.31761 8.96343 8.21046 9 8.1 9H5.5C5.22386 9 5 9.22386 5 9.5Z" fill="#7b6758"/>
            <path d="M16.2 9.2C17.1 10 17.6 11 17.6 12C17.6 13 17.1 14 16.2 14.8" stroke="#7b6758" stroke-width="1.8" stroke-linecap="round"/>
            <path d="M17.9 7.5C19.2 8.7 20 10.3 20 12C20 13.7 19.2 15.3 17.9 16.5" stroke="#7b6758" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
    </button>
    """
# =========================
# 高亮
# =========================
def highlight_word(sentence: str, word: str) -> str:
    if not sentence or not word:
        return sentence

    pattern = re.compile(re.escape(word), re.IGNORECASE)

    def repl(match):
        return f"<span style='color:#4c8fff; font-weight:800;'>{match.group(0)}</span>"

    return pattern.sub(repl, sentence, count=1)

# =========================
# 生成音频
# =========================
@st.cache_data
def generate_sentence_tts_base64(sentence: str):
    tts = gtts.gTTS(sentence, lang="en")
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    return base64.b64encode(audio_buffer.getvalue()).decode()


@st.cache_data
def generate_tts_base64(word: str):
    tts = gtts.gTTS(word, lang="en")
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    return base64.b64encode(audio_buffer.getvalue()).decode()

@st.dialog("📘 单词卡")
def show_review_dialog(q):
    word = q.get("word", "")
    ipa = q.get("ipa", "")
    pos = q.get("pos", "")
    cn = q.get("cn", "")
    collocations = q.get("collocations", [])

    syllables = [s.strip() for s in q.get("visual_syllables", []) if s and s.strip()]
    syllable_line = " - ".join(syllables)

    meaning_line = f"{pos} {cn}" if pos else cn

    # ✅ 用缓存音频
    audio_b64 = generate_tts_base64(word)

    # -------------------
    # 1️⃣ 核心信息
    # -------------------
    audio_id = f"word-audio-{word}"
    button_html = build_audio_button_html(audio_id, size=48)

    components.html(
        f"""
        <div style="
            margin:0;
            padding:0;
        ">

            <!-- 单词 + 按钮 -->
            <div style="
                display:flex;
                align-items:center;
                gap:8px;
                margin:0;
            ">
                <div style="
                    font-size:1.45rem;
                    font-weight:800;
                    color:#3d3a4b;
                    line-height:1.1;
                ">
                    {word}
                </div>

                <div style="transform: scale(0.9);">
                    {button_html}
                </div>
            </div>

            <!-- 音标 -->
            <div style="
                color:#8b7b6d;
                font-size:1rem;
                line-height:1.2;
                margin-top:2px;
            ">
                {ipa if ipa else ""}
            </div>

            <audio id="{audio_id}">
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>

        </div>
        """,
        height=80,
    )



    if meaning_line:
        st.markdown(f"<div style='margin-top:0px; font-size:1.05rem'>{meaning_line}</div>", unsafe_allow_html=True)

    # 5️⃣ 音节速记（有才显示）
    # -------------------
    if syllable_line:
        st.markdown(
            f"<div style='margin-top:8px; margin-bottom:14px; color:#7a6758;'>音节速记： {syllable_line}</div>",
            unsafe_allow_html=True,
        )
    # -------------------
    # 4️⃣ 常见组合（默认展开）
    # -------------------
    if collocations:
        st.markdown("### ✨ 常见组合")

        for c in collocations:
            st.markdown(f"""
            <div style="
                padding:8px 12px;
                margin-bottom:6px;
                background:rgba(255,255,255,0.75);
                border-radius:10px;
                border:1px solid #eee;
            ">
                {c}
            </div>
            """, unsafe_allow_html=True)

    # -------------------


    # -------------------
    # 6️⃣ 关闭按钮
    # -------------------
    if st.button("关闭", use_container_width=True):
        st.session_state.show_review = False
        st.rerun()

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
# =========================
# UI
# =========================
def main():

    # 1️⃣ 初始化语言（必须最先）
    if "lang" not in st.session_state:
        st.session_state.lang = "EN"

    st.set_page_config(
        page_title=t("title"),
        page_icon="🐱",
        layout="centered"
        )

    # 2️⃣ 语言选择 UI
    lang = st.radio(
        "",
        ["EN", "中文"],
        horizontal=True,
        index=0 if st.session_state.lang == "EN" else 1
    )

    st.session_state.lang = lang

    # 3️⃣ 初始化 last_lang
    if "last_lang" not in st.session_state:
        st.session_state.last_lang = st.session_state.lang

    # 4️⃣ 如果语言发生变化 → 更新文案
    if st.session_state.last_lang != st.session_state.lang:
        st.session_state.pet_status_line = t("pet_status_line_default")
        st.session_state.rule_status_line = t("rule_status_line_default")
        st.session_state.last_lang = st.session_state.lang
        st.rerun()   # ⭐⭐⭐ 关键
        

    render_css()

    words = load_words(DATA_FILE)
    init_state(words)

    q = st.session_state.current_q
    # ✅ 提前预生成当前单词的音频（避免点击 review 时卡顿）
    _ = generate_tts_base64(q.get("word", ""))
    _ = generate_sentence_tts_base64(q.get("example_en", ""))
    pet_img = get_cat_image(st.session_state.today_done, DAILY_GOAL, st.session_state.sleeping)
    pet_msg = get_pet_message(st.session_state.today_done, DAILY_GOAL, st.session_state.sleeping)

    st.markdown(
        f"""
        <h1 style='text-align: center; color: #5b4636; margin-top: 0.2rem; margin-bottom: 0.8rem; font-weight: 800;'>
            {t("title")}
        </h1>
        """,
        unsafe_allow_html=True,
    )

    left, middle, right = st.columns(
        [0.9, 1.6, 1.0],
        vertical_alignment="center"
        )

    with left:
        if pet_img.exists():
            st.markdown("<div class='cat-wrap'>", unsafe_allow_html=True)
            st.image(str(pet_img), width=150)
            st.markdown("</div>", unsafe_allow_html=True)

    with middle:
        st.markdown(
            f"""
            <div style="max-width: 420px">
                <div class="status-title">{t("pet_status_title")}</div>
                <div class="status-text">{pet_msg}</div>
                <div class="status-hint">{st.session_state.pet_status_line}</div>
                <div class="rule-text">{st.session_state.rule_status_line}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            f"""
            <div class="stats-wrap">
                <div class="mini-label">{t("progress_label")}</div>
                <div class="big-progress">{st.session_state.today_done}/{DAILY_GOAL}</div>
                <div class="mini-label">{t("food_label")}</div>
                <div class="big-progress" style="margin-bottom:0;">{st.session_state.cat_food}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(st.session_state.today_done / DAILY_GOAL, 1.0))

    if st.session_state.sleeping:
        st.success(t("sleep_done"))
        if st.button(t("new_day"), use_container_width=True):
            st.session_state.today_done = 0
            st.session_state.cat_food = 0
            st.session_state.total_wrong_today = 0
            st.session_state.sleeping = False
            st.session_state.done_ids = []
            st.session_state.last_result = None
            st.session_state.food_lost = False
            st.session_state.last_drop = 0
            st.session_state.pet_status_line = t("pet_status_line_default")
            st.session_state.rule_status_line = t("rule_status_line_default")
            go_next(words)
            st.rerun()
        st.stop()

    render_fish_progress()

    is_correct = (
        st.session_state.get("answered", False)
        and st.session_state.get("last_result") is True
    )

    if not is_correct:
        st.markdown(
            f"""
            <div class='question-box'>
                <div class='question-text'>
                    {q.get("question_sentence", "")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        full_sentence = q.get("example_en", "")
        correct_word = q.get("word", "")
        highlighted_sentence = highlight_word(full_sentence, correct_word)

        audio_b64 = generate_sentence_tts_base64(full_sentence)
        audio_id = f"sentence-audio-{q.get('id', 'x')}"
        button_html = build_audio_button_html(audio_id, size=46)

        components.html(
            f"""
            <div class="question-box" style="
                background: rgba(255,255,255,0.92);
                border: 1px solid #f0ece6;
                border-radius: 20px;
                padding: 10px 18px;
                box-shadow: 0 5px 16px rgba(0,0,0,0.04);
                margin-top: 4px;
                margin-bottom: 16px;
                backdrop-filter: blur(6px);
            ">
                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap:12px;
                ">
                    <div style="
                        font-size:1.35rem;
                        font-weight:700;
                        color:#3d3a4b;
                        line-height:1.4;
                        flex:1;
                    ">
                        {highlighted_sentence}
                    </div>

                    {button_html}
                </div>

                <audio id="{audio_id}">
                    <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                </audio>
            </div>
            """,
            height=95,
        )
    render_option_buttons(q["options"], words)

    feedback_html = "<div class='feedback-card neutral'>占位</div>"

    

    lang = st.session_state.get("lang", "EN")

    if st.session_state.answered:
        if st.session_state.last_result is True:

            msg = t_choice("correct_feedback")

            feedback_html = f"""
                <div class='feedback-card'>
                    <span class='feedback-paw'>🐾</span>
                    {msg}
                </div>
            """

        else:
            if st.session_state.get("food_lost", False):

                drop = st.session_state.get("last_drop", 1)
                template = t_choice("food_lost")
                msg = template.format(drop=drop)

                feedback_html = f"""
                    <div class='feedback-card error'>
                        <span class='feedback-paw'>🐾</span>
                        {msg}
                    </div>
                """

            else:
                msg = t_choice("wrong_feedback")

                feedback_html = f"""
                    <div class='feedback-card error'>
                        <span class='feedback-paw'>🐾</span>
                        {msg}
                    </div>
                """

    st.markdown(
        f"<div class='feedback-slot'>{feedback_html}</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.answered:
        if st.session_state.last_result is True:

            # ✅ 答对：只显示 review + next
            st.markdown("<div class='action-buttons'>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("review", key="review_correct", use_container_width=True):
                    st.session_state.show_review = True
                    st.rerun()
            with c2:
                if st.button("next", key="next_correct", use_container_width=True):
                    go_next(words)
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            # ❌ 答错：显示 hint（如果有）
            hint_msg = get_wrong_hint_message(q)

            if hint_msg:
                st.markdown(
                    f"""
                    <div class='hint-card'>
                        <span class='feedback-paw'>🐾</span>
                        {hint_msg}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # ✅ 再显示 try again + next
            st.markdown("<div class='action-buttons'>", unsafe_allow_html=True)

            c0, c1 = st.columns(2)
            with c0:
                if st.button("try again", key="try_again_wrong", use_container_width=True):
                    try_again()
                    st.rerun()
            with c1:
                if st.button("next", key="next_wrong", use_container_width=True):
                    go_next(words)
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
        
    if st.session_state.show_review:
        show_review_dialog(q)

if __name__ == "__main__":
    main()