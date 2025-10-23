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


async def send_schedule(callback, group_display, group_number, week_type, schedule_type):
    try:
        week_display = "верхняя" if week_type == "upper" else "нижняя"
        if schedule_type == "today":
            day_of_week = datetime.now().weekday()
            if day_of_week > 4:
                await callback.message.answer("Сегодня выходной! Расписания нет.")
                return
            days_en = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            days_ru = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу']
            day_name = days_en[day_of_week]
            day_name_ru = days_ru[day_of_week]
            schedule_text = read_schedule_file(group_number, week_type, day_name)
            if schedule_text:
                message = f"📅 Расписание на {day_name_ru}\n👥 {group_display}, {week_display} неделя\n\n{schedule_text}"
                await callback.message.answer(message)
            else:
                await callback.message.answer(f"На {day_name_ru} ({week_display} неделя) расписания нет.")
        else:
            week_schedule = f"📅 Расписание на неделю\n👥 {group_display}, {week_display} неделя\n\n"
            days = [
                ('monday', 'Понедельник'),
                ('tuesday', 'Вторник'),
                ('wednesday', 'Среда'),
                ('thursday', 'Четверг'),
                ('friday', 'Пятница')
            ]
            has_content = False
            for day_en, day_ru in days:
                day_schedule = read_schedule_file(group_number, week_type, day_en)
                if day_schedule:
                    week_schedule += f"📌{day_ru}:\n\n{day_schedule}\n\n\n"
                    has_content = True
            if has_content:
                await callback.message.answer(week_schedule)
            else:
                await callback.message.answer(f"Расписание на {week_display} неделю не найдено.")
    except Exception:
        await callback.message.answer("Произошла ошибка при загрузке расписания. Попробуйте позже.")


async def send_daily_schedule():
    while True:
        try:
            now = datetime.now()
            users = get_mailing_users()
            current_week = get_current_week()
            for user_id, mailing_time_str, group_number in users:
                try:
                    mailing_time = datetime.strptime(mailing_time_str, '%H:%M').time()
                    current_time = now.time()
                    if current_time.hour == mailing_time.hour and current_time.minute == mailing_time.minute:
                        day_of_week = datetime.now().weekday()
                        if day_of_week > 4:
                            continue
                        days_en = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
                        days_ru = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу']
                        day_name = days_en[day_of_week]
                        day_name_ru = days_ru[day_of_week]
                        schedule_text = read_schedule_file(group_number, current_week, day_name)
                        if schedule_text:
                            week_display = "верхняя" if current_week == "upper" else "нижняя"
                            message = f"📅 Расписание на {day_name_ru}\n👥 {group_number}, {week_display} неделя\n\n{schedule_text}"
                            await bot.send_message(user_id, message)
                except Exception:
                    continue
            await asyncio.sleep(60)
        except Exception:
            await asyncio.sleep(60)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if is_user_registered(user_id):
        await message.answer("Добро пожаловать! Выберите опцию:", reply_markup=get_main_keyboard())
    else:
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer("Добро пожаловать! Для регистрации введите вашу Фамилию и Имя через пробел:")


@router.message(F.text == "Мой профиль")
async def my_profile(message: Message):
    user_data = get_user_data(message.from_user.id)
    if user_data:
        profile_text = get_profile_text(user_data)
        await message.answer(profile_text, reply_markup=get_profile_inline_keyboard(user_data))
    else:
        await message.answer("Профиль не найден.", reply_markup=get_main_keyboard())


@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name_parts = message.text.split()
    if len(name_parts) < 2:
        await message.answer("Пожалуйста, введите Фамилию и Имя через пробел:")
        return
    await state.update_data(last_name=name_parts[0], first_name=' '.join(name_parts[1:]))
    await state.set_state(RegistrationStates.waiting_for_group)
    await message.answer("Выберите вашу группу:", reply_markup=get_group_selection_registration_keyboard())


@router.callback_query(F.data.endswith("_reg"), RegistrationStates.waiting_for_group)
async def process_group_callback(callback: types.CallbackQuery, state: FSMContext):
    group_mapping = {
        "group_3_reg": "3 группа",
        "group_4_reg": "4 группа",
        "group_guest_reg": "Гость"
    }
    group = group_mapping.get(callback.data)
    if not group:
        await callback.message.answer("Пожалуйста, выберите группу из предложенных вариантов:")
        return
    await state.update_data(group=group)
    if group == "Гость":
        data = await state.get_data()
        register_user(
            user_id=callback.from_user.id,
            last_name=data['last_name'],
            first_name=data['first_name'],
            group_number=data['group'],
            email="Не указан"
        )
        await callback.message.answer("Регистрация завершена! Теперь вы можете пользоваться ботом.",
                                      reply_markup=get_main_keyboard())
        await state.clear()
    else:
        await state.set_state(RegistrationStates.waiting_for_email)
        await callback.message.answer("Введите вашу корпоративную почту:")
    await callback.answer()


