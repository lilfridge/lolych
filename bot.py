import telebot
import markovify
import random
import threading
import time
import json
import os
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import logging

# ─── Логирование ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─── Конфиг ────────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TOKEN", "8464842453:AAE4QiUoCGhNdjNyCA3vRLMuloDOIinMPGc")

FILES = {
    "messages": "messages.json",
    "users": "users.json",
    "photos": "photos.json",
    "counter": "counter.json",
}

LIMITS = {
    "messages": 10000,
    "user_msgs": 2000,
    "photos": 500,
}

TRIGGERS = {
    "poem": 50,
    "reply": 30,
    "photo_reply": 50,
}

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

RHYMES = {
    "ай": ["давай", "трамвай", "сарай", "лентяй", "урожай"],
    "ой": ["герой", "горой", "тобой", "судьбой", "головой"],
    "ать": ["мать", "спать", "послать", "сосать", "страдать"],
    "еть": ["пиздеть", "сидеть", "глядеть", "балдеть", "хотеть"],
    "ить": ["жить", "любить", "тупить", "ходить", "варить"],
    "уй": ["хуй", "поцелуй", "танцуй", "воруй", "голосуй"],
    "як": ["дурак", "пятак", "большак", "свояк", "рыбак"],
    "ок": ["дружок", "пирожок", "утюжок", "прыжок", "кружок"],
    "ак": ["дурак", "батрак", "бивак", "чужак", "рыбак"],
    "ек": ["человек", "век", "снег", "бег", "оберег"],
}

# ─── Хранилище ─────────────────────────────────────────────────────────────────
_cache = {}

def _load(key):
    if key in _cache:
        return _cache[key]
    path = FILES[key]
    if not os.path.exists(path):
        default = {} if key in ("users", "counter") else []
        if key == "counter":
            default = {"msgs": 0, "reply": 0, "photo_reply": 0}
        _cache[key] = default
        return default
    with open(path, "r", encoding="utf-8") as f:
        _cache[key] = json.load(f)
    return _cache[key]

def _save(key):
    with open(FILES[key], "w", encoding="utf-8") as f:
        json.dump(_cache[key], f, ensure_ascii=False)

# ─── Сообщения ─────────────────────────────────────────────────────────────────
_markov_model = None
_markov_dirty = True

def get_messages():
    return _load("messages")

def add_message(text):
    global _markov_dirty
    msgs = get_messages()
    msgs.append(text)
    if len(msgs) > LIMITS["messages"]:
        _cache["messages"] = msgs[-LIMITS["messages"]:]
    _save("messages")
    _markov_dirty = True

def get_users():
    return _load("users")

def add_user_message(user_id, name, text):
    users = get_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"name": name, "messages": []}
    users[uid]["name"] = name
    users[uid]["messages"].append(text)
    if len(users[uid]["messages"]) > LIMITS["user_msgs"]:
        users[uid]["messages"] = users[uid]["messages"][-LIMITS["user_msgs"]:]
    _save("users")

def get_photos():
    return _load("photos")

def add_photo(file_id):
    photos = get_photos()
    if file_id not in photos:
        photos.append(file_id)
    if len(photos) > LIMITS["photos"]:
        _cache["photos"] = photos[-LIMITS["photos"]:]
    _save("photos")

def get_counter():
    return _load("counter")

def save_counter():
    _save("counter")

# ─── Markov ────────────────────────────────────────────────────────────────────
def _get_markov_model():
    global _markov_model, _markov_dirty
    if _markov_dirty or _markov_model is None:
        msgs = get_messages()
        if len(msgs) < 10:
            return None
        try:
            _markov_model = markovify.Text(" ".join(msgs), state_size=2)
            _markov_dirty = False
        except Exception as e:
            log.warning(f"Markov build error: {e}")
            return None
    return _markov_model

def generate_markov():
    model = _get_markov_model()
    if not model:
        return "ещё мало сообщений, пишите больше!"
    msgs = get_messages()
    result = model.make_sentence(tries=50)
    return result if result else random.choice(msgs)

