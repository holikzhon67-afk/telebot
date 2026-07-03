import telebot
from telebot import types
import sqlite3
import config

# Инициализация бота
bot = telebot.TeleBot(config.TOKEN)
ADMIN_ID = config.ADMIN_ID  # Теперь переменная доступна всему коду

# --- ИЗОЛИРОВАННЫЙ МЕНЕДЖЕР БАЗЫ ДАННЫХ ---
def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect("fitness_bot.db", timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка БД: {e}")
    finally:
        conn.close()

def init_db():
    execute_query("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            step TEXT,
            name TEXT,
            age INTEGER,
            type TEXT,
            time TEXT
        )
    """, commit=True)
    execute_query("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            age INTEGER,
            type TEXT,
            time TEXT
        )
    """, commit=True)

init_db()

# --- КЛАВИАТУРЫ ---
def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Записаться на тренировку"))
    markup.add(types.KeyboardButton("Мои записи"), types.KeyboardButton("Контакты"))
    if str(user_id) == str(ADMIN_ID):
        markup.add(types.KeyboardButton("👑 Все записи"), types.KeyboardButton("👑 Количество записей"))
    return markup

def get_step_keyboard(buttons=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if buttons:
        for btn in buttons:
            markup.add(types.KeyboardButton(btn))
    markup.add(types.KeyboardButton("⬅️ Назад"))
    return markup

def get_confirm_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✅ Подтвердить"), types.KeyboardButton("❌ Изменить"))
    return markup

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_user_state(user_id):
    row = execute_query("SELECT step, name, age, type, time FROM user_states WHERE user_id = ?", (user_id,), fetchone=True)
    if row:
        return {"step": row[0], "name": row[1], "age": row[2], "type": row[3], "time": row[4]}
    return None

def update_user_state(user_id, **kwargs):
    execute_query("INSERT OR IGNORE INTO user_states (user_id, step) VALUES (?, 'none')", (user_id,), commit=True)
    for key, value in kwargs.items():
        execute_query(f"UPDATE user_states SET {key} = ? WHERE user_id = ?", (value, user_id), commit=True)

def delete_user_state(user_id):
    execute_query("DELETE FROM user_states WHERE user_id = ?", (user_id,), commit=True)

def add_appointment(user_id, data):
    execute_query("INSERT INTO appointments (user_id, name, age, type, time) VALUES (?, ?, ?, ?, ?)",
                  (user_id, data["name"], data["age"], data["type"], data["time"]), commit=True)

def get_last_appointment(user_id):
    row = execute_query("SELECT name, age, type, time FROM appointments WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,), fetchone=True)
    if row:
        return {"name": row[0], "age": row[1], "type": row[2], "time": row[3]}
    return None

def get_all_appointments():
    rows = execute_query("SELECT name, age, type, time FROM appointments", fetchall=True)
    return [{"name": r[0], "age": r[1], "type": r[2], "time": r[3]} for r in rows] if rows else []

# --- ОБРАБОТЧИК ---
@bot.message_handler(commands=['start'])
def cmd_start(message):
    delete_user_state(message.chat.id)  
    bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}! Выберите действие:", reply_markup=get_main_menu(message.chat.id))

@bot.message_handler(content_types=['text'])
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text
    state = get_user_state(chat_id)

    # Исправлена логика с правильными отступами
    if state and state["step"] != "none":
        current_step = state["step"]
        # ... (вся логика опроса) ...
        # Обязательно проверь, что код внутри 'if' имеет 4 пробела отступа
        if text == "⬅️ Назад":
            # ... логика назад ...
            pass
        # и так далее...
        # (код внутри этого блока у тебя был правильный, просто следи за пробелами)
    
    # Главное меню (внешний блок)
    elif text == "Записаться на тренировку":
        update_user_state(chat_id, step="name")
        bot.send_message(chat_id, "Введите ваше имя:", reply_markup=get_step_keyboard())
    elif text == "Мои записи":
        # ... логика записей ...
        pass
    # ... остальная логика ...

if __name__ == '__main__':
    bot.infinity_polling()