@router.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    email = message.text
    if '@' not in email or '.' not in email:
        await message.answer("Пожалуйста, введите корректный email:")
        return
    data = await state.get_data()
    register_user(
        user_id=message.from_user.id,
        last_name=data['last_name'],
        first_name=data['first_name'],
        group_number=data['group'],
        email=email
    )
    await message.answer("Регистрация завершена! Теперь вы можете пользоваться ботом.",
                         reply_markup=get_main_keyboard())
    await state.clear()


@router.callback_query(F.data == "edit_name")
async def edit_name_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(EditProfileStates.waiting_for_new_name)
    await callback.message.answer("Введите новую Фамилию и Имя через пробел:")
    await callback.answer()


@router.callback_query(F.data == "edit_group")
async def edit_group_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(EditProfileStates.waiting_for_new_group)
    await callback.message.answer("Выберите новую группу:", reply_markup=get_group_selection_registration_keyboard())
    await callback.answer()


@router.callback_query(F.data == "edit_email")
async def edit_email_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(EditProfileStates.waiting_for_new_email)
    await callback.message.answer("Введите новый email:")
    await callback.answer()


@router.message(EditProfileStates.waiting_for_new_name)
async def process_new_name(message: Message, state: FSMContext):
    name_parts = message.text.split()
    if len(name_parts) < 2:
        await message.answer("Пожалуйста, введите Фамилию и Имя через пробел:")
        return
    user_data = get_user_data(message.from_user.id)
    update_user_data(
        user_id=message.from_user.id,
        last_name=name_parts[0],
        first_name=' '.join(name_parts[1:]),
        group_number=user_data[3],
        email=user_data[4]
    )
    await message.answer("✅ Имя успешно изменено!")
    await state.clear()


@router.callback_query(F.data.endswith("_reg"), EditProfileStates.waiting_for_new_group)
async def process_new_group_callback(callback: types.CallbackQuery, state: FSMContext):
    group_mapping = {
        "group_3_reg": "3 группа",
        "group_4_reg": "4 группа",
        "group_guest_reg": "Гость"
    }
    group = group_mapping.get(callback.data)
    if not group:
        await callback.message.answer("Пожалуйста, выберите группу из предложенных вариантов:")
        return
    user_data = get_user_data(callback.from_user.id)
    if group == "Гость" and user_data[3] != "Гость":
        disable_mailing(callback.from_user.id)
        update_user_data(
            user_id=callback.from_user.id,
            last_name=user_data[1],
            first_name=user_data[2],
            group_number=group,
            email="Не указан"
        )
        await callback.message.answer("✅ Группа успешно изменена! Рассылка автоматически выключена.")
        await state.clear()
    elif group != "Гость" and user_data[3] == "Гость":
        await state.update_data(new_group=group)
        await state.set_state(EditProfileStates.waiting_for_new_email)
        await callback.message.answer("Введите вашу корпоративную почту:")
    elif group != "Гость" and user_data[3] != "Гость":
        update_user_data(
            user_id=callback.from_user.id,
            last_name=user_data[1],
            first_name=user_data[2],
            group_number=group,
            email=user_data[4]
        )
        await callback.message.answer("✅ Группа успешно изменена!")
        await state.clear()
    else:
        update_user_data(
            user_id=callback.from_user.id,
            last_name=user_data[1],
            first_name=user_data[2],
            group_number=group,
            email=user_data[4]
        )
        await callback.message.answer("✅ Группа успешно изменена!")
        await state.clear()
    await callback.answer()


@router.message(EditProfileStates.waiting_for_new_email)
async def process_new_email(message: Message, state: FSMContext):
    email = message.text
    if '@' not in email or '.' not in email:
        await message.answer("Пожалуйста, введите корректный email:")
        return
    user_data = get_user_data(message.from_user.id)
    data = await state.get_data()
    new_group = data.get('new_group')
    if new_group:
        update_user_data(
            user_id=message.from_user.id,
            last_name=user_data[1],
            first_name=user_data[2],
            group_number=new_group,
            email=email
        )
        await message.answer("✅ Данные профиля успешно обновлены!")
        await state.clear()
    else:
        await message.answer("Ошибка при обновлении данных. Попробуйте еще раз.")
        await state.clear()


async def main():
    create_database()
    asyncio.create_task(send_daily_schedule())
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())