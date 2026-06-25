import telebot
import urllib.parse
import markovify
import random
import threading
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import logging
from gtts import gTTS

# ─── Логирование ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─── Конфиг ────────────────────────────────────────────────────────────────────
TOKEN = "8464842453:AAE4QiUoCGhNdjNyCA3vRLMuloDOIinMPGc"

LIMITS = {
    "messages": 5000,
    "user_msgs": 700,
    "photos": 200,
}

# Уровни активности: (авто-ответ, стих, мем, войс, дем, мат, стик)
LEVELS = {
    1: (200, 500, 400, 500, 800, 200, 600),
    2: (150, 350, 300, 350, 600, 150, 450),
    3: (100, 250, 200, 250, 400, 100, 300),
    4: (75,  150, 150, 150, 300, 75,  200),
    5: (40,  80,  80,  80,  150, 40,  100),
}

MAT_VOICE_EVERY = 10
MAT_REPLY_CHANCE = 0.05

MAT = [
    "блять", "бля", "нахуй", "хуй", "пизда", "ебать", "сука", "пиздец",
    "залупа", "мудак", "долбаёб", "ёбанный", "хуйня", "пиздабол", "уёбок",
    "гондон", "мразь", "тварь", "ушлёпок", "дебил", "идиот", "придурок",
    "сволочь", "скотина", "паскуда", "ебанат", "охуел", "охренел",
    "заебал", "наебал", "обоссан", "выебон", "хуесос", "пидор", "ебало",
    "рыло", "чмо", "лох", "дурак", "тупой", "конченый", "огрызок",
]

EMOJI = ["💀","🗿","😭","🤡","👀","🔥","😐","💅","🫡","🤨","😤","🥶","🤙","🦧",
         "🫠","🤌","😈","🧌","🫃","🤯","💩","🙈","😵","🤪","👁️","🦴","🫀","🧠",
         "🤡","👺","💢","🔞","☠️","🤮","😬","🥴","👻","🫵","🤬"]

# Шаблоны memegen.link
MEME_TEMPLATES = [
    "drake", "buttons", "brain", "change", "gru", "rollsafe", "both",
    "keanu", "sad", "fry", "success", "disaster", "fine", "wolverine",
    "wonka", "patrick", "spongebob", "yuno", "everywhere", "woman",
    "facepalm", "firsttry", "tried", "buzz", "chosen", "bad", "good",
    "money", "idea", "same", "winter", "truth", "doge", "bernie",
    "waiting", "skeleton", "office", "bender", "interesting",
]

# Наклейки (URL)
STICKERS = [
    # Like a boss (очки + сигара)
    "https://i.postimg.cc/xTQn4K5L/boss.png",
    # Очки Minecraft
    "https://i.postimg.cc/3R0KF9Qs/minecraft-glasses.png",
    # Пукающий стикер
    "https://i.postimg.cc/5tZVQ0bN/fart.png",
    # Цифра 67
    "https://i.postimg.cc/8CYKQqW5/67.png",
    # MLG очки
    "https://i.postimg.cc/9QkB8L3H/mlg.png",
    # Смешной лев
    "https://i.postimg.cc/zGxHYsQf/lion.png",
    # Сердечко
    "https://i.postimg.cc/3wGLyN2Q/heart.png",
    # Шаринган
    "https://i.postimg.cc/fyn2n5Vz/sharingan.png",
    # Петух
    "https://i.postimg.cc/4x5kW2kB/rooster.png",
    # Смеющийся смайл
    "https://i.postimg.cc/wMxN0YWg/laughing.png",
    # Supreme box logo
    "https://i.postimg.cc/FHNg6YR4/supreme.png",
    # Adidas значок
    "https://i.postimg.cc/85RGLYS0/adidas.png",
    # Череп
    "https://i.postimg.cc/0NXdBLJX/skull.png",
    # Корона
    "https://i.postimg.cc/yYcLQpW2/crown.png",
    # Слеза
    "https://i.postimg.cc/tJbnQs9x/tear.png",
    # Красный круг (как в ютубе)
    "https://i.postimg.cc/8ctcH2Wx/circle.png",
    # Спарклы
    "https://i.postimg.cc/2yX1p3qR/sparkles.png",
    # Огонь
    "https://i.postimg.cc/sgc5GQQR/fire.png",
    # Каменное лицо
    "https://i.postimg.cc/TPG4wLCQ/moai.png",
    # Глаз терминатора
    "https://i.postimg.cc/d3XjC3jD/terminator.png",
]
# Триггер «кто» — варианты ответов
KTO_ANSWERS = [
    "это {user}, без сомнений",
    "{user}, больше некому",
    "очевидно, {user}",
    "{user}, я так чувствую",
    "все знают что это {user}",
    "{user}, и это не обсуждается",
    "мой внутренний голос говорит — {user}",
    "{user}, а кто же ещё",
    "ну конечно {user}, красавчик",
    "{user}, я за ним давно слежу",
    "это {user}, сто процентов",
    "гадалка сказала — {user}",
    "{user}, я посчитал",
    "по звёздам выходит {user}",
    "{user}, тут и думать нечего",
]

