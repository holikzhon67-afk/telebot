# main.py
import telebot
from telebot import types
import sqlite3
import config  # Импортируем наш файл с настройками

# Теперь используем config.TOKEN вместо прямой строки
bot = telebot.TeleBot(config.TOKEN)

# В проверке админа используй config.ADMIN_ID
if message.from_user.id == config.ADMIN_ID:
    # Твой код...


# --- ИЗОЛИРОВАННЫЙ И БЕЗОПАСНЫЙ МЕНЕДЖЕР БАЗЫ ДАННЫХ ---
def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """
    Универсальная функция для безопасной работы с SQLite в многопоточном режиме.
    Гарантированно закрывает соединение в любых ситуациях.
    """
    conn = sqlite3.connect("fitness_bot.db", timeout=15.0) # Увеличили таймаут ожидания файла
    try:
        # Включаем режим WAL для предотвращения блокировок при одновременных запросах
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
        conn.close() # Выполнится СТРОГО в любом случае (даже при ошибке)

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
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

# --- ФУНКЦИИ-ОБЕРТКИ ДЛЯ СТЭЙТОВ И ЗАПИСЕЙ ---
def get_user_state(user_id):
    row = execute_query(
        "SELECT step, name, age, type, time FROM user_states WHERE user_id = ?", 
        (user_id,), fetchone=True
    )
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
    execute_query(
        "INSERT INTO appointments (user_id, name, age, type, time) VALUES (?, ?, ?, ?, ?)",
        (user_id, data["name"], data["age"], data["type"], data["time"]), commit=True
    )

def get_last_appointment(user_id):
    row = execute_query(
        "SELECT name, age, type, time FROM appointments WHERE user_id = ? ORDER BY id DESC LIMIT 1", 
        (user_id,), fetchone=True
    )
    if row:
        return {"name": row[0], "age": row[1], "type": row[2], "time": row[3]}
    return None

def get_all_appointments():
    rows = execute_query("SELECT name, age, type, time FROM appointments", fetchall=True)
    return [{"name": r[0], "age": r[1], "type": r[2], "time": r[3]} for r in rows] if rows else []

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---

@bot.message_handler(commands=['start'])
def cmd_start(message):
    chat_id = message.chat.id
    delete_user_state(chat_id)  
    bot.send_message(
        chat_id, 
        f"Привет, {message.from_user.first_name}! Я бот для записи на тренировки. Выберите действие:", 
        reply_markup=get_main_menu(chat_id)
    )

