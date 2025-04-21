import os
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
)
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

from models import Base, User
from utils import check_user_subscription, is_user_allowed_to_chat
from openai import AsyncOpenAI
from aiogram.client.default import DefaultBotProperties

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_URL")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

storage = MemoryStorage()
logger.warning("⚠️ Redis не используется. Используется память.")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=storage)

engine = create_async_engine(DB_URL, echo=False)
Session = async_sessionmaker(engine, expire_on_commit=False)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def get_subscription_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц — 299₽", callback_data="subscribe_1")],
        [InlineKeyboardButton(text="3 месяца — 799₽", callback_data="subscribe_3")],
        [InlineKeyboardButton(text="6 месяцев — 1499₽", callback_data="subscribe_6")],
        [InlineKeyboardButton(text="12 месяцев — 2999₽", callback_data="subscribe_12")],
    ])

def get_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Мой статус", callback_data="my_status")],
        [InlineKeyboardButton(text="💳 Подписка", callback_data="pay")],
        [InlineKeyboardButton(text="❓ FAQ", callback_data="faq")],
    ])

@dp.message(Command("start"))
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
        "👋 <b>Добро пожаловать в АНОНИМНОГО ПСИХОЛОГА</b>! 🤖 Я использую <b>GPT-4</b> для платной подписки и <b>GPT-3.5</b> для бесплатного режима. 🫖 Просто напишите, как прошёл ваш день или что вас тревожит. 📌 Для начала вы можете использовать 3 бесплатных запроса каждый день. Подробнее — команда /help\n\n"
        "🤖 Я использую GPT-4 (для подписчиков) и GPT-3.5 (в бесплатном режиме).\n"
        "🫖 Просто напишите, как прошёл ваш день или что вас тревожит.\n"
        "📌 У вас 3 бесплатных запроса каждый день.\n"
        "ℹ️ Используйте /help для получения всех команд."
    )
    await message.answer(text, reply_markup=get_main_menu_kb())

@dp.message(Command("help"))
async def handle_help(message: Message):
    await message.answer(
        "<b>📘 Доступные команды:</b>\n"
        "/start — Перезапуск и приветствие\n"
        "/help — Описание команд\n"
        "/profile — Проверка статуса подписки\n"
        "/subscribe — Оформление подписки\n"
        "/chat — Общение с ботом"
    )

@dp.message(Command("profile"))
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
            status = "🔒 Доступ ограничен"

        await message.answer(
            f"📊 <b>Ваш статус:</b> {status}\n"
            f"📅 Подписка до: {user.subscription_expires_at.strftime('%d.%m.%Y') if user.subscription_expires_at else '—'}"
        )

@dp.message(Command("subscribe"))
async def handle_subscribe(message: Message):
    await message.answer("💳 Выберите тариф:", reply_markup=get_subscription_kb())

@dp.message(Command("chat"))
async def handle_chat(message: Message):
    async with Session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            await message.answer("Пожалуйста, введите /start")
            return

        if not await is_user_allowed_to_chat(session, user):
            await message.answer("🚫 Лимит запросов исчерпан. Активируйте подписку для безлимитного доступа.")
            return

        model = "gpt-4" if user.is_premium else "gpt-3.5-turbo"

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": message.text}],
            )
            reply = response.choices[0].message.content.strip()
            await message.answer(reply)
        except Exception as e:
            logger.error(f"Ошибка при запросе к OpenAI: {e}")
            await message.answer("⚠️ Ошибка при обращении к ИИ. Попробуйте позже.")

        today = datetime.now().strftime("%Y-%m-%d")
        if not hasattr(user, "daily_requests"):
            user.daily_requests = {}
        user.daily_requests[today] = user.daily_requests.get(today, 0) + 1
        await session.commit()

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Перезапуск бота"),
        BotCommand(command="help", description="Описание команд"),
        BotCommand(command="profile", description="Ваш статус"),
        BotCommand(command="subscribe", description="Оформить подписку"),
        BotCommand(command="chat", description="Поговорить с ботом"),
    ]
    await bot.set_my_commands(commands)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Таблицы БД инициализированы.")

    await setup_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())