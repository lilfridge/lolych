import sys
import os as _os

print(f"[DEBUG] Python: {sys.executable}", flush=True)
print(f"[DEBUG] CWD: {_os.getcwd()}", flush=True)
print(f"[DEBUG] __file__: {__file__}", flush=True)

_base = _os.path.dirname(_os.path.abspath(__file__))
print(f"[DEBUG] base_dir: {_base}", flush=True)
try:
    print(f"[DEBUG] files: {_os.listdir(_base)[:15]}", flush=True)
except: pass

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

TOKEN = os.environ.get("TOKEN")
GIPHY_KEY = os.environ.get("GIPHY_KEY")
IMGFLIP_USER = os.environ.get("IMGFLIP_USER")
IMGFLIP_PASS = os.environ.get("IMGFLIP_PASS")

LIMITS = {"messages": 5000, "user_msgs": 700, "photos": 200}

LEVELS = {
    1: (600, 700, 800, 1000, 500, 700, 500, 1000, 600, 1000, 800, 1200, 0.005, 1500, 2000),
    2: (350, 500, 600, 800, 400, 600, 500, 1000, 500, 800, 700, 1000, 0.03, 700, 1000),
    3: (100, 250, 200, 400, 100, 300, 200, 300, 100, 200, 100, 200, 0.30, 200, 400),
}

LEVEL_EXTRAS = {
    1: (0.01, 0.05, 0.30, 0.05, 0.05, 0.05),
    2: (0.03, 0.20, 0.60, 0.15, 0.20, 0.20),
    3: (0.10, 0.50, 1.00, 0.40, 0.50, 0.35),
}

MAT = [
    "блять", "бля", "нахуй", "хуй", "пизда", "ебать", "сука", "пиздец",
    "залупа", "мудак", "долбаёб", "ёбанный", "хуйня", "уёбок",
    "гондон", "мразь", "тварь", "ушлёпок", "дебил", "идиот",
    "заебал", "наебал", "хуесос", "чмо", "лох", "тупой", "конченый",
]

EMOJI = ["💀","🗿","😭","🤡","👀","🔥","😐","💅","🤨","😤","🥶","🤙","🦧",
         "🤯","💩","🙈","🤪","🤮","😬","🥴","👻","🫠","🫃","🧌","🫵","☠️","👺","💢","🔞","🤬"]

EMPTY_PHRASES = ["жто не не", "67", "WTF", "🥶", "🗿", "💀", "🤡", "а где слова", "пустота...", "🫠", "ой всё"]
EMPTY_MEME_TEXTS = ["nah", "nope", "lol", "omg", "wtf", "67", "bruh", "WW", "yo"]

STICKERS = [
    "https://i.postimg.cc/pXzFLvS7/Pngtree-black-gradient-3d-number-67-5994973.png",
    "https://i.postimg.cc/yxXs2Lfn/584999937b7d4d76317f5ffd.png",
    "https://i.postimg.cc/vmLhg9SW/IMG-4768.png",
    "https://i.postimg.cc/vmNr6zt2/IMG-4772.png",
    "https://i.postimg.cc/ydT7bfp0/IMG-4776.png",
    "https://i.postimg.cc/brJfFqtJ/IMG-4774.png",
    "https://i.postimg.cc/904N7090/IMG-4779.png",
    "https://i.postimg.cc/QxTyNBhj/IMG-4780.png",
    "https://i.postimg.cc/XvzP79Zm/IMG-4783.png",
    "https://i.postimg.cc/0NFtqxFM/IMG-4785.png",
    "https://i.postimg.cc/NF47LwJ6/IMG-4787.png",
    "https://i.postimg.cc/wxf1xvFb/IMG-4791.png",
    "https://i.postimg.cc/zDbhzFCF/IMG-4801.png",
    "https://i.postimg.cc/9MvrRsd4/IMG-4790.png",
    "https://i.postimg.cc/QdwG3shp/IMG-4803.png",
    "https://i.postimg.cc/HsNPJ2R5/IMG-4805.png",
    "https://i.postimg.cc/G2k4WdTT/IMG-4809.png",
    "https://i.postimg.cc/J0fZ8GYW/IMG-4807.png",
    "https://i.postimg.cc/fynrbjbf/IMG-4811.png",
    "https://i.postimg.cc/fWV8GP8t/IMG-4815.png",
]

IMGFLIP_TEMPLATES = {
    181913649: 2, 87743020: 3, 93895088: 4, 252600902: 2, 131940431: 4,
    89370399: 2, 110163934: 2, 61579: 2, 101470: 2, 217743513: 2,
    91538330: 2, 4087833: 2, 5496396: 2, 1035805: 4, 123999232: 2,
    124822590: 3, 148909805: 2, 97984: 2, 161865971: 2, 9440985: 2,
    55353130: 2, 8072285: 5, 188390779: 2, 155067746: 3, 142009471: 3,
    180190441: 3, 29617627: 2, 27813981: 2, 129242436: 2, 114585149: 4,
    178591752: 2, 135256802: 3, 100777631: 3, 102156234: 2, 101288: 2,
    259237855: 2, 50421420: 2, 222403160: 2, 438680: 2, 3218037: 2,
    196652226: 2, 175540452: 2, 119139145: 2, 195515965: 4, 134242370: 2,
    99683372: 2, 92084495: 2, 84341851: 2,
}

