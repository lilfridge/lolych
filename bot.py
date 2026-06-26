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

TOKEN = "8464842453:AAE4QiUoCGhNdjNyCA3vRLMuloDOIinMPGc"
OPENROUTER_KEY = "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"
GIPHY_KEY = "ks2qau91LISJrgKVPhhSGOTzsCiJUUZL"

LIMITS = {"messages": 5000, "user_msgs": 700, "photos": 200}

# (мем, войс, дем, мат, стик, гифка, random_chance)
LEVELS = {
    1: (2000, 2000, 3000, 1000, 2000, 2000, 0.005),
    2: (500, 500, 800, 300, 500, 500, 0.03),
    3: (100, 100, 150, 80, 100, 100, 0.30),
}

# (реакция_на_мат, кто_шанс, лолыч_шанс, фото_реакция, когда_шанс)
LEVEL_EXTRAS = {
    1: (0.01, 0.05, 0.30, 0.05, 0.05),
    2: (0.03, 0.20, 0.60, 0.15, 0.20),
    3: (0.10, 0.50, 1.00, 0.40, 0.50),
}

DEEPSEEK_CHANCE = 0.05

MAT = [
    "блять", "бля", "нахуй", "хуй", "пизда", "ебать", "сука", "пиздец",
    "залупа", "мудак", "долбаёб", "ёбанный", "хуйня", "уёбок",
    "гондон", "мразь", "тварь", "ушлёпок", "дебил", "идиот",
    "заебал", "наебал", "хуесос", "чмо", "лох", "тупой", "конченый",
]

EMOJI = ["💀","🗿","😭","🤡","👀","🔥","😐","💅","🤨","😤","🥶","🤙","🦧",
         "🤯","💩","🙈","🤪","🤮","😬","🥴","👻"]

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

IMGFLIP_USER = "lilifridge"
IMGFLIP_PASS = "eMsWrri64INeGJd"
IMGFLIP_TEMPLATES = [
    181913649, 87743020, 93895088, 252600902, 131940431,
    89370399, 110163934, 61579, 101470, 217743513,
    91538330, 4087833, 5496396, 1035805, 123999232,
    124822590, 148909805, 97984, 161865971, 9440985, 55353130,
]

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

# ─── Файлы ────────────────────────────────────────────────────────────────────
def _chat_file(chat_id, name): return f"chat_{chat_id}_{name}"

_cache = {}
_my_photos = set()

def _load(chat_id, key):
    cache_key = f"{chat_id}_{key}"
    if cache_key in _cache: return _cache[cache_key]
    path = _chat_file(chat_id, f"{key}.json")
    if not os.path.exists(path):
        default = {} if key in ("users","counter","settings") else []
        if key == "counter": default = {"msgs":0,"meme":0,"voice":0,"mat":0,"dem":0,"stick":0,"gif":0}
        if key == "settings": default = {"level":1,"muted":False}
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
    if random.random() < 0.5:
        phrase = _random_phrase(chat_id)
        if phrase:
            words = phrase.split()
            if len(words) > length: phrase = " ".join(words[:length])
            return phrase.strip()
    pool = _chat_words(chat_id)
    if source_text: pool.extend(w.strip(".,!?:;\"'()«»") for w in source_text.split() if len(w)>1)
    if not pool: return random.choice(EMOJI)
    result = [random.choice(pool) for _ in range(length)]
    text = " ".join(result)
    if random.random() < 0.1: text = text.upper()
    return text.strip()

# ─── OpenRouter (DeepSeek) ─────────────────────────────────────────────────────
def ask_ai(prompt, chat_id):
    try:
        context = " ".join(_load(chat_id, "messages")[-20:])
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "deepseek/deepseek-chat",
            "messages": [
                {"role": "system", "content": f"Ты — бот Лолыч в чате. Отвечай коротко (1-3 предложения), смешно и дерзко. Контекст чата: {context[:300]}"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 100,
            "temperature": 0.9
        }
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=20)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"].strip()
        log.error(f"OpenRouter error: {r.status_code} {r.text}")
    except Exception as e: log.error(f"OpenRouter exception: {e}")
    return None