@bot.message_handler(content_types=['text'])
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text
    state = get_user_state(chat_id)

    # ЛОГИКА АКТИВНОГО ОПРОСА
    if state and state["step"] != "none":
        current_step = state["step"]

        if text == "⬅️ Назад":
            if current_step == "name":
                delete_user_state(chat_id)
                bot.send_message(chat_id, "Возвращаюсь в главное меню:", reply_markup=get_main_menu(chat_id))
            elif current_step == "age":
                update_user_state(chat_id, step="name")
                bot.send_message(chat_id, "Введите ваше имя:", reply_markup=get_step_keyboard())
            elif current_step == "type":
                update_user_state(chat_id, step="age")
                bot.send_message(chat_id, "Введите ваш возраст (от 8 до 60 лет):", reply_markup=get_step_keyboard())
            elif current_step == "time":
                update_user_state(chat_id, step="type")
                bot.send_message(chat_id, "Выберите вид тренировки:", reply_markup=get_step_keyboard(["Футбол", "Бокс", "Воркаут"]))
            elif current_step == "confirm":
                update_user_state(chat_id, step="time")
                bot.send_message(chat_id, "Выберите удобное время:", reply_markup=get_step_keyboard(["Утро", "День", "Вечер"]))
            return

        if current_step == "name":
            if text == "Записаться на тренировку": return
            update_user_state(chat_id, name=text, step="age")
            bot.send_message(chat_id, "Введите ваш возраст (от 8 до 60 лет):", reply_markup=get_step_keyboard())
            return

        elif current_step == "age":
            if not text.isdigit() or not (8 <= int(text) <= 60):
                bot.send_message(chat_id, "Ошибка! Введите возраст числом от 8 до 60 лет:", reply_markup=get_step_keyboard())
                return
            update_user_state(chat_id, age=int(text), step="type")
            bot.send_message(chat_id, "Выберите вид тренировки:", reply_markup=get_step_keyboard(["Футбол", "Бокс", "Воркаут"]))
            return

        elif current_step == "type":
            if text not in ["Футбол", "Бокс", "Воркаут"]:
                bot.send_message(chat_id, "Используйте кнопки на экране:", reply_markup=get_step_keyboard(["Футбол", "Бокс", "Воркаут"]))
                return
            update_user_state(chat_id, type=text, step="time")
            bot.send_message(chat_id, "Выберите удобное время:", reply_markup=get_step_keyboard(["Утро", "День", "Вечер"]))
            return

        elif current_step == "time":
            if text not in ["Утро", "День", "Вечер"]:
                bot.send_message(chat_id, "Используйте кнопки на экране:", reply_markup=get_step_keyboard(["Утро", "День", "Вечер"]))
                return
            update_user_state(chat_id, time=text, step="confirm")
            
            st = get_user_state(chat_id)
            summary = (
                f"📋 *Сводка вашей записи:*\n\n"
                f"👤 Имя: {st['name']}\n"
                f"🔢 Возраст: {st['age']}\n"
                f"💪 Тренировка: {st['type']}\n"
                f"⏰ Время: {st['time']}"
            )
            bot.send_message(chat_id, summary, parse_mode="Markdown", reply_markup=get_confirm_keyboard())
            return

        elif current_step == "confirm":
            if text == "✅ Подтвердить":
                username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
                admin_text = (
                    f"🚨 *Новая запись на тренировку!*\n\n"
                    f"👤 Имя: {state['name']}\n"
                    f"🔢 Возраст: {state['age']}\n"
                    f"💪 Тренировка: {state['type']}\n"
                    f"⏰ Время: {state['time']}\n"
                    f"💬 Клиент: {username} (ID: {chat_id})"
                )
                try:
                    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", timeout=3)
                except Exception as e:
                    print(f"Ошибка отправки админу: {e}")

                add_appointment(chat_id, state)
                bot.send_message(chat_id, "🎉 Успешно! Ваша запись принята.", reply_markup=get_main_menu(chat_id))
                delete_user_state(chat_id)
                return
                
            elif text == "❌ Изменить":
                update_user_state(chat_id, step="name")
                bot.send_message(chat_id, "Введите ваше имя:", reply_markup=get_step_keyboard())
                return
            else:
                bot.send_message(chat_id, "Используйте кнопки на экране:", reply_markup=get_confirm_keyboard())
                return

    # НАВИГАЦИЯ ГЛАВНОГО МЕНЮ
    if text == "Записаться на тренировку":
        update_user_state(chat_id, step="name")
        bot.send_message(chat_id, "Введите ваше имя:", reply_markup=get_step_keyboard())

    elif text == "Мои записи":
        record = get_last_appointment(chat_id)
        if record:
            text_record = (
                f"🏋️‍♂️ *Ваша последняя запись:*\n\n"
                f"👤 Имя: {record['name']}\n"
                f"🔢 Возраст: {record['age']}\n"
                f"💪 Тренировка: {record['type']}\n"
                f"⏰ Время: {record['time']}"
            )
            bot.send_message(chat_id, text_record, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "У вас пока нет активных записей.")

    elif text == "Контакты":
        bot.send_message(chat_id, "📞 Наш телефон: +7 (999) 000-11-22\n📍 Адрес: Комплекс «Арена»")

    # АДМИН ПАНЕЛЬ
    elif text == "👑 Количество записей" and str(chat_id) == str(ADMIN_ID):
        records = get_all_appointments()
        bot.send_message(chat_id, f"📊 Всего записей в системе: *{len(records)}*", parse_mode="Markdown")

    elif text == "👑 Все записи" and str(chat_id) == str(ADMIN_ID):
        records = get_all_appointments()
        if not records:
            bot.send_message(chat_id, "Записей пока нет.")
            return
        report = "📋 *Список всех записей:*\n\n"
        for idx, r in enumerate(records, 1):
            report += f"{idx}. {r['name']} ({r['age']} лет) — *{r['type']}*, время: {r['time']}\n"
        bot.send_message(chat_id, report, parse_mode="Markdown")

# --- СТАБИЛЬНЫЙ ЗАПУСК ---
if __name__ == '__main__':
    print("Бот запущен. Архитектура БД защищена от параллельных блокировок (WAL режим включен).")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
