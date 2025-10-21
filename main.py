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
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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


def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мой профиль")],
            [KeyboardButton(text="Основная информация"), KeyboardButton(text="Расписание")],
            [KeyboardButton(text="Контакты"), KeyboardButton(text="Дисциплины")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_profile_inline_keyboard(user_data):
    if user_data[3] == "Гость":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Изменить фамилию и имя", callback_data="edit_name")],
                [InlineKeyboardButton(text="✏️ Изменить группу", callback_data="edit_group")]
            ]
        )
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Изменить фамилию и имя", callback_data="edit_name")],
                [InlineKeyboardButton(text="✏️ Изменить группу", callback_data="edit_group")],
                [InlineKeyboardButton(text="✏️ Изменить email", callback_data="edit_email")]
            ]
        )
    return keyboard


def get_schedule_inline_keyboard(user_data):
    if user_data[3] == "Гость":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 Расписание на сегодня", callback_data="schedule_today")],
                [InlineKeyboardButton(text="📅 Расписание на неделю", callback_data="schedule_week")]
            ]
        )
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 Расписание на сегодня", callback_data="schedule_today")],
                [InlineKeyboardButton(text="📅 Расписание на неделю", callback_data="schedule_week")],
                [InlineKeyboardButton(text="⚙️ Настройки рассылки", callback_data="mailing_settings")]
            ]
        )
    return keyboard


def get_group_selection_keyboard(schedule_type):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 3 группа", callback_data=f"guest_{schedule_type}_3")],
            [InlineKeyboardButton(text="👥 4 группа", callback_data=f"guest_{schedule_type}_4")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_schedule")]
        ]
    )
    return keyboard


def get_week_selection_keyboard(schedule_type, group_number=None):
    callback_prefix = f"guest_{schedule_type}_{group_number}" if group_number else schedule_type
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔺 Верхняя неделя", callback_data=f"{callback_prefix}_upper")],
            [InlineKeyboardButton(text="🔻 Нижняя неделя", callback_data=f"{callback_prefix}_lower")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_schedule")]
        ]
    )
    return keyboard


def get_contacts_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Одногруппники", callback_data="groupmates")],
            [InlineKeyboardButton(text="👨‍🏫👩‍🏫 Преподаватели", callback_data="teachers")],
            [InlineKeyboardButton(text="🌟 Кураторы", callback_data="curators")]
        ]
    )
    return keyboard


def get_groupmates_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="3 группа", callback_data="group_3")],
            [InlineKeyboardButton(text="4 группа", callback_data="group_4")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_contacts")]
        ]
    )
    return keyboard


def get_teachers_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Городнова А.А.", callback_data="gorodnova")],
            [InlineKeyboardButton(text="Константинова Т.Н.", callback_data="konstantinova")],
            [InlineKeyboardButton(text="Кочеров С.Н.", callback_data="kocherov")],
            [InlineKeyboardButton(text="Марьевичев Н.", callback_data="marevichev")],
            [InlineKeyboardButton(text="Пеплин Ф.С.", callback_data="peplin")],
            [InlineKeyboardButton(text="Полонецкая Н.А.", callback_data="poloneckaya")],
            [InlineKeyboardButton(text="Савина О.Н.", callback_data="savina")],
            [InlineKeyboardButton(text="Талецкий Д.С.", callback_data="taleckiy")],
            [InlineKeyboardButton(text="Улитин Б.И.", callback_data="ulitin")],
            [InlineKeyboardButton(text="Чистякова С.А.", callback_data="chistyakova")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_contacts")]
        ]
    )
    return keyboard


def get_curators_groups_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="3 группа", callback_data="curators_group_3")],
            [InlineKeyboardButton(text="4 группа", callback_data="curators_group_4")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_contacts")]
        ]
    )
    return keyboard


def get_mailing_settings_keyboard(user_data):
    mailing_enabled = user_data[5] if len(user_data) > 5 else False
    if mailing_enabled:
        mailing_buttons = [[
            InlineKeyboardButton(text="✅ ВКЛ", callback_data="disable_mailing"),
            InlineKeyboardButton(text="❌ ВЫКЛ", callback_data="disable_mailing")
        ]]
    else:
        mailing_buttons = [[
            InlineKeyboardButton(text="✅ ВКЛ", callback_data="enable_mailing"),
            InlineKeyboardButton(text="❌ ВЫКЛ", callback_data="enable_mailing")
        ]]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            *mailing_buttons,
            [InlineKeyboardButton(text="🕐 Изменить время рассылки", callback_data="change_mailing_time")],
            [InlineKeyboardButton(text="🔙 Назад в расписание", callback_data="back_to_schedule")]
        ]
    )
    return keyboard


def get_subjects_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Английский язык", callback_data="english")],
            [InlineKeyboardButton(text="Безопасность жизнедеятельности", callback_data="safe")],
            [InlineKeyboardButton(text="Дискретная математика", callback_data="discrete")],
            [InlineKeyboardButton(text="История России", callback_data="history")],
            [InlineKeyboardButton(text="Линейная алгебра и геометрия", callback_data="linear")],
            [InlineKeyboardButton(text="Математический анализ", callback_data="calculus")],
            [InlineKeyboardButton(text='НПС "Цифровая грамотность"', callback_data="digital")],
            [InlineKeyboardButton(text="Основы российской государственности", callback_data="statehood")],
            [InlineKeyboardButton(text="Программирование C/C++", callback_data="cpp")],
            [InlineKeyboardButton(text="Технологии программирования", callback_data="software")],
            [InlineKeyboardButton(text="Физическая культура", callback_data="pe")]
        ]
    )
    return keyboard


def get_addresses_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📍 Большая Печерская ул., 25/12", callback_data="address_1")],
            [InlineKeyboardButton(text="📍 Костина ул., 2Б", callback_data="address_2")],
            [InlineKeyboardButton(text="📍 Львовская ул., 1в", callback_data="address_3")],
            [InlineKeyboardButton(text="📍 Родионова ул., 136", callback_data="address_4")],
            [InlineKeyboardButton(text="📍 Сормовское ш., 30", callback_data="address_5")]
        ]
    )
    return keyboard


def get_group_selection_registration_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="3 группа", callback_data="group_3_reg")],
            [InlineKeyboardButton(text="4 группа", callback_data="group_4_reg")],
            [InlineKeyboardButton(text="Гость", callback_data="group_guest_reg")]
        ]
    )
    return keyboard


def get_subject_teacher_keyboard(subject):
    teacher_keyboards = {
        "safe": InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Городнова А.А.", callback_data="gorodnova")]]
        ),
        "discrete": InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Талецкий Д.С.", callback_data="taleckiy")]]
        ),
        "history": InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Константинова Т.Н.", callback_data="konstantinova")]]
        ),
        "linear": InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Савина О.Н.", callback_data="savina")]]
        ),
        "calculus": InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Чистякова С.А.", callback_data="chistyakova")]]
        ),
        "digital": InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Полонецкая Н.А.", callback_data="poloneckaya")]]
        ),
        "statehood": InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Константинова Т.Н.", callback_data="konstantinova")],
                [InlineKeyboardButton(text="Кочеров С.Н.", callback_data="kocherov")]
            ]
        ),
        "cpp": InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Марьевичев Н.", callback_data="marevichev")],
                [InlineKeyboardButton(text="Пеплин Ф.С.", callback_data="peplin")]
            ]
        ),
        "software": InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Улитин Б.И.", callback_data="ulitin")]]
        )
    }
    return teacher_keyboards.get(subject)


async def main():
    create_database()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())