# ─── GIPHY ─────────────────────────────────────────────────────────────────────
def get_random_gif():
    try:
        url = f"https://api.giphy.com/v1/gifs/random?api_key={GIPHY_KEY}&tag=meme&rating=r"
        r = requests.get(url, timeout=10).json()
        if r.get("data",{}).get("images",{}).get("original",{}).get("url"):
            return r["data"]["images"]["original"]["url"]
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
    msgs = _load(chat_id, "messages")
    if len(msgs) < 2: return absurd_word_salad(chat_id)
    a, b = random.choice(msgs).split(), random.choice(msgs).split()
    if len(a)<2 or len(b)<2: return absurd_word_salad(chat_id)
    return " ".join(a[:len(a)//2] + b[len(b)//2:])

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
    if w>500 or h>500:
        r = min(500/w, 500/h); img = img.resize((int(w*r), int(h*r)), Image.LANCZOS); w, h = img.size
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
        fi = bot_instance.get_file(fid)
        dl = bot_instance.download_file(fi.file_path)
        out = make_demotivator(dl, text)
        _my_photos.add(fid)
        if reply_to: bot_instance.send_photo(chat_id, out, reply_to_message_id=reply_to)
        else: bot_instance.send_photo(chat_id, out)
        return True
    except: return False

# ─── Мемы ─────────────────────────────────────────────────────────────────────
def make_imgflip_meme(template_id, texts):
    params = {"template_id":template_id,"username":IMGFLIP_USER,"password":IMGFLIP_PASS}
    for i,t in enumerate(texts): params[f"boxes[{i}][text]"] = t[:100]
    try:
        r = requests.post("https://api.imgflip.com/caption_image", data=params, timeout=15).json()
        if r.get("success") and r.get("data",{}).get("url"): return r["data"]["url"]
    except: pass
    return None

def send_template_meme(bot_instance, chat_id, reply_to=None):
    tid = random.choice(IMGFLIP_TEMPLATES)
    texts = [absurd_word_salad(chat_id, length=random.randint(2,5)) for _ in range(random.randint(2,3))]
    url = make_imgflip_meme(tid, texts)
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
            tx = 6 + (tw - (bbox[2]-bbox[0]+6)) // 2
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
    sticker_url = random.choice(STICKERS)
    try:
        sticker_data = requests.get(sticker_url, timeout=10).content
        sticker = Image.open(io.BytesIO(sticker_data)).convert("RGBA")
        ss = min(w,h)//5; sticker = sticker.resize((ss,ss), Image.LANCZOS)
        img.paste(sticker, (random.randint(0,max(0,w-ss)), random.randint(0,max(0,h-ss))), sticker)
    except: pass
    out = io.BytesIO(); img.convert("RGB").save(out, format="JPEG"); out.seek(0)
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
_clear_confirm = {}

# ─── Приветствие при добавлении ──────────────────────────────────────────────
@bot.message_handler(content_types=["new_chat_members"])
def handle_new_member(message):
    for member in message.new_chat_members:
        if member.username == bot.get_me().username:
            bot.send_message(message.chat.id, "👋 <b>Привет, хомяк, с тобой земляк!</b>", parse_mode="HTML")

# ─── Главное меню ────────────────────────────────────────────────────────────
def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("😂 Развлечения", callback_data="menu_fun"),
        InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")
    )
    markup.add(
        InlineKeyboardButton("🤖 ИИ ответ", callback_data="menu_ask"),
        InlineKeyboardButton("🗑 Очистить", callback_data="menu_clear")
    )
    return markup

def fun_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🖼 Мем", callback_data="meme"),
        InlineKeyboardButton("😔 Демотиватор", callback_data="dem")
    )
    markup.add(
        InlineKeyboardButton("🎭 Стикер", callback_data="stick"),
        InlineKeyboardButton("🎬 Гифка", callback_data="gif")
    )
    markup.add(
        InlineKeyboardButton("💬 Микс", callback_data="mix"),
        InlineKeyboardButton("🎙 Голос", callback_data="voice")
    )
    markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_back"))
    return markup

def stats_menu(cid):
    lv = get_level(cid)
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("📊 Статы", callback_data="stats"),
        InlineKeyboardButton("⭐ Уровень", callback_data="level_menu")
    )
    markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_back"))
    return markup

def level_menu(cid):
    lv = get_level(cid)
    markup = InlineKeyboardMarkup(row_width=3)
    btns = []
    for i in [1,2,3]:
        label = f"{'✅ ' if i==lv else ''}{i} ({ {1:'молчун',2:'редко',3:'часто'}[i]})"
        btns.append(InlineKeyboardButton(label, callback_data=f"setlevel_{i}"))
    markup.add(*btns)
    markup.add(InlineKeyboardButton("⬅ Назад", callback_data="menu_stats"))
    return markup