# ─── Файлы для каждого чата ───────────────────────────────────────────────────
def _chat_file(chat_id, name):
    return f"chat_{chat_id}_{name}"

# ─── Хранилище ─────────────────────────────────────────────────────────────────
_cache = {}
_chat_levels = {}
_chat_muted = {}

def _load(chat_id, key):
    cache_key = f"{chat_id}_{key}"
    if cache_key in _cache:
        return _cache[cache_key]
    path = _chat_file(chat_id, f"{key}.json")
    if not os.path.exists(path):
        default = {} if key in ("users", "counter", "settings") else []
        if key == "counter":
            default = {"msgs": 0, "reply": 0, "meme": 0, "voice": 0, "mat": 0, "mat_voice": 0, "dem": 0, "stick": 0}
        if key == "settings":
            default = {"level": 1, "muted": False}
        _cache[cache_key] = default
        return default
    with open(path, "r", encoding="utf-8") as f:
        _cache[cache_key] = json.load(f)
    return _cache[cache_key]

def _save(chat_id, key):
    cache_key = f"{chat_id}_{key}"
    path = _chat_file(chat_id, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_cache[cache_key], f, ensure_ascii=False)

# ─── Markov ────────────────────────────────────────────────────────────────────
_markov_models = {}
_markov_dirty = {}

def _get_markov_model(chat_id):
    if chat_id not in _markov_dirty:
        _markov_dirty[chat_id] = True
    if _markov_dirty[chat_id] or chat_id not in _markov_models:
        msgs = _load(chat_id, "messages")
        if len(msgs) < 10:
            _markov_models[chat_id] = None
            return None
        try:
            _markov_models[chat_id] = markovify.Text(" ".join(msgs), state_size=2)
            _markov_dirty[chat_id] = False
        except Exception as e:
            log.warning(f"Markov error chat {chat_id}: {e}")
            _markov_models[chat_id] = None
    return _markov_models.get(chat_id)

# ─── Сообщения ─────────────────────────────────────────────────────────────────
def add_message(chat_id, text):
    msgs = _load(chat_id, "messages")
    msgs.append(text)
    if len(msgs) > LIMITS["messages"]:
        _cache[f"{chat_id}_messages"] = msgs[-LIMITS["messages"]:]
    _save(chat_id, "messages")
    _markov_dirty[chat_id] = True

def add_user_message(chat_id, user_id, name, text):
    users = _load(chat_id, "users")
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"name": name, "messages": []}
    users[uid]["name"] = name
    users[uid]["messages"].append(text)
    if len(users[uid]["messages"]) > LIMITS["user_msgs"]:
        users[uid]["messages"] = users[uid]["messages"][-LIMITS["user_msgs"]:]
    _save(chat_id, "users")

def get_users(chat_id):
    return _load(chat_id, "users")

# ─── Фото ─────────────────────────────────────────────────────────────────────
def add_photo(chat_id, file_id, from_bot=False):
    if from_bot:
        return
    photos = _load(chat_id, "photos")
    if file_id not in photos:
        photos.append(file_id)
    if len(photos) > LIMITS["photos"]:
        _cache[f"{chat_id}_photos"] = photos[-LIMITS["photos"]:]
    _save(chat_id, "photos")

def get_photos(chat_id):
    return _load(chat_id, "photos")

