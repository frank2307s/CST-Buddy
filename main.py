import asyncio
import logging
import os
import re
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

API_TOKEN = '8273165864:AAF1DG7kUiQXS6qwvxwU3klt8cSgjZpJsjI'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_group = State()
    waiting_for_email = State()


class EditProfileStates(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_group = State()
    waiting_for_new_email = State()


class MailingTimeStates(StatesGroup):
    waiting_for_time = State()


def create_database():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            last_name TEXT,
            first_name TEXT,
            group_number TEXT,
            email TEXT,
            mailing_enabled BOOLEAN DEFAULT FALSE,
            mailing_time TEXT DEFAULT '07:00'
        )
    ''')
    conn.commit()
    conn.close()


def is_user_registered(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user is not None


def get_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_group_users(group_number):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_name, first_name, user_id, email FROM users WHERE group_number = ?', (group_number,))
    users = cursor.fetchall()
    conn.close()
    users_sorted = sorted(users, key=lambda x: x[0].lower())
    return users_sorted


def register_user(user_id, last_name, first_name, group_number, email):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, last_name, first_name, group_number, email, mailing_enabled, mailing_time)
        VALUES (?, ?, ?, ?, ?, FALSE, '07:00')
    ''', (user_id, last_name, first_name, group_number, email))
    conn.commit()
    conn.close()


def update_user_data(user_id, last_name, first_name, group_number, email):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET last_name = ?, first_name = ?, group_number = ?, email = ?
        WHERE user_id = ?
    ''', (last_name, first_name, group_number, email, user_id))
    conn.commit()
    conn.close()


def enable_mailing(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET mailing_enabled = TRUE WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def disable_mailing(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET mailing_enabled = FALSE WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def update_mailing_time(user_id, mailing_time):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET mailing_time = ? WHERE user_id = ?', (mailing_time, user_id))
    conn.commit()
    conn.close()


def get_mailing_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, mailing_time, group_number FROM users WHERE mailing_enabled = TRUE')
    users = cursor.fetchall()
    conn.close()
    return users


def read_text_file(file_path):
    try:
        if not os.path.exists(file_path):
            return "Информация пока не добавлена"
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            return content if content else "Информация пока не добавлена"
    except Exception:
        return "Ошибка при чтении информации"


def read_schedule_file(group_number, week_type, day_en):
    try:
        if "3" in group_number:
            group_folder = "group 3"
        elif "4" in group_number:
            group_folder = "group 4"
        else:
            group_folder = "group 3"
        file_path = os.path.join('storage/schedule', group_folder, week_type, f"{day_en}.txt")
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            return content if content else None
    except Exception:
        return None


def get_current_week():
    week_number = datetime.now().isocalendar()[1]
    return "lower" if week_number % 2 == 0 else "upper"


def is_valid_time(time_str):
    pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
    return re.match(pattern, time_str) is not None


def get_profile_text(user_data):
    profile_template = read_text_file('storage/data/profile.txt')
    return profile_template.format(
        last_name=user_data[1],
        first_name=user_data[2],
        group=user_data[3],
        email=user_data[4]
    )


def get_mailing_status_text(user_data):
    mailing_enabled = user_data[5] if len(user_data) > 5 else False
    mailing_time = user_data[6] if len(user_data) > 6 else "07:00"
    mailing_status = "✅ Включена" if mailing_enabled else "❌ Выключена"
    status_text = f"📧 Текущие настройки рассылки:\n\nСостояние: {mailing_status}\nВремя рассылки: {mailing_time}\n\nВыберите действие:"
    return status_text


def read_curators_file(group_number):
    try:
        if group_number == "3":
            filename = "group 3.txt"
        elif group_number == "4":
            filename = "group 4.txt"
        else:
            return None
        file_path = os.path.join('storage', 'contacts', 'curators', filename)
        return read_text_file(file_path)
    except Exception:
        return "Информация о кураторах не найдена"


async def main():
    create_database()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())