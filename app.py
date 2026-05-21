import telebot
from telebot import types
import sqlite3
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
import random
from collections import defaultdict

API_TOKEN = 'your_bot_api_token'
DB_PATH = "anxiety_bot.db"

bot = telebot.TeleBot(API_TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        biweekly_opt_in INTEGER DEFAULT 0
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS diary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        day DATE,
        anxious INTEGER,
        note TEXT,
        UNIQUE(user_id, day)
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS reminders (
        user_id INTEGER PRIMARY KEY,
        interval_hours INTEGER,
        times TEXT
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp DATETIME,
        score INTEGER,
        type TEXT
    )''')
    conn.commit()
    conn.close()

def db_execute(query, params=(), fetch=False, many=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if many:
        c.executemany(query, params)
        conn.commit()
        conn.close()
        return None
    c.execute(query, params)
    if fetch:
        rows = c.fetchall()
        conn.commit()
        conn.close()
        return rows
    conn.commit()
    conn.close()
    return None

def ensure_user(user):
    db_execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
        (user.id, user.username, user.first_name, user.last_name)
    )

def show_main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('/help', '/methods', '/sos')
    kb.row('/diary', '/reminders')
    kb.row('/test')
    bot.send_message(chat_id, "Главное меню:", reply_markup=kb)

@bot.message_handler(commands=['start'])
def handle_start(msg):
    ensure_user(msg.from_user)
    text = (
        "Привет🌸 Этот бот создан, чтобы помочь тебе начать пользоваться методами самопомощи для избавления от тревоги чаще. Это очень важно, ведь это состояние может быть очень тяжелым, а бездействие сделает только хуже. Нажми /help, чтобы узнать про функции :3"
    )
    bot.send_message(msg.chat.id, text)
    show_main_menu(msg.chat.id)

@bot.message_handler(commands=['help'])
def handle_help(msg):
    text = (
        "/methods - случайный метод самопомощи\n"
        "/sos - экстренная помощь\n"
        "/diary - дневник тревожности\n"
        "/reminders - настройки напоминаний\n"
        "/test - тест Спилбергера-Ханина на выявление ситуативной и личностной тревоги"
    )
    bot.send_message(msg.chat.id, text)

@bot.message_handler(commands=['methods'])
def handle_methods(msg):
    random_method = random.choice(HELP_METHODS)
    text = f"Попробуй это:\n\n{random_method}\n\n Нажми /methods для нового!!"
    bot.send_message(msg.chat.id, text)

@bot.message_handler(commands=['sos'])
def handle_sos(msg):
    text = (
        "1. Встряхнитесь. Если дрожите - усильте тремор, похлопайте себя по плечам\n"
        "2. «Заземлитесь». Сосредоточьтесь на свои ощущениях. Замедлите темп и дыхание\n"
        "3. Медленно прижмите ноги к полу, вытяните руки и сомкните ладони\n"
        "4. Назовите 5 предметов, которые видите, 4 звука, которые слышите, запахи\n"
        "5. Дотроньтесь до колена или любого предмета\n"
        "6. Обратите внимание на то, что вы чувствуете пальцами"
    )
    text2 = ("У вас есть свои мысли и чувства и окружающий мир, который можете почувствовать. Вы можете двигаться и если захотите - действовать. Если вы в опасности или планируете причинить вред себе - немедленно обратитесь в экстренные службы. Если нужна срочная психологическая помощь, обратитесь на местную горячую линию кризисной помощи‼️")
    bot.send_message(msg.chat.id, text)
    bot.send_message(msg.chat.id, text2)

STAI_QUESTIONS = statements_list = [
    'Я спокоен \n ❗️первые 20 вопросов про состояние на данный момент❗️',
    'Мне ничто не угрожает',
    'Я нахожусь в напряжении',
    'Я испытываю сожаление',
    'Я чувствую себя свободно',
    'Я расстроен',
    'Меня волнуют возможные неудачи',
    'Я чувствую себя отдохнувшим',
    'Я не доволен собой',
    'Я испытываю чувство внутреннего удовлетворения',
    'Я уверен в себе',
    'Я нервничаю',
    'Я не нахожу себе места',
    'Я взвинчен',
    'Я не чувствую скованности, напряженности',
    'Я доволен',
    'Я озабочен',
    'Я слишком возбужден, и мне не по себе',
    'Мне радостно',
    'Мне приятно \n ❗️следующие вопросы будут про обычное среднее состояние, не в конкретный момент❗️ \n',
    'Я испытываю удовольствие',
    'Я очень легко устаю',
    'Я легко могу заплакать',
    'Я хотел бы быть таким же счастливым, как другие люди',
    'Нередко я проигрываю из-за того что недостаточно быстро принимаю решения',
    'Обычно я чувствую себя бодрым',
    'Я спокоен, хладнокровен и собран',
    'Ожидаемые трудности обычно очень беспокоят меня',
    'Я слишком переживаю из-за пустяков',
    'Я вполне счастлив',
    'Я принимаю все близко к сердцу',
    'Мне не хватает уверенности в себе',
    'Обычно я чувствую себя в безопасности',
    'Я стараюсь избегать критических ситуаций и трудностей',
    'У меня бывает хандра',
    'Я доволен',
    'Всякие пустяки отвлекают и волнуют меня',
    'Я так сильно переживаю свои разочарования, что потом долго не могу забыть о них',
    'Я уравновешенный человек',
    'Меня охватывает сильное беспокойство, когда я думаю о своих делах и заботах'
]


STATE_INVERT = {1, 2, 5, 8, 10, 11, 15, 16, 19, 20}
TRAIT_INVERT = {21, 26, 27, 30, 33, 36, 39}
user_test_sessions = {}

@bot.message_handler(commands=['test'])
def start_test(msg):
    ensure_user(msg.from_user)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('Пройти тест сейчас', 'История тестов')
    kb.row('Главное меню')
    bot.send_message(msg.chat.id, "Тест Спилбергера-Ханина - возможность узнать об общем состоянии своей тревожности всего за 40 вопросов", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Пройти тест сейчас')
def handle_start_test(m):
    user = m.from_user
    ensure_user(user)
    user_test_sessions[user.id] = {"index": 0, "answers": []}
    send_next_test_question(user.id, m.chat.id)

@bot.message_handler(func=lambda m: m.text == 'История тестов')
def handle_test_stats(m):
    user = m.from_user
    ensure_user(user)
    rows = db_execute("SELECT timestamp, score, type FROM tests WHERE user_id = ? ORDER BY timestamp ASC", (user.id,), fetch=True)
    if not rows:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В тест', 'Главное меню')
        bot.send_message(m.chat.id, "История тестов пуста;(", reply_markup=kb)
        return
    
    grouped = defaultdict(dict)
    for ts, score, typ in rows:
        grouped[ts][typ] = score
    items = sorted(grouped.items(), key=lambda x: x[0])
    text = "История тестов:\n"
    for ts, parts in items:
        dt = datetime.fromisoformat(ts)
        s_state = parts.get('state', '-')
        s_trait = parts.get('trait', '-')
        s_total = parts.get('total', '-')
        text += f"{dt.date().isoformat()}: Ситуативная тревожность={s_state} Личностная={s_trait}\n"
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В тест', 'Главное меню')
    bot.send_message(m.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'В тест')
def back_to_test(m):
    start_test(m)

def send_next_test_question(user_id, chat_id):
    session = user_test_sessions.get(user_id)
    if session is None:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В тест', 'Главное меню')
        bot.send_message(chat_id, "Сессия теста не найдена. Нажмите 'Пройти тест сейчас'.", reply_markup=kb)
        return
    idx = session["index"]
    if idx >= len(STAI_QUESTIONS):
        finalize_test(user_id, chat_id)
        return
    q = STAI_QUESTIONS[idx]
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('1', '2', '3', '4')
    kb.row('Прервать тест')
    if idx == 0:
        bot.send_message(chat_id, "Отвечайте честно. Шкала: 1 - совсем нет, 2 - немного, 3 - довольно сильно, 4 - очень сильно. Первые 20 вопросов про состояние на данный момент, оставшиеся 20 про обычное среднее состояние", reply_markup=kb)
    bot.send_message(chat_id, f"{idx+1}. {q}", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ['1','2','3','4','Прервать тест'])
def handle_test_answer(m):
    user = m.from_user
    if user.id not in user_test_sessions:
        return
    if m.text == 'Прервать тест':
        user_test_sessions.pop(user.id, None)
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В тест', 'Главное меню')
        bot.send_message(m.chat.id, "Тест прерван", reply_markup=kb)
        return
    try:
        val = int(m.text)
    except:
        bot.send_message(m.chat.id, "Выберите 1–4")
        return
    session = user_test_sessions[user.id]
    session['answers'].append(val)
    session['index'] += 1
    send_next_test_question(user.id, m.chat.id)

def finalize_test(user_id, chat_id):
    session = user_test_sessions.pop(user_id, None)
    if not session or len(session['answers']) < 40:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В тест', 'Главное меню')
        bot.send_message(chat_id, "Тест не завершен полностью", reply_markup=kb)
        return
    
    answers = session['answers']
    state_scores = 50
    trait_scores = 35
    
    for i in range(20):
        a = answers[i]
        if i+1 in STATE_INVERT:
            state_scores -= a
        else:
            state_scores +=a
    
    for i in range(20, 40):
        a = answers[i]
        if i+1 in TRAIT_INVERT:
            trait_scores -= a
        else:
            trait_scores += a
    
    ts = datetime.utcnow().isoformat()
    
    db_execute("INSERT INTO tests (user_id, timestamp, score, type) VALUES (?, ?, ?, ?)",
               (user_id, ts, state_scores, 'state'))
    db_execute("INSERT INTO tests (user_id, timestamp, score, type) VALUES (?, ?, ?, ?)",
               (user_id, ts, trait_scores, 'trait'))
    
    text = (f"Ура, тест завершен\n\n"
            f"Ситуативная тревога (сейчас): {state_scores}\n"
            f"Личностная тревога (обычно): {trait_scores}\n"
            f"Чем выше балл - тем выше тревожность. \nИнтерпретация (типы по отдельности):\n до 30 - низкая тревожность;\n 31-45 - умеренная тревожность;\n 46 и более - высокая тревожность.")
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В тест', 'Главное меню')
    bot.send_message(chat_id, text, reply_markup=kb)

@bot.message_handler(commands=['diary'])
def handle_diary(msg):
    ensure_user(msg.from_user)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('Сегодня было тревожно', 'Тревоги не было')
    kb.row('Добавить заметку', 'Посмотреть запись за дату')
    kb.row('Статистика дневника', 'Главное меню')
    bot.send_message(msg.chat.id, "Дневник тревожности:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Статистика дневника')
def handle_diary_stats(m):
    user = m.from_user
    ensure_user(user)
    rows = db_execute("SELECT COUNT(*) FROM diary WHERE user_id = ? AND anxious = 1", (user.id,), fetch=True)
    anxious_count = rows[0][0]
    rows = db_execute("SELECT COUNT(*) FROM diary WHERE user_id = ?", (user.id,), fetch=True)
    total = rows[0][0]
    non_anxious = total - anxious_count
    text = f"Статистика дневника:\nВсего записей: {total}\nТревожных дней: {anxious_count}\nДней без тревоги: {non_anxious}\n"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В дневник', 'Главное меню')
    bot.send_message(m.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'В дневник')
def back_to_diary(m):
    handle_diary(m)

@bot.message_handler(func=lambda m: m.text in ['Сегодня было тревожно', 'Тревоги не было'])
def handle_diary_mark(m):
    user = m.from_user
    ensure_user(user)
    if m.text == 'Сегодня было тревожно':
        is_anxious = 1
    if m.text == 'Тревоги не было':
        is_anxious = 0
    today = date.today().isoformat()
    try:
        db_execute("INSERT OR REPLACE INTO diary (user_id, day, anxious, note) VALUES (?, ?, ?, COALESCE((SELECT note FROM diary WHERE user_id=? AND day=?), ''))",
                   (user.id, today, is_anxious, user.id, today))
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В дневник', 'Главное меню')
        bot.send_message(m.chat.id, "Запись сохранена!", reply_markup=kb)
    except Exception as e:
        logging.exception("Ошибка сохранения записи в дневник для user_id=%s, day=%s: %s", user.id, today, e)
        bot.send_message(m.chat.id, "Ошибка сохранения")

@bot.message_handler(func=lambda m: m.text == 'Добавить заметку')
def handle_diary_note(m):
    msg = bot.send_message(m.chat.id, "Напиши заметку:")
    bot.register_next_step_handler(msg, save_diary_note)

def save_diary_note(m):
    user = m.from_user
    ensure_user(user)
    if not m.text:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В дневник', 'Главное меню')
        bot.send_message(m.chat.id, "Заметка должна быть текстом. Попробуйте ещё раз.", reply_markup=kb)
        return
    text = m.text.strip()
    today = date.today().isoformat()
    db_execute("INSERT OR IGNORE INTO diary(user_id, day, anxious, note) VALUES (?, ?, ?, '')", (user.id, today, 0))
    db_execute("UPDATE diary SET note = ? WHERE user_id = ? AND day = ?", (text, user.id, today))
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В дневник', 'Главное меню')
    bot.send_message(m.chat.id, "Заметка добавлена!", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Посмотреть запись за дату')
def handle_view_date(m):
    msg = bot.send_message(m.chat.id, "Дата (ГГГГ-ММ-ДД):")
    bot.register_next_step_handler(msg, show_entry_for_date)

def show_entry_for_date(m):
    user = m.from_user
    dstr = m.text.strip()
    try:
        dt = datetime.fromisoformat(dstr)
        ds = dt.date().isoformat()
    except:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В дневник', 'Главное меню')
        bot.send_message(m.chat.id, "Неверный формат", reply_markup=kb)
        return
    rows = db_execute("SELECT anxious, note FROM diary WHERE user_id = ? AND day = ?", (user.id, ds), fetch=True)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В дневник', 'Главное меню')
    if not rows:
        bot.send_message(m.chat.id, "Запись не найдена ;(", reply_markup=kb)
    else:
        anxious, note = rows[0]
        text = f"{ds}\nТревога: {'Да' if anxious else 'Нет'}\nЗаметка: {note or '-'}"
        bot.send_message(m.chat.id, text, reply_markup=kb)

@bot.message_handler(commands=['reminders'])
def handle_reminders(msg):
    ensure_user(msg.from_user)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('Установить интервал (в часах)', 'Установить время напоминаний')
    kb.row('Выключить напоминания', 'Показать текущие настройки')
    kb.row('Напоминания о тесте (раз в 2 недели)', 'Главное меню')
    bot.send_message(msg.chat.id, "Настройки напоминаний:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Напоминания о тесте (раз в 2 недели)')
def handle_biweekly_settings(m):
    user = m.from_user
    rows = db_execute("SELECT biweekly_opt_in FROM users WHERE user_id = ?", (user.id,), fetch=True)
    is_enabled = rows[0][0] if rows else 0
    status = "включены" if is_enabled else "отключены"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('Включить' if not is_enabled else 'Отключить')
    kb.row('В напоминания', 'Главное меню')
    bot.send_message(m.chat.id, f"Напоминания о тесте (раз в 2 недели) ({status}):", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ['Включить', 'Отключить'])
def toggle_biweekly(m):
    user = m.from_user
    ensure_user(user)
    new_state = 1 if 'Включить' in m.text else 0
    action = "включены" if new_state else "отключены"
    db_execute("UPDATE users SET biweekly_opt_in = ? WHERE user_id = ?", (new_state, user.id))
    if new_state:
        schedule_biweekly_for_user(user.id)
    else:
        try:
            scheduler.remove_job(f"biweekly_{user.id}")
        except Exception:
            pass
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В напоминания', 'Главное меню')
    bot.send_message(m.chat.id, f"Напоминания о тесте {action}!", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'В напоминания')
def back_to_reminders(m):
    handle_reminders(m)

@bot.message_handler(func=lambda m: m.text == 'Установить интервал (в часах)')
def ask_interval(m):
    msg = bot.send_message(m.chat.id, "Интервал в часах (например: 4):")
    bot.register_next_step_handler(msg, set_interval)

def set_interval(m):
    user = m.from_user
    try:
        hours = int(m.text.strip())
        if hours <= 0: raise ValueError()
    except:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В напоминания', 'Главное меню')
        bot.send_message(m.chat.id, "Введите число больше 0", reply_markup=kb)
        return
    prev = db_execute("SELECT times FROM reminders WHERE user_id = ?", (user.id,), fetch=True)
    times = prev[0][0] if prev and prev[0][0] else ""
    db_execute("INSERT OR REPLACE INTO reminders (user_id, interval_hours, times) VALUES (?, ?, ?)",
               (user.id, hours, times))
    schedule_user_reminders(user.id)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В напоминания', 'Главное меню')
    bot.send_message(m.chat.id, f"Напоминания каждые {hours} часов", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Установить время напоминаний')
def ask_times(m):
    text = "Время через запятую (HH:MM):\nнапример: 09:00,15:30,21:00"
    msg = bot.send_message(m.chat.id, text)
    bot.register_next_step_handler(msg, set_times)

def set_times(m):
    user = m.from_user
    raw = m.text.strip()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    try:
        for p in parts:
            hh, mm = map(int, p.split(":"))
            assert 0 <= hh < 24 and 0 <= mm < 60
    except Exception:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.row('В напоминания', 'Главное меню')
        bot.send_message(m.chat.id, "Неверный формат (HH:MM)", reply_markup=kb)
        return
    prev = db_execute("SELECT interval_hours FROM reminders WHERE user_id = ?", (user.id,), fetch=True)
    interval = prev[0][0] if prev and prev[0][0] is not None else 0
    times_joined = ",".join(parts)
    db_execute("INSERT OR REPLACE INTO reminders (user_id, interval_hours, times) VALUES (?, ?, ?)",
               (user.id, interval, times_joined))
    schedule_user_reminders(user.id)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В напоминания', 'Главное меню')
    bot.send_message(m.chat.id, f"Напоминания в: {times_joined}", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Выключить напоминания')
def disable_reminders(m):
    user = m.from_user
    db_execute("DELETE FROM reminders WHERE user_id = ?", (user.id,))
    base = f"reminder_{user.id}"
    for job in scheduler.get_jobs():
        if job.id.startswith(base):
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В напоминания', 'Главное меню')
    bot.send_message(m.chat.id, "Напоминания отключены.", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Показать текущие настройки')
def show_reminders(m):
    user = m.from_user
    rows = db_execute("SELECT interval_hours, times FROM reminders WHERE user_id = ?", (user.id,), fetch=True)
    if not rows:
        text = "Напоминания не настроены."
    else:
        interval, times = rows[0]
        text = "Текущие настройки:\n"
        if interval:
            text += f"Интервал: каждые {interval} ч\n"
        if times:
            text += f"Время: {times}\n"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row('В напоминания', 'Главное меню')
    bot.send_message(m.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == 'Главное меню')
def menu_button(m):
    show_main_menu(m.chat.id)

def schedule_user_reminders(user_id):
    rows = db_execute("SELECT interval_hours, times FROM reminders WHERE user_id = ?",
                      (user_id,), fetch=True)
    if not rows:
        return
    interval_hours, times_str = rows[0]
    job_id_base = f"reminder_{user_id}"
    for job in scheduler.get_jobs():
        if job.id.startswith(job_id_base):
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass
    if interval_hours and interval_hours > 0:
        scheduler.add_job(send_reminder_to_user, IntervalTrigger(hours=interval_hours), 
                         args=(user_id,), id=f"{job_id_base}_interval", replace_existing=True)
    if times_str:
        times = [t.strip() for t in times_str.split(",") if t.strip()]
        for i, t in enumerate(times):
            try:
                hh, mm = map(int, t.split(":"))
                scheduler.add_job(send_reminder_to_user, CronTrigger(hour=hh, minute=mm),
                                args=(user_id,), id=f"{job_id_base}_time_{i}", replace_existing=True)
            except Exception as e:
                logging.exception("Не удалось запланировать напоминание по времени %r для пользователя %s: %s", t, user_id, e)

def send_reminder_to_user(user_id):
    try:
        text = (
            "Напоминание: маленькая помощь при тревоге.\n\n"
            "• дыхание по квадрату\n"
            "• 5-4-3-2-1 техника\n"
            "• подержи запястья под холодной водой\n\n"
            "Если нужно - жми /sos"
        )
        bot.send_message(user_id, text)
    except Exception as e:
        logging.exception("Не удалось отправить напоминание пользователю %s: %s", user_id, e)

def schedule_biweekly_for_user(user_id):
    job_id = f"biweekly_{user_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    scheduler.add_job(send_biweekly_prompt, IntervalTrigger(days=14), 
                     args=(user_id,), id=job_id, replace_existing=True)

def send_biweekly_prompt(user_id):
    try:
        bot.send_message(user_id, "Прошло 2 недели. Пройти тест Спилберга-Ханина? /test")
    except Exception as e:
        logging.exception("Не удалось отправить двухнедельное напоминание пользователю %s: %s", user_id, e)

def load_schedules_from_db():
    rows = db_execute("SELECT user_id FROM reminders", fetch=True)
    if rows:
        for (uid,) in rows:
            schedule_user_reminders(uid)
    rows = db_execute("SELECT user_id FROM users WHERE biweekly_opt_in = 1", fetch=True)
    if rows:
        for (uid,) in rows:
            schedule_biweekly_for_user(uid)


HELP_METHODS = [
    "Техника 4-7-8 (Andrew Weil, 2019). Полностью выдохните через рот, издавая свистящий звук. Закройте рот и тихо вдохните через нос, мысленно считая до четырех. Задержите дыхание, считая до семи. Полностью выдохните через рот, издавая свистящий звук, считая до восьми. Это один вдох. Теперь вдохните снова и повторите цикл еще три раза, чтобы в общей сложности получилось четыре вдоха.",
    "Техника дыхания по квадрату. Закройте рот и тихо вдохните через нос, мысленно считая до четырех. Задержите дыхание, снова считая до четырех. Полностью выдохните через рот, издавая свистящий звук, считая до четырех. Еще раз задержите дыхание, считая до четырех. Теперь вдохните снова и повторите цикл еще три раза, чтобы в общей сложности получилось четыре вдоха.",
    " 1. Закройте глаза и попытайтесь успокоить разум. \n 2. Почувствуйте тело, его вес, «просканируйте» его, посмотрите на себя как бы со стороны. \n 3. Почувствуйте мышцы ног и расслабьте их. \n 4. Переведите внимание на икроножные мышцы и попробуйте снова их расслабить. \n 5. Представьте себе мышцы бедра и расслабьте их. \n 6. Почувствуйте и расслабьте мышцы живота. \n 7. Визуализируйте и расслабьте свои внутренние органы, почувствуйте, как расширяются и опадают легкие, как пульсирует ваше сердце. \n 8. Расслабьте мышцы плеча, предплечья, всей руки. \n 9. Представьте себе шею и расслабьте ее. \n 10. Расслабьте все мышцы лица так, чтобы челюсть слегка опустилась.",
    "Сидя или лежа с закрытыми глазами, добейтесь ощущения спокойствия. \nПерейдите к чувству тяжести в руке, которое должно постепенно распространиться по всему телу. Выполняйте это упражнение одну минуту. \nЗатем согните руки в локтях и сделайте 2-3 глубоких вдоха.",
    "Дневник мыслей: запиши тревожную мысль и 3 контраргумента.",
    "Сидя или лежа с закрытыми глазами, добейтесь ощущения спокойствия. Ощутите тепло в левой, а затем правой руке. Вскоре возникнет чувство тяжести в результате расслабления мышц. \n\n Расширение сосудов и расслабление мышц - неотъемлемые компоненты релаксации. Именно благодаря этой реакции происходит снятие стресса.",
    "Возьмите небольшой тазик и налейте в него холодной воды \nСделайте глубокий вдох и опустите лицо полностью (до линии роста волос) в воду на 20-30 сек. \nЗамена попроще: умойтесь холодной водой",
    "Прогулка 5 минут: просто пройдись, дыши свежим воздухом.",
    "Держите запястья 2-3 мин под струей холодной воды",
    "1. Сядьте ровно, стопы плотно стоят на полу. \n 2. Сделайте 3 глубоких вдоха и выдоха. \n 3. Представьте ваше любимое, комфортное место, где вам нравиться находиться. Вспомните это место и подумайте, благодаря чему вам там так хорошо, что вам так нравиться: обстановка, запах, приятные события? Кто тогда с вами был, когда это происходило, что именно вы тогда видели, слышали, чувствовали? Что вы делали в этом воспоминании? Что было приоритетным и ценным? Просто наблюдайте за тем, какие мысли и чувства поднимаются и позволяйте им быть. \n 4. Побудьте в этой картинке столько, сколько необходимо. И когда будете готовы закончить – сделайте 3 глубоких вдоха и выдоха и возвращайтесь в реальность.",
    "1. Посмотрите на 5 предметов. \n2. Прикоснитесь к 4 предметам. \n3. Услышьте 3 звука. \n4. Почувствуйте 2 запаха. \n5. Попробуйте 1 вкус.",
    "Ароматерапия: вдохни любимый аромат (лаванда, цитрус).",
    "Посчитайте от 100 назад, по 7 (100, 93, 86...).",
    "Сосредоточьтесь на прямоугольном предмете и плавно перемещайте взгляд, считая до четырех: вдох по верхней грани, задержка по правой, выдох по нижней, пауза по левой.",
    "Сосредоточьтесь на том, что вы видите. Посчитайте, сколько предметов определенного цвета в комнате. Посчитайте количество источников света в помещении.",
    "Попробуйте услышать все звуки, которые сейчас вас окружают. \nВы можете уловить щебетание птиц или шум машин за окном? \nЕсли вы находитесь в закрытом помещении, где нет никаких звуков, попробуйте создать их сами. Это могут быть хлопки, щелчки, звуки растирания ладоней или перелистывания страниц в книге.",
    "Возьмите в руки любой предмет и изучите его. Если под рукой ничего нет, проведите пальцами по волосам или собственной коже. Почувствуйте вес, текстуру и температуру предмета, который держите в руках..",
    "Попробуйте сосредоточиться на том, чем пахнет воздух. Можете ли вы определить запах или разбить его на составляющие?",
    "Попробуйте встать на две ноги, почувствовать опору, почувствовать свой вес и попереносить его с ноги на ногу. Если у вас есть возможность, подвигайтесь под любимую музыку.",
    "Найдите тихое место, где вас никто не будет отвлекать. \nСядьте удобно и сосредоточьтесь на своем дыхании. \nОщутите, как воздух входит и выходит из вашего тела, обращая внимание на каждую деталь. \nКогда тревожные мысли начинают появляться, мягко возвращайте внимание к своему дыханию, не оценивая эти мысли.",
    "В течение одной минуты осознанно ощущайте все, что происходит в вашем теле. Посчитайте, сколько всего вы ощущаете."
]

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    init_db()
    load_schedules_from_db()
    print("бот запущен. ctrl+c для выхода")
    bot.infinity_polling()