KTO_ANSWERS = [
    "это {user}, без сомнений", "{user}, больше некому",
    "очевидно, {user}", "{user}, я так чувствую",
    "все знают что это {user}", "{user}, и это не обсуждается",
    "{user}, а кто же ещё", "ну конечно {user}",
    "это {user}, сто процентов", "гадалка сказала — {user}",
]

KOGDA_ANSWERS = [
    "никогда", "завтра", "через 5 минут",
    "когда рак на горе свистнет", "скоро",
    "в следующей жизни", "после дождичка в четверг",
    "в 3024 году", "как только так сразу",
    "когда {user} перестанет тупить",
    "после того как {user} поумнеет",
]

# ─── Фотомем: шаблоны ───────────────────────────────────────────────────────
TEMPLATES_DIR = "templates"
PHOTO_TEMPLATES = {
    "IMG_4862.jpeg": {
        "photos": [{"x": 59, "y": 246, "w": 847, "h": 964}],
        "texts": [],
    },
    "IMG_4864.jpeg": {
        "photos": [{"x": 608, "y": 650, "w": 577, "h": 384}],
        "texts": [],
    },
    "IMG_4837.jpeg": {
        "photos": [{"x": 348, "y": 21, "w": 323, "h": 323}],
        "texts": [],
    },
    "IMG_4838.JPG": {
        "photos": [{"x": 601, "y": 3, "w": 595, "h": 595}, {"x": 601, "y": 601, "w": 595, "h": 595}],
        "texts": [],
    },
    "IMG_4841.JPG": {
        "photos": [{"x": 6, "y": 6, "w": 589, "h": 589}, {"x": 6, "y": 603, "w": 590, "h": 591}],
        "texts": [],
    },
    "IMG_4842.jpg": {
        "photos": [{"x": 0, "y": 0, "w": 620, "h": 836}],
        "texts": [],
    },
    "IMG_4843.jpg": {
        "photos": [{"x": 12, "y": 388, "w": 504, "h": 504}],
        "texts": [],
    },
    "IMG_4844.jpg": {
        "photos": [{"x": 13, "y": 542, "w": 1184, "h": 646}],
        "texts": [],
    },
    "IMG_4845.jpg": {
        "photos": [{"x": 0, "y": 0, "w": 1206, "h": 991}],
        "texts": [],
    },
    "IMG_4846.jpg": {
        "photos": [{"x": 0, "y": 193, "w": 1206, "h": 774}],
        "texts": [],
    },
    "IMG_4847.jpg": {
        "photos": [{"x": 0, "y": 264, "w": 1206, "h": 735}],
        "texts": [],
    },
    "IMG_4848.jpg": {
        "photos": [{"x": 0, "y": 175, "w": 1206, "h": 1019}],
        "texts": [],
    },
    "IMG_4849.jpg": {
        "photos": [{"x": 410, "y": 1097, "w": 419, "h": 452}],
        "texts": [],
    },
    "IMG_4850.jpg": {
        "photos": [{"x": 113, "y": 198, "w": 333, "h": 392}],
        "texts": [],
    },
    "IMG_4851.jpg": {
        "photos": [{"x": 683, "y": 587, "w": 500, "h": 500}],
        "texts": [],
    },
    "IMG_4852.jpg": {
        "photos": [{"x": 0, "y": 481, "w": 585, "h": 423}],
        "texts": [],
    },
    "IMG_4856.jpg": {
        "photos": [{"x": 79, "y": 369, "w": 1000, "h": 687}],
        "texts": [],
    },
    "IMG_4857.jpg": {
        "photos": [{"x": 54, "y": 200, "w": 1109, "h": 1109}],
        "texts": [],
    },
    "IMG_4858.jpg": {
        "photos": [{"x": 430, "y": 450, "w": 441, "h": 294}],
        "texts": [],
    },
    "IMG_4860.JPG": {
        "photos": [{"x": 607, "y": 0, "w": 599, "h": 465}, {"x": 607, "y": 473, "w": 599, "h": 471}],
        "texts": [],
    },
}

# ─── Файлы ────────────────────────────────────────────────────────────────────
def _chat_file(chat_id, name): return f"chat_{chat_id}_{name}"

_cache = {}
_my_photos = set()
_chat_stickers = []
MAX_CHAT_STICKERS = 100
_clear_confirm = {}
_clear_category = {}
_gif_mode = {}

def _load(chat_id, key):
    cache_key = f"{chat_id}_{key}"
    if cache_key in _cache: return _cache[cache_key]
    path = _chat_file(chat_id, f"{key}.json")
    if not os.path.exists(path):
        default = {} if key in ("users","counter","settings") else []
        if key == "counter": default = {"msgs":0,"meme":0,"voice":0,"mat":0,"dem":0,"stick":0,"gif":0,"sticker_send":0,"poll":0}
        if key == "settings": default = {"level":1,"muted":False,"no_mat":False}
        _cache[cache_key] = default
        return default
    with open(path, "r", encoding="utf-8") as f: _cache[cache_key] = json.load(f)
    return _cache[cache_key]

