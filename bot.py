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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

TOKEN = "8464842453:AAE4QiUoCGhNdjNyCA3vRLMuloDOIinMPGc"

LIMITS = {"messages": 5000, "user_msgs": 700, "photos": 200}

# (стих, мем, войс, дем, мат, стик, random_chance)
LEVELS = {
    1: (2000, 2000, 2000, 3000, 1000, 2000, 0.005),
    2: (500, 500, 500, 800, 300, 500, 0.03),
    3: (100, 100, 100, 150, 80, 100, 0.30),
}

# (реакция_на_мат, мат_войс_каждые_N, кто_шанс, лолыч_шанс, фото_реакция)
LEVEL_EXTRAS = {
    1: (0.01, 30, 0.05, 0.30, 0.05),
    2: (0.03, 15, 0.20, 0.60, 0.15),
    3: (0.10, 5, 0.50, 1.00, 0.40),
}

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
    "https://i.postimg.cc/pTBnJJDZ/IMG-4790.png",
    "https://i.postimg.cc/wxf1xvFb/IMG-4791.png",
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

# ─── Файлы ────────────────────────────────────────────────────────────────────
def _chat_file(chat_id, name):
    return f"chat_{chat_id}_{name}"

_cache = {}
_my_photos = set()

def _load(chat_id, key):
    cache_key = f"{chat_id}_{key}"
    if cache_key in _cache: return _cache[cache_key]
    path = _chat_file(chat_id, f"{key}.json")
    if not os.path.exists(path):
        default = {} if key in ("users","counter","settings") else []
        if key == "counter": default = {"msgs":0,"meme":0,"voice":0,"mat":0,"mat_voice":0,"dem":0,"stick":0}
        if key == "settings": default = {"level":1,"muted":False}
        _cache[cache_key] = default
        return default
    with open(path, "r", encoding="utf-8") as f:
        _cache[cache_key] = json.load(f)
    return _cache[cache_key]

def _save(chat_id, key):
    path = _chat_file(chat_id, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_cache[f"{chat_id}_{key}"], f, ensure_ascii=False)

_markov_models = {}
_markov_dirty = {}

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

def remove_last_photo(chat_id):
    photos = _load(chat_id, "photos")
    if photos: photos.pop(); _save(chat_id, "photos"); return True
    return False

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

def send_mat_voice(bot_instance, chat_id, reply_to=None):
    text = " ".join(random.choices(MAT, k=random.randint(3,6))).upper()
    log.info(f"МАТ-ВОЙС: {text}")
    v = generate_voice(text)
    if v:
        try:
            if reply_to: bot_instance.send_voice(chat_id, v, reply_to_message_id=reply_to)
            else: bot_instance.send_voice(chat_id, v)
            log.info("МАТ-ВОЙС ОТПРАВЛЕН!")
            return True
        except Exception as e:
            log.error(f"МАТ-ВОЙС ОШИБКА: {e}")
    return False

# ─── Микс ─────────────────────────────────────────────────────────────────────
def mix_messages(chat_id):
    msgs = _load(chat_id, "messages")
    if len(msgs) < 2: return absurd_word_salad(chat_id)
    a, b = random.choice(msgs).split(), random.choice(msgs).split()
    if len(a)<2 or len(b)<2: return absurd_word_salad(chat_id)
    return " ".join(a[:len(a)//2] + b[len(b)//2:])

# ─── Стихи ────────────────────────────────────────────────────────────────────
RHYME_DICT = {
    "ать":["мать","спать","ждать","страдать"], "ить":["жить","любить","тупить","говорить"],
    "ой":["тобой","судьбой","головой","луной"], "ай":["давай","лентяй","урожай","сарай"],
    "еть":["сидеть","глядеть","хотеть","пиздеть"], "ок":["дружок","пирожок","прыжок","кружок"],
}

def find_rhyme(word):
    w = word.lower().strip(".,!?:;\"'()")
    for end, rhymes in RHYME_DICT.items():
        if w.endswith(end): return random.choice(rhymes)
    return None

def make_poem(chat_id):
    model = _get_markov_model(chat_id)
    words = _chat_words(chat_id)
    if not words: return absurd_word_salad(chat_id)
    lines = []
    for i in range(4):
        line = (model.make_short_sentence(50,tries=20) if model and random.random()<0.5 else " ".join(random.choices(words,k=random.randint(3,6))))
        if not line: continue
        wl = line.split()
        if len(wl)>6: line = " ".join(wl[:6])
        if i>=2 and len(lines)>=2:
            rhyme = find_rhyme(lines[i-2].split()[-1].strip(".,!?:;\"'()"))
            if rhyme: wl[-1]=rhyme; line=" ".join(wl)
        lines.append(line)
    return "\n".join(lines) if len(lines)>=2 else absurd_word_salad(chat_id)

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
        if reply_to: bot_instance.send_photo(chat_id, out, reply_to_message_id=reply_to)
        else: bot_instance.send_photo(chat_id, out)
        return True
    except: return False

# ─── Мемы imgflip ─────────────────────────────────────────────────────────────
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
            # Скачиваем мем
            img_data = requests.get(url, timeout=15).content
            img = Image.open(io.BytesIO(img_data)).convert("RGBA")
            draw = ImageDraw.Draw(img)
            
            # Водяной знак lolych в левом нижнем углу
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=14)
            except:
                font = ImageFont.load_default()
            
            # Белый фон под текстом
            text = "lolych"
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0] + 6, bbox[3] - bbox[1] + 4
            draw.rectangle([3, img.height - th - 3, 3 + tw, img.height - 3], fill=(255, 255, 255, 200))
            draw.text((6, img.height - th - 1), text, font=font, fill=(0, 0, 0))
            
            # Отправляем
            out = io.BytesIO()
            img.convert("RGB").save(out, format="JPEG")
            out.seek(0)
            if reply_to: bot_instance.send_photo(chat_id, out, reply_to_message_id=reply_to)
            else: bot_instance.send_photo(chat_id, out)
            return True
        except Exception as e:
            log.error(f"send_template_meme error: {e}")
    return False
