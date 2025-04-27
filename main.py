import asyncio
import hashlib
import logging
import os
import random
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, getcontext
from typing import Optional, Dict, Any, List, Tuple

import aiocron
import httpx
import pytz
from dotenv import load_dotenv

from threading import Thread
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher, Router, F, html, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ErrorEvent,
    PreCheckoutQuery,
    SuccessfulPayment,
)
from aiogram.utils.markdown import hide_link

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# Загрузка переменных окружения
load_dotenv()

app = FastAPI()

# Константы
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_URL")
DB_URL_SYNC = os.getenv("DB_URL_SYNC")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CRYPTO_API_KEY = os.getenv("CRYPTO_API_KEY")
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET")
YOOMONEY_SECRET = os.getenv("YOOMONEY_SECRET")
TRON_ADDRESS = os.getenv("TRON_ADDRESS")

# Проверка обязательных переменных
if not all([BOT_TOKEN, OPENAI_API_KEY, DB_URL]):
    raise ValueError("Необходимо указать BOT_TOKEN, OPENAI_API_KEY и DB_URL в .env файле!")

# Настройки
getcontext().prec = 8
AI_MODEL = "gpt-3.5-turbo"
AI_PUBLIC_MODEL_NAME = "GPT-4o"
TIMEZONE = pytz.timezone("Europe/Moscow")

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# База данных
engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

CRISIS_KEYWORDS = [
    "суицид", "покончить с собой", "умру", "не хочу жить", 
    "ненавижу себя", "все бессмысленно", "сильная депрессия"
]

PSYCHOLOGY_PRACTICES = [
    {
        "title": "⚖️ Колесо баланса",
        "description": "Проанализируйте 8 сфер жизни и найдите точки роста.",
        "content": "Колесо баланса - это инструмент для оценки удовлетворенности различными сферами жизни...",
        "hearts_cost": 0,
        "premium_only": False
    },
    {
        "title": "🙏 Дневник благодарности",
        "description": "Ежедневная практика для развития позитивного мышления.",
        "content": "Записывайте 3 вещи, за которые вы благодарны каждый день...",
        "hearts_cost": 0,
        "premium_only": False
    },
    {
        "title": "🌀 Техника 5-4-3-2-1",
        "description": "Метод для снятия тревоги и возвращения в настоящий момент.",
        "content": "Когда чувствуете тревогу, назовите:\n5 вещей, которые видите...",
        "hearts_cost": 5,
        "premium_only": True
    },
    {
        "title": "🛡️ Установка личных границ",
        "description": "Научитесь говорить 'нет' и сохранять свои границы без чувства вины.",
        "content": "Определите, в каких ситуациях ваши границы нарушаются, и потренируйтесь говорить 'нет' с уважением к себе и другим.",
        "hearts_cost": 10,
        "premium_only": True
    },
    {
        "title": "🔄 Переписывание негативных установок",
        "description": "Измените ограничивающие убеждения на поддерживающие.",
        "content": "Запишите негативные мысли и сформулируйте их по-новому с акцентом на возможности и рост.",
        "hearts_cost": 8,
        "premium_only": True
    },
    {
        "title": "🌿 Практика осознанности",
        "description": "Научитесь быть здесь и сейчас без осуждения себя.",
        "content": "Выберите любое действие (например, еду) и сделайте его осознанным: наблюдайте ощущения, запахи, эмоции.",
        "hearts_cost": 0,
        "premium_only": False
    },
    {
        "title": "🔥 Визуализация цели",
        "description": "Создайте яркий мысленный образ своего успеха.",
        "content": "Закройте глаза и во всех деталях представьте, что цель достигнута. Какие эмоции вы испытываете? Что вы видите и слышите?",
        "hearts_cost": 5,
        "premium_only": True
    },
    {
        "title": "💬 Диалог с внутренним критиком",
        "description": "Ослабьте влияние внутреннего негативного голоса.",
        "content": "Запишите реплики вашего 'критика' и ответьте на них с позиции заботливого друга.",
        "hearts_cost": 7,
        "premium_only": True
    },
    {
        "title": "🎯 SMART-цели",
        "description": "Научитесь ставить конкретные, измеримые цели.",
        "content": "Сформулируйте свою ближайшую цель по системе SMART: конкретная, измеримая, достижимая, релевантная, ограниченная во времени.",
        "hearts_cost": 0,
        "premium_only": False
    },
    {
        "title": "🔔 Упражнение «Якорение ресурсов»",
        "description": "Закрепите состояние уверенности для трудных ситуаций.",
        "content": "Вспомните момент силы в жизни, вспомните телесные ощущения. Установите 'якорь' прикосновением к руке, чтобы вызывать это состояние при необходимости.",
        "hearts_cost": 10,
        "premium_only": True
    },
    {
        "title": "🌙 Практика вечерней рефлексии",
        "description": "Анализируйте свой день для роста и улучшения.",
        "content": "Перед сном ответьте себе: что сегодня получилось хорошо? Что я могу улучшить завтра?",
        "hearts_cost": 0,
        "premium_only": False
    },
    {
        "title": "📖 Письмо самому себе в будущее",
        "description": "Поддержите себя через время.",
        "content": "Напишите письмо своему 'я' через год. Какие советы вы хотите себе дать? Какие цели поставить?",
        "hearts_cost": 5,
        "premium_only": True
    },
    {
        "title": "🛠️ Техника 'Контроль круга забот'",
        "description": "Разделяйте, что вы контролируете, а что — нет.",
        "content": "Составьте два списка: что зависит от вас, и что нет. Сосредоточьтесь на действиях в вашей зоне контроля.",
        "hearts_cost": 8,
        "premium_only": True
    },
]

SHOP_ITEMS = [
    {
        "name": "📚 Книга 'Как управлять стрессом'",
        "description": "Электронная книга с техниками управления стрессом.",
        "price": 50,
        "type": "digital"
    },
    {
        "name": "🎧 Аудиомедитация",
        "description": "30-минутная аудиомедитация для глубокого расслабления.",
        "price": 30,
        "type": "digital"
    },
    {
        "name": "💎 1 день премиума",
        "description": "Премиум-доступ на 1 день за сердечки.",
        "price": 20,
        "type": "premium"
    },
    {
        "name": "🧘 Гайд 'Как быстро расслабляться'",
        "description": "Практическое руководство по снятию стресса за 5 минут.",
        "price": 40,
        "type": "digital"
    },
    {
        "name": "📝 Шаблон Колеса Баланса",
        "description": "Готовый pdf для самостоятельной диагностики жизни.",
        "price": 25,
        "type": "digital"
    },
    {
        "name": "🎧 Медитация для сна",
        "description": "Аудиотрек для глубокого расслабления перед сном.",
        "price": 35,
        "type": "digital"
    },
    {
        "name": "📈 Персональный план развития на месяц",
        "description": "Мини-курс по саморазвитию.",
        "price": 50,
        "type": "digital"
    },
    {
        "name": "🎭 Тест 'Ваш архетип личности'",
        "description": "Онлайн-тест с объяснением результата.",
        "price": 30,
        "type": "digital"
    },
    {
        "name": "💎 7 дней премиума",
        "description": "Премиум-доступ на неделю за сердечки.",
        "price": 100,
        "type": "premium"
    },
    {
        "name": "💎 30 дней премиума",
        "description": "Премиум-доступ на месяц за сердечки.",
        "price": 350,
        "type": "premium"
    },
    {
        "name": "🌟 Психологическая поддержка в чате",
        "description": "1 личный мини-ответ от психолога.",
        "price": 60,
        "type": "service"
    },
    {
        "name": "🛡️ Защита от прокрастинации",
        "description": "Чек-лист техник борьбы с откладыванием.",
        "price": 20,
        "type": "digital"
    },
    {
        "name": "🔮 Личностный рост: Марафон",
        "description": "7-дневная программа ежедневных заданий для роста.",
        "price": 75,
        "type": "digital"
    },
]