def _save(chat_id, key):
    path = _chat_file(chat_id, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f: json.dump(_cache[f"{chat_id}_{key}"], f, ensure_ascii=False)

_markov_models, _markov_dirty = {}, {}

def _get_markov_model(chat_id):
    if chat_id not in _markov_dirty: _markov_dirty[chat_id] = True
    if _markov_dirty[chat_id] or chat_id not in _markov_models:
        msgs = _load(chat_id, "messages")
        if len(msgs) < 10: return None
        try:
            _markov_models[chat_id] = markovify.Text(" ".join(msgs), state_size=2)
            _markov_dirty[chat_id] = False
        except: _markov_models[chat_id] = None
    return _markov_models.get(chat_id)

def add_message(chat_id, text):
    msgs = _load(chat_id, "messages")
    msgs.append(text)
    if len(msgs) > LIMITS["messages"]: _cache[f"{chat_id}_messages"] = msgs[-LIMITS["messages"]:]
    _save(chat_id, "messages")
    _markov_dirty[chat_id] = True

def add_user_message(chat_id, user_id, name, text):
    users = _load(chat_id, "users")
    uid = str(user_id)
    if uid not in users: users[uid] = {"name":name,"messages":[]}
    users[uid]["name"] = name
    users[uid]["messages"].append(text)
    if len(users[uid]["messages"]) > LIMITS["user_msgs"]: users[uid]["messages"] = users[uid]["messages"][-LIMITS["user_msgs"]:]
    _save(chat_id, "users")

def get_users(chat_id): return _load(chat_id, "users")

def add_photo(chat_id, file_id):
    if file_id in _my_photos: return
    photos = _load(chat_id, "photos")
    if file_id not in photos: photos.append(file_id)
    if len(photos) > LIMITS["photos"]: _cache[f"{chat_id}_photos"] = photos[-LIMITS["photos"]:]
    _save(chat_id, "photos")

def get_photos(chat_id): return _load(chat_id, "photos")

def get_settings(chat_id): return _load(chat_id, "settings")
def save_settings(chat_id): _save(chat_id, "settings")
def get_level(chat_id): return get_settings(chat_id).get("level",1)
def is_muted(chat_id): return get_settings(chat_id).get("muted",False)
def is_no_mat(chat_id): return get_settings(chat_id).get("no_mat",False)
def get_counter(chat_id): return _load(chat_id, "counter")
def save_counter(chat_id): _save(chat_id, "counter")

# ─── Слова ─────────────────────────────────────────────────────────────────────
def _chat_words(chat_id, min_len=2):
    msgs = _load(chat_id, "messages")
    if not msgs: return []
    words = []
    for m in msgs: words.extend(w.strip(".,!?:;\"'()«»") for w in m.split())
    return [w for w in words if len(w) > min_len]

def _random_phrase(chat_id):
    msgs = _load(chat_id, "messages")
    if not msgs: return None
    msg = random.choice(msgs)
    words = msg.split()
    if len(words) > 10:
        start = random.randint(0, max(0,len(words)-10))
        return " ".join(words[start:start+random.randint(3,10)])
    return msg

def absurd_word_salad(chat_id, source_text="", length=None):
    if length is None:
        r = random.random()
        if r < 0.6: length = random.randint(1,3)
        elif r < 0.9: length = random.randint(4,7)
        else: length = random.randint(8,10)
    pool = _chat_words(chat_id)
    if source_text: pool.extend(w.strip(".,!?:;\"'()«»") for w in source_text.split() if len(w)>1)
    if not pool: return random.choice(EMPTY_PHRASES)
    if random.random() < 0.5:
        phrase = _random_phrase(chat_id)
        if phrase:
            words = phrase.split()
            if len(words) > length: phrase = " ".join(words[:length])
            return phrase.strip()
    result = [random.choice(pool) for _ in range(length)]
    text = " ".join(result)
    if random.random() < 0.1: text = text.upper()
    return text.strip()

# ─── GIPHY ─────────────────────────────────────────────────────────────────────
def get_gif_by_query(query):
    try:
        url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_KEY}&q={query}&limit=10&rating=r"
        r = requests.get(url, timeout=10).json()
        results = r.get("data", [])
        if results:
            gif = random.choice(results)
            return gif["images"]["original"]["url"]
    except: pass
    return None

def get_random_gif():
    try:
        r = requests.get(f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_KEY}&tag=meme&rating=r", timeout=10).json()
        if r.get("data",{}).get("images",{}).get("original",{}).get("url"): return r["data"]["images"]["original"]["url"]
    except: pass
    return None

# ─── Голосовые ────────────────────────────────────────────────────────────────
def generate_voice(text):
    try:
        tts = gTTS(text=text, lang="ru", slow=False)
        io_ = io.BytesIO(); tts.write_to_fp(io_); io_.seek(0); io_.name="voice.mp3"
        return io_
    except: return None

