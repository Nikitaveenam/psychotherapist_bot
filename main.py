
import os
import logging
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage  # Используем память вместо Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

from models import Base, User
from utils import check_user_subscription, is_user_allowed_to_chat

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_URL")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FSM-хранилище (внутреннее хранилище памяти)
storage = MemoryStorage()
logger.warning("⚠️ Redis не используется. Используется память.")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Устанавливаем default параметры для бота
async def set_default_commands():
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Help"),
        BotCommand(command="profile", description="User profile"),
        BotCommand(command="subscription", description="Manage subscription"),
        BotCommand(command="admin", description="Admin panel"),
    ]
    await bot.set_my_commands(commands)

# Подключение к БД
engine = create_async_engine(DB_URL, echo=False)
Session = async_sessionmaker(engine, expire_on_commit=False)

# Клавиатура подписки
def get_subscription_kb():
    return InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="1 month — 299₽", callback_data="subscribe_1")],
        [InlineKeyboardButton(text="3 months — 799₽", callback_data="subscribe_3")],
        [InlineKeyboardButton(text="6 months — 1499₽", callback_data="subscribe_6")],
        [InlineKeyboardButton(text="12 months — 2999₽", callback_data="subscribe_12")],
    ])

# Главное меню
def get_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="📊 My status", callback_data="my_status")],
        [InlineKeyboardButton(text="💳 Pay subscription", callback_data="pay")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="faq")],
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
        "👋 <b>Welcome to ANONYMOUS PSYCHOLOGIST</b>!  "
        "🤖 I use <b>GPT-4</b> for paid subscriptions and <b>GPT-3.5</b> for the free version. "
        "🫖 Just write about how your day went or what troubles you.  "
        "📌 You can use 3 free queries each day. "
        "For more info, use /help"
    )

    await message.answer(text, reply_markup=get_main_menu_kb())  # явное использование клавиатуры

# Команда /help
@router.message(Command("help"))
async def handle_help(message: Message):
    await message.answer(
        "📘 <b>How to use the bot</b>  "
        "• Write about your condition, question, or emotions "
        "• Receive an answer from AI (GPT-3.5 / GPT-4) "
        "• You have 3 free queries per day  "
        "🔐 Want more? Activate subscription via /subscription "
        "🔎 The /profile command will show your status "
        "📋 The /admin command is for admins only"
    )

# Команда /profile
@router.message(Command("profile"))
async def handle_profile(message: Message):
    async with Session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            await message.answer("User not found.")
            return

        await check_user_subscription(user, session)

        if user.is_premium:
            status = "✅ Active subscription"
        elif user.trial_started_at and (datetime.utcnow() - user.trial_started_at).days <= 3:
            status = "🆓 Trial period"
        else:
            status = "🔒 Limited access"

        await message.answer(
            f"📊 <b>Your status:</b> {status} 📅 Subscription until: {user.subscription_expires_at.strftime('%d.%m.%Y') if user.subscription_expires_at else '—'}"
        )

# Команда /subscription
@router.message(Command("subscription"))
async def handle_subscribe(message: Message):
    await message.answer("💳 Choose a suitable plan:", reply_markup=get_subscription_kb())

# Админ панель
@router.message(Command("admin"))
async def handle_admin(message: Message):
    if str(message.from_user.id) not in ADMIN_IDS:
        await message.answer("⛔ You don't have access.")
        return
    await message.answer("👨‍💼 Admin panel: Only basic functions are available for now.")

# Запуск
async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables initialized.")
    
    await set_default_commands()  # Устанавливаем команды
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