# ─── Настройки чата ───────────────────────────────────────────────────────────
def get_settings(chat_id):
    return _load(chat_id, "settings")

def save_settings(chat_id):
    _save(chat_id, "settings")

def get_level(chat_id):
    settings = get_settings(chat_id)
    return settings.get("level", 1)

def is_muted(chat_id):
    settings = get_settings(chat_id)
    return settings.get("muted", False)

# ─── Счётчики ─────────────────────────────────────────────────────────────────
def get_counter(chat_id):
    return _load(chat_id, "counter")

def save_counter(chat_id):
    _save(chat_id, "counter")

# ─── Слова чата ───────────────────────────────────────────────────────────────
def _chat_words(chat_id, min_len=2):
    msgs = _load(chat_id, "messages")
    if not msgs:
        return []
    words = []
    for m in msgs:
        words.extend(w.strip(".,!?:;\"'()«»") for w in m.split())
    return [w for w in words if len(w) > min_len]

def _random_phrase(chat_id):
    msgs = _load(chat_id, "messages")
    if not msgs:
        return None
    msg = random.choice(msgs)
    words = msg.split()
    if len(words) > 10:
        start = random.randint(0, max(0, len(words) - 10))
        end = min(start + random.randint(3, 10), len(words))
        return " ".join(words[start:end])
    return msg

def absurd_word_salad(chat_id, source_text="", length=None):
    """60% — 1-3 слова, 30% — 4-7, 10% — 8-10"""
    if length is None:
        roll = random.random()
        if roll < 0.6:
            length = random.randint(1, 3)
        elif roll < 0.9:
            length = random.randint(4, 7)
        else:
            length = random.randint(8, 10)
    
    if random.random() < 0.5:
        phrase = _random_phrase(chat_id)
        if phrase:
            words = phrase.split()
            if len(words) > length:
                phrase = " ".join(words[:length])
            return phrase.strip()
    
    pool = _chat_words(chat_id)
    if source_text:
        pool.extend(w.strip(".,!?:;\"'()«»") for w in source_text.split() if len(w) > 1)
    if not pool:
        return random.choice(EMOJI)
    result = [random.choice(pool) for _ in range(length)]
    text = " ".join(result)
    if random.random() < 0.1:
        text = text.upper()
    if random.random() < 0.3:
        text += random.choice(["?", "!", "??", ""])
    return text.strip()

# ─── Голосовые ────────────────────────────────────────────────────────────────
def generate_voice(text):
    try:
        tts = gTTS(text=text, lang="ru", slow=False)
        voice_io = io.BytesIO()
        tts.write_to_fp(voice_io)
        voice_io.seek(0)
        voice_io.name = "voice.mp3"
        return voice_io
    except Exception as e:
        log.error(f"Voice error: {e}")
        return None

def send_random_voice(bot_instance, chat_id, reply_to=None):
    text = absurd_word_salad(chat_id, length=random.randint(8, 12))
    voice = generate_voice(text)
    if voice:
        try:
            if reply_to:
                bot_instance.send_voice(chat_id, voice, reply_to_message_id=reply_to)
            else:
                bot_instance.send_voice(chat_id, voice)
            return True
        except Exception as e:
            log.error(f"send_random_voice error: {e}")
    return False

def send_mat_voice(bot_instance, chat_id, reply_to=None):
    text = " ".join(random.choices(MAT, k=random.randint(3, 6))).upper()
    voice = generate_voice(text)
    if voice:
        try:
            if reply_to:
                bot_instance.send_voice(chat_id, voice, reply_to_message_id=reply_to)
            else:
                bot_instance.send_voice(chat_id, voice)
            return True
        except Exception as e:
            log.error(f"send_mat_voice error: {e}")
    return False