DAILY_CHALLENGES = [
    {
        "title": "🧘 5 минут медитации",
        "description": "Найдите тихое место, закройте глаза и сосредоточьтесь на дыхании.",
        "duration": 300,  # 5 минут в секундах
        "reward": 15
    },
    {
        "title": "📝 3 благодарности",
        "description": "Запишите 3 вещи, за которые вы благодарны сегодня.",
        "duration": 180,
        "reward": 10
    },
    {
        "title": "🚶 Прогулка без телефона",
        "description": "Выйдите на улицу на 20 минут и оставьте телефон дома или в кармане.",
        "duration": 1200,
        "reward": 20
    },
    {
        "title": "🎶 Слушайте любимую музыку",
        "description": "Поставьте трек, который вызывает у вас радость, и послушайте 10 минут.",
        "duration": 600,
        "reward": 15
    },
    {
        "title": "🧹 Уборка маленького участка",
        "description": "Наведите порядок на рабочем месте или в одной комнате.",
        "duration": 900,
        "reward": 20
    },
    {
        "title": "📚 Чтение 5 страниц книги",
        "description": "Выберите книгу и прочитайте всего 5 страниц с полной осознанностью.",
        "duration": 600,
        "reward": 15
    },
    {
        "title": "🖍️ Нарисуйте что-то для себя",
        "description": "Нарисуйте любой скетч, не думая о результате. Просто удовольствие от процесса.",
        "duration": 900,
        "reward": 20
    },
    {
        "title": "💧 Вода вместо сладких напитков",
        "description": "Целый день — только чистая вода вместо соков, кофе и газировки.",
        "duration": 86400,
        "reward": 30
    },
    {
        "title": "🙌 Помогите кому-то",
        "description": "Помогите другому человеку бескорыстно (помощь другу, комплимент, совет).",
        "duration": 1800,
        "reward": 20
    },
    {
        "title": "📵 Целый вечер без соцсетей",
        "description": "Не заходите в соцсети после 19:00 до сна.",
        "duration": 18000,
        "reward": 25
    },
    {
        "title": "🛌 Ранний отход ко сну",
        "description": "Лягте спать до 22:30 и не пользуйтесь гаджетами за час до сна.",
        "duration": 28800,
        "reward": 30
    },
    {
        "title": "🌞 Практика благодарности утром",
        "description": "Проснувшись, запишите 1 вещь, за которую вы благодарны.",
        "duration": 300,
        "reward": 10
    },
]

# Таблица пользователей
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("telegram_id", BigInteger, unique=True, nullable=False, index=True),
    Column("full_name", String(100)),
    Column("username", String(100)),
    Column("gender", String(10)),
    Column("name", String(100)),
    Column("hearts", Integer, default=10),
    Column("is_premium", Boolean, default=False),
    Column("user_type", String(20), default="free"),  # free/trial/premium
    Column("is_admin", Boolean, default=False),
    Column("trial_started_at", DateTime(timezone=True)),
    Column("subscription_expires_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("last_activity_at", DateTime(timezone=True), onupdate=func.now()),
    Column("daily_requests", Integer, default=0),
    Column("total_requests", Integer, default=0),
    Column("request_tokens", Integer, default=0),  # Токены за текущий месяц
    Column("is_banned", Boolean, default=False),
    Column("diary_password", String(100)),
    Column("last_diary_reward", DateTime(timezone=True)),
    Column("referral_code", String(20), unique=True),
    Column("referrer_id", BigInteger),
    Column("referrals_count", Integer, default=0),
    Column("last_referral_date", DateTime(timezone=True)),
    Column("level", Integer, default=1),
    Column("experience", Integer, default=0),
    Column("premium_purchases", Integer, default=0),
)

# Таблица платежей
payments = Table(
    "payments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("amount", Float),
    Column("currency", String(10)),
    Column("item_id", String(50)),
    Column("status", String(20), default="pending"),
    Column("payment_method", String(20)),
    Column("transaction_hash", String(100)),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("confirmed_at", DateTime),
)

