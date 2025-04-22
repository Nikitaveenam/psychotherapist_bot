import os
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv
import openai
import httpx

from models import Base, User
from utils import check_user_subscription, is_user_allowed_to_chat

# Загрузка переменных окружения
load_dotenv()

# Загрузка переменных окружения и проверка
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_URL")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

if not BOT_TOKEN or not OPENAI_API_KEY or not DB_URL:
    logging.critical("Не заданы переменные окружения. Завершаю работу...")
    exit(1)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# FSM-хранилище (внутреннее хранилище памяти)
storage = MemoryStorage()
logger.warning("⚠️ Redis не используется. Используется память.")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Устанавливаем стандартные команды для бота
async def set_default_commands():
    try:
        commands = [
            BotCommand(command="start", description="Запуск бота"),
            BotCommand(command="help", description="Справка"),
            BotCommand(command="profile", description="Профиль пользователя"),
            BotCommand(command="subscription", description="Управление подпиской"),
            BotCommand(command="admin", description="Админ панель"),
        ]
        await bot.set_my_commands(commands)
        logger.info("Команды бота установлены успешно.")
    except Exception as e:
        logger.error(f"Ошибка при установке команд бота: {e}")

# Подключение к базе данных
engine = create_async_engine(DB_URL, echo=False)
Session = async_sessionmaker(engine, expire_on_commit=False)

# Клавиатура подписки
def get_subscription_kb():
    return InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="1 месяц — 299₽", callback_data="subscribe_1")],
        [InlineKeyboardButton(text="3 месяца — 799₽", callback_data="subscribe_3")],
        [InlineKeyboardButton(text="6 месяцев — 1499₽", callback_data="subscribe_6")],
        [InlineKeyboardButton(text="12 месяцев — 2999₽", callback_data="subscribe_12")],
    ])

# Главное меню
def get_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="📊 Мой статус", callback_data="my_status")],
        [InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="pay")],
        [InlineKeyboardButton(text="❓ Часто задаваемые вопросы", callback_data="faq")],
    ])

# Команда /start
@router.message(Command("start"))
async def handle_start(message: Message):
    async with Session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name,
                trial_started_at=datetime.utcnow()
            )
            session.add(user)
            await session.commit()

    text = (
        "👋 <b>Добро пожаловать в АНОНИМНЫЙ ПСИХОЛОГ</b>!  "
        "🤖 Я использую <b>GPT-4</b> для платных подписок и <b>GPT-3.5</b> для бесплатной версии. "
        "🫖 Напиши, как прошел твой день или что тебя беспокоит.  "
        "📌 Ты можешь использовать 3 бесплатных запроса в день. "
        "Для получения подробной информации, используйте команду /help"
    )

    await message.answer(text, reply_markup=get_main_menu_kb())  # Явное использование клавиатуры

# Команда /help
@router.message(Command("help"))
async def handle_help(message: Message):
    await message.answer(
        "📘 <b>Как пользоваться ботом</b>  "
        "• Напиши о своем состоянии, вопросе или эмоциях "
        "• Получи ответ от ИИ (GPT-3.5 / GPT-4) "
        "• У тебя есть 3 бесплатных запроса в день  "
        "🔐 Хочешь больше? Активируй подписку через /subscription "
        "🔎 Команда /profile покажет твой статус "
        "📋 Команда /admin доступна только для администраторов"
    )

# Команда /profile
@router.message(Command("profile"))
async def handle_profile(message: Message):
    async with Session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            await message.answer("Пользователь не найден.")
            return

        await check_user_subscription(user, session)

        if user.is_premium:
            status = "✅ Активная подписка"
        elif user.trial_started_at and (datetime.utcnow() - user.trial_started_at).days <= 3:
            status = "🆓 Пробный период"
        else:
            status = "🔒 Ограниченный доступ"

        await message.answer(
            f"📊 <b>Твой статус:</b> {status} 📅 Подписка до: {user.subscription_expires_at.strftime('%d.%m.%Y') if user.subscription_expires_at else '—'}"
        )

# Команда /subscription
@router.message(Command("subscription"))
async def handle_subscribe(message: Message):
    await message.answer("💳 Выбери подходящий план:", reply_markup=get_subscription_kb())

# Админ панель
@router.message(Command("admin"))
async def handle_admin(message: Message):
    if str(message.from_user.id) not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.answer("👨‍💼 Админ панель: На данный момент доступны только базовые функции.")

# Запуск бота
async def main():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Таблицы базы данных инициализированы.")
        
        await set_default_commands()  # Устанавливаем команды
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())