# ─── Стикеры ──────────────────────────────────────────────────────────────────
def make_sticker(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    w, h = img.size
    sticker_url = random.choice(STICKERS)
    try:
        sticker_data = requests.get(sticker_url, timeout=10).content
        sticker = Image.open(io.BytesIO(sticker_data)).convert("RGBA")
        ss = min(w, h) // 5
        sticker = sticker.resize((ss, ss), Image.LANCZOS)
        x = random.randint(0, max(0, w - ss))
        y = random.randint(0, max(0, h - ss))
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
def has_mat(text): return any(m in text.lower() for m in MAT)
def get_random_user(chat_id):
    u = get_users(chat_id)
    return random.choice(list(u.values()))["name"] if u else None

# ─── Бот ──────────────────────────────────────────────────────────────────────
bot = telebot.TeleBot(TOKEN)
_clear_confirm = {}

@bot.message_handler(commands=["start","help"])
def cmd_start(message):
    bot.reply_to(message, """🎭 *Лолыч:*
/mix • /poem • /meme • /dem • /stick • /voice
/stats • /level 1-3 • /mute • /unmute • /forget • /clear""", parse_mode="Markdown")

@bot.message_handler(commands=["level"])
def cmd_level(message):
    a = message.text.split()
    if len(a)<2: bot.reply_to(message, f"Уровень: {get_level(message.chat.id)}\n/level 1-3"); return
    try:
        lv = int(a[1])
        if lv<1 or lv>3: raise ValueError
        s = get_settings(message.chat.id); s["level"]=lv; save_settings(message.chat.id)
        bot.reply_to(message, f"Уровень: {lv} ({ {1:'молчун',2:'редко',3:'часто'}[lv]})")
    except: bot.reply_to(message, "/level 1, 2 или 3")

@bot.message_handler(commands=["mute"])
def cmd_mute(message):
    s=get_settings(message.chat.id); s["muted"]=True; save_settings(message.chat.id)
    bot.reply_to(message, "🔇 /unmute чтобы включить")

@bot.message_handler(commands=["unmute"])
def cmd_unmute(message):
    s=get_settings(message.chat.id); s["muted"]=False; save_settings(message.chat.id)
    bot.reply_to(message, "🔈 Проснулся!")

@bot.message_handler(commands=["mix"])
def cmd_mix(m): bot.send_message(m.chat.id, mix_messages(m.chat.id))

@bot.message_handler(commands=["poem","стих"])
def cmd_poem(m): bot.send_message(m.chat.id, f"🎭\n{make_poem(m.chat.id)}")

@bot.message_handler(commands=["meme","мем"])
def cmd_meme(m):
    if not send_template_meme(bot, m.chat.id): bot.reply_to(m, "не смог")

@bot.message_handler(commands=["dem","дем"])
def cmd_dem(m):
    a = m.text.split(maxsplit=1); txt = a[1] if len(a)>1 else None
    if m.reply_to_message and m.reply_to_message.photo:
        fid=m.reply_to_message.photo[-1].file_id
        try:
            fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
            bot.send_photo(m.chat.id, make_demotivator(dl, txt or absurd_word_salad(m.chat.id, length=random.randint(3,8))))
        except: bot.reply_to(m, "не смог")
    elif not send_random_dem(bot, m.chat.id, custom_text=txt): bot.reply_to(m, "нет фото")

@bot.message_handler(commands=["stick","стик"])
def cmd_stick(m):
    if m.reply_to_message and m.reply_to_message.photo:
        fid=m.reply_to_message.photo[-1].file_id
        try:
            fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
            bot.send_photo(m.chat.id, make_sticker(dl))
        except: bot.reply_to(m, "не смог")
    elif not send_sticker_photo(bot, m.chat.id): bot.reply_to(m, "нет фото")

@bot.message_handler(commands=["voice","войс"])
def cmd_voice(m):
    v=generate_voice(absurd_word_salad(m.chat.id))
    if v: bot.send_voice(m.chat.id, v)
    else: bot.reply_to(m, "не смог")

@bot.message_handler(commands=["stats","стат"])
def cmd_stats(m):
    cid=m.chat.id; msgs=_load(cid,"messages"); users=_load(cid,"users"); photos=_load(cid,"photos")
    s=get_settings(cid)
    bot.reply_to(m, f"📊 *Хранилище:*\n• Сообщений: {len(msgs)}/{LIMITS['messages']}\n• Участников: {len(users)}\n• Фото: {len(photos)}/{LIMITS['photos']}\n• Уровень: {s.get('level',1)} ({ {1:'молчун',2:'редко',3:'часто'}[s.get('level',1)]})\n• {'🔇 тишина' if s.get('muted') else '🔈 активен'}", parse_mode="Markdown")

@bot.message_handler(commands=["forget"])
def cmd_forget(m):
    bot.reply_to(m, "🗑 Удалено" if remove_last_photo(m.chat.id) else "Нет фото")

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
    
    lv = get_level(cid)
    tr = LEVELS.get(lv, LEVELS[1])
    extras = LEVEL_EXTRAS.get(lv, LEVEL_EXTRAS[1])
    
    c=get_counter(cid)
    for k in ["msgs","meme","voice","mat","dem","stick"]: c[k]=c.get(k,0)+1
    
    # «Кто»
    if "кто" in text.lower().split() and random.random() < extras[2]:
        u=get_random_user(cid)
        if u: bot.reply_to(message, random.choice(KTO_ANSWERS).format(user=u)); return
    
    # «лолыч»
    if any(w in text.lower() for w in ["лолыч","лолич"]) and random.random() < extras[3]:
        clean=text.lower()
        for w in ["лолыч","лолич"]: clean=clean.replace(w,"").strip()
        bot.reply_to(message, absurd_word_salad(cid, clean)); return
    
    # Мат
    if has_mat(text):
        c["mat_voice"]=c.get("mat_voice",0)+1
        log.info(f"МАТ #{c['mat_voice']} от {name}, нужно {extras[1]} для войса")
        if c["mat_voice"] >= extras[1]:
            log.info("ЗАПУСК МАТ-ВОЙСА!")
            c["mat_voice"]=0; save_counter(cid)
            threading.Thread(target=lambda: send_mat_voice(bot,cid,message.message_id), daemon=True).start(); return
        if random.random() < extras[0]:
            bot.reply_to(message, random.choice(MAT).upper()+"!"); return
    
    # Авто-триггеры
    if c["mat"]>=tr[4]: c["mat"]=0; save_counter(cid); bot.reply_to(message, random.choice(MAT).upper()+"!"); return
    if c["voice"]>=tr[2]: c["voice"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_voice(bot,cid), daemon=True).start(); return
    if c["msgs"]>=tr[0]: c["msgs"]=0; save_counter(cid); threading.Thread(target=lambda: bot.send_message(cid, f"🎭\n{make_poem(cid)}"), daemon=True).start(); return
    if c["meme"]>=tr[1]: c["meme"]=0; save_counter(cid); threading.Thread(target=lambda: send_template_meme(bot,cid), daemon=True).start(); return
    if c["dem"]>=tr[3] and get_photos(cid): c["dem"]=0; save_counter(cid); threading.Thread(target=lambda: send_random_dem(bot,cid), daemon=True).start(); return
    if c["stick"]>=tr[5] and get_photos(cid): c["stick"]=0; save_counter(cid); threading.Thread(target=lambda: send_sticker_photo(bot,cid), daemon=True).start(); return
    save_counter(cid)
    
    # @упоминание
    if f"@{bot.get_me().username}" in text:
        bot.reply_to(message, absurd_word_salad(cid, text.replace(f"@{bot.get_me().username}","").strip())); return
    
    # Случайный ответ
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
    
    if any(w in cap for w in ["мем","meme"]): send_template_meme(bot, cid, message.message_id)
    elif any(w in cap for w in ["дем","dem"]):
        fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
        bot.send_photo(cid, make_demotivator(dl, absurd_word_salad(cid, length=random.randint(3,8))))
    elif any(w in cap for w in ["стик","stick"]):
        fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
        bot.send_photo(cid, make_sticker(dl))
    elif random.random() < extras[4]:
        bot.reply_to(message, random.choice([absurd_word_salad(cid, length=random.randint(1,10)), random.choice(EMOJI)*random.randint(1,2), "это чё такое?", "🤔"]))

# ─── Запуск ────────────────────────────────────────────────────────────────────
log.info("Лолыч проснулся!")
bot.polling(none_stop=True)