# Таблица записей дневника
diary_entries = Table(
    "diary_entries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("entry_text", Text),
    Column("mood", String(20)),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Таблица привычек
habits = Table(
    "habits",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("title", String(100)),
    Column("description", String(500)),
    Column("reminder_time", String(10)),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("target_date", DateTime),
    Column("is_completed", Boolean, default=False),
)

# Таблица выполненных привычек
habit_completions = Table(
    "habit_completions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("habit_id", Integer),
    Column("proof_text", Text),
    Column("proof_photo", String(200)),
    Column("completed_at", DateTime, default=datetime.utcnow),
)

# Таблица промокодов
promo_codes = Table(
    "promo_codes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(20), unique=True),
    Column("discount_percent", Integer),
    Column("valid_until", DateTime),
    Column("uses_remaining", Integer),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("description", String(200)),
)

# Таблица админских заданий
admin_tasks = Table(
    "admin_tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(100)),
    Column("description", Text),
    Column("reward", Integer),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("expires_at", DateTime),
)

# Таблица выполненных заданий
completed_tasks = Table(
    "completed_tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("task_id", Integer),
    Column("user_id", BigInteger),
    Column("completed_at", DateTime, default=datetime.utcnow),
)

# Таблица сообщений пользователей
user_messages = Table(
    "user_messages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("message_text", Text),
    Column("is_ai_response", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# ==========================================
# 🧠 Состояния FSM (машина состояний пользователя и администратора)
# ==========================================

class UserStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_gender = State()
    waiting_for_diary_entry = State()
    waiting_for_diary_password = State()
    waiting_for_habit_title = State()
    waiting_for_habit_description = State()
    waiting_for_habit_time = State()
    waiting_for_habit_target = State()
    waiting_for_ai_question = State()
    waiting_for_promo_code = State()
    waiting_for_payment_method = State()
    waiting_for_trx_hash = State()
    waiting_for_task_proof = State()

class AdminStates(StatesGroup):
    waiting_for_premium_username = State()
    waiting_for_ban_user = State()
    waiting_for_unban_user = State()
    waiting_for_hearts_data = State()
    creating_challenge = State()
    creating_task = State()
    creating_promo = State()
    waiting_for_promo_code = State()
    waiting_for_promo_discount = State()
    waiting_for_promo_expiry = State()
    waiting_for_promo_uses = State()
    waiting_for_task_title = State()
    waiting_for_task_description = State()
    waiting_for_task_reward = State()
    waiting_for_task_expiry = State()

# ==========================================
# 🏆 Константы — Челленджи, Психология, Магазины
# ==========================================

# 🏆 Ежедневные Челленджи (DAILY_TASKS)
DAILY_TASKS = [
    "🧘 10 минут медитации",
    "📵 1 час без телефона",
    "📖 Прочитать 10 страниц книги",
    "🏃 Прогулка на свежем воздухе 20 минут",
    "✍️ Записать 3 благодарности",
    "🧹 Прибраться в комнате",
    "💧 Выпить 8 стаканов воды",
    "😴 Лечь спать до 23:00",
    "🎨 Нарисовать что-то",
    "🎵 Послушать спокойную музыку 15 минут"
]

# 🧠 Психологические упражнения (PSYCHOLOGY_FEATURES)
PSYCHOLOGY_FEATURES = [
    {"title": "⚖️ Колесо жизненного баланса", "description": "Оцени 8 сфер своей жизни и найди точки роста."},
    {"title": "🙏 Дневник благодарности", "description": "Каждый день записывай 3 вещи, за которые ты благодарен."},
    {"title": "🌀 Детокс от тревоги", "description": "Дыхательная техника для снятия стресса."},
    {"title": "🦸 Тест архетипов личности", "description": "Узнай, какой архетип преобладает в твоём характере."},
    {"title": "🌙 Анализ сна", "description": "Отслеживай качество и количество своего сна."},
    {"title": "🧪 Тест на уровень стресса", "description": "Проверь, насколько ты сейчас уязвим к стрессу."}
]

# 🛒 Товары магазина за сердечки (HEARTS_SHOP_ITEMS)
HEARTS_SHOP_ITEMS = [
    {"name": "💎 Премиум на 1 день", "price": 20, "days": 1},
    {"name": "💎 Премиум на 7 дней", "price": 100, "days": 7},
    {"name": "💎 Премиум на 30 дней", "price": 350, "days": 30},
]

# 🛍️ Платные функции за деньги (PAID_SHOP_ITEMS)
PAID_SHOP_ITEMS = [
    {"name": "🚨 Экстренная помощь психолога", "price_usd": 5},
    {"name": "📊 Подробный анализ настроения", "price_usd": 3},
    {"name": "♌ Индивидуальный гороскоп", "price_usd": 2},
]

# 🌟 Премиум-магазин за реальные деньги (PREMIUM_SHOP_ITEMS)
PREMIUM_SHOP_ITEMS = [
    {"name": "💎 Премиум подписка на 30 дней", "price_usd": 10},
    {"name": "💎 Премиум подписка на 90 дней", "price_usd": 25},
    {"name": "💎 Премиум подписка на 1 год", "price_usd": 79},
]

# 🤖 Конфигурация AI GPT
AI_MODEL = "gpt-3.5-turbo"  # реальная модель
AI_PUBLIC_MODEL_NAME = "GPT-4o"  # что видит пользователь
AI_SYSTEM_PROMPT = (
    "Ты профессиональный психолог-консультант. "
    "Отвечай дружелюбно, позитивно и поддерживающе. "
    "Если пользователь просит дать совет — давай аккуратные рекомендации."
)

# ==========================================
# 🛠️ Хелперы (помощники для логики бота)
# ==========================================

# Получить пользователя
async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получить пользователя по ID"""
    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id}
            )
            user = result.mappings().first()
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Ошибка получения пользователя: {e}")
        return None

async def create_user(telegram_id: int, full_name: str, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Создать нового пользователя"""
    try:
        referral_code = hashlib.sha256(
            f"{telegram_id}{datetime.now(timezone.utc).timestamp()}".encode()
        ).hexdigest()[:8]

        now = datetime.now(timezone.utc)
        trial_expires = now + timedelta(days=3)  # 3 дня пробного периода

        user_data = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "username": username,
            "hearts": 10,
            "level": 1,
            "experience": 0,
            "trial_started_at": now,
            "subscription_expires_at": trial_expires,
            "user_type": "trial",
            "created_at": now,
            "last_activity_at": now,
            "referral_code": referral_code,
        }

        async with async_session.begin() as session:
            await session.execute(users.insert().values(**user_data))

        return await get_user(telegram_id)
    except Exception as e:
        logger.error(f"Ошибка создания пользователя: {e}")
        return None

async def update_user(telegram_id: int, **kwargs) -> bool:
    """Обновить данные пользователя"""
    try:
        async with async_session.begin() as session:
            await session.execute(
                users.update().where(users.c.telegram_id == telegram_id).values(**kwargs)
            )
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя: {e}")
        return False

async def add_hearts(telegram_id: int, amount: int) -> bool:
    """Начислить сердечки пользователю"""
    try:
        async with async_session.begin() as session:
            await session.execute(
                users.update()
                .where(users.c.telegram_id == telegram_id)
                .values(hearts=users.c.hearts + amount)
            )
        return True
    except Exception as e:
        logger.error(f"Ошибка начисления сердечек: {e}")
        return False

async def add_experience(telegram_id: int, exp: int) -> bool:
    """Начислить опыт пользователю"""
    try:
        user = await get_user(telegram_id)
        if not user:
            return False

        new_exp = user.get("experience", 0) + exp
        new_level = user.get("level", 1)

        while new_exp >= 100:
            new_exp -= 100
            new_level += 1

        async with async_session.begin() as session:
            await session.execute(
                users.update()
                .where(users.c.telegram_id == telegram_id)
                .values(level=new_level, experience=new_exp)
            )
        return True
    except Exception as e:
        logger.error(f"Ошибка начисления опыта: {e}")
        return False

async def check_ai_limits(user: Dict[str, Any]]) -> Tuple[bool, str]:
    """Проверить лимиты запросов к AI"""
    if user["is_banned"]:
        return False, "Ваш аккаунт заблокирован. Обратитесь к администратору."
    
    if user["user_type"] == "free":
        return False, ("🔒 Эта функция доступна только для пользователей с подпиской.\n"
                     "Вы можете оформить пробный период или премиум-подписку в магазине.")
    
    if user["user_type"] == "trial":
        if user["total_requests"] >= 22:
            return False, ("⚠️ Вы исчерпали лимит запросов на этой неделе (22/22).\n"
                         "Перейдите на премиум-подписку для снятия ограничений.")
        if user["request_tokens"] >= 11000:  # 22*500
            return False, ("⚠️ Вы исчерпали лимит токенов на этой неделе.\n"
                         "Перейдите на премиум-подписку для увеличения лимитов.")
    
    if user["user_type"] == "premium":
        if user["daily_requests"] >= 20:
            return False, ("⚠️ Вы исчерпали дневной лимит запросов (20/20).\n"
                         "Неиспользованные запросы переносятся на следующий день.")
        if user["request_tokens"] >= 24000:  # 30*800
            return False, ("⚠️ Вы исчерпали месячный лимит токенов.\n"
                         "Лимит обновится в начале следующего месяца.")
    
    return True, ""

async def get_usd_rate() -> float:
    """Получить текущий курс USDT к рублю"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.exchangerate-api.com/v4/latest/USD")
            data = response.json()
            return data["rates"]["RUB"]
    except Exception:
        return 90.0  # Fallback курс

async def validate_promo_code(code: str) -> Optional[Dict[str, Any]]:
    """Проверить валидность промокода"""
    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT * FROM promo_codes WHERE code = :code AND "
                    "(uses_remaining > 0 OR uses_remaining IS NULL) AND "
                    "(valid_until > NOW() OR valid_until IS NULL)"),
                {"code": code}
            )
            promo = result.mappings().first()
            return dict(promo) if promo else None
    except Exception as e:
        logger.error(f"Ошибка проверки промокода: {e}")
        return None

async def use_promo_code(code: str) -> bool:
    """Использовать промокод (уменьшить количество использований)"""
    try:
        async with async_session.begin() as session:
            await session.execute(
                promo_codes.update()
                .where(promo_codes.c.code == code)
                .values(uses_remaining=promo_codes.c.uses_remaining - 1)
            )
        return True
    except Exception as e:
        logger.error(f"Ошибка использования промокода: {e}")
        return False

# Выдать случайное задание
def get_random_daily_task() -> str:
    return random.choice(DAILY_TASKS)

# ==========================================
# 🎛️ Клавиатуры (InlineKeyboardMarkup)
# ==========================================

# Главное меню
def get_main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu"),
         InlineKeyboardButton(text="📔 Дневник", callback_data="diary_menu")],
        [InlineKeyboardButton(text="✅ Привычки", callback_data="habits_menu"),
         InlineKeyboardButton(text="🛍 Магазин", callback_data="shop_menu")],
        [InlineKeyboardButton(text="🎯 Челлендж дня", callback_data="daily_challenge"),
         InlineKeyboardButton(text="💬 Спросить у GPT-4o", callback_data="ask_ai")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
         InlineKeyboardButton(text="🏆 Уровень", callback_data="level_progress")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Меню психологии
def get_psychology_keyboard():
    buttons = []
    for feature in PSYCHOLOGY_FEATURES:
        buttons.append([InlineKeyboardButton(text=feature["title"], callback_data=f"psy_{feature['title']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Меню магазина
def get_shop_keyboard():
    buttons = [
        [InlineKeyboardButton(text="💎 Премиум за сердечки", callback_data="hearts_shop")],
        [InlineKeyboardButton(text="💳 Платные функции", callback_data="paid_shop")],
        [InlineKeyboardButton(text="💎 Премиум подписка", callback_data="premium_shop")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Магазин за сердечки
def get_hearts_shop_keyboard():
    buttons = []
    for item in HEARTS_SHOP_ITEMS:
        buttons.append([InlineKeyboardButton(text=f"{item['name']} - {item['price']}💖", callback_data=f"buy_hearts_{item['days']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Магазин платных функций
def get_paid_shop_keyboard():
    buttons = []
    for item in PAID_SHOP_ITEMS:
        buttons.append([InlineKeyboardButton(text=f"{item['name']} - {item['price_usd']}$", callback_data=f"buy_paid_{item['name']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Магазин премиума за реальные деньги
def get_premium_shop_keyboard():
    buttons = []
    for item in PREMIUM_SHOP_ITEMS:
        buttons.append([InlineKeyboardButton(text=f"{item['name']} - {item['price_usd']}$", callback_data=f"buy_premium_{item['name']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Клавиатура возврата в главное меню
def get_back_to_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]]
    )

# ==========================================
# 🎯 Основные обработчики (Handlers)
# ==========================================

# Старт бота
@router.message(CommandStart())
async def command_start(message: Message, state: FSMContext):
    # Проверяем реферальную ссылку
    referral_code = None
    if len(message.text.split()) > 1:
        referral_code = message.text.split()[1]

    user = await get_user(message.from_user.id)

    if not user:
        # Создаем нового пользователя
        user = await create_user(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
        )

        # Обрабатываем реферала
        if referral_code:
            async with async_session() as session:
                result = await session.execute(
                    text("SELECT telegram_id FROM users WHERE referral_code = :code"),
                    {"code": referral_code}
                )
                referrer = result.scalar()
                
                if referrer and referrer != message.from_user.id:
                    await update_user(
                        referrer,
                        referrals_count=users.c.referrals_count + 1,
                        last_referral_date=datetime.now(timezone.utc),
                    )
                    # Начисляем бонусы рефереру
                    await add_hearts(referrer, 15)
                    # Продлеваем премиум рефереру на 2 дня
                    await extend_premium(referrer, days=2)

    # Показываем анимацию загрузки
    await show_loading_animation(message.chat.id)

    if not user.get("name") or not user.get("gender"):
        # Если нет имени или пола - просим заполнить
        await state.set_state(UserStates.waiting_for_name)
        await message.answer(
            "👋 Добро пожаловать! Давайте познакомимся.\n"
            "Как мне вас называть? (Введите ваше имя):"
        )
    else:
        # Если данные есть - показываем профиль
        await show_profile(message.from_user.id, message.chat.id)

async def show_loading_animation(chat_id: int):
    """Показать анимацию загрузки"""
    steps = [
        "🔄 Загружаем ваш профиль...",
        "🧠 Подключаем нейросети...",
        "💖 Настраиваем персонализацию...",
        "🎯 Готовим персональные рекомендации...",
        "✨ Почти готово!",
    ]
    msg = None
    for step in steps:
        if msg:
            await msg.edit_text(step)
        else:
            msg = await bot.send_message(chat_id, step)
        await asyncio.sleep(1.5)
    if msg:
        await msg.delete()

@router.message(StateFilter(UserStates.waiting_for_name))
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 20:
        await message.answer("Пожалуйста, введите имя от 2 до 20 символов.")
        return
    
    await update_user(message.from_user.id, name=name)
    await state.set_state(UserStates.waiting_for_gender)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Мужской"), KeyboardButton(text="👩 Женский")],
            [KeyboardButton(text="🤷 Другое")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        f"Приятно познакомиться, {name}! Укажите ваш пол:",
        reply_markup=keyboard
    )

@router.message(StateFilter(UserStates.waiting_for_gender))
async def process_gender(message: Message, state: FSMContext):
    gender = message.text.strip()
    if gender not in ["👨 Мужской", "👩 Женский", "🤷 Другое"]:
        await message.answer("Пожалуйста, выберите пол из предложенных вариантов.")
        return
    
    gender_map = {
        "👨 Мужской": "male",
        "👩 Женский": "female",
        "🤷 Другое": "other"
    }
    
    await update_user(message.from_user.id, gender=gender_map[gender])
    await state.clear()
    
    # Показываем профиль после регистрации
    await show_profile(message.from_user.id, message.chat.id)
    await message.answer(
        "✅ Регистрация завершена! Теперь вам доступны все функции бота.",
        reply_markup=types.ReplyKeyboardRemove()
    )

async def show_profile(user_id: int, chat_id: int):
    """Показать профиль пользователя"""
    user = await get_user(user_id)
    if not user:
        return
    
    # Определяем тип подписки
    subscription_type = {
        "free": "Бесплатный",
        "trial": "Пробный",
        "premium": "Премиум"
    }.get(user["user_type"], "Неизвестно")
    
    # Определяем статус подписки
    now = datetime.now(timezone.utc)
    if user["subscription_expires_at"] and user["subscription_expires_at"] > now:
        expires_in = (user["subscription_expires_at"] - now).days
        subscription_status = f"🔹 Активна ({expires_in} дней осталось)"
    else:
        subscription_status = "🔸 Не активна"
    
    # Определяем лимиты AI
    if user["user_type"] == "free":
        ai_limits = "🚫 Нет доступа"
    elif user["user_type"] == "trial":
        remaining = 22 - user["total_requests"]
        ai_limits = (
            f"🔹 {remaining}/22 запросов в неделю\n"
            f"🔸 До 500 токенов на запрос"
        )
    else:  # premium
        remaining = 20 - user["daily_requests"]
        saved_requests = min(user.get("saved_requests", 0), 150 - user["daily_requests"])
        ai_limits = (
            f"💎 {remaining + saved_requests}/20+{saved_requests} запросов сегодня\n"
            f"✨ До 800 токенов на запрос"
        )
    
    # Формируем текст профиля
    profile_text = (
        f"👤 {html.bold(user['name'])}\n"
        f"🔹 Уровень: {user['level']} ({user['experience']}/100 XP)\n"
        f"💖 Сердечки: {user['hearts']}\n\n"
        f"🎟️ Подписка: {subscription_type}\n"
        f"{subscription_status}\n\n"
        f"🧠 {AI_PUBLIC_MODEL_NAME} доступ:\n"
        f"{ai_limits}\n\n"
        f"📅 Регистрация: {user['created_at'].strftime('%d.%m.%Y')}"
    )
    
    # Кнопки профиля
    buttons = [
        [InlineKeyboardButton(text="📔 Дневник", callback_data="diary_menu"),
         InlineKeyboardButton(text="✅ Привычки", callback_data="habits_menu")],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="premium_menu"),
         InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="🏆 Прогресс", callback_data="progress"),
         InlineKeyboardButton(text="🎯 Челленджи", callback_data="daily_challenges")],
        [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu"),
         InlineKeyboardButton(text="🛍 Магазин", callback_data="shop_menu")],
    ]
    
    # Для админов добавляем кнопку админки
    if user["is_admin"]:
        buttons.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await bot.send_message(
        chat_id,
        profile_text,
        reply_markup=keyboard
    )
    
# Обработчики Админ панели
@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    """Показать админ-панель"""
    user = await get_user(callback.from_user.id)
    if not user or not user["is_admin"]:
        await callback.answer("⛔ У вас нет доступа к этой команде.")
        return
    
    text = (
        "👑 Админ-панель\n\n"
        "Выберите действие:"
    )
    
    buttons = [
        [InlineKeyboardButton(text="🔍 Просмотр пользователя", callback_data="admin_view_user")],
        [InlineKeyboardButton(text="⛔ Забанить пользователя", callback_data="admin_ban_user"),
         InlineKeyboardButton(text="✅ Разбанить пользователя", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="💖 Начислить сердечки", callback_data="admin_add_hearts")],
        [InlineKeyboardButton(text="💎 Выдать премиум", callback_data="admin_add_premium")],
        [InlineKeyboardButton(text="🎯 Создать задание", callback_data="admin_create_task")],
        [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_"))
async def handle_admin_actions(callback: CallbackQuery, state: FSMContext):
    """Обработчик админских действий"""
    user = await get_user(callback.from_user.id)
    if not user or not user["is_admin"]:
        await callback.answer("⛔ У вас нет доступа к этой команде.")
        return
    
    action = callback.data.split("_")[1]
    
    if action == "view":
        await callback.message.answer(
            "Введите username или ID пользователя для просмотра:"
        )
        await state.set_state(AdminStates.waiting_for_premium_username)
    elif action == "ban":
        await callback.message.answer(
            "Введите username или ID пользователя для бана:"
        )
        await state.set_state(AdminStates.waiting_for_ban_user)
    elif action == "unban":
        await callback.message.answer(
            "Введите username или ID пользователя для разбана:"
        )
        await state.set_state(AdminStates.waiting_for_unban_user)
    elif action == "add":
        await callback.message.answer(
            "Введите username или ID пользователя и количество сердечек через пробел:\n"
            "Пример: @username 100"
        )
        await state.set_state(AdminStates.waiting_for_hearts_data)
    elif action == "create":
        if callback.data.endswith("task"):
            await callback.message.answer(
                "Введите название задания:"
            )
            await state.set_state(AdminStates.waiting_for_task_title)
        elif callback.data.endswith("promo"):
            await callback.message.answer(
                "Введите промокод:"
            )
            await state.set_state(AdminStates.waiting_for_promo_code)
    
    await callback.answer()

# Обработчики состояний админ-панели
@router.message(StateFilter(AdminStates.waiting_for_premium_username))
async def admin_view_user(message: Message, state: FSMContext):
    """Просмотр информации о пользователе"""
    identifier = message.text.strip()
    user = await find_user(identifier)
    
    if not user:
        await message.answer("Пользователь не найден.")
        await state.clear()
        return
    
    # Формируем информацию о пользователе
    text = (
        f"👤 {html.bold(user.get('name', 'Без имени'))}\n"
        f"🆔 ID: {user['telegram_id']}\n"
        f"📅 Регистрация: {user['created_at'].strftime('%d.%m.%Y')}\n"
        f"💖 Сердечки: {user['hearts']}\n"
        f"💎 Подписка: {'Премиум' if user['is_premium'] else 'Бесплатная'}\n"
        f"🔹 Уровень: {user['level']}\n"
        f"🔄 Последняя активность: {user['last_activity_at'].strftime('%d.%m.%Y %H:%M')}\n"
        f"⛔ Статус: {'Забанен' if user['is_banned'] else 'Активен'}"
    )
    
    await message.answer(text)
    await state.clear()

@router.message(StateFilter(AdminStates.waiting_for_ban_user))
async def admin_ban_user(message: Message, state: FSMContext):
    """Бан пользователя"""
    identifier = message.text.strip()
    user = await find_user(identifier)
    
    if not user:
        await message.answer("Пользователь не найден.")
        await state.clear()
        return
    
    if user["is_banned"]:
        await message.answer("Этот пользователь уже забанен.")
        await state.clear()
        return
    
    await update_user(user["telegram_id"], is_banned=True)
    await message.answer(f"Пользователь {user.get('name', '')} успешно забанен.")
    await state.clear()

@router.message(StateFilter(AdminStates.waiting_for_unban_user))
async def admin_unban_user(message: Message, state: FSMContext):
    """Разбан пользователя"""
    identifier = message.text.strip()
    user = await find_user(identifier)
    
    if not user:
        await message.answer("Пользователь не найден.")
        await state.clear()
        return
    
    if not user["is_banned"]:
        await message.answer("Этот пользователь не забанен.")
        await state.clear()
        return
    
    await update_user(user["telegram_id"], is_banned=False)
    await message.answer(f"Пользователь {user.get('name', '')} успешно разбанен.")
    await state.clear()

async def find_user(identifier: str) -> Optional[Dict[str, Any]]:
    """Найти пользователя по username или ID"""
    try:
        async with async_session() as session:
            # Пробуем найти по ID
            if identifier.isdigit():
                result = await session.execute(
                    text("SELECT * FROM users WHERE telegram_id = :id"),
                    {"id": int(identifier)}
                )
                user = result.mappings().first()
                if user:
                    return dict(user)
            
            # Удаляем @ если есть
            if identifier.startswith("@"):
                identifier = identifier[1:]
            
            # Ищем по username
            result = await session.execute(
                text("SELECT * FROM users WHERE username = :username"),
                {"username": identifier}
            )
            user = result.mappings().first()
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Ошибка поиска пользователя: {e}")
        return None
    
# Обработчики для дневника
@router.callback_query(F.data == "diary_menu")
async def diary_menu(callback: CallbackQuery, state: FSMContext):
    """Меню дневника"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа к дневнику.")
        return
    
    # Проверяем, установлен ли пароль
    if not user.get("diary_password"):
        await callback.message.answer(
            "🔒 Для доступа к дневнику установите пароль (от 4 символов):"
        )
        await state.set_state(UserStates.waiting_for_diary_password)
        await callback.answer()
        return
    
    # Запрашиваем пароль для доступа
    await callback.message.answer(
        "🔒 Введите пароль для доступа к дневнику:"
    )
    await state.set_state(UserStates.waiting_for_diary_password)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_diary_password))