def send_random_voice(bot_instance, chat_id, reply_to=None):
    text = absurd_word_salad(chat_id, length=random.randint(8,12))
    v = generate_voice(text)
    if v:
        try:
            if reply_to: bot_instance.send_voice(chat_id, v, reply_to_message_id=reply_to)
            else: bot_instance.send_voice(chat_id, v)
            return True
        except: pass
    return False

# ─── Микс ─────────────────────────────────────────────────────────────────────
def mix_messages(chat_id):
    _save(chat_id, "messages")
    path = _chat_file(chat_id, "messages.json")
    if not os.path.exists(path): return random.choice(EMPTY_PHRASES)
    with open(path, "r", encoding="utf-8") as f: msgs = json.load(f)
    if len(msgs) < 2: return random.choice(EMPTY_PHRASES)
    
    recent = msgs[-100:]
    msg1 = random.choice(recent)
    msg2 = random.choice(recent)
    while msg2 == msg1 and len(recent) > 1:
        msg2 = random.choice(recent)
    
    words1 = msg1.split()
    words2 = msg2.split()
    
    if len(words1) < 3 and len(words2) < 3:
        return absurd_word_salad(chat_id)
    
    if len(words1) >= 3:
        cut1 = random.randint(2, len(words1) - 1)
        part1 = words1[:cut1]
    else:
        part1 = words1
    
    if len(words2) >= 3:
        cut2 = random.randint(1, len(words2) - 2)
        part2 = words2[cut2:]
    else:
        part2 = words2
    
    return " ".join(part1 + part2)

# ─── Опросы ───────────────────────────────────────────────────────────────────
def send_random_poll(bot_instance, chat_id):
    words = _chat_words(chat_id)
    if len(words) < 5: return
    question_word = random.choice(words)
    options = random.sample([w for w in words if w != question_word], min(4, len(words)-1))
    if len(options) < 2: options = ["жто не не", "67"]
    options = options[:4]
    question = f"Что такое «{question_word}»?"
    try: bot_instance.send_poll(chat_id, question=question, options=options, is_anonymous=False)
    except: pass

# ─── Фотомем ──────────────────────────────────────────────────────────────────
def make_photo_meme(chat_id):
    photos = get_photos(chat_id)
    if not photos: return None

    available = [t for t in PHOTO_TEMPLATES if os.path.exists(os.path.join(TEMPLATES_DIR, t))]
    if not available: return None

    template_name = random.choice(available)
    template_data = PHOTO_TEMPLATES[template_name]
    template_path = os.path.join(TEMPLATES_DIR, template_name)

    try:
        template = Image.open(template_path).convert("RGBA")

        for slot in template_data.get("photos", []):
            fid = random.choice(photos)
            fi = bot.get_file(fid)
            photo_bytes = bot.download_file(fi.file_path)
            photo = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
            photo = photo.resize((slot["w"], slot["h"]), Image.LANCZOS)
            template.paste(photo, (slot["x"], slot["y"]), photo)

        out = io.BytesIO()
        template.convert("RGB").save(out, format="JPEG", quality=90)
        out.seek(0)
        return out
    except Exception as e:
        log.error(f"Фотомем ошибка: {e}")
        return None

# ─── Шрифты ───────────────────────────────────────────────────────────────────
def _find_font(size):
    for p in ["impact.ttf", os.path.join(os.path.dirname(__file__),"impact.ttf"),
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try: return ImageFont.truetype(p, size=size)
        except: continue
    return ImageFont.load_default()

def _find_serif_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]:
        try: return ImageFont.truetype(p, size=size)
        except: continue
    return _find_font(size)