# ─── Микс ─────────────────────────────────────────────────────────────────────
def mix_messages(chat_id):
    msgs = _load(chat_id, "messages")
    if len(msgs) < 2:
        return absurd_word_salad(chat_id)
    msg1 = random.choice(msgs)
    msg2 = random.choice(msgs)
    words1 = msg1.split()
    words2 = msg2.split()
    if len(words1) < 2 or len(words2) < 2:
        return absurd_word_salad(chat_id)
    half1 = words1[:len(words1)//2]
    half2 = words2[len(words2)//2:]
    mixed = " ".join(half1 + half2)
    return mixed.strip()

# ─── Стихи с рифмами ──────────────────────────────────────────────────────────
RHYMES = {
    "ать": ["мать", "спать", "послать", "страдать", "ждать"],
    "ить": ["жить", "любить", "тупить", "ходить", "говорить"],
    "ой": ["тобой", "судьбой", "головой", "стеной", "луной"],
    "ай": ["давай", "лентяй", "урожай", "сарай", "знай"],
    "еть": ["сидеть", "глядеть", "хотеть", "балдеть", "пиздеть"],
    "ок": ["дружок", "пирожок", "прыжок", "кружок", "звонок"],
    "ак": ["дурак", "рыбак", "чужак", "бивак", "пятак"],
}

def find_rhyme(word):
    word = word.lower()
    for ending, rhymes in RHYMES.items():
        if word.endswith(ending):
            return random.choice(rhymes)
    return word

def make_poem(chat_id):
    model = _get_markov_model(chat_id)
    words = _chat_words(chat_id)
    if not words:
        return absurd_word_salad(chat_id)
    
    lines = []
    for i in range(random.randint(2, 4)):
        if model and random.random() < 0.5:
            line = model.make_short_sentence(50, tries=20)
        else:
            line = " ".join(random.choices(words, k=random.randint(3, 6)))
        
        if line:
            words_in_line = line.split()
            if len(words_in_line) > 8:
                line = " ".join(words_in_line[:8])
            
            # Рифма для чётных строк
            if i % 2 == 1 and len(lines) > 0:
                last_word_prev = lines[-1].split()[-1].strip(".,!?:;\"'()")
                last_word_curr = words_in_line[-1].strip(".,!?:;\"'()")
                if random.random() < 0.5:
                    rhyme = find_rhyme(last_word_prev)
                    if rhyme != last_word_curr:
                        words_in_line[-1] = rhyme
                        line = " ".join(words_in_line)
            
            lines.append(line)
    
    if len(lines) < 2:
        return absurd_word_salad(chat_id)
    return "\n".join(lines[:4])

# ─── Шрифты ───────────────────────────────────────────────────────────────────
def _find_font(size):
    paths = [
        "impact.ttf",
        os.path.join(os.path.dirname(__file__), "impact.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size=size)
        except:
            continue
    return ImageFont.load_default()

def _find_serif_font(size):
    paths = [
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "Times New Roman.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size=size)
        except:
            continue
    return _find_font(size)

# ─── Демотиватор ─────────────────────────────────────────────────────────────
def make_demotivator(img_bytes, text):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    
    max_size = 500
    if w > max_size or h > max_size:
        ratio = min(max_size / w, max_size / h)
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        w, h = new_w, new_h
    
    border = 10
    text_height = 80
    
    canvas_w = w + border * 2
    canvas_h = h + border * 2 + text_height + border
    canvas = Image.new("RGB", (canvas_w, canvas_h), "black")
    
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([3, 3, canvas_w - 3, canvas_h - 3], outline="white", width=3)
    
    canvas.paste(img, (border, border))
    
    font = _find_serif_font(24)
    lines = textwrap.wrap(text, width=30) or [text]
    line_h = 28
    text_y = h + border * 2 + 5
    
    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = (canvas_w - text_w) // 2
        draw.text((text_x, text_y), line, font=font, fill="white")
        text_y += line_h
    
    # Марка lolych
    try:
        mark_font = _find_font(14)
        mark_text = "lolych"
        mark_bbox = draw.textbbox((0, 0), mark_text, font=mark_font)
        mark_w = mark_bbox[2] - mark_bbox[0]
        draw.text((canvas_w - mark_w - 8, canvas_h - 22), mark_text, font=mark_font, fill=(180, 180, 180))
    except:
        pass
    
    out = io.BytesIO()
    canvas.save(out, format="JPEG")
    out.seek(0)
    return out

def send_random_dem(bot_instance, chat_id, reply_to=None, custom_text=None):
    photos = get_photos(chat_id)
    if not photos:
        return False
    file_id = random.choice(photos)
    
    text = custom_text or absurd_word_salad(chat_id, length=random.randint(3, 8))
    
    try:
        file_info = bot_instance.get_file(file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        output = make_demotivator(downloaded, text)
        if reply_to:
            bot_instance.send_photo(chat_id, output, reply_to_message_id=reply_to)
        else:
            bot_instance.send_photo(chat_id, output)
        return True
    except Exception as e:
        log.error(f"send_random_dem error: {e}")
    return False

# ─── Мемы через memegen.link ───────────────────────────────────────────────────
# ─── Мемы через imgflip ───────────────────────────────────────────────────────
IMGFLIP_USER = "lilifridge"
IMGFLIP_PASS = "eMsWrri64INeGJd"

# Популярные шаблоны imgflip (template_id)
IMGFLIP_TEMPLATES = [
    181913649,  # Drake Hotline Bling
    87743020,   # Two Buttons
    93895088,   # Expanding Brain
    252600902,  # Change My Mind
    131940431,  # Gru's Plan
    89370399,   # Roll Safe
    110163934,  # Both Buttons
    61579,      # One Does Not Simply
    101470,     # Ancient Aliens
    217743513,  # UNO Draw 25
    91538330,   # Monkey Puppet
    4087833,    # Waiting Skeleton
    5496396,    # Leonardo Dicaprio Cheers
    1035805,    # Boardroom Meeting
    123999232,  # The Scroll of Truth
    124822590,  # Left Exit 12
    148909805,  # Monkey Puppet Side Eye
    97984,      # Disaster Girl
    161865971,  # Gru's Plan 3 panels
    9440985,    # Third World Skeptical Kid
    55353130,   # Spongebob Ight Imma Head Out
]

def make_imgflip_meme(template_id, texts):
    """Создаёт мем через imgflip API"""
    url = "https://api.imgflip.com/caption_image"
    params = {
        "template_id": template_id,
        "username": IMGFLIP_USER,
        "password": IMGFLIP_PASS,
    }
    for i, text in enumerate(texts):
        params[f"boxes[{i}][text]"] = text[:100]  # макс 100 символов
    
    try:
        resp = requests.post(url, data=params, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("url"):
            return data["data"]["url"]
        else:
            log.error(f"imgflip error: {data.get('error_message', 'unknown')}")
            return None
    except Exception as e:
        log.error(f"imgflip request error: {e}")
        return None

def send_template_meme(bot_instance, chat_id, reply_to=None):
    template_id = random.choice(IMGFLIP_TEMPLATES)
    
    # 1-3 текста для разных шаблонов
    num_texts = random.randint(2, 3)
    texts = [absurd_word_salad(chat_id, length=random.randint(2, 6)) for _ in range(num_texts)]
    
    url = make_imgflip_meme(template_id, texts)
    if url:
        try:
            if reply_to:
                bot_instance.send_photo(chat_id, url, reply_to_message_id=reply_to)
            else:
                bot_instance.send_photo(chat_id, url)
            return True
        except Exception as e:
            log.error(f"send_template_meme error: {e}")
    return False
# ─── Наклейки ────────────────────────────────────────────────────────────────
def make_sticker(img_bytes):
    """Накладывает случайную наклейку на фото"""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    w, h = img.size
    
    # Скачиваем наклейку
    sticker_url = random.choice(STICKERS)
    try:
        sticker_data = requests.get(sticker_url, timeout=5).content
        sticker = Image.open(io.BytesIO(sticker_data)).convert("RGBA")
        
        # Размер наклейки ~20% от фото
        sticker_size = min(w, h) // 5
        sticker = sticker.resize((sticker_size, sticker_size), Image.LANCZOS)
        
        # Случайная позиция
        x = random.randint(0, max(0, w - sticker_size))
        y = random.randint(0, max(0, h - sticker_size))
        
        img.paste(sticker, (x, y), sticker)
    except Exception as e:
        log.error(f"Sticker error: {e}")
    
    # Конвертируем в RGB для JPEG
    img_rgb = img.convert("RGB")
    out = io.BytesIO()
    img_rgb.save(out, format="JPEG")
    out.seek(0)
    return out

def send_sticker_photo(bot_instance, chat_id, reply_to=None):
    photos = get_photos(chat_id)
    if not photos:
        return False
    
    file_id = random.choice(photos)
    try:
        file_info = bot_instance.get_file(file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        output = make_sticker(downloaded)
        if reply_to:
            bot_instance.send_photo(chat_id, output, reply_to_message_id=reply_to)
        else:
            bot_instance.send_photo(chat_id, output)
        return True
    except Exception as e:
        log.error(f"send_sticker_photo error: {e}")
    return False

# ─── Хелперы ──────────────────────────────────────────────────────────────────
def has_mat(text):
    return any(m in text.lower() for m in MAT)

def get_random_user(chat_id):
    users = get_users(chat_id)
    if not users:
        return None
    return random.choice(list(users.values()))["name"]

# ─── Бот ──────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(TOKEN)
_clear_confirm = {}

# ─── Команды ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    commands = """
🎭 *Лолыч к вашим услугам:*
/mix — микс двух сообщений
/poem — стих с рифмой
/meme — мем (шаблонный)
/dem — демотиватор
/stick — наклейка на фото
/voice — голосовое
/stats — статистика
/level 1-5 — уровень активности
/mute — режим тишины
/unmute — включить
/clear — очистить память
"""
    bot.reply_to(message, commands, parse_mode="Markdown")

@bot.message_handler(commands=["level"])
def cmd_level(message):
    args = message.text.split()
    if len(args) < 2:
        current = get_level(message.chat.id)
        bot.reply_to(message, f"Текущий уровень: {current}\n/level 1-5 чтобы изменить")
        return
    
    try:
        level = int(args[1])
        if level < 1 or level > 5:
            bot.reply_to(message, "Уровень от 1 до 5")
            return
        
        settings = get_settings(message.chat.id)
        settings["level"] = level
        save_settings(message.chat.id)
        
        names = {1: "тихий", 2: "спокойный", 3: "обычный", 4: "активный", 5: "бешеный"}
        bot.reply_to(message, f"Уровень: {level} ({names[level]})")
    except:
        bot.reply_to(message, "Напиши: /level 1-5")

@bot.message_handler(commands=["mute"])
def cmd_mute(message):
    settings = get_settings(message.chat.id)
    settings["muted"] = True
    save_settings(message.chat.id)
    bot.reply_to(message, "🔇 Режим тишины. Не пишу, не запоминаю.\n/unmute чтобы включить обратно")

@bot.message_handler(commands=["unmute"])
def cmd_unmute(message):
    settings = get_settings(message.chat.id)
    settings["muted"] = False
    save_settings(message.chat.id)
    bot.reply_to(message, "🔈 Проснулся! Снова с вами.")

@bot.message_handler(commands=["mix", "микс"])
def cmd_mix(message):
    bot.send_message(message.chat.id, mix_messages(message.chat.id))

@bot.message_handler(commands=["poem", "стих", "стишок", "поэзия"])
def cmd_poem(message):
    poem = make_poem(message.chat.id)
    bot.send_message(message.chat.id, f"🎭 *Стихотворение:*\n{poem}", parse_mode="Markdown")

@bot.message_handler(commands=["meme", "мем", "mem"])
def cmd_meme(message):
    if not send_template_meme(bot, message.chat.id):
        bot.reply_to(message, "не смог сделать мем")

@bot.message_handler(commands=["dem", "дем", "демотиватор"])
def cmd_dem(message):
    args = message.text.split(maxsplit=1)
    custom_text = args[1] if len(args) > 1 else None
    
    if message.reply_to_message and message.reply_to_message.photo:
        file_id = message.reply_to_message.photo[-1].file_id
        text = custom_text or absurd_word_salad(message.chat.id, length=random.randint(3, 8))
        try:
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            output = make_demotivator(downloaded, text)
            bot.send_photo(message.chat.id, output)
            return
        except Exception as e:
            log.error(f"dem error: {e}")
            bot.reply_to(message, "не смог сделать демотиватор")
            return
    
    if not send_random_dem(bot, message.chat.id, custom_text=custom_text):
        bot.reply_to(message, "ещё не видел фоток в беседе!")

@bot.message_handler(commands=["stick", "стик", "наклейка"])
def cmd_stick(message):
    if message.reply_to_message and message.reply_to_message.photo:
        file_id = message.reply_to_message.photo[-1].file_id
        try:
            file_info = bot.get_file(file_id)
            downloaded = bot.download_file(file_info.file_path)
            output = make_sticker(downloaded)
            bot.send_photo(message.chat.id, output)
            return
        except Exception as e:
            log.error(f"stick error: {e}")
            bot.reply_to(message, "не смог наложить наклейку")
            return
    
    if not send_sticker_photo(bot, message.chat.id):
        bot.reply_to(message, "ещё не видел фоток в беседе!")

@bot.message_handler(commands=["voice", "войс", "голос"])
def cmd_voice(message):
    text = absurd_word_salad(message.chat.id)
    voice = generate_voice(text)
    if voice:
        bot.send_voice(message.chat.id, voice)
    else:
        bot.reply_to(message, "не смог сказать")

@bot.message_handler(commands=["stats", "стат", "статистика"])
def cmd_stats(message):
    chat_id = message.chat.id
    msgs = _load(chat_id, "messages")
    users = _load(chat_id, "users")
    photos = _load(chat_id, "photos")
    settings = get_settings(chat_id)
    
    names = {1: "тихий", 2: "спокойный", 3: "обычный", 4: "активный", 5: "бешеный"}
    
    stats = f"""📊 *Хранилище чата:*
• Сообщений: {len(msgs)} / {LIMITS['messages']}
• Участников: {len(users)}
• Фото: {len(photos)} / {LIMITS['photos']}
• Уровень: {settings.get('level', 1)} ({names.get(settings.get('level', 1), 'тихий')})
• Режим: {'🔇 тишина' if settings.get('muted') else '🔈 активен'}"""
    
    bot.reply_to(message, stats, parse_mode="Markdown")

@bot.message_handler(commands=["clear", "очистить", "сброс"])
def cmd_clear(message):
    chat_id = message.chat.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].lower() == "yes":
        if chat_id in _clear_confirm and _clear_confirm[chat_id]:
            global _markov_models, _markov_dirty
            
            for key in ["messages", "users", "photos", "counter"]:
                path = _chat_file(chat_id, f"{key}.json")
                if os.path.exists(path):
                    os.remove(path)
            
            for prefix in ["messages", "users", "photos", "counter"]:
                cache_key = f"{chat_id}_{prefix}"
                if cache_key in _cache:
                    del _cache[cache_key]
            
            if chat_id in _markov_models:
                del _markov_models[chat_id]
            if chat_id in _markov_dirty:
                _markov_dirty[chat_id] = True
            
            _clear_confirm[chat_id] = False
            bot.reply_to(message, "🧹 Память чата очищена!")
            return
        else:
            bot.reply_to(message, "Сначала напиши /clear для подтверждения")
            return
    
    _clear_confirm[chat_id] = True
    bot.reply_to(message, "⚠️ Уверен? Вся память этого чата будет стёрта.\nНапиши /clear yes для подтверждения")

# ─── Обработка сообщений ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    if not message.text or message.text.startswith("/"):
        return
    
    chat_id = message.chat.id
    
    # Режим тишины
    if is_muted(chat_id):
        return
    
    text = message.text
    name = message.from_user.first_name or "Аноним"
    uid = message.from_user.id
    text_lower = text.lower().strip()
    
    add_message(chat_id, text)
    add_user_message(chat_id, uid, name, text)
    
    level = get_level(chat_id)
    triggers = LEVELS.get(level, LEVELS[1])
    
    c = get_counter(chat_id)
    c["msgs"] = c.get("msgs", 0) + 1
    c["reply"] = c.get("reply", 0) + 1
    c["meme"] = c.get("meme", 0) + 1
    c["voice"] = c.get("voice", 0) + 1
    c["mat"] = c.get("mat", 0) + 1
    c["dem"] = c.get("dem", 0) + 1
    c["stick"] = c.get("stick", 0) + 1
    
    # «Кто...» — в любом месте сообщения
    if "кто" in text_lower.split():
        user = get_random_user(chat_id)
        if user:
            answer = random.choice(KTO_ANSWERS).format(user=user)
            bot.reply_to(message, answer)
            return
    
    # «лолыч», «лолич»
    if any(w in text_lower for w in ["лолыч", "лолич"]):
        clean = text
        for w in ["лолыч", "лолич"]:
            clean = clean.lower().replace(w, "").strip()
        bot.reply_to(message, absurd_word_salad(chat_id, clean))
        return
    
    # Мат
    if has_mat(text):
        c["mat_voice"] = c.get("mat_voice", 0) + 1
        if c["mat_voice"] >= MAT_VOICE_EVERY:
            c["mat_voice"] = 0
            save_counter(chat_id)
            threading.Thread(target=lambda: send_mat_voice(bot, chat_id, message.message_id), daemon=True).start()
            return
        if random.random() < MAT_REPLY_CHANCE:
            bot.reply_to(message, random.choice(MAT).upper() + "!")
            return
    
    # Авто-мат
    if c["mat"] >= triggers[5]:
        c["mat"] = 0
        save_counter(chat_id)
        bot.reply_to(message, random.choice(MAT).upper() + "!")
        return
    
    # Авто-войс
    if c["voice"] >= triggers[3]:
        c["voice"] = 0
        save_counter(chat_id)
        threading.Thread(target=lambda: send_random_voice(bot, chat_id), daemon=True).start()
        return
    
    # Авто-стих
    if c["msgs"] >= triggers[1]:
        c["msgs"] = 0
        save_counter(chat_id)
        threading.Thread(target=lambda: bot.send_message(chat_id, f"🎭\n{make_poem(chat_id)}"), daemon=True).start()
        return
    
    # Авто-мем (шаблонный)
    if c["meme"] >= triggers[2]:
        c["meme"] = 0
        save_counter(chat_id)
        threading.Thread(target=lambda: send_template_meme(bot, chat_id), daemon=True).start()
        return
    
    # Авто-демотиватор
    if c["dem"] >= triggers[4]:
        c["dem"] = 0
        save_counter(chat_id)
        if get_photos(chat_id):
            threading.Thread(target=lambda: send_random_dem(bot, chat_id), daemon=True).start()
        return
    
    # Авто-стик
    if c["stick"] >= triggers[6]:
        c["stick"] = 0
        save_counter(chat_id)
        if get_photos(chat_id):
            threading.Thread(target=lambda: send_sticker_photo(bot, chat_id), daemon=True).start()
        return
    
    # Авто-ответ
    if c["reply"] >= triggers[0]:
        c["reply"] = 0
        save_counter(chat_id)
        bot.reply_to(message, absurd_word_salad(chat_id, text))
        return
    
    save_counter(chat_id)
    
    # Упоминание @
    bot_username = bot.get_me().username
    if bot_username and f"@{bot_username}" in text:
        clean = text.replace(f"@{bot_username}", "").strip()
        bot.reply_to(message, absurd_word_salad(chat_id, clean))
        return
    
    # Случайный ответ (40%)
    if random.random() < 0.4:
        if random.random() < 0.15:
            bot.reply_to(message, " ".join(random.choices(EMOJI, k=random.randint(1, 3))))
        else:
            bot.reply_to(message, absurd_word_salad(chat_id, text))

# ─── Фото ─────────────────────────────────────────────────────────────────────
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.chat.id
    
    # Режим тишины — не запоминаем
    if is_muted(chat_id):
        return
    
    file_id = message.photo[-1].file_id
    add_photo(chat_id, file_id)
    caption = (message.caption or "").lower()
    
    if any(w in caption for w in ["мем", "meme"]):
        send_template_meme(bot, chat_id, message.message_id)
    elif any(w in caption for w in ["дем", "dem"]):
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        text = absurd_word_salad(chat_id, length=random.randint(3, 8))
        output = make_demotivator(downloaded, text)
        bot.send_photo(chat_id, output)
    elif any(w in caption for w in ["стик", "stick"]):
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        output = make_sticker(downloaded)
        bot.send_photo(chat_id, output)
    elif random.random() < 0.3:
        comments = [
            absurd_word_salad(chat_id, length=random.randint(1, 10)),
            random.choice(EMOJI) * random.randint(1, 2),
            "это чё такое?",
            "🤔",
        ]
        bot.reply_to(message, random.choice(comments))

# ─── Запуск ────────────────────────────────────────────────────────────────────
log.info("Лолыч проснулся!")
bot.polling(none_stop=True)
