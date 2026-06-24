import telebot
import markovify
import random
import threading
import json
import os
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
    "messages": 3000,
    "user_msgs": 700,
    "photos": 200,
}

TRIGGERS = {
    "poem": (100, 300),
    "reply": (75, 75),
    "meme": (100, 200),
    "voice": (100, 200),
    "mat": (75, 75),
    "dem": (200, 400),
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

# ─── Файлы для каждого чата ───────────────────────────────────────────────────
def _chat_file(chat_id, name):
    return f"chat_{chat_id}_{name}"

# ─── Хранилище ─────────────────────────────────────────────────────────────────
_cache = {}

def _load(chat_id, key):
    cache_key = f"{chat_id}_{key}"
    if cache_key in _cache:
        return _cache[cache_key]
    path = _chat_file(chat_id, f"{key}.json")
    if not os.path.exists(path):
        default = {} if key in ("users", "counter") else []
        if key == "counter":
            default = {"msgs": 0, "reply": 0, "meme": 0, "voice": 0, "mat": 0, "mat_voice": 0, "dem": 0}
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
def add_photo(chat_id, file_id):
    photos = _load(chat_id, "photos")
    if file_id not in photos:
        photos.append(file_id)
    if len(photos) > LIMITS["photos"]:
        _cache[f"{chat_id}_photos"] = photos[-LIMITS["photos"]:]
    _save(chat_id, "photos")

def get_photos(chat_id):
    return _load(chat_id, "photos")

# ─── Счётчики ─────────────────────────────────────────────────────────────────
def get_counter(chat_id):
    return _load(chat_id, "counter")

def save_counter(chat_id):
    _save(chat_id, "counter")

# ─── Слова чата ───────────────────────────────────────────────────────────────
def _chat_words(chat_id, min_len=2, last_n=300):
    msgs = _load(chat_id, "messages")
    if not msgs:
        return []
    words = []
    for m in msgs[-last_n:]:
        words.extend(w.strip(".,!?:;\"'()«»") for w in m.split())
    return [w for w in words if len(w) > min_len]

def _random_phrase(chat_id):
    """Возвращает случайное целое сообщение или его кусок"""
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
    """50% — целая фраза из чата, 50% — салат из слов"""
    if length is None:
        length = random.randint(1, 10)
    
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

# ─── Цитата ───────────────────────────────────────────────────────────────────
def random_quote_salad(chat_id, length=None):
    msgs = _load(chat_id, "messages")
    if not msgs:
        return None
    if length is None:
        length = random.randint(6, 12)
    words = []
    attempts = 0
    while len(words) < length and attempts < length * 5:
        attempts += 1
        msg = random.choice(msgs)
        candidates = [w.strip(".,!?:;\"'()«»") for w in msg.split() if len(w) > 1]
        if candidates:
            words.append(random.choice(candidates))
    if not words:
        return None
    return " ".join(words)

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

# ─── Стихи ────────────────────────────────────────────────────────────────────
def make_poem(chat_id):
    model = _get_markov_model(chat_id)
    words = _chat_words(chat_id)
    if not words:
        return absurd_word_salad(chat_id)
    lines = []
    for _ in range(random.randint(2, 4)):
        if model and random.random() < 0.5:
            line = model.make_short_sentence(50, tries=20)
        else:
            line = " ".join(random.choices(words, k=random.randint(3, 6)))
        if line:
            words_in_line = line.split()
            if len(words_in_line) > 8:
                line = " ".join(words_in_line[:8])
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

# ─── Мемы ─────────────────────────────────────────────────────────────────────
def get_meme_text(chat_id):
    """Текст для мема: до 10 слов"""
    if random.random() < 0.5:
        msgs = _load(chat_id, "messages")
        if msgs:
            msg = random.choice(msgs)
            words = msg.split()[:10]
            return " ".join(words).upper()
    all_words = _chat_words(chat_id, min_len=2)
    if all_words:
        count = min(random.randint(2, 5), len(all_words))
        return " ".join(random.choices(all_words, k=count)).upper()
    return "ЛОЛЫЧ"

def _draw_meme_text(draw, text, img_w, img_h, position="bottom"):
    text = text.upper().strip()
    if not text:
        return
    font_size = max(int(img_h * 0.10), 24)
    font = _find_font(font_size)
    wrap_width = max(int(img_w / (font_size * 0.62)), 6)
    lines = textwrap.wrap(text, width=wrap_width) or [text]
    outline = max(int(font_size * 0.07), 2)
    line_height = int(font_size * 1.15)
    total_h = line_height * len(lines)
    y = int(img_h * 0.02) if position == "top" else img_h - total_h - int(img_h * 0.03)
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
        except:
            text_w = len(line) * int(font_size * 0.55)
        x = max(5, (img_w - text_w) // 2)
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += line_height

def make_meme(img_bytes, top_text, bottom_text):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    _draw_meme_text(draw, top_text, w, h, "top")
    _draw_meme_text(draw, bottom_text, w, h, "bottom")
    out = io.BytesIO()
    img.save(out, format="JPEG")
    out.seek(0)
    return out

def send_random_meme(bot_instance, chat_id, reply_to=None):
    photos = get_photos(chat_id)
    if not photos:
        return False
    file_id = random.choice(photos)
    top = get_meme_text(chat_id)
    bottom = get_meme_text(chat_id)
    try:
        file_info = bot_instance.get_file(file_id)
        downloaded = bot_instance.download_file(file_info.file_path)
        output = make_meme(downloaded, top, bottom)
        if reply_to:
            bot_instance.send_photo(chat_id, output, reply_to_message_id=reply_to)
        else:
            bot_instance.send_photo(chat_id, output)
        return True
    except Exception as e:
        log.error(f"send_random_meme error: {e}")
    return False

# ─── Демотиваторы ─────────────────────────────────────────────────────────────
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
    
    out = io.BytesIO()
    canvas.save(out, format="JPEG")
    out.seek(0)
    return out

def send_random_dem(bot_instance, chat_id, reply_to=None, custom_text=None):
    photos = get_photos(chat_id)
    if not photos:
        return False
    file_id = random.choice(photos)
    
    if custom_text:
        text = custom_text
    else:
        text = absurd_word_salad(chat_id, length=random.randint(3, 8))
    
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

# ─── Подтверждение очистки ────────────────────────────────────────────────────
_clear_confirm = {}

# ─── Команды ──────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    commands = """
🎭 *Лолыч-сглыпа к вашим услугам:*
/mix — микс двух сообщений
/poem — сгенерировать стих
/meme — создать мем
/dem \[текст\] — демотиватор
/quote — случайная цитата
/voice — голосовое с абсурдом
/stats — статистика хранилища
/clear — очистить память чата
"""
    bot.reply_to(message, commands, parse_mode="Markdown")

@bot.message_handler(commands=["mix", "микс"])
def cmd_mix(message):
    bot.send_message(message.chat.id, mix_messages(message.chat.id))

@bot.message_handler(commands=["poem", "стих", "стишок", "поэзия"])
def cmd_poem(message):
    poem = make_poem(message.chat.id)
    bot.send_message(message.chat.id, f"🎭 *Стихотворение:*\n{poem}", parse_mode="Markdown")

@bot.message_handler(commands=["meme", "мем", "mem"])
def cmd_meme(message):
    if not send_random_meme(bot, message.chat.id):
        bot.reply_to(message, "ещё не видел фоток в беседе!")

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
            log.error(f"dem from reply error: {e}")
            bot.reply_to(message, "не смог сделать демотиватор")
            return
    
    if not send_random_dem(bot, message.chat.id, custom_text=custom_text):
        bot.reply_to(message, "ещё не видел фоток в беседе!")

@bot.message_handler(commands=["quote", "цитата"])
def cmd_quote(message):
    quote = random_quote_salad(message.chat.id)
    if not quote:
        bot.reply_to(message, "цитат пока нет")
        return
    bot.reply_to(message, f"💬 «{quote}»")

@bot.message_handler(commands=["voice", "войс", "голос"])
def cmd_voice(message):
    text = absurd_word_salad(message.chat.id)
    voice = generate_voice(text)
    if voice:
        bot.send_voice(message.chat.id, voice, caption="сглыпа говорит")
    else:
        bot.reply_to(message, "не смог сказать. слова кончились.")

@bot.message_handler(commands=["stats", "стат", "статистика"])
def cmd_stats(message):
    chat_id = message.chat.id
    msgs = _load(chat_id, "messages")
    users = _load(chat_id, "users")
    photos = _load(chat_id, "photos")
    c = get_counter(chat_id)
    
    stats = f"""📊 *Хранилище чата:*
• Сообщений: {len(msgs)} / {LIMITS['messages']}
• Участников: {len(users)}
• Фото: {len(photos)} / {LIMITS['photos']}
• Счётчик сообщений: {c.get('msgs', 0)}"""
    
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
    bot.reply_to(message, "⚠️ Ты уверен? Вся память этого чата будет стёрта.\nНапиши /clear yes для подтверждения")

# ─── Обработка сообщений ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    if not message.text or message.text.startswith("/"):
        return
    
    text = message.text
    name = message.from_user.first_name or "Аноним"
    uid = message.from_user.id
    chat_id = message.chat.id
    text_lower = text.lower().strip()
    
    add_message(chat_id, text)
    add_user_message(chat_id, uid, name, text)
    c = get_counter(chat_id)
    c["msgs"] = c.get("msgs", 0) + 1
    c["reply"] = c.get("reply", 0) + 1
    c["meme"] = c.get("meme", 0) + 1
    c["voice"] = c.get("voice", 0) + 1
    c["mat"] = c.get("mat", 0) + 1
    c["dem"] = c.get("dem", 0) + 1
    
    # «Кто...»
    if text_lower.startswith(("кто из нас", "кто тут", "кто здесь", "кто у нас")):
        user = get_random_user(chat_id)
        if user:
            bot.reply_to(message, f"это {user}")
            return
    
    # «лолыч», «лолич»
    if any(w in text_lower for w in ["лолыч", "лолич"]):
        clean = text
        for w in ["лолыч", "лолич"]:
            clean = clean.lower().replace(w, "").strip()
        bot.reply_to(message, absurd_word_salad(chat_id, clean, length=random.randint(1, 10)))
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
    if c["mat"] >= TRIGGERS["mat"][0]:
        c["mat"] = 0
        save_counter(chat_id)
        bot.reply_to(message, random.choice(MAT).upper() + "!")
        return
    
    # Авто-войс
    voice_trigger = random.randint(*TRIGGERS["voice"])
    if c["voice"] >= voice_trigger:
        c["voice"] = 0
        save_counter(chat_id)
        threading.Thread(target=lambda: send_random_voice(bot, chat_id), daemon=True).start()
        return
    
    # Авто-стих
    poem_trigger = random.randint(*TRIGGERS["poem"])
    if c["msgs"] >= poem_trigger:
        c["msgs"] = 0
        save_counter(chat_id)
        threading.Thread(target=lambda: bot.send_message(chat_id, f"🎭\n{make_poem(chat_id)}"), daemon=True).start()
        return
    
    # Авто-мем
    meme_trigger = random.randint(*TRIGGERS["meme"])
    if c["meme"] >= meme_trigger:
        c["meme"] = 0
        save_counter(chat_id)
        if get_photos(chat_id):
            threading.Thread(target=lambda: send_random_meme(bot, chat_id), daemon=True).start()
        return
    
    # Авто-демотиватор
    dem_trigger = random.randint(*TRIGGERS["dem"])
    if c["dem"] >= dem_trigger:
        c["dem"] = 0
        save_counter(chat_id)
        if get_photos(chat_id):
            threading.Thread(target=lambda: send_random_dem(bot, chat_id), daemon=True).start()
        return
    
    # Авто-ответ
    if c["reply"] >= TRIGGERS["reply"][0]:
        c["reply"] = 0
        save_counter(chat_id)
        bot.reply_to(message, absurd_word_salad(chat_id, text, length=random.randint(1, 10)))
        return
    
    save_counter(chat_id)
    
    # Упоминание @
    bot_username = bot.get_me().username
    if bot_username and f"@{bot_username}" in text:
        clean = text.replace(f"@{bot_username}", "").strip()
        bot.reply_to(message, absurd_word_salad(chat_id, clean, length=random.randint(1, 10)))
        return
    
    # Случайный ответ (40%)
    if random.random() < 0.4:
        if random.random() < 0.15:
            bot.reply_to(message, " ".join(random.choices(EMOJI, k=random.randint(1, 3))))
        else:
            bot.reply_to(message, absurd_word_salad(chat_id, text, length=random.randint(1, 10)))

# ─── Фото ─────────────────────────────────────────────────────────────────────
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    chat_id = message.chat.id
    add_photo(chat_id, file_id)
    caption = (message.caption or "").lower()
    
    if any(w in caption for w in ["мем", "meme"]):
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        top = get_meme_text(chat_id)
        bottom = get_meme_text(chat_id)
        output = make_meme(downloaded, top, bottom)
        bot.send_photo(chat_id, output)
    elif any(w in caption for w in ["дем", "dem"]):
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        text = absurd_word_salad(chat_id, length=random.randint(3, 8))
        output = make_demotivator(downloaded, text)
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