# ─── Демотиватор ─────────────────────────────────────────────────────────────
def make_demotivator(img_bytes, text):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    if w>500 or h>500: r = min(500/w, 500/h); img = img.resize((int(w*r), int(h*r)), Image.LANCZOS); w, h = img.size
    border=10; th=80
    cw, ch = w+border*2, h+border*2+th+border
    canvas = Image.new("RGB",(cw,ch),"black")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([3,3,cw-3,ch-3], outline="white", width=3)
    canvas.paste(img,(border,border))
    font = _find_serif_font(24)
    for i, line in enumerate(textwrap.wrap(text, width=30)[:3]):
        bb = draw.textbbox((0,0), line, font=font)
        draw.text(((cw-(bb[2]-bb[0]))//2, h+border*2+5+i*28), line, font=font, fill="white")
    try:
        mf = _find_font(12)
        draw.text((cw-50,ch-18),"lolych",font=mf,fill=(150,150,150))
    except: pass
    out = io.BytesIO(); canvas.save(out,format="JPEG"); out.seek(0)
    return out

def send_random_dem(bot_instance, chat_id, reply_to=None, custom_text=None):
    photos = get_photos(chat_id)
    if not photos: return False
    fid = random.choice(photos)
    text = custom_text or absurd_word_salad(chat_id, length=random.randint(3,8))
    try:
        fi = bot_instance.get_file(fid); dl = bot_instance.download_file(fi.file_path)
        out = make_demotivator(dl, text); _my_photos.add(fid)
        if reply_to: bot_instance.send_photo(chat_id, out, reply_to_message_id=reply_to)
        else: bot_instance.send_photo(chat_id, out)
        return True
    except: return False

# ─── Мемы ─────────────────────────────────────────────────────────────────────
def make_imgflip_meme(template_id, texts, num_boxes=2):
    params = {"template_id":template_id,"username":IMGFLIP_USER,"password":IMGFLIP_PASS}
    for i, t in enumerate(texts[:num_boxes]):
        params[f"boxes[{i}][text]"] = t[:100]
    try:
        r = requests.post("https://api.imgflip.com/caption_image", data=params, timeout=15).json()
        if r.get("success") and r.get("data",{}).get("url"): return r["data"]["url"]
    except: pass
    return None

def send_template_meme(bot_instance, chat_id, reply_to=None, texts=None):
    tid = random.choice(list(IMGFLIP_TEMPLATES.keys()))
    num_boxes = IMGFLIP_TEMPLATES[tid]
    if not texts:
        words = _chat_words(chat_id)
        texts = [random.choice(EMPTY_MEME_TEXTS) for _ in range(num_boxes)] if not words else [absurd_word_salad(chat_id, length=random.randint(2,5)) for _ in range(num_boxes)]
    url = make_imgflip_meme(tid, texts[:num_boxes], num_boxes)
    if url:
        try:
            img_data = requests.get(url, timeout=15).content
            img = Image.open(io.BytesIO(img_data)).convert("RGBA")
            draw = ImageDraw.Draw(img)
            try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=14)
            except: font = ImageFont.load_default()
            text = "lolych"
            bbox = draw.textbbox((0,0), text, font=font)
            tw = int((bbox[2]-bbox[0]+6)*1.4); th = bbox[3]-bbox[1]+4
            tx = 6 + (tw - (bbox[2]-bbox[0]+6))//2
            draw.rectangle([3, img.height-th-3, 3+tw, img.height-3], fill=(255,255,255,200))
            draw.text((tx+3, img.height-th-1), text, font=font, fill=(0,0,0))
            out = io.BytesIO(); img.convert("RGB").save(out, format="JPEG"); out.seek(0)
            if reply_to: bot_instance.send_photo(chat_id, out, reply_to_message_id=reply_to)
            else: bot_instance.send_photo(chat_id, out)
            return True
        except: pass
    return False

# ─── Стикеры ──────────────────────────────────────────────────────────────────
def make_sticker(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    w, h = img.size
    all_stickers = STICKERS + _chat_stickers
    if not all_stickers: return io.BytesIO()
    choice = random.choice(all_stickers)
    if choice.startswith("http"):
        try:
            sticker_data = requests.get(choice, timeout=10).content
            sticker = Image.open(io.BytesIO(sticker_data)).convert("RGBA")
        except: return io.BytesIO()
    else:
        try:
            file_info = bot.get_file(choice)
            sticker_data = bot.download_file(file_info.file_path)
            sticker = Image.open(io.BytesIO(sticker_data)).convert("RGBA")
        except: return io.BytesIO()
    ss = min(w, h) // 5
    sticker = sticker.resize((ss, ss), Image.LANCZOS)
    img.paste(sticker, (random.randint(0, max(0, w-ss)), random.randint(0, max(0, h-ss))), sticker)
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG")
    out.seek(0)
    return out

def send_sticker_photo(bot_instance, chat_id, reply_to=None):
    photos = get_photos(chat_id)
    if not photos: return False
    fid = random.choice(photos)
    try:
        fi = bot_instance.get_file(fid); dl = bot_instance.download_file(fi.file_path)
        out = make_sticker(dl); _my_photos.add(fid)
        if reply_to: bot_instance.send_photo(chat_id, out, reply_to_message_id=reply_to)
        else: bot_instance.send_photo(chat_id, out)
        return True
    except: return False

# ─── Хелперы ──────────────────────────────────────────────────────────────────
def has_mat(text): return any(m in text.lower() for m in MAT)
def get_random_user(chat_id):
    u = get_users(chat_id)
    return random.choice(list(u.values()))["name"] if u else None

# ─── Бот ──────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(TOKEN)

# ─── Меню ────────────────────────────────────────────────────────────────────
def main_menu(cid):
    msgs = _load(cid, "messages")
    photos = _load(cid, "photos")
    lv = get_level(cid)
    lv_name = {1: "молчун", 2: "редко", 3: "часто"}[lv]
    
    txt = f"""🃏 <b>Лолыч</b>

📋 <b>Главное меню</b>
🔧 ID: <code>{cid}</code>
⭐ Активность: {lv_name}

📚 Сообщений: {len(msgs)}
🖼 Фото: {len(photos)} · 🎨 Стикеров: {len(_chat_stickers)}"""
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("😂 Развлечения", callback_data="menu_fun"))
    markup.add(InlineKeyboardButton("⚙️ Параметры", callback_data="menu_params"))
    return txt, markup

def fun_menu(page=1):
    if page == 1:
        txt = """🎪 <b>Тут мои таланты</b>

Не обращайте внимания, я просто рофлю 🥶"""
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("🖼 Мем", callback_data="meme"), InlineKeyboardButton("😔 Демотиватор", callback_data="dem"))
        markup.add(InlineKeyboardButton("📸 Фотомем", callback_data="photomeme"), InlineKeyboardButton("🎭 Стикер", callback_data="stick"))
        markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_back"), InlineKeyboardButton("➡️ Дальше", callback_data="menu_fun_page2"))
    else:
        txt = """🎪 <b>Тут мои таланты</b>

Не обращайте внимания, я просто рофлю 🥶"""
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("🎬 Гифка", callback_data="gif"), InlineKeyboardButton("💬 Микс", callback_data="mix"))
        markup.add(InlineKeyboardButton("🎙 Голос", callback_data="voice"))
        markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_fun_page1"), InlineKeyboardButton("↩ В меню", callback_data="menu_back"))
    return txt, markup