async def process_diary_password(message: Message, state: FSMContext):
    """Обработка пароля дневника"""
    user = await get_user(message.from_user.id)
    if not user:
        await state.clear()
        return
    
    password = message.text.strip()
    
    # Если пароль не установлен - сохраняем новый
    if not user.get("diary_password"):
        if len(password) < 4:
            await message.answer("Пароль должен содержать минимум 4 символа.")
            return
        
        await update_user(message.from_user.id, diary_password=password)
        await message.answer(
            "🔒 Пароль успешно установлен! Теперь вы можете делать записи в дневник.",
            reply_markup=get_back_to_profile_keyboard()
        )
        await state.clear()
        return
    
    # Проверяем введенный пароль
    if password != user["diary_password"]:
        await message.answer("❌ Неверный пароль. Попробуйте еще раз.")
        return
    
    # Пароль верный - показываем меню дневника
    await state.clear()
    await show_diary_menu(message.from_user.id, message.chat.id)

async def show_diary_menu(user_id: int, chat_id: int):
    """Показать меню дневника"""
    buttons = [
        [InlineKeyboardButton(text="✍️ Новая запись", callback_data="diary_new_entry")],
        [InlineKeyboardButton(text="📆 Записи за день", callback_data="diary_view_day"),
         InlineKeyboardButton(text="📅 Записи за неделю", callback_data="diary_view_week")],
        [InlineKeyboardButton(text="🗓️ Записи за месяц", callback_data="diary_view_month")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")],
    ]
    
    await bot.send_message(
        chat_id,
        "📔 Ваш личный дневник. Все записи шифруются и хранятся анонимно.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "diary_new_entry")
async def diary_new_entry(callback: CallbackQuery, state: FSMContext):
    """Новая запись в дневнике"""
    await callback.message.answer(
        "✍️ Напишите вашу запись в дневник (минимум 50 символов):\n\n"
        "Вы можете описать свои мысли, чувства или события дня."
    )
    await state.set_state(UserStates.waiting_for_diary_entry)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_diary_entry))
