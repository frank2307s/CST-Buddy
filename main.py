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


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())