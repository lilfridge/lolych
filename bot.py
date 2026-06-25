import telebot
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
import urllib.parse

# ─── Логирование ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─── Конфиг ────────────────────────────────────────────────────────────────────
TOKEN = "8464842453:AAE4QiUoCGhNdjNyCA3vRLMuloDOIinMPGc

"

LIMITS = {
    "messages": 5000,
    "user_msgs": 700,
    "photos": 200,
}

# Уровни: (авто-ответ, стих, мем, войс, дем, мат, стик)
LEVELS = {
    1: (300, 600, 500, 600, 800, 300, 600),  # редко
    2: (150, 300, 250, 300, 400, 150, 300),  # средне
    3: (60,  100, 100, 100, 150, 60,  100),  # часто
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

# ─── Стикеры (PNG с прозрачным фоном) ─────────────────────────────────────────
STICKERS = [
    "https://i.ibb.co/0jX5Y8F/boss.png",
    "https://i.ibb.co/7Jp3K9d/minecraft-glasses.png",
    "https://i.ibb.co/4ZqG9Y8/fart.png",
    "https://i.ibb.co/8zH5G3c/67.png",
    "https://i.ibb.co/2YmL5X8/mlg.png",
    "https://i.ibb.co/7XzG3Y8/lion.png",
    "https://i.ibb.co/9wL5Y8F/heart.png",
    "https://i.ibb.co/3hG9Y8F/sharingan.png",
    "https://i.ibb.co/6ZqG9Y8/rooster.png",
    "https://i.ibb.co/5XmL5Y8/laughing.png",
    "https://i.ibb.co/1ZqG9Y8/supreme.png",
    "https://i.ibb.co/0mL5Y8F/adidas.png",
    "https://i.ibb.co/4YqG9Y8/skull.png",
    "https://i.ibb.co/7qL5Y8F/crown.png",
    "https://i.ibb.co/8mL5Y8F/tear.png",
    "https://i.ibb.co/9bL5Y8F/circle.png",
    "https://i.ibb.co/2hL5Y8F/sparkles.png",
    "https://i.ibb.co/5nL5Y8F/fire.png",
    "https://i.ibb.co/3pL5Y8F/moai.png",
    "https://i.ibb.co/4kL5Y8F/terminator.png",
]

# ─── imgflip ───────────────────────────────────────────────────────────────────
IMGFLIP_USER = "lilifridge"
IMGFLIP_PASS = "eMsWrri64INeGJd"

IMGFLIP_TEMPLATES = [
    181913649, 87743020, 93895088, 252600902, 131940431,
    89370399, 110163934, 61579, 101470, 217743513,
    91538330, 4087833, 5496396, 1035805, 123999232,
    124822590, 148909805, 97984, 161865971, 9440985, 55353130,
]

# Триггер «кто»
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

# ─── Файлы ────────────────────────────────────────────────────────────────────
def _chat_file(chat_id, name):
    return f"chat_{chat_id}_{name}"

# ─── Хранилище ─────────────────────────────────────────────────────────────────
_cache = {}
_my_photos = set()  # свои фото чтобы не запоминать

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
def add_photo(chat_id, file_id):
    if file_id in _my_photos:
        return
    photos = _load(chat_id, "photos")
    if file_id not in photos:
        photos.append(file_id)
    if len(photos) > LIMITS["photos"]:
        _cache[f"{chat_id}_photos"] = photos[-LIMITS["photos"]:]
    _save(chat_id, "photos")

def get_photos(chat_id):
    return _load(chat_id, "photos")

def remove_last_photo(chat_id):
    photos = _load(chat_id, "photos")
    if photos:
        photos.pop()
        _save(chat_id, "photos")
        return True
    return False

# ─── Настройки ────────────────────────────────────────────────────────────────
def get_settings(chat_id):
    return _load(chat_id, "settings")

def save_settings(chat_id):
    _save(chat_id, "settings")

def get_level(chat_id):
    return get_settings(chat_id).get("level", 1)

def is_muted(chat_id):
    return get_settings(chat_id).get("muted", False)

def get_counter(chat_id):
    return _load(chat_id, "counter")

def save_counter(chat_id):
    _save(chat_id, "counter")

# ─── Слова ─────────────────────────────────────────────────────────────────────
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
    if length is None:
        roll = random.random()
        if roll < 0.6: length = random.randint(1, 3)
        elif roll < 0.9: length = random.randint(4, 7)
        else: length = random.randint(8, 10)
    
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
    if random.random() < 0.1: text = text.upper()
    if random.random() < 0.3: text += random.choice(["?", "!", "??", ""])
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
    except:
        return None

def send_random_voice(bot_instance, chat_id, reply_to=None):
    text = absurd_word_salad(chat_id, length=random.randint(8, 12))
    voice = generate_voice(text)
    if voice:
        try:
            if reply_to: bot_instance.send_voice(chat_id, voice, reply_to_message_id=reply_to)
            else: bot_instance.send_voice(chat_id, voice)
            return True
        except: pass
    return False

def send_mat_voice(bot_instance, chat_id, reply_to=None):
    text = " ".join(random.choices(MAT, k=random.randint(3, 6))).upper()
    voice = generate_voice(text)
    if voice:
        try:
            if reply_to: bot_instance.send_voice(chat_id, voice, reply_to_message_id=reply_to)
            else: bot_instance.send_voice(chat_id, voice)
            return True
        except: pass
    return False

# ─── Микс ─────────────────────────────────────────────────────────────────────
def mix_messages(chat_id):
    msgs = _load(chat_id, "messages")
    if len(msgs) < 2: return absurd_word_salad(chat_id)
    msg1, msg2 = random.choice(msgs), random.choice(msgs)
    w1, w2 = msg1.split(), msg2.split()
    if len(w1) < 2 or len(w2) < 2: return absurd_word_salad(chat_id)
    return " ".join(w1[:len(w1)//2] + w2[len(w2)//2:])

# ─── Стихи с рифмами ─────────────────────────────────────────────────────────
RHYME_DICT = {
    "ать": ["мать","спать","ждать","страдать","послать"],
    "ить": ["жить","любить","тупить","говорить","ходить"],
    "ой": ["тобой","судьбой","головой","луной","стеной"],
    "ай": ["давай","лентяй","урожай","сарай","знай"],
    "еть": ["сидеть","глядеть","хотеть","пиздеть","балдеть"],
    "ок": ["дружок","пирожок","прыжок","кружок","звонок"],
    "ак": ["дурак","рыбак","чужак","пятак","бивак"],
    "ешь": ["идёшь","поёшь","живёшь","умрёшь","поймёшь"],
    "ить": ["любить","ходить","говорить","курить","творить"],
}

def find_rhyme(word):
    w = word.lower().strip(".,!?:;\"'()")
    for end, rhymes in RHYME_DICT.items():
        if w.endswith(end):
            return random.choice(rhymes)
    return None

def make_poem(chat_id):
    model = _get_markov_model(chat_id)
    words = _chat_words(chat_id)
    if not words: return absurd_word_salad(chat_id)
    
    lines = []
    for i in range(4):
        if model and random.random() < 0.5:
            line = model.make_short_sentence(50, tries=20)
        else:
            line = " ".join(random.choices(words, k=random.randint(3, 6)))
        if not line: continue
        
        wline = line.split()
        if len(wline) > 6: line = " ".join(wline[:6])
        
        # Рифма через строку (A-B-A-B)
        if i >= 2 and len(lines) >= 2:
            prev = lines[i-2].split()[-1].strip(".,!?:;\"'()")
            curr = wline[-1].strip(".,!?:;\"'()")
            rhyme = find_rhyme(prev)
            if rhyme and rhyme != curr:
                wline[-1] = rhyme
                line = " ".join(wline)
        
        lines.append(line)
    
    return "\n".join(lines) if len(lines) >= 2 else absurd_word_salad(chat_id)

# ─── Шрифты ───────────────────────────────────────────────────────────────────
def _find_font(size):
    paths = [
        "impact.ttf",
        os.path.join(os.path.dirname(__file__), "impact.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for p in paths:
        try: return ImageFont.truetype(p, size=size)
        except: continue
    return ImageFont.load_default()

def _find_serif_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ]
    for p in paths:
        try: return ImageFont.truetype(p, size=size)
        except: continue
    return _find_font(size)

# ─── Демотиватор ─────────────────────────────────────────────────────────────
def make_demotivator(img_bytes, text):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    
    max_size = 500
    if w > max_size or h > max_size:
        ratio = min(max_size/w, max_size/h)
        img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        w, h = img.size
    
    border = 10
    text_height = 80
    canvas_w, canvas_h = w+border*2, h+border*2+text_height+border
    canvas = Image.new("RGB", (canvas_w, canvas_h), "black")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([3,3,canvas_w-3,canvas_h-3], outline="white", width=3)
    canvas.paste(img, (border, border))
    
    font = _find_serif_font(24)
    for i, line in enumerate(textwrap.wrap(text, width=30)[:3]):
        bbox = draw.textbbox((0,0), line, font=font)
        x = (canvas_w - (bbox[2]-bbox[0])) // 2
        draw.text((x, h+border*2+5 + i*28), line, font=font, fill="white")
    
    # Марка lolych
    try:
        mf = _find_font(12)
        draw.text((canvas_w-50, canvas_h-18), "lolych", font=mf, fill=(150,150,150))
    except: pass
    
    out = io.BytesIO()
    canvas.save(out, format="JPEG")
    out.seek(0)
    return out

def send_random_dem(bot_instance, chat_id, reply_to=None, custom_text=None):
    photos = get_photos(chat_id)
    if not photos: return False
    file_id = random.choice(photos)
    text = custom_text or absurd_word_salad(chat_id, length=random.randint(3, 8))
    try:
        file_info = bot_instance.get_file(file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        output = make_demotivator(downloaded, text)
        if reply_to: bot_instance.send_photo(chat_id, output, reply_to_message_id=reply_to)
        else: bot_instance.send_photo(chat_id, output)
        return True
    except Exception as e:
        log.error(f"dem error: {e}")
    return False

# ─── Мемы imgflip ─────────────────────────────────────────────────────────────
def make_imgflip_meme(template_id, texts):
    url = "https://api.imgflip.com/caption_image"
    params = {
        "template_id": template_id,
        "username": IMGFLIP_USER,
        "password": IMGFLIP_PASS,
    }
    for i, text in enumerate(texts):
        params[f"boxes[{i}][text]"] = text[:100]
    try:
        resp = requests.post(url, data=params, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("url"):
            return data["data"]["url"]
        else:
            log.error(f"imgflip: {data.get('error_message','?')}")
            return None
    except Exception as e:
        log.error(f"imgflip req: {e}")
        return None

def send_template_meme(bot_instance, chat_id, reply_to=None):
    tid = random.choice(IMGFLIP_TEMPLATES)
    texts = [absurd_word_salad(chat_id, length=random.randint(2,5)) for _ in range(random.randint(2,3))]
    url = make_imgflip_meme(tid, texts)
    if url:
        try:
            if reply_to: bot_instance.send_photo(chat_id, url, reply_to_message_id=reply_to)
            else: bot_instance.send_photo(chat_id, url)
            return True
        except: pass
    return False

# ─── Стикеры ──────────────────────────────────────────────────────────────────
def make_sticker(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    w, h = img.size
    
    sticker_url = random.choice(STICKERS)
    try:
        sticker_data = requests.get(sticker_url, timeout=10).content
        sticker = Image.open(io.BytesIO(sticker_data)).convert("RGBA")
        sticker_size = min(w, h) // 5
        sticker = sticker.resize((sticker_size, sticker_size), Image.LANCZOS)
        x = random.randint(0, max(0, w - sticker_size))
        y = random.randint(0, max(0, h - sticker_size))
        img.paste(sticker, (x, y), sticker)
    except Exception as e:
        log.error(f"Sticker error: {e}")
    
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG")
    out.seek(0)
    return out

def send_sticker_photo(bot_instance, chat_id, reply_to=None):
    photos = get_photos(chat_id)
    if not photos: return False
    file_id = random.choice(photos)
    try:
        file_info = bot_instance.get_file(file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        output = make_sticker(downloaded)
        if reply_to: bot_instance.send_photo(chat_id, output, reply_to_message_id=reply_to)
        else: bot_instance.send_photo(chat_id, output)
        return True
    except: return False

# ─── Хелперы ──────────────────────────────────────────────────────────────────
def has_mat(text):
    return any(m in text.lower() for m in MAT)

def get_random_user(chat_id):
    users = get_users(chat_id)
    if not users: return None
    return random.choice(list(users.values()))["name"]

# ─── Бот ──────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(TOKEN)
_clear_confirm = {}

# ─── Команды ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    cmds = """
🎭 *Лолыч:*
/mix — микс фраз
/poem — стих
/meme — мем
/dem — демотиватор
/stick — наклейка
/voice — голосовое
/stats — статистика
/level 1-3 — активность
/mute /unmute — тишина
/forget — удалить фото
/clear — очистить память
"""
    bot.reply_to(message, cmds, parse_mode="Markdown")

@bot.message_handler(commands=["level"])
def cmd_level(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, f"Уровень: {get_level(message.chat.id)}\n/level 1-3")
        return
    try:
        lv = int(args[1])
        if lv < 1 or lv > 3: raise ValueError
        s = get_settings(message.chat.id)
        s["level"] = lv
        save_settings(message.chat.id)
        names = {1:"редко", 2:"средне", 3:"часто"}
        bot.reply_to(message, f"Уровень: {lv} ({names[lv]})")
    except:
        bot.reply_to(message, "/level 1, 2 или 3")

@bot.message_handler(commands=["mute"])
def cmd_mute(message):
    s = get_settings(message.chat.id)
    s["muted"] = True
    save_settings(message.chat.id)
    bot.reply_to(message, "🔇 Тишина. /unmute чтобы включить")

@bot.message_handler(commands=["unmute"])
def cmd_unmute(message):
    s = get_settings(message.chat.id)
    s["muted"] = False
    save_settings(message.chat.id)
    bot.reply_to(message, "🔈 Проснулся!")

@bot.message_handler(commands=["mix", "микс"])
def cmd_mix(message):
    bot.send_message(message.chat.id, mix_messages(message.chat.id))

@bot.message_handler(commands=["poem", "стих"])
def cmd_poem(message):
    poem = make_poem(message.chat.id)
    bot.send_message(message.chat.id, f"🎭\n{poem}")

@bot.message_handler(commands=["meme", "мем"])
def cmd_meme(message):
    if not send_template_meme(bot, message.chat.id):
        bot.reply_to(message, "не смог сделать мем")

@bot.message_handler(commands=["dem", "дем"])
def cmd_dem(message):
    args = message.text.split(maxsplit=1)
    txt = args[1] if len(args) > 1 else None
    
    if message.reply_to_message and message.reply_to_message.photo:
        fid = message.reply_to_message.photo[-1].file_id
        text = txt or absurd_word_salad(message.chat.id, length=random.randint(3,8))
        try:
            fi = bot.get_file(fid)
            dl = bot.download_file(fi.file_path)
            out = make_demotivator(dl, text)
            bot.send_photo(message.chat.id, out)
            return
        except:
            bot.reply_to(message, "не смог")
            return
    
    if not send_random_dem(bot, message.chat.id, custom_text=txt):
        bot.reply_to(message, "нет фото в памяти")

@bot.message_handler(commands=["stick", "стик"])
def cmd_stick(message):
    if message.reply_to_message and message.reply_to_message.photo:
        fid = message.reply_to_message.photo[-1].file_id
        try:
            fi = bot.get_file(fid)
            dl = bot.download_file(fi.file_path)
            out = make_sticker(dl)
            bot.send_photo(message.chat.id, out)
            return
        except:
            bot.reply_to(message, "не смог")
            return
    
    if not send_sticker_photo(bot, message.chat.id):
        bot.reply_to(message, "нет фото в памяти")

@bot.message_handler(commands=["voice", "войс"])
def cmd_voice(message):
    text = absurd_word_salad(message.chat.id)
    voice = generate_voice(text)
    if voice: bot.send_voice(message.chat.id, voice)
    else: bot.reply_to(message, "не смог")

@bot.message_handler(commands=["stats", "стат"])
def cmd_stats(message):
    cid = message.chat.id
    msgs = _load(cid, "messages")
    users = _load(cid, "users")
    photos = _load(cid, "photos")
    s = get_settings(cid)
    names = {1:"редко", 2:"средне", 3:"часто"}
    
    stats = f"""📊 *Хранилище:*
• Сообщений: {len(msgs)}/{LIMITS['messages']}
• Участников: {len(users)}
• Фото: {len(photos)}/{LIMITS['photos']}
• Уровень: {s.get('level',1)} ({names.get(s.get('level',1),'редко')})
• Режим: {'🔇 тишина' if s.get('muted') else '🔈 активен'}"""
    
    bot.reply_to(message, stats, parse_mode="Markdown")

@bot.message_handler(commands=["forget"])
def cmd_forget(message):
    if remove_last_photo(message.chat.id):
        bot.reply_to(message, "🗑 Последнее фото удалено из памяти")
    else:
        bot.reply_to(message, "В памяти нет фото")

@bot.message_handler(commands=["clear", "очистить"])
def cmd_clear(message):
    cid = message.chat.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].lower() == "yes":
        if cid in _clear_confirm and _clear_confirm[cid]:
            global _markov_models, _markov_dirty
            for key in ["messages","users","photos","counter"]:
                path = _chat_file(cid, f"{key}.json")
                if os.path.exists(path): os.remove(path)
            for prefix in ["messages","users","photos","counter"]:
                if f"{cid}_{prefix}" in _cache: del _cache[f"{cid}_{prefix}"]
            if cid in _markov_models: del _markov_models[cid]
            if cid in _markov_dirty: _markov_dirty[cid] = True
            _clear_confirm[cid] = False
            bot.reply_to(message, "🧹 Память очищена!")
            return
        else:
            bot.reply_to(message, "Сначала /clear")
            return
    
    _clear_confirm[cid] = True
    bot.reply_to(message, "⚠️ /clear yes для подтверждения")

# ─── Сообщения ────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    if not message.text or message.text.startswith("/"): return
    cid = message.chat.id
    if is_muted(cid): return
    
    text = message.text
    name = message.from_user.first_name or "Аноним"
    uid = message.from_user.id
    
    add_message(cid, text)
    add_user_message(cid, uid, name, text)
    
    lv = get_level(cid)
    tr = LEVELS.get(lv, LEVELS[1])
    
    c = get_counter(cid)
    c["msgs"] = c.get("msgs",0)+1
    c["reply"] = c.get("reply",0)+1
    c["meme"] = c.get("meme",0)+1
    c["voice"] = c.get("voice",0)+1
    c["mat"] = c.get("mat",0)+1
    c["dem"] = c.get("dem",0)+1
    c["stick"] = c.get("stick",0)+1
    
    # «Кто»
    if "кто" in text.lower().split():
        user = get_random_user(cid)
        if user:
            bot.reply_to(message, random.choice(KTO_ANSWERS).format(user=user))
            return
    
    # «лолыч»
    if any(w in text.lower() for w in ["лолыч","лолич"]):
        clean = text.lower()
        for w in ["лолыч","лолич"]: clean = clean.replace(w,"").strip()
        bot.reply_to(message, absurd_word_salad(cid, clean))
        return
    
    # Мат
    if has_mat(text):
        c["mat_voice"] = c.get("mat_voice",0)+1
        if c["mat_voice"] >= MAT_VOICE_EVERY:
            c["mat_voice"] = 0
            save_counter(cid)
            threading.Thread(target=lambda: send_mat_voice(bot, cid, message.message_id), daemon=True).start()
            return
        if random.random() < MAT_REPLY_CHANCE:
            bot.reply_to(message, random.choice(MAT).upper()+"!")
            return
    
    # Авто-мат
    if c["mat"] >= tr[5]: c["mat"]=0; save_counter(cid); bot.reply_to(message, random.choice(MAT).upper()+"!"); return
    # Авто-войс
    if c["voice"] >= tr[3]: c["voice"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_voice(bot,cid), daemon=True).start(); return
    # Авто-стих
    if c["msgs"] >= tr[1]: c["msgs"]=0; save_counter(cid); threading.Thread(target=lambda: bot.send_message(cid, f"🎭\n{make_poem(cid)}"), daemon=True).start(); return
    # Авто-мем
    if c["meme"] >= tr[2]: c["meme"]=0; save_counter(cid); threading.Thread(target=lambda: send_template_meme(bot,cid), daemon=True).start(); return
    # Авто-дем
    if c["dem"] >= tr[4]: c["dem"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_dem(bot,cid), daemon=True).start() if get_photos(cid) else None; return
    # Авто-стик
    if c["stick"] >= tr[6]: c["stick"]=0; save_counter(cid); threading.Thread(target=lambda: send_sticker_photo(bot,cid), daemon=True).start() if get_photos(cid) else None; return
    # Авто-ответ
    if c["reply"] >= tr[0]: c["reply"]=0; save_counter(cid); bot.reply_to(message, absurd_word_salad(cid, text)); return    
    save_counter(cid)
    
    # @упоминание
    if f"@{bot.get_me().username}" in text:
        clean = text.replace(f"@{bot.get_me().username}","").strip()
        bot.reply_to(message, absurd_word_salad(cid, clean))
        return
    
    # Случайный ответ (40%)
    if random.random() < 0.4:
        if random.random() < 0.15: bot.reply_to(message, " ".join(random.choices(EMOJI, k=random.randint(1,3))))
        else: bot.reply_to(message, absurd_word_salad(cid, text))

# ─── Фото ─────────────────────────────────────────────────────────────────────
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    cid = message.chat.id
    if is_muted(cid): return
    
    file_id = message.photo[-1].file_id
    add_photo(cid, file_id)
    caption = (message.caption or "").lower()
    
    if any(w in caption for w in ["мем","meme"]):
        send_template_meme(bot, cid, message.message_id)
    elif any(w in caption for w in ["дем","dem"]):
        fi = bot.get_file(file_id)
        dl = bot.download_file(fi.file_path)
        text = absurd_word_salad(cid, length=random.randint(3,8))
        out = make_demotivator(dl, text)
        bot.send_photo(cid, out)
    elif any(w in caption for w in ["стик","stick"]):
        fi = bot.get_file(file_id)
        dl = bot.download_file(fi.file_path)
        out = make_sticker(dl)
        bot.send_photo(cid, out)
    elif random.random() < 0.3:
        comments = [absurd_word_salad(cid, length=random.randint(1,10)), random.choice(EMOJI)*random.randint(1,2), "это чё такое?", "🤔"]
        bot.reply_to(message, random.choice(comments))

# ─── Запуск ────────────────────────────────────────────────────────────────────
log.info("Лолыч проснулся!")
bot.polling(none_stop=True)