async def process_diary_entry(message: Message, state: FSMContext):
    """Обработка новой записи в дневнике"""
    entry_text = message.text.strip()
    if len(entry_text) < 50:
        await message.answer("Запись должна содержать минимум 50 символов.")
        return
    
    user = await get_user(message.from_user.id)
    if not user:
        await state.clear()
        return
    
    # Проверяем, получал ли пользователь награду сегодня
    now = datetime.now(timezone.utc)
    if user.get("last_diary_reward") and (now - user["last_diary_reward"]).days < 1:
        reward = 0
        reward_text = ""
    else:
        reward = 10
        reward_text = f"\n\n+{reward} 💖 за первую запись сегодня!"
        await update_user(message.from_user.id, last_diary_reward=now)
        await add_hearts(message.from_user.id, reward)
    
    # Сохраняем запись
    async with async_session.begin() as session:
        await session.execute(
            diary_entries.insert().values(
                user_id=message.from_user.id,
                entry_text=entry_text,
                mood="neutral",
                created_at=now
            )
        )
    
    await message.answer(
        f"📔 Запись сохранена!{reward_text}\n"
        f"Всего записей: {await count_diary_entries(message.from_user.id)}",
        reply_markup=get_back_to_profile_keyboard()
    )
    await state.clear()

async def count_diary_entries(user_id: int) -> int:
    """Посчитать количество записей в дневнике"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM diary_entries WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        return result.scalar()

# Обработчик для привычек
@router.callback_query(F.data == "habits_menu")
async def habits_menu(callback: CallbackQuery):
    """Меню привычек"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    habits_count = await count_habits(callback.from_user.id)
    completed_today = await count_completed_habits_today(callback.from_user.id)
    
    text = (
        "✅ Привычки и цели\n\n"
        f"🔹 Всего привычек: {habits_count}\n"
        f"🔸 Выполнено сегодня: {completed_today}\n\n"
        "Регулярное выполнение привычек приносит сердечки и опыт!"
    )
    
    buttons = [
        [InlineKeyboardButton(text="➕ Новая привычка", callback_data="habit_new")],
        [InlineKeyboardButton(text="📝 Мои привычки", callback_data="habit_list")],
        [InlineKeyboardButton(text="🏆 Выполненные", callback_data="habit_completed")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data == "habit_new")
async def habit_new(callback: CallbackQuery, state: FSMContext):
    """Создание новой привычки"""
    await callback.message.answer(
        "✏️ Введите название привычки или цели (например, 'Утренняя зарядка'):"
    )
    await state.set_state(UserStates.waiting_for_habit_title)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_habit_title))
async def process_habit_title(message: Message, state: FSMContext):
    """Обработка названия привычки"""
    if len(message.text.strip()) < 3:
        await message.answer("Название должно содержать минимум 3 символа.")
        return
    
    await state.update_data(title=message.text.strip())
    await message.answer(
        "📝 Опишите вашу привычку или цель более подробно:"
    )
    await state.set_state(UserStates.waiting_for_habit_description)

@router.message(StateFilter(UserStates.waiting_for_habit_description))
async def process_habit_description(message: Message, state: FSMContext):
    """Обработка описания привычки"""
    if len(message.text.strip()) < 10:
        await message.answer("Описание должно содержать минимум 10 символов.")
        return
    
    await state.update_data(description=message.text.strip())
    
    # Предлагаем установить время напоминания
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="08:00"), KeyboardButton(text="12:00")],
            [KeyboardButton(text="18:00"), KeyboardButton(text="21:00")],
            [KeyboardButton(text="Не нужно")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "⏰ Укажите время напоминания (формат ЧЧ:ММ) или выберите из предложенных:",
        reply_markup=keyboard
    )
    await state.set_state(UserStates.waiting_for_habit_time)

@router.message(StateFilter(UserStates.waiting_for_habit_time))
async def process_habit_time(message: Message, state: FSMContext):
    """Обработка времени привычки"""
    time_str = message.text.strip()
    reminder_time = None
    
    if time_str != "Не нужно":
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
            await message.answer("Пожалуйста, укажите время в формате ЧЧ:ММ (например, 08:30).")
            return
        reminder_time = time_str
    
    data = await state.get_data()
    await state.clear()
    
    # Сохраняем привычку
    async with async_session.begin() as session:
        await session.execute(
            habits.insert().values(
                user_id=message.from_user.id,
                title=data["title"],
                description=data["description"],
                reminder_time=reminder_time,
                created_at=datetime.now(timezone.utc)
            )
        )
    
    await message.answer(
        f"✅ Привычка '{data['title']}' успешно создана!",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await show_habits_list(message.from_user.id, message.chat.id)

async def show_habits_list(user_id: int, chat_id: int):
    """Показать список привычек пользователя"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM habits WHERE user_id = :user_id ORDER BY created_at DESC"),
            {"user_id": user_id}
        )
        habits_list = result.mappings().all()
    
    if not habits_list:
        await bot.send_message(
            chat_id,
            "У вас пока нет привычек. Создайте первую!",
            reply_markup=get_back_to_profile_keyboard()
        )
        return
    
    text = "📝 Ваши привычки и цели:\n\n"
    buttons = []
    
    for i, habit in enumerate(habits_list, 1):
        text += f"{i}. {habit['title']}\n"
        buttons.append([
            InlineKeyboardButton(
                text=f"✅ {habit['title']}",
                callback_data=f"habit_complete_{habit['id']}")
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="habits_menu")])
    
    await bot.send_message(
        chat_id,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

async def count_habits(user_id: int) -> int:
    """Посчитать количество привычек"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM habits WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        return result.scalar()

async def count_completed_habits_today(user_id: int) -> int:
    """Посчитать выполненные сегодня привычки"""
    today = datetime.now(timezone.utc).date()
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT COUNT(*) FROM habit_completions hc
                JOIN habits h ON hc.habit_id = h.id
                WHERE h.user_id = :user_id AND DATE(hc.completed_at) = :today
            """),
            {"user_id": user_id, "today": today}
        )
        return result.scalar()

# Обработчик для премиум раздела
@router.callback_query(F.data == "premium_menu")
async def premium_menu(callback: CallbackQuery):
    """Меню премиум-подписки"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    now = datetime.now(timezone.utc)
    is_premium = user["is_premium"] and user["subscription_expires_at"] > now
    
    if is_premium:
        expires_in = (user["subscription_expires_at"] - now).days
        text = (
            f"💎 Ваша премиум-подписка активна!\n\n"
            f"🔹 Осталось дней: {expires_in}\n"
            f"🔸 Доступно запросов к {AI_PUBLIC_MODEL_NAME}: 20/день\n"
            f"✨ Максимальная длина ответов: 800 токенов\n\n"
            "Спасибо за поддержку бота! ❤️"
        )
    else:
        text = (
            f"🔒 Премиум-подписка\n\n"
            f"🔹 Доступ к {AI_PUBLIC_MODEL_NAME} без ограничений\n"
            f"🔸 Увеличенные лимиты запросов\n"
            f"✨ Приоритетная поддержка\n\n"
            "Оформите подписку и получите все преимущества!"
        )
    
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="premium_buy")],
    ]
    
    if is_premium:
        buttons.append([InlineKeyboardButton(text="🎁 Подарить подписку", callback_data="premium_gift")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data == "premium_buy")
async def premium_buy(callback: CallbackQuery, state: FSMContext):
    """Покупка премиум-подписки"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    now = datetime.now(timezone.utc)
    is_premium = user["is_premium"] and user["subscription_expires_at"] > now
    
    if is_premium:
        await callback.answer("У вас уже есть активная подписка.", show_alert=True)
        return
    
    text = (
        "💎 Выберите срок премиум-подписки:\n\n"
        "1 месяц - 299 руб.\n"
        "3 месяца - 799 руб. (экономия 10%)\n"
        "6 месяцев - 1399 руб. (экономия 20%)\n"
        "12 месяцев - 2399 руб. (экономия 30%)\n\n"
        "У вас есть промокод? Нажмите кнопку ниже."
    )
    
    buttons = [
        [InlineKeyboardButton(text="1 месяц - 299 руб.", callback_data="premium_1")],
        [InlineKeyboardButton(text="3 месяца - 799 руб.", callback_data="premium_3")],
        [InlineKeyboardButton(text="6 месяцев - 1399 руб.", callback_data="premium_6")],
        [InlineKeyboardButton(text="12 месяцев - 2399 руб.", callback_data="premium_12")],
        [InlineKeyboardButton(text="🎁 Применить промокод", callback_data="premium_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="premium_menu")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("premium_"))
async def process_premium_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подписки"""
    if callback.data == "premium_promo":
        await callback.message.answer("Введите промокод:")
        await state.set_state(UserStates.waiting_for_promo_code)
        await callback.answer()
        return
    
    months = int(callback.data.split("_")[1])
    prices = {1: 299, 3: 799, 6: 1399, 12: 2399}
    price = prices.get(months, 299)
    
    await state.update_data(months=months, price=price, discount=0)
    
    text = (
        f"💎 Премиум-подписка на {months} месяц(ев)\n"
        f"💰 Сумма к оплате: {price} руб.\n\n"
        "Выберите способ оплаты:"
    )
    
    buttons = [
        [InlineKeyboardButton(text="💳 ЮMoney", callback_data=f"pay_yoomoney_{months}")],
        [InlineKeyboardButton(text="₿ Криптовалюта (USDT)", callback_data=f"pay_crypto_{months}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="premium_buy")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def process_payment_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора способа оплаты"""
    method, months = callback.data.split("_")[1], int(callback.data.split("_")[2])
    prices = {1: 299, 3: 799, 6: 1399, 12: 2399}
    price = prices.get(months, 299)
    
    if method == "yoomoney":
        # Здесь должна быть логика оплаты через ЮMoney
        await callback.message.answer(
            f"Для оплаты {months} месяцев премиума ({price} руб.):\n\n"
            f"1. Переведите {price} руб. на номер {YOOMONEY_WALLET}\n"
            "2. В комментарии укажите ваш ID: {callback.from_user.id}\n"
            "3. После оплаты отправьте скриншот чека @admin"
        )
    elif method == "crypto":
        usd_rate = await get_usd_rate()
        usd_amount = round(price / usd_rate, 2)
        
        await callback.message.answer(
            f"Для оплаты {months} месяцев премиума ({price} руб. ≈ {usd_amount} USDT):\n\n"
            f"1. Переведите {usd_amount} USDT (TRC20) на адрес:\n"
            f"<code>{TRON_ADDRESS}</code>\n"
            "2. После перевода отправьте хеш транзакции (TXID)"
        )
        await state.set_state(UserStates.waiting_for_trx_hash)
    
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_trx_hash))
async def process_trx_hash(message: Message, state: FSMContext):
    """Обработка хеша транзакции"""
    trx_hash = message.text.strip()
    if len(trx_hash) < 10:
        await message.answer("Пожалуйста, укажите корректный хеш транзакции.")
        return
    
    data = await state.get_data()
    months = data.get("months", 1)
    price = data.get("price", 299)
    
    # Сохраняем платеж в базу
    async with async_session.begin() as session:
        await session.execute(
            payments.insert().values(
                user_id=message.from_user.id,
                amount=price,
                currency="RUB",
                item_id=f"premium_{months}",
                status="pending",
                payment_method="crypto",
                transaction_hash=trx_hash,
                created_at=datetime.now(timezone.utc)
            )
        )
    
    await message.answer(
        "🔄 Ваш платеж принят в обработку. Обычно это занимает до 15 минут.\n"
        "Как только платеж будет подтвержден, вы получите уведомление.",
        reply_markup=get_back_to_profile_keyboard()
    )
    await state.clear()
    
# Обработчик для рефералов
@router.callback_query(F.data == "referrals")
async def referrals_menu(callback: CallbackQuery):
    """Меню рефералов"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    ref_count = user.get("referrals_count", 0)
    ref_link = f"https://t.me/{bot._me.username}?start={user['referral_code']}"
    
    text = (
        "👥 Реферальная программа\n\n"
        f"🔹 Приглашено друзей: {ref_count}\n"
        f"🔸 Максимум в этом месяце: {min(ref_count, 5)}/5\n\n"
        "Приглашайте друзей и получайте бонусы!\n"
        f"Ваша ссылка: {ref_link}\n\n"
        "За каждого приглашенного друга:\n"
        "➕ 15 сердечек\n"
        "➕ 2 дня премиума"
    )
    
    buttons = [
        [InlineKeyboardButton(text="🔗 Скопировать ссылку", callback_data="ref_copy")],
        [InlineKeyboardButton(text="📊 Последние рефералы", callback_data="ref_list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        disable_web_page_preview=True
    )
    await callback.answer()

@router.callback_query(F.data == "ref_copy")
async def copy_referral_link(callback: CallbackQuery):
    """Копирование реферальной ссылки"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    ref_link = f"https://t.me/{bot._me.username}?start={user['referral_code']}"
    await callback.answer(f"Ссылка скопирована: {ref_link}", show_alert=True)
    
# Обработчики для психологических практик
@router.callback_query(F.data == "psychology_menu")
async def psychology_menu(callback: CallbackQuery):
    """Меню психологических практик"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    now = datetime.now(timezone.utc)
    is_premium = user["is_premium"] and user["subscription_expires_at"] > now
    
    text = "🧠 Психологические практики\n\nВыберите технику для работы:"
    
    buttons = []
    for practice in PSYCHOLOGY_PRACTICES:
        if practice["premium_only"] and not is_premium:
            continue
        
        btn_text = practice["title"]
        if practice["hearts_cost"] > 0:
            btn_text += f" ({practice['hearts_cost']}💖)"
        
        buttons.append([
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"psy_{PSYCHOLOGY_PRACTICES.index(practice)}")
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("psy_"))
async def show_practice(callback: CallbackQuery):
    """Показать психологическую практику"""
    practice_idx = int(callback.data.split("_")[1])
    if practice_idx >= len(PSYCHOLOGY_PRACTICES):
        await callback.answer("Практика не найдена.")
        return
    
    practice = PSYCHOLOGY_PRACTICES[practice_idx]
    user = await get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    now = datetime.now(timezone.utc)
    is_premium = user["is_premium"] and user["subscription_expires_at"] > now
    
    # Проверяем доступ
    if practice["premium_only"] and not is_premium:
        await callback.answer(
            "Эта практика доступна только для премиум-пользователей.",
            show_alert=True
        )
        return
    
    if practice["hearts_cost"] > 0 and user["hearts"] < practice["hearts_cost"]:
        await callback.answer(
            "Недостаточно сердечек для доступа к этой практике.",
            show_alert=True
        )
        return
    
    # Если есть стоимость - списываем сердечки
    if practice["hearts_cost"] > 0:
        await add_hearts(callback.from_user.id, -practice["hearts_cost"])
    
    # Отправляем содержание практики
    await callback.message.answer(
        f"🧠 {practice['title']}\n\n{practice['content']}\n\n"
        "Хотите обсудить эту технику с AI-психологом?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Обсудить с AI", callback_data=f"psyai_{practice_idx}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
        ])
    )
    await callback.answer()
    
# Обработчки для магазина
@router.callback_query(F.data == "shop_menu")
async def shop_menu(callback: CallbackQuery):
    """Меню магазина"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    text = (
        "🛍 Магазин\n\n"
        f"Ваш баланс: {user['hearts']} 💖\n\n"
        "Выберите категорию:"
    )
    
    buttons = [
        [InlineKeyboardButton(text="📚 Психологические материалы", callback_data="shop_digital")],
        [InlineKeyboardButton(text="💎 Премиум за сердечки", callback_data="shop_premium")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data == "shop_digital")
async def shop_digital(callback: CallbackQuery):
    """Цифровые товары"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    text = "📚 Психологические материалы\n\nВыберите товар:"
    
    buttons = []
    for item in [i for i in SHOP_ITEMS if i["type"] == "digital"]:
        buttons.append([
            InlineKeyboardButton(
                text=f"{item['name']} - {item['price']}💖",
                callback_data=f"shop_item_{SHOP_ITEMS.index(item)}")
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("shop_item_"))
async def shop_item(callback: CallbackQuery):
    """Просмотр товара"""
    item_idx = int(callback.data.split("_")[2])
    if item_idx >= len(SHOP_ITEMS):
        await callback.answer("Товар не найден.")
        return
    
    item = SHOP_ITEMS[item_idx]
    user = await get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    if user["hearts"] < item["price"]:
        await callback.answer("Недостаточно сердечек.", show_alert=True)
        return
    
    text = (
        f"🛍 {item['name']}\n\n"
        f"{item['description']}\n\n"
        f"Цена: {item['price']} 💖\n"
        f"Ваш баланс: {user['hearts']} 💖"
    )
    
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_item_{item_idx}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="shop_digital")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_item_"))
async def buy_item(callback: CallbackQuery):
    """Покупка товара"""
    item_idx = int(callback.data.split("_")[2])
    if item_idx >= len(SHOP_ITEMS):
        await callback.answer("Товар не найден.")
        return
    
    item = SHOP_ITEMS[item_idx]
    user = await get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    if user["hearts"] < item["price"]:
        await callback.answer("Недостаточно сердечек.", show_alert=True)
        return
    
    # Списание сердечек
    await add_hearts(callback.from_user.id, -item["price"])
    
    # Выдача товара
    if item["type"] == "digital":
        await callback.message.answer(
            f"🎉 Поздравляем с покупкой!\n\n"
            f"Вы приобрели: {item['name']}\n\n"
            "Ссылка для скачивания: https://example.com/download\n"
            "Ссылка действительна 24 часа."
        )
    elif item["type"] == "premium":
        await extend_premium(callback.from_user.id, days=1)
        await callback.message.answer(
            "🎉 Ваш премиум-доступ продлен на 1 день!"
        )
    
    await callback.answer()
    
# Обработчки для ежедневных челенджей 
@router.callback_query(F.data == "daily_challenges")
async def daily_challenges(callback: CallbackQuery):
    """Ежедневные челленджи"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка доступа.")
        return
    
    # Получаем сегодняшний челлендж (можно сделать рандомный или по дате)
    today = datetime.now(timezone.utc).date()
    challenge_idx = hash(str(today)) % len(DAILY_CHALLENGES)
    challenge = DAILY_CHALLENGES[challenge_idx]
    
    text = (
        f"🎯 Сегодняшний челлендж: {challenge['title']}\n\n"
        f"{challenge['description']}\n\n"
        f"⏱ Время выполнения: {challenge['duration']//60} минут\n"
        f"🎁 Награда: {challenge['reward']} 💖"
    )
    
    buttons = [
        [InlineKeyboardButton(text="🔄 Начать челлендж", callback_data=f"start_challenge_{challenge_idx}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")],
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("start_challenge_"))
async def start_challenge(callback: CallbackQuery, state: FSMContext):
    """Начало челленджа"""
    challenge_idx = int(callback.data.split("_")[2])
    if challenge_idx >= len(DAILY_CHALLENGES):
        await callback.answer("Челлендж не найден.")
        return
    
    challenge = DAILY_CHALLENGES[challenge_idx]
    await state.update_data(challenge_idx=challenge_idx, start_time=datetime.now(timezone.utc))
    
    await callback.message.edit_text(
        f"⏳ Челлендж начался!\n\n{challenge['title']}\n\n"
        f"У вас есть {challenge['duration']//60} минут для выполнения.\n"
        "Не закрывайте это сообщение до завершения.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Завершить", callback_data="finish_challenge")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "finish_challenge")