def params_menu(cid):
    no_mat = is_no_mat(cid); muted = is_muted(cid)
    txt = """⚙️ <b>Параметры</b>

Здесь командуешь ты 👑"""
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"{'✅ Бот включен' if not muted else '🔇 Бот выключен'}", callback_data="toggle_mute"),
        InlineKeyboardButton("⭐ Активность", callback_data="menu_activity")
    )
    markup.add(InlineKeyboardButton("🗑 Очистить", callback_data="menu_clear"))
    markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_back"))
    return txt, markup

def activity_menu(cid):
    lv = get_level(cid)
    no_mat = is_no_mat(cid)
    lv_name = {1: "молчун", 2: "редко", 3: "часто"}[lv]
    
    txt = f"""⭐ <b>Активность</b>

Уровень: {lv} ({lv_name})
Мат: {'✅ разрешён' if not no_mat else '🚫 запрещён'}"""
    
    markup = InlineKeyboardMarkup(row_width=3)
    emoji_map = {1: "😴", 2: "🤙", 3: "🔥"}
    btns = []
    for i in [1, 2, 3]:
        mark = "✅" if i == lv else ""
        btns.append(InlineKeyboardButton(f"{mark} {emoji_map[i]} {i}", callback_data=f"setlevel_{i}"))
    markup.add(*btns)
    markup.add(InlineKeyboardButton(f"{'✅ Мат разрешён' if not no_mat else '🚫 Без мата'}", callback_data="toggle_mat"))
    markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_params"))
    return txt, markup

def clear_menu():
    txt = "🗑 <b>Что очистить?</b>"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💬 Сообщения", callback_data="clear_msgs"),
        InlineKeyboardButton("🖼 Фото", callback_data="clear_photos")
    )
    markup.add(
        InlineKeyboardButton("🎨 Стикеры", callback_data="clear_stickers"),
        InlineKeyboardButton("🗑 Всё", callback_data="clear_all")
    )
    markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_params"))
    return txt, markup

# ─── Приветствие ─────────────────────────────────────────────────────────────
@bot.message_handler(content_types=["new_chat_members"])
def handle_new_member(message):
    for member in message.new_chat_members:
        if member.username == bot.get_me().username:
            bot.send_message(message.chat.id, "👋 <b>Привет, хомяк, с тобой земляк!</b>", parse_mode="HTML")

# ─── Стикеры из чата ─────────────────────────────────────────────────────────
@bot.message_handler(content_types=["sticker"])
def handle_sticker(message):
    cid = message.chat.id
    if is_muted(cid): return
    if message.from_user.is_bot: return
    file_id = message.sticker.file_id
    if not message.sticker.is_animated and not message.sticker.is_video:
        if file_id not in _chat_stickers:
            _chat_stickers.append(file_id)
            if len(_chat_stickers) > MAX_CHAT_STICKERS:
                _chat_stickers.pop(0)
    extras = LEVEL_EXTRAS.get(get_level(cid), LEVEL_EXTRAS[1])
    if _chat_stickers and random.random() < extras[5]:
        fid = random.choice(_chat_stickers)
        bot.send_sticker(cid, fid)

# ─── Команды ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message):
    cid = message.chat.id
    for d in [_gif_mode]:
        d[cid] = False
    txt, markup = main_menu(cid)
    bot.send_message(cid, txt, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=["fun"])
def cmd_fun(message):
    cid = message.chat.id
    txt, markup = fun_menu(1)
    bot.send_message(cid, txt, reply_markup=markup, parse_mode="HTML")

@bot.message_handler(commands=["settings"])
def cmd_params(message):
    cid = message.chat.id
    txt, markup = params_menu(cid)
    bot.send_message(cid, txt, reply_markup=markup, parse_mode="HTML")

# ─── Кнопки ──────────────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    bot.answer_callback_query(call.id)
    cid = call.message.chat.id
    
    nav = {
        "menu_back": main_menu(cid),
        "menu_fun": fun_menu(1),
        "menu_fun_page2": fun_menu(2),
        "menu_fun_page1": fun_menu(1),
        "menu_params": params_menu(cid),
        "menu_activity": activity_menu(cid),
    }
    
    if call.data in nav:
        if call.data in ("menu_fun", "menu_fun_page1"):
            txt, markup = fun_menu(1)
        elif call.data == "menu_fun_page2":
            txt, markup = fun_menu(2)
        else:
            txt, markup = nav[call.data]
        bot.edit_message_text(txt, cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        return
    
    if call.data == "gif":
        _gif_mode[cid] = True
        bot.edit_message_text("🎬 <b>Напиши слово для поиска гифки</b>", cid, call.message.message_id, parse_mode="HTML")
    elif call.data == "menu_clear":
        txt, markup = clear_menu()
        bot.edit_message_text(txt, cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data == "clear_all":
        _clear_confirm[cid] = True; _clear_category[cid] = "all"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Да", callback_data="clear_yes"), InlineKeyboardButton("❌ Нет", callback_data="menu_params"))
        bot.edit_message_text("⚠️ <b>Удалить ВСЁ?</b>", cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data == "clear_msgs":
        _clear_confirm[cid] = True; _clear_category[cid] = "messages"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Да", callback_data="clear_yes"), InlineKeyboardButton("❌ Нет", callback_data="menu_params"))
        bot.edit_message_text("⚠️ <b>Удалить сообщения?</b>", cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data == "clear_photos":
        _clear_confirm[cid] = True; _clear_category[cid] = "photos"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Да", callback_data="clear_yes"), InlineKeyboardButton("❌ Нет", callback_data="menu_params"))
        bot.edit_message_text("⚠️ <b>Удалить фото?</b>", cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data == "clear_stickers":
        _chat_stickers.clear()
        bot.edit_message_text("🎨 <b>Стикеры из чата удалены!</b>", cid, call.message.message_id, parse_mode="HTML")
    elif call.data == "clear_yes":
        if cid in _clear_confirm and _clear_confirm[cid]:
            cat = _clear_category.get(cid, "all")
            if cat in ("all", "messages"):
                for k in ["messages","users"]:
                    p = _chat_file(cid, f"{k}.json")
                    if os.path.exists(p): os.remove(p)
                    if f"{cid}_{k}" in _cache: del _cache[f"{cid}_{k}"]
                if cid in _markov_models: del _markov_models[cid]
                if cid in _markov_dirty: _markov_dirty[cid] = True
            if cat in ("all", "photos"):
                p = _chat_file(cid, "photos.json")
                if os.path.exists(p): os.remove(p)
                if f"{cid}_photos" in _cache: del _cache[f"{cid}_photos"]
            if cat == "all":
                p = _chat_file(cid, "counter.json")
                if os.path.exists(p): os.remove(p)
                if f"{cid}_counter" in _cache: del _cache[f"{cid}_counter"]
                _chat_stickers.clear()
                _my_photos.clear()
            _clear_confirm[cid] = False
            bot.edit_message_text("🧹 <b>Очищено!</b>", cid, call.message.message_id, parse_mode="HTML")
    elif call.data == "toggle_mat":
        s = get_settings(cid); s["no_mat"] = not s.get("no_mat", False); save_settings(cid)
        txt, markup = activity_menu(cid)
        bot.edit_message_text(txt, cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data == "toggle_mute":
        s = get_settings(cid); s["muted"] = not s.get("muted", False); save_settings(cid)
        txt, markup = params_menu(cid)
        bot.edit_message_text(txt, cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data.startswith("setlevel_"):
        lv = int(call.data.split("_")[1])
        s = get_settings(cid); s["level"] = lv; save_settings(cid)
        txt, markup = activity_menu(cid)
        bot.edit_message_text(txt, cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
    elif call.data == "meme":
        if not send_template_meme(bot, cid): bot.send_message(cid, "не смог")
    elif call.data == "dem":
        if not send_random_dem(bot, cid): bot.send_message(cid, "нет фото")
    elif call.data == "mix": bot.send_message(cid, mix_messages(cid))
    elif call.data == "voice":
        v = generate_voice(absurd_word_salad(cid))
        if v: bot.send_voice(cid, v)
        else: bot.send_message(cid, "не смог")
    elif call.data == "stick":
        if not send_sticker_photo(bot, cid): bot.send_message(cid, "нет фото")
    elif call.data == "photomeme":
        out = make_photo_meme(cid)
        if out: bot.send_photo(cid, out)
        else: bot.send_message(cid, "нет фото или шаблонов")

# ─── Сообщения ────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    if not message.text or message.text.startswith("/"): return
    if message.from_user.is_bot: return
    cid=message.chat.id
    if is_muted(cid): return
    
    text=message.text; name=message.from_user.first_name or "Аноним"; uid=message.from_user.id
    
    if _gif_mode.get(cid):
        _gif_mode[cid] = False
        gif_url = get_gif_by_query(text)
        if gif_url: bot.send_document(cid, gif_url)
        else: bot.send_message(cid, "не нашёл гифку")
        return
    
    add_message(cid, text); add_user_message(cid, uid, name, text)
    
    no_mat = is_no_mat(cid)
    lv = get_level(cid)
    tr = LEVELS.get(lv, LEVELS[1])
    extras = LEVEL_EXTRAS.get(lv, LEVEL_EXTRAS[1])
    c=get_counter(cid)
    for k in ["msgs","meme","voice","mat","dem","stick","gif","sticker_send","poll"]: c[k]=c.get(k,0)+1
    
    if "кто" in text.lower().split() and random.random() < extras[1]:
        u=get_random_user(cid)
        if u: bot.reply_to(message, random.choice(KTO_ANSWERS).format(user=u)); return
    
    if "когда" in text.lower().split() and random.random() < extras[4]:
        u=get_random_user(cid)
        answer = random.choice(KOGDA_ANSWERS)
        if "{user}" in answer and u: answer = answer.format(user=u)
        elif "{user}" in answer: answer = "никогда"
        bot.reply_to(message, answer); return
    
    if any(w in text.lower() for w in ["лолыч","лолич"]) and random.random() < extras[2]:
        clean=text.lower()
        for w in ["лолыч","лолич"]: clean=clean.replace(w,"").strip()
        bot.reply_to(message, absurd_word_salad(cid, clean))
        return
    
    if has_mat(text) and not no_mat:
        if random.random() < extras[0]: bot.reply_to(message, random.choice(MAT).upper()+"!"); return
    
    meme_trigger = random.randint(tr[0], tr[1])
    voice_trigger = random.randint(tr[2], tr[3])
    dem_trigger = random.randint(tr[4], tr[5])
    mat_trigger = random.randint(tr[6], tr[7])
    stick_trigger = random.randint(tr[8], tr[9])
    gif_trigger = random.randint(tr[10], tr[11])
    sticker_send_trigger = random.randint(tr[8], tr[9])
    poll_trigger = random.randint(tr[13], tr[14])
    
    if c["mat"]>=mat_trigger and not no_mat: c["mat"]=0; save_counter(cid); bot.reply_to(message, random.choice(MAT).upper()+"!"); return
    if c["mat"]>=mat_trigger: c["mat"]=0; save_counter(cid)
    if c["voice"]>=voice_trigger: c["voice"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_voice(bot,cid), daemon=True).start(); return
    if c["meme"]>=meme_trigger: c["meme"]=0; save_counter(cid); threading.Thread(target=lambda: send_template_meme(bot,cid), daemon=True).start(); return
    if c["gif"]>=gif_trigger: c["gif"]=0; save_counter(cid); threading.Thread(target=lambda: (lambda u: u and bot.send_document(cid, u))(get_random_gif()), daemon=True).start(); return
    if c["dem"]>=dem_trigger and get_photos(cid): c["dem"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_dem(bot,cid), daemon=True).start(); return
    if c["stick"]>=stick_trigger and get_photos(cid): c["stick"]=0; save_counter(cid); threading.Thread(target=lambda: send_sticker_photo(bot,cid), daemon=True).start(); return
    if c["sticker_send"]>=sticker_send_trigger and _chat_stickers:
        c["sticker_send"]=0; save_counter(cid)
        fid = random.choice(_chat_stickers)
        bot.send_sticker(cid, fid)
        return
    if c["poll"]>=poll_trigger:
        c["poll"]=0; save_counter(cid)
        send_random_poll(bot, cid)
        return
    save_counter(cid)
    
    if f"@{bot.get_me().username}" in text:
        bot.reply_to(message, absurd_word_salad(cid, text.replace(f"@{bot.get_me().username}","").strip())); return
    
    if random.random() < tr[12]:
        if random.random()<0.15: bot.reply_to(message, " ".join(random.choices(EMOJI, k=random.randint(1,3))))
        else: bot.reply_to(message, absurd_word_salad(cid, text))

# ─── Фото ─────────────────────────────────────────────────────────────────────
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    if message.from_user.is_bot: return
    cid=message.chat.id
    if is_muted(cid): return
    fid=message.photo[-1].file_id
    add_photo(cid, fid)
    cap=(message.caption or "").lower()
    extras = LEVEL_EXTRAS.get(get_level(cid), LEVEL_EXTRAS[1])
    
    if any(w in cap for w in ["мем","meme"]): send_template_meme(bot, cid, message.message_id)
    elif any(w in cap for w in ["дем","dem"]):
        fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
        out=make_demotivator(dl, absurd_word_salad(cid, length=random.randint(3,8)))
        _my_photos.add(fid); bot.send_photo(cid, out)
    elif any(w in cap for w in ["стик","stick"]):
        fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
        out=make_sticker(dl); _my_photos.add(fid); bot.send_photo(cid, out)
    elif random.random() < extras[3]:
        bot.reply_to(message, random.choice([absurd_word_salad(cid, length=random.randint(1,10)), random.choice(EMOJI)*random.randint(1,2), "это чё такое?", "🤔"]))

import os as _os2
log.info(f"[KILL] PID: {_os2.getpid()}")
log.info("Лолыч проснулся!")
bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
