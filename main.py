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


async def main():
    create_database()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())