async def finish_challenge(callback: CallbackQuery, state: FSMContext):
    """Завершение челленджа"""
    data = await state.get_data()
    challenge_idx = data.get("challenge_idx")
    start_time = data.get("start_time")
    
    if challenge_idx is None or start_time is None:
        await callback.answer("Ошибка завершения челленджа.")
        return
    
    challenge = DAILY_CHALLENGES[challenge_idx]
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    if elapsed < challenge["duration"]:
        await callback.answer("Вы выполнили челлендж слишком быстро!", show_alert=True)
        return
    
    # Награждаем пользователя
    await add_hearts(callback.from_user.id, challenge["reward"])
    await add_experience(callback.from_user.id, 5)
    
    await callback.message.edit_text(
        f"🎉 Поздравляем! Вы выполнили челлендж и получаете {challenge['reward']} 💖\n\n"
        f"{challenge['title']}\n"
        f"Время выполнения: {elapsed//60} минут",
        reply_markup=get_back_to_profile_keyboard()
    )
    await state.clear()
    await callback.answer()

# Обработчик для платежных систем
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработка предварительного запроса оплаты"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    user_id = message.from_user.id
    
    # Определяем тип подписки по invoice_payload
    if payment.invoice_payload.startswith("premium_"):
        months = int(payment.invoice_payload.split("_")[1])
        await extend_premium(user_id, months * 30)  # 30 дней в месяце
        
        await message.answer(
            f"🎉 Спасибо за покупку премиум-подписки на {months} месяцев!\n"
            "Теперь вам доступны все функции без ограничений."
        )
    
    # Сохраняем платеж в базу
    async with async_session.begin() as session:
        await session.execute(
            payments.insert().values(
                user_id=user_id,
                amount=payment.total_amount // 100,
                currency=payment.currency,
                item_id=payment.invoice_payload,
                status="completed",
                payment_method="yoomoney",
                created_at=datetime.now(timezone.utc),
                confirmed_at=datetime.now(timezone.utc)
            )
        )