# ─── Абсурдный набор слов ──────────────────────────────────────────────────────
def _chat_words(min_len=2):
    msgs = get_messages()
    if not msgs:
        return []
    words = []
    for m in msgs[-300:]:
        words.extend(w.strip(".,!?:;\"'()") for w in m.split())
    return [w for w in words if len(w) > min_len]

def absurd_word_salad(source_text="", length=None):
    if length is None:
        length = random.randint(10, 15)
    
    pool = _chat_words()
    if source_text:
        pool.extend(w.strip(".,!?:;\"'()") for w in source_text.split() if len(w) > 1)
    pool.extend(random.choices(MAT, k=max(3, length // 3)))
    
    if not pool:
        pool = MAT[:]
    
    result = []
    while len(result) < length:
        w = random.choice(pool)
        if random.random() < 0.35 and len(result) + 2 <= length:
            repeat = random.randint(2, 3)
            result.extend([w] * min(repeat, length - len(result)))
        else:
            result.append(w)
    
    if random.random() < 0.5:
        result.append(random.choice(MAT))
    
    result = result[:length + 1]
    text = " ".join(result)
    
    if random.random() < 0.2:
        text = text.upper()
    if random.random() < 0.4:
        text += random.choice(["?", "!", "??", "сука!", ""])
    
    return text.strip()

# ─── Стихи ─────────────────────────────────────────────────────────────────────
def find_rhyme(word):
    word = word.lower()
    for ending, rhymes in RHYMES.items():
        if word.endswith(ending):
            return random.choice(rhymes)
    return word

def make_poem():
    model = _get_markov_model()
    words = _chat_words()
    
    if not words:
        return absurd_word_salad()
    
    lines = []
    for _ in range(random.randint(2, 4)):
        if model and random.random() < 0.5:
            line = model.make_short_sentence(50, tries=20)
        else:
            line = " ".join(random.choices(words, k=random.randint(3, 7)))
        
        if line:
            last_word = line.split()[-1].strip(".,!?:;\"'()")
            if random.random() < 0.3:
                rhyme = find_rhyme(last_word)
                if rhyme != last_word:
                    line = " ".join(line.split()[:-1]) + " " + rhyme
            lines.append(line)
    
    if len(lines) < 2:
        return absurd_word_salad()
    
    return "\n".join(lines[:4])

# ─── Оскорбления ───────────────────────────────────────────────────────────────
def generate_insult(name=""):
    adjectives = [
        "конченый", "тупорылый", "бездарный", "унылый", "позорный",
        "жалкий", "никчемный", "глупый", "бестолковый", "криворукий"
    ]
    nouns = [
        "огузок", "огрызок", "пень", "баран", "индюк", "валенок",
        "сапог", "чемодан", "кабачок", "огурец"
    ]
    
    if name:
        return f"{name} — {random.choice(adjectives)} {random.choice(nouns)}"
    else:
        return f"ты {random.choice(adjectives)} {random.choice(nouns)}"

# ─── Фото-ответы ───────────────────────────────────────────────────────────────
def send_random_photo(bot_instance, chat_id, reply_to=None):
    photos = get_photos()
    if not photos:
        return False
    
    file_id = random.choice(photos)
    try:
        captions = [
            absurd_word_salad(length=5),
            random.choice(EMOJI) * random.randint(1, 3),
            random.choice(MAT).upper() + "!",
            generate_insult(),
            "чё думаешь?",
            "вот это да...",
            "🤔",
        ]
        caption = random.choice(captions)
        
        if reply_to:
            bot_instance.send_photo(chat_id, file_id, caption=caption, reply_to_message_id=reply_to)
        else:
            bot_instance.send_photo(chat_id, file_id, caption=caption)
        return True
    except Exception as e:
        log.error(f"send_random_photo error: {e}")
        return False

# ─── Мемы ──────────────────────────────────────────────────────────────────────
def get_random_words(n=3):
    msgs = get_messages()
    if not msgs:
        return "НУ И ДЕЛА БРАТАН"
    all_words = [w for w in " ".join(msgs).split() if len(w) > 2]
    if not all_words:
        return "НУ И ДЕЛА БРАТАН"
    return " ".join(random.choices(all_words, k=n)).upper()

def _draw_meme_text(draw, text, img_w, img_h, position="bottom"):
    try:
        font = ImageFont.truetype("impact.ttf", size=int(img_h * 0.1))
    except:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text, width=12)
    line_height = int(img_h * 0.12)
    y = 10 if position == "top" else img_h - line_height * len(lines) - 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (img_w - text_w) // 2
        for dx in (-3, 3):
            for dy in (-3, 3):
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

# ─── Хелперы ───────────────────────────────────────────────────────────────────
def has_mat(text):
    t = text.lower()
    return any(m in t for m in MAT)

def random_response(source_text=""):
    roll = random.random()
    if roll < 0.15:
        return " ".join(random.choices(EMOJI, k=random.randint(1, 4)))
    elif roll < 0.3:
        return generate_insult()
    return absurd_word_salad(source_text)

# ─── Бот ───────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(TOKEN)

# ─── Команды ───────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    commands = """
🎭 *Лолыч-сглыпа к вашим услугам:*
/who \[действие\] — выбрать виноватого
/salad — абсурдный набор слов
/poem — сгенерировать стих
/meme — создать мем
/imitate \[имя\] — спародировать
/roast \[имя\] — смешное оскорбление
/quote — случайная цитата
/when \[вопрос\] — магический шар
"""
    bot.reply_to(message, commands, parse_mode="Markdown")

@bot.message_handler(commands=["salad", "sglypa", "сглыпа"])
def cmd_salad(message):
    bot.send_message(message.chat.id, absurd_word_salad())

@bot.message_handler(commands=["who", "кто"])
def cmd_who(message):
    text = message.text
    for cmd in ["/who", "/кто"]:
        text = text.replace(cmd, "").strip()
    
    text = text or "должен купить еду"
    users = get_users()
    if not users:
        bot.send_message(message.chat.id, "не знаю никого ещё")
        return
    chosen = random.choice(list(users.values()))
    bot.send_message(message.chat.id, f"{chosen['name']} {text}!")

@bot.message_handler(commands=["poem", "стих", "стишок", "поэзия"])
def cmd_poem(message):
    poem = make_poem()
    bot.send_message(message.chat.id, f"🎭 *Стихотворение:*\n{poem}", parse_mode="Markdown")

@bot.message_handler(commands=["meme", "мем", "mem"])
def cmd_meme(message):
    photos = get_photos()
    if not photos:
        bot.reply_to(message, "ещё не видел фоток в беседе!")
        return
    file_id = random.choice(photos)
    top = get_random_words(random.randint(2, 3))
    bottom = get_random_words(random.randint(2, 4))
    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        output = make_meme(downloaded, top, bottom)
        bot.send_photo(message.chat.id, output)
    except Exception as e:
        log.error(f"cmd_meme error: {e}")
        bot.reply_to(message, "не смог сделать мем")

@bot.message_handler(commands=["imitate", "имитировать"])
def cmd_imitate(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "напиши /imitate имя")
        return
    name = args[1].replace("@", "")
    users = get_users()
    found = next(
        (uid for uid, data in users.items() if data["name"].lower() == name.lower()),
        None
    )
    if not found:
        bot.reply_to(message, "не знаю такого")
        return
    msgs = users[found]["messages"]
    if len(msgs) < 5:
        bot.reply_to(message, "мало сообщений от этого человека")
        return
    try:
        model = markovify.Text(" ".join(msgs), state_size=1)
        result = model.make_sentence(tries=50) or random.choice(msgs)
    except:
        result = random.choice(msgs)
    bot.reply_to(message, f"{users[found]['name']}: {result}")

@bot.message_handler(commands=["roast", "обосрать"])
def cmd_roast(message):
    args = message.text.split()
    if len(args) > 1:
        name = " ".join(args[1:]).replace("@", "")
    else:
        name = ""
    
    insult = generate_insult(name)
    bot.reply_to(message, insult)

@bot.message_handler(commands=["quote", "цитата"])
def cmd_quote(message):
    msgs = get_messages()
    if not msgs:
        bot.reply_to(message, "цитат пока нет")
        return
    
    good_msgs = [m for m in msgs if len(m) > 20 and len(m) < 200]
    if good_msgs:
        quote = random.choice(good_msgs)
        bot.reply_to(message, f"💬 «{quote}»")
    else:
        bot.reply_to(message, random.choice(msgs))

@bot.message_handler(commands=["when", "когда"])
def cmd_when(message):
    text = message.text
    for cmd in ["/when", "/когда"]:
        text = text.replace(cmd, "").strip()
    
    answers = [
        "никогда", "завтра", "через 5 минут", 
        "когда рак на горе свистнет", "скоро",
        "в следующей жизни", "после дождичка в четверг",
        "когда хуй на крыше вырастет", "в 3024 году",
    ]
    
    if text:
        bot.reply_to(message, f"{text} — *{random.choice(answers)}*!", parse_mode="Markdown")
    else:
        bot.reply_to(message, "Что когда? Напиши /when [вопрос]")

# ─── Обработка сообщений ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    if not message.text or message.text.startswith("/"):
        return
    
    text = message.text
    name = message.from_user.first_name or "Аноним"
    uid = message.from_user.id
    chat_id = message.chat.id
    
    add_message(text)
    add_user_message(uid, name, text)
    c = get_counter()
    c["msgs"] += 1
    c["reply"] += 1
    c["photo_reply"] += 1
    
    # Авто-стих
    if c["msgs"] >= TRIGGERS["poem"]:
        c["msgs"] = 0
        save_counter()
        threading.Thread(
            target=lambda: bot.send_message(chat_id, f"🎭\n{make_poem()}"),
            daemon=True
        ).start()
        return
    
    # Авто-фото-ответ
    if c["photo_reply"] >= TRIGGERS["photo_reply"]:
        c["photo_reply"] = 0
        save_counter()
        threading.Thread(
            target=lambda: send_random_photo(bot, chat_id),
            daemon=True
        ).start()
        return
    
    # Авто-текстовый ответ
    if c["reply"] >= TRIGGERS["reply"]:
        c["reply"] = 0
        save_counter()
        reply = absurd_word_salad(text)
        bot.reply_to(message, reply)
        return
    
    save_counter()
    
    # Ответ на упоминание
    bot_username = bot.get_me().username
    if bot_username and f"@{bot_username}" in text:
        clean = text.replace(f"@{bot_username}", "").strip()
        
        if random.random() < 0.3 and get_photos():
            send_random_photo(bot, chat_id, message.message_id)
        else:
            reply = absurd_word_salad(clean)
            bot.reply_to(message, reply)
        return
    
    # Реакция на мат
    if has_mat(text) and random.random() < 0.6:
        if random.random() < 0.2 and get_photos():
            send_random_photo(bot, chat_id, message.message_id)
        else:
            bot.reply_to(message, random.choice(MAT).upper() + "!")
        return
    
    # Случайный ответ (30% шанс)
    if random.random() < 0.3:
        if random.random() < 0.15 and get_photos():
            send_random_photo(bot, chat_id, message.message_id)
        else:
            bot.reply_to(message, random_response(text))

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    add_photo(file_id)
    caption = (message.caption or "").lower()
    
    if "мем" in caption or "meme" in caption:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        top = get_random_words(random.randint(2, 3))
        bottom = get_random_words(random.randint(2, 4))
        output = make_meme(downloaded, top, bottom)
        bot.send_photo(message.chat.id, output)
    elif random.random() < 0.3:
        comments = [
            absurd_word_salad(length=5),
            generate_insult(),
            random.choice(EMOJI) * random.randint(1, 3),
            "это чё такое?",
            "🤔",
        ]
        bot.reply_to(message, random.choice(comments))

# ─── Запуск ────────────────────────────────────────────────────────────────────
log.info("Лолыч проснулся!")
bot.polling(none_stop=True)