@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.send_message(message.chat.id, "🎭 <b>Лолыч:</b>\nВыбери что хочешь:", reply_markup=main_menu(), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    bot.answer_callback_query(call.id)
    cid = call.message.chat.id
    
    # Навигация
    if call.data == "menu_back":
        bot.edit_message_text("🎭 <b>Лолыч:</b>\nВыбери что хочешь:", cid, call.message.message_id, reply_markup=main_menu(), parse_mode="HTML")
        return
    elif call.data == "menu_fun":
        bot.edit_message_text("😂 <b>Развлечения:</b>", cid, call.message.message_id, reply_markup=fun_menu(), parse_mode="HTML")
        return
    elif call.data == "menu_stats":
        bot.edit_message_text("📊 <b>Статистика:</b>", cid, call.message.message_id, reply_markup=stats_menu(cid), parse_mode="HTML")
        return
    elif call.data == "level_menu":
        bot.edit_message_text("⭐ <b>Выбери уровень:</b>", cid, call.message.message_id, reply_markup=level_menu(cid), parse_mode="HTML")
        return
    elif call.data == "menu_ask":
        bot.send_message(cid, "Напиши /ask и свой вопрос")
        return
    elif call.data == "menu_clear":
        _clear_confirm[cid] = True
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Да, удалить", callback_data="clear_yes"), InlineKeyboardButton("❌ Отмена", callback_data="menu_back"))
        bot.edit_message_text("⚠️ <b>Удалить всю память чата?</b>", cid, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        return
    elif call.data == "clear_yes":
        if cid in _clear_confirm and _clear_confirm[cid]:
            global _markov_models, _markov_dirty
            for k in ["messages","users","photos","counter"]:
                p = _chat_file(cid, f"{k}.json")
                if os.path.exists(p): os.remove(p)
            for p in ["messages","users","photos","counter"]:
                if f"{cid}_{p}" in _cache: del _cache[f"{cid}_{p}"]
            if cid in _markov_models: del _markov_models[cid]
            if cid in _markov_dirty: _markov_dirty[cid] = True
            _clear_confirm[cid] = False
            bot.edit_message_text("🧹 <b>Память очищена!</b>", cid, call.message.message_id, parse_mode="HTML")
        return
    elif call.data.startswith("setlevel_"):
        lv = int(call.data.split("_")[1])
        s = get_settings(cid); s["level"] = lv; save_settings(cid)
        bot.edit_message_text(f"⭐ <b>Уровень: {lv}</b> ({ {1:'молчун',2:'редко',3:'часто'}[lv]})", cid, call.message.message_id, reply_markup=level_menu(cid), parse_mode="HTML")
        return
    
    # Действия
    if call.data == "meme":
        if not send_template_meme(bot, cid): bot.send_message(cid, "не смог")
    elif call.data == "dem":
        if not send_random_dem(bot, cid): bot.send_message(cid, "нет фото")
    elif call.data == "mix":
        bot.send_message(cid, mix_messages(cid))
    elif call.data == "voice":
        v = generate_voice(absurd_word_salad(cid))
        if v: bot.send_voice(cid, v)
        else: bot.send_message(cid, "не смог")
    elif call.data == "stick":
        if not send_sticker_photo(bot, cid): bot.send_message(cid, "нет фото")
    elif call.data == "gif":
        gif_url = get_random_gif()
        if gif_url: bot.send_document(cid, gif_url)
        else: bot.send_message(cid, "не нашёл гифку")
    elif call.data == "stats":
        msgs=_load(cid,"messages"); users=_load(cid,"users"); photos=_load(cid,"photos")
        s=get_settings(cid)
        bot.send_message(cid, f"📊 *Хранилище:*\n• Сообщений: {len(msgs)}/{LIMITS['messages']}\n• Участников: {len(users)}\n• Фото: {len(photos)}/{LIMITS['photos']}\n• Уровень: {s.get('level',1)} ({ {1:'молчун',2:'редко',3:'часто'}[s.get('level',1)]})\n• {'🔇 тишина' if s.get('muted') else '🔈 активен'}", parse_mode="Markdown")

# ─── Обычные команды ─────────────────────────────────────────────────────────
@bot.message_handler(commands=["level"])
def cmd_level(message):
    lv = get_level(message.chat.id)
    bot.reply_to(message, f"Уровень: {lv}\n/level 1-3 чтобы изменить")

@bot.message_handler(commands=["mute"])
def cmd_mute(message):
    s=get_settings(message.chat.id); s["muted"]=True; save_settings(message.chat.id)
    bot.reply_to(message, "🔇 /unmute чтобы включить")

@bot.message_handler(commands=["unmute"])
def cmd_unmute(message):
    s=get_settings(message.chat.id); s["muted"]=False; save_settings(message.chat.id)
    bot.reply_to(message, "🔈 Проснулся!")

@bot.message_handler(commands=["gif","гиф"])
def cmd_gif(m):
    gif_url = get_random_gif()
    if gif_url: bot.send_document(m.chat.id, gif_url)
    else: bot.reply_to(m, "не нашёл гифку")

@bot.message_handler(commands=["ask","спроси"])
def cmd_ask(m):
    question = m.text.split(maxsplit=1)
    if len(question) < 2: bot.reply_to(m, "Напиши: /ask твой вопрос"); return
    bot.reply_to(m, "🤔 Дай подумать...")
    answer = ask_ai(question[1], m.chat.id)
    if answer: bot.send_message(m.chat.id, answer)
    else: bot.reply_to(m, "не смог ответить")

@bot.message_handler(commands=["clear","очистить"])
def cmd_clear(m):
    cid=m.chat.id; a=m.text.split()
    if len(a)>1 and a[1].lower()=="yes":
        if cid in _clear_confirm and _clear_confirm[cid]:
            global _markov_models, _markov_dirty
            for k in ["messages","users","photos","counter"]:
                p=_chat_file(cid,f"{k}.json")
                if os.path.exists(p): os.remove(p)
            for p in ["messages","users","photos","counter"]:
                if f"{cid}_{p}" in _cache: del _cache[f"{cid}_{p}"]
            if cid in _markov_models: del _markov_models[cid]
            if cid in _markov_dirty: _markov_dirty[cid]=True
            _clear_confirm[cid]=False
            bot.reply_to(m, "🧹 Очищено!"); return
        else: bot.reply_to(m, "Сначала /clear"); return
    _clear_confirm[cid]=True
    bot.reply_to(m, "⚠️ /clear yes для подтверждения")

# ─── Сообщения ────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message):
    if not message.text or message.text.startswith("/"): return
    cid=message.chat.id
    if is_muted(cid): return
    
    text=message.text; name=message.from_user.first_name or "Аноним"; uid=message.from_user.id
    add_message(cid, text); add_user_message(cid, uid, name, text)
    
    lv = get_level(cid); tr = LEVELS.get(lv, LEVELS[1]); extras = LEVEL_EXTRAS.get(lv, LEVEL_EXTRAS[1])
    c=get_counter(cid)
    for k in ["msgs","meme","voice","mat","dem","stick","gif"]: c[k]=c.get(k,0)+1
    
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
        bot.reply_to(message, absurd_word_salad(cid, clean)); return
    
    if has_mat(text):
        if random.random() < extras[0]: bot.reply_to(message, random.choice(MAT).upper()+"!"); return    
    if random.random() < DEEPSEEK_CHANCE:
        answer = ask_ai(text, cid)
        if answer: bot.reply_to(message, answer); return
    
    if c["mat"]>=tr[3]: c["mat"]=0; save_counter(cid); bot.reply_to(message, random.choice(MAT).upper()+"!"); return
    if c["voice"]>=tr[1]: c["voice"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_voice(bot,cid), daemon=True).start(); return
    if c["meme"]>=tr[0]: c["meme"]=0; save_counter(cid); threading.Thread(target=lambda: send_template_meme(bot,cid), daemon=True).start(); return
    if c["gif"]>=tr[5]:
        c["gif"]=0; save_counter(cid)
        threading.Thread(target=lambda: (lambda url: url and bot.send_document(cid, url))(get_random_gif()), daemon=True).start()
        return
    if c["dem"]>=tr[2] and get_photos(cid): c["dem"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_dem(bot,cid), daemon=True).start(); return
    if c["stick"]>=tr[4] and get_photos(cid): c["stick"]=0; save_counter(cid); threading.Thread(target=lambda: send_sticker_photo(bot,cid), daemon=True).start(); return
    save_counter(cid)
    
    if f"@{bot.get_me().username}" in text:
        bot.reply_to(message, absurd_word_salad(cid, text.replace(f"@{bot.get_me().username}","").strip())); return
    
    if random.random() < tr[6]:
        if random.random()<0.15: bot.reply_to(message, " ".join(random.choices(EMOJI, k=random.randint(1,3))))
        else: bot.reply_to(message, absurd_word_salad(cid, text))

# ─── Фото ─────────────────────────────────────────────────────────────────────
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    cid=message.chat.id
    if is_muted(cid): return
    fid=message.photo[-1].file_id
    add_photo(cid, fid)
    cap=(message.caption or "").lower()
    extras = LEVEL_EXTRAS.get(get_level(cid), LEVEL_EXTRAS[1])
    
    if any(w in cap for w in ["мем","meme"]):
        send_template_meme(bot, cid, message.message_id)
    elif any(w in cap for w in ["дем","dem"]):
        fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
        out=make_demotivator(dl, absurd_word_salad(cid, length=random.randint(3,8)))
        _my_photos.add(fid); bot.send_photo(cid, out)
    elif any(w in cap for w in ["стик","stick"]):
        fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
        out=make_sticker(dl); _my_photos.add(fid); bot.send_photo(cid, out)
    elif random.random() < extras[3]:
        bot.reply_to(message, random.choice([absurd_word_salad(cid, length=random.randint(1,10)), random.choice(EMOJI)*random.randint(1,2), "это чё такое?", "🤔"]))

log.info("Лолыч проснулся!")
bot.polling(none_stop=True)