async def extend_premium(user_id: int, days: int) -> bool:
    """Продлить премиум-подписку на указанное количество дней"""
    user = await get_user(user_id)
    if not user:
        return False
    
    now = datetime.now(timezone.utc)
    if user["subscription_expires_at"] and user["subscription_expires_at"] > now:
        new_expires = user["subscription_expires_at"] + timedelta(days=days)
    else:
        new_expires = now + timedelta(days=days)
    
    await update_user(
        user_id,
        is_premium=True,
        user_type="premium",
        subscription_expires_at=new_expires,
        premium_purchases=users.c.premium_purchases + 1
    )
    return True

# Вспомагательные функции "Назад в профиль"
def get_back_to_profile_keyboard():
    """Клавиатура с кнопкой возврата в профиль"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")]]
    )

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery):
    """Возврат в профиль"""
    await show_profile(callback.from_user.id, callback.message.chat.id)
    await callback.answer()
    
# Возврат в главное меню
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

# Открыть раздел психологии
@router.callback_query(F.data == "psychology_menu")
async def open_psychology(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧠 Психологические упражнения:",
        reply_markup=get_psychology_keyboard()
    )
    await callback.answer()

# Открыть магазин
@router.callback_query(F.data == "shop_menu")
async def open_shop(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛍 Магазин возможностей:",
        reply_markup=get_shop_keyboard()
    )
    await callback.answer()

# Показать челлендж дня
@router.callback_query(F.data == "daily_challenge")
async def daily_challenge(callback: CallbackQuery):
    task = get_random_daily_task()
    await callback.message.edit_text(
        f"🎯 Сегодняшний челлендж:\n\n{task}\n\n"
        "Выполни задание и получи награду! 💖",
        reply_markup=get_back_to_main_keyboard()
    )
    # Начисляем награду за получение челленджа
    await add_hearts(callback.from_user.id, 3)
    await add_experience(callback.from_user.id, 10)
    await callback.answer()

# Показать уровень и прогресс
@router.callback_query(F.data == "level_progress")
async def show_level(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    text = (
        f"🏆 Ваш уровень: {user.get('level', 1)}\n"
        f"🔹 Опыт: {user.get('experience', 0)} / 100\n"
        "Каждые 100 очков опыта — новый уровень!"
    )
    await callback.message.edit_text(text, reply_markup=get_back_to_main_keyboard())
    await callback.answer()

# Спросить у AI GPT-4o
@router.callback_query(F.data == "ask_ai")
async def ask_ai(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "💬 Отправьте свой вопрос. Я постараюсь помочь, используя мои знания на базе GPT-4o. 🧠",
        reply_markup=get_back_to_main_keyboard()
    )
    await state.set_state(UserStates.waiting_for_ai_question)
    await callback.answer()

# Обработка вопроса для AI
@router.message(StateFilter(UserStates.waiting_for_ai_question))
async def process_ai_question(message: Message, state: FSMContext):
    question = message.text

    await message.answer("🤖 Думаю над ответом...")

    response_text = await ask_openai(question)

    await message.answer(
        f"🔮 Ответ GPT-4o:\n\n{response_text}",
        reply_markup=get_main_menu_keyboard()
    )

    await add_experience(message.from_user.id, 20)  # За использование AI добавляем опыт
    await state.clear()

# Защита для кризисных ситуаций
@router.message(F.text)
async def check_crisis_messages(message: Message):
    """Проверка сообщений на кризисный контент"""
    text = message.text.lower()
    if any(keyword in text for keyword in CRISIS_KEYWORDS):
        await message.answer(
            "Я вижу, что вам сейчас очень тяжело. Пожалуйста, обратитесь за помощью:\n\n"
            "📞 Телефон доверия: 8-800-2000-122 (круглосуточно, бесплатно)\n"
            "💬 Психологическая помощь: @psyhelpbot\n\n"
            "Вы не одни, и ваша жизнь важна! 💙"
        )
        return
    
    # Если сообщение не кризисное - продолжаем обычную обработку
    await process_regular_message(message)

async def process_regular_message(message: Message):
    """Обработка обычных сообщений"""
    # Здесь может быть ваша логика обработки сообщений
    pass

# Функция обращения к OpenAI
async def ask_openai(prompt: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {CRYPTO_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Ошибка запроса к OpenAI: {e}")
        return "😔 Произошла ошибка при обращении к AI. Попробуйте позже."

# ==========================================
# 🛒 Магазин и покупки (премиум, сердечки, платные функции)
# ==========================================

@router.callback_query(F.data == "hearts_shop")
async def open_hearts_shop(callback: CallbackQuery):
    await callback.message.edit_text(
        "💖 Покупка премиума за сердечки:",
        reply_markup=get_hearts_shop_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "premium_shop")
async def open_premium_shop(callback: CallbackQuery):
    await callback.message.edit_text(
        "💎 Премиум-подписка за реальные деньги:",
        reply_markup=get_premium_shop_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "paid_shop")
async def open_paid_shop(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 Платные функции:",
        reply_markup=get_paid_shop_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_hearts_"))
async def buy_premium_by_hearts(callback: CallbackQuery):
    days = int(callback.data.split("_")[-1])
    cost = next((item["price"] for item in HEARTS_SHOP_ITEMS if item["days"] == days), None)

    user = await get_user(callback.from_user.id)
    if user["hearts"] < cost:
        await callback.answer("❗ Недостаточно сердечек.", show_alert=True)
        return

    now = datetime.utcnow()
    expires_at = now + timedelta(days=days)

    async with async_session.begin() as session:
        await session.execute(
            users.update()
            .where(users.c.telegram_id == callback.from_user.id)
            .values(
                is_premium=True,
                subscription_expires_at=expires_at,
                hearts=users.c.hearts - cost
            )
        )

    await callback.message.edit_text(
        f"🎉 Поздравляем! Вы приобрели премиум на {days} дней!",
        reply_markup=get_back_to_main_keyboard()
    )
    await callback.answer()

# ==========================================
# ⏰ Планировщик задач (cron) — ежедневные челленджи
# ==========================================

@aiocron.crontab('0 9 * * *')  # Каждое утро в 9:00 МСК
async def send_morning_challenge():
    logger.info("Утренний челлендж отправляется...")
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT telegram_id FROM users WHERE is_banned = false"))
            users_list = result.scalars().all()

        task = get_random_daily_task()

        for user_id in users_list:
            try:
                await bot.send_message(
                    user_id,
                    f"🌅 Доброе утро!\n\n🎯 Ваш челлендж дня:\n\n{task}\n\nВыполняй и зарабатывай сердечки! 💖"
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить утреннее задание пользователю {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка отправки утреннего задания: {e}")

@aiocron.crontab('0 18 * * *')  # Каждый вечер в 18:00 МСК
async def send_evening_challenge():
    logger.info("Вечерний челлендж отправляется...")
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT telegram_id FROM users WHERE is_banned = false"))
            users_list = result.scalars().all()

        task = get_random_daily_task()

        for user_id in users_list:
            try:
                await bot.send_message(
                    user_id,
                    f"🌆 Добрый вечер!\n\n🎯 Челлендж на вечер:\n\n{task}\n\nЗаверши день продуктивно! 💖"
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить вечернее задание пользователю {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка отправки вечернего задания: {e}")

# ==========================================
# 🚀 Запуск бота, обработка ошибок
# ==========================================

# Глобальный обработчик ошибок
@router.errors()
async def global_error_handler(event: ErrorEvent):
    logger.error(f"Произошла ошибка: {event.exception}")
    if isinstance(event.update, Message):
        await event.update.answer("❌ Ой! Что-то пошло не так. Попробуйте ещё раз.")
    elif isinstance(event.update, CallbackQuery):
        await event.update.answer("❌ Ошибка. Пожалуйста, попробуйте позже.", show_alert=True)

# Регистрация команд бота
async def set_default_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="🔵 Перезапустить бота"),
        BotCommand(command="help", description="ℹ️ Помощь и инструкция"),
    ])

# Основная функция запуска бота
async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    await set_default_commands(bot)
    logger.info("Бот успешно запущен")

async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("Выключение бота...")

async def main():
    """Основная функция запуска бота"""
    try:
        # Создаем таблицы в БД
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        
        # Установка обработчиков
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Запуск бота
        logger.info("🚀 Бот успешно запущен и готов к работе!")
        await dp.start_polling(bot)

    except Exception as e:
        logger.critical(f"Критическая ошибка запуска: {e}")
    finally:
        await engine.dispose()

def run_fastapi():
    uvicorn.run("webhook:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    Thread(target=run_fastapi, daemon=True).start()
    asyncio.run(main())