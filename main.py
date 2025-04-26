import os
import logging
import asyncio
import random
import httpx
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal, getcontext
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F, html
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, 
    InlineKeyboardMarkup, BotCommand, ErrorEvent
)
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.markdown import hide_link

from sqlalchemy import text, MetaData, Table, Column, Integer, String, Boolean, DateTime, BigInteger, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# --- Configuration ---
load_dotenv()

# Decimal precision
getcontext().prec = 8

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

# --- States ---
class UserStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_gender = State()
    waiting_for_diary_entry = State()
    waiting_for_diary_password = State()
    waiting_for_wheel = State()
    waiting_for_detox = State()
    waiting_for_archetype = State()
    waiting_for_gratitude = State()
    waiting_for_promo = State()
    waiting_for_task_completion = State()
    waiting_for_sleep_data = State()

class HabitCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_time = State()

class AdminStates(StatesGroup):
    creating_challenge = State()
    setting_rewards = State()
    waiting_for_premium_username = State()
    waiting_for_ban_user = State()     
    waiting_for_unban_user = State()
    waiting_for_hearts_data = State()
    waiting_for_ban_username = State()
    waiting_for_user_history = State()
    creating_task = State()
    creating_promo = State()

class Config:
    TRIAL_DAYS = 3
    TRIAL_DAILY_LIMIT = 25
    TRIAL_TOKEN_LIMIT = 500
    PREMIUM_DAILY_LIMIT = 20
    PREMIUM_TOKEN_LIMIT = 800
    FREE_WEEKLY_LIMIT = 5
    HEARTS_PER_DAY = 3
    CHALLENGE_REWARD = 5
    CHALLENGE_DURATION = 120
    REFERRAL_REWARD_HEARTS = 10
    REFERRAL_REWARD_DAYS = 2
    MAX_REFERRALS_PER_MONTH = 5
    DIARY_REWARD = 5
    TASK_REWARD_RANGE = (5, 15)

# --- Constants ---
PSYCHOLOGY_FEATURES = [
    {
        "id": "wheel_of_life",
        "title": "⚖️ Колесо баланса",
        "description": "Анализ 8 ключевых сфер жизни. Награда: 30💖",
        "reward": 30,
        "duration": "5-10 минут"
    },
    {
        "id": "detox_anxiety",
        "title": "🌀 Детокс тревоги",
        "description": "3-дневный курс по методике КПТ. Награда: 50💖",
        "reward": 50,
        "duration": "15-20 минут"
    },
    {
        "id": "archetype_test",
        "title": "🦸 Тест архетипов",
        "description": "Определите свой психологический архетип. Награда: 20💖",
        "reward": 20,
        "duration": "5 минут"
    },
    {
        "id": "gratitude_journal",
        "title": "🙏 Дневник благодарности",
        "description": "Формируем привычку благодарности. Награда: 10💖/день",
        "reward": 10,
        "duration": "3-5 минут"
    },
    {
        "id": "sleep_analyzer",
        "title": "🌙 Анализ сна",
        "description": "Оценка качества сна и рекомендации. Награда: 25💖",
        "reward": 25,
        "duration": "5-7 минут"
    },
    {
        "id": "stress_test",
        "title": "🧪 Тест уровня стресса",
        "description": "Определите ваш текущий уровень стресса. Награда: 15💖",
        "reward": 15,
        "duration": "3-5 минут"
    },
    {
        "id": "emotional_diary",
        "title": "🎭 Дневник эмоций",
        "description": "Анализ вашего эмоционального состояния. Награда: 20💖",
        "reward": 20,
        "duration": "7-10 минут"
    },
    {
        "id": "relationship_advice",
        "title": "💞 Советы по отношениям",
        "description": "Рекомендации по улучшению отношений. Награда: 25💖",
        "reward": 25,
        "duration": "10-15 минут"
    }
]

DAILY_TASKS = [
    {
        "id": "meditation",
        "title": "🧘 Медитация 5 минут",
        "description": "Практикуйте осознанность в течение 5 минут",
        "reward": 10
    },
    {
        "id": "gratitude_list",
        "title": "🙏 Список благодарности",
        "description": "Запишите 3 вещи, за которые вы благодарны сегодня",
        "reward": 8
    },
    {
        "id": "water_reminder",
        "title": "💧 Выпить воды",
        "description": "Выпейте стакан воды и запишите, как вы себя чувствуете",
        "reward": 5
    },
    {
        "id": "positive_affirmation",
        "title": "💫 Позитивное утверждение",
        "description": "Повторите 3 позитивных утверждения о себе",
        "reward": 7
    },
    {
        "id": "small_step",
        "title": "👣 Маленький шаг",
        "description": "Сделайте один маленький шаг к вашей цели",
        "reward": 12
    },
    {
        "id": "digital_detox",
        "title": "📵 Цифровой детокс",
        "description": "Проведите 30 минут без гаджетов",
        "reward": 15
    },
    {
        "id": "nature_time",
        "title": "🌳 Время на природе",
        "description": "Проведите хотя бы 10 минут на свежем воздухе",
        "reward": 10
    },
    {
        "id": "kindness_act",
        "title": "🤝 Акт доброты",
        "description": "Совершите один добрый поступок сегодня",
        "reward": 12
    },
    {
        "id": "evening_reflection",
        "title": "🌙 Вечерняя рефлексия",
        "description": "Проанализируйте прошедший день",
        "reward": 10
    },
    {
        "id": "morning_routine",
        "title": "🌅 Утренний ритуал",
        "description": "Выполните ваш утренний ритуал",
        "reward": 8
    }
]

PREMIUM_SHOP_ITEMS = [
    {
        "id": "premium_1_day",
        "title": "💎 Премиум на 1 день",
        "description": "100💖 | Неограниченные запросы",
        "price": 100,
        "type": "hearts"
    },
    {
        "id": "premium_7_days",
        "title": "💎 Премиум на 7 дней",
        "description": "600💖 | Доступ ко всем функциям",
        "price": 600,
        "type": "hearts"
    },
    {
        "id": "premium_1_month",
        "title": "💎 Премиум на 1 месяц",
        "description": "2000💖 | Персональный гид",
        "price": 2000,
        "type": "hearts"
    }
]

HEARTS_SHOP_ITEMS = [
    {
        "id": "custom_analysis",
        "title": "🔍 Персональный анализ",
        "description": "Глубокий анализ ваших записей и привычек",
        "price": 150,
        "type": "hearts"
    },
    {
        "id": "dream_interpretation",
        "title": "🌌 Толкование снов",
        "description": "Анализ ваших снов и их значения",
        "price": 120,
        "type": "hearts"
    },
    {
        "id": "relationship_guide",
        "title": "💑 Гид по отношениям",
        "description": "Персональные рекомендации по отношениям",
        "price": 180,
        "type": "hearts"
    },
    {
        "id": "career_consult",
        "title": "💼 Карьерная консультация",
        "description": "Анализ вашей карьерной ситуации",
        "price": 200,
        "type": "hearts"
    },
    {
        "id": "motivation_boost",
        "title": "🚀 Мотивационный буст",
        "description": "Персональный мотивационный план",
        "price": 100,
        "type": "hearts"
    },
    {
        "id": "sleep_improvement",
        "title": "😴 Улучшение сна",
        "description": "Персональные рекомендации по сну",
        "price": 150,
        "type": "hearts"
    }
]

PAID_SHOP_ITEMS = [
    {
        "id": "emergency_help",
        "title": "🚨 Экстренная помощь",
        "description": "Гид по выходу из кризиса",
        "price": 99,
        "currency": "RUB",
        "details": "Мгновенные рекомендации в сложных ситуациях"
    },
    {
        "id": "personal_guide",
        "title": "🧭 Персональный гид",
        "description": "Индивидуальный план на месяц",
        "price": 149,
        "currency": "RUB",
        "details": "30-дневный персонализированный план развития"
    },
    {
        "id": "mood_analysis",
        "title": "📊 Анализ эмоций",
        "description": "График настроения за 30 дней",
        "price": 129,
        "currency": "RUB",
        "details": "Визуализация вашего эмоционального состояния"
    },
    {
        "id": "horoscope",
        "title": "♌ Гороскоп",
        "description": "Персональный прогноз на месяц",
        "price": 99,
        "currency": "RUB",
        "details": "Детальный астрологический прогноз"
    },
    {
        "id": "anxiety_detox",
        "title": "🧠 Детокс тревоги",
        "description": "3-дневный курс по КПТ",
        "price": 149,
        "currency": "RUB",
        "details": "Пошаговая программа снижения тревожности"
    },
    {
        "id": "deep_analysis",
        "title": "🔮 Глубинный анализ",
        "description": "Анализ всех ваших записей",
        "price": 149,
        "currency": "RUB",
        "details": "Комплексный анализ вашего психологического состояния"
    }
]

PREMIUM_PAID_ITEMS = [
    {
        "id": "premium_1_month",
        "title": "💎 Премиум на 1 месяц",
        "description": "Полный доступ ко всем функциям",
        "price": 299,
        "currency": "RUB",
        "days": 30
    },
    {
        "id": "premium_3_months",
        "title": "💎 Премиум на 3 месяца",
        "description": "Полный доступ + персональный гид",
        "price": 799,
        "currency": "RUB",
        "days": 90
    },
    {
        "id": "premium_6_months",
        "title": "💎 Премиум на 6 месяцев",
        "description": "Полный доступ + приоритетная поддержка",
        "price": 1499,
        "currency": "RUB",
        "days": 180
    },
    {
        "id": "premium_1_year",
        "title": "💎 Премиум на 1 год",
        "description": "Максимальный доступ + бонусы",
        "price": 2599,
        "currency": "RUB",
        "days": 365
    }
]

# Check environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DB_URL")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
CRYPTO_API_KEY = os.getenv("CRYPTO_API_KEY")

if not all([BOT_TOKEN, DB_URL]):
    logger.critical("Missing required environment variables!")
    exit(1)

# --- Bot initialization ---
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Database connection
engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Define users table with all required columns
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("telegram_id", BigInteger, unique=True, nullable=False),
    Column("full_name", String(100)),
    Column("username", String(100)),
    Column("gender", String(10)),
    Column("is_premium", Boolean, default=False),
    Column("hearts", Integer, default=Config.HEARTS_PER_DAY),
    Column("is_admin", Boolean, default=False),
    Column("trial_started_at", DateTime),
    Column("subscription_expires_at", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("last_activity_at", DateTime, default=datetime.utcnow),
    Column("is_banned", Boolean, default=False),
    Column("name", String(100), nullable=True),
    Column("diary_password", String(100), nullable=True),
    Column("daily_requests", Integer, default=0),
    Column("total_requests", Integer, default=0),
    Column("last_diary_reward", DateTime),
    Column("referral_code", String(20), unique=True),
    Column("referrer_id", BigInteger),
    Column("referrals_count", Integer, default=0),
    Column("last_referral_date", DateTime),
    Column("ip_address", String(45))
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
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Таблица дневника
diary_entries = Table(
    "diary_entries",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("entry_text", String(2000)),
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
    Column("reminder_time", String(10), nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Таблица выполненных привычек
habit_completions = Table(
    "habit_completions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("habit_id", Integer),
    Column("completed_at", DateTime, default=datetime.utcnow),
)

# Таблица колеса баланса
wheel_balance = Table(
    "wheel_balance",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("health", Integer),
    Column("relationships", Integer),
    Column("career", Integer),
    Column("finance", Integer),
    Column("spirit", Integer),
    Column("hobbies", Integer),
    Column("environment", Integer),
    Column("growth", Integer),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Add new tables for the additional functionality
user_tasks = Table(
    "user_tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("task_id", String(50)),
    Column("completed_at", DateTime, default=datetime.utcnow),
    Column("reward_received", Boolean, default=False)
)

admin_tasks = Table(
    "admin_tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(100)),
    Column("description", String(500)),
    Column("reward", Integer),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("expires_at", DateTime)
)

promo_codes = Table(
    "promo_codes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(20), unique=True),
    Column("discount_percent", Integer),
    Column("valid_until", DateTime),
    Column("uses_remaining", Integer),
    Column("created_at", DateTime, default=datetime.utcnow)
)

# --- Helper functions ---
def get_archetype_description(archetype: str) -> str:
    """Возвращает описание архетипа"""
    descriptions = {
        'Герой': "Вы стремитесь доказать свою ценность через смелые поступки.",
        'Опекун': "Вы заботитесь о других и защищаете слабых.",
        'Мудрец': "Вы ищете истину и делитесь знаниями с миром.",
        'Искатель': "Вы жаждете свободы и новых впечатлений."
    }
    return descriptions.get(archetype, "Неизвестный архетип")

async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Get user from database"""
    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id}
            )
            user = result.mappings().first()
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

async def update_user(telegram_id: int, **kwargs) -> bool:
    """Update user data"""
    try:
        async with async_session() as session:
            stmt = users.update().where(users.c.telegram_id == telegram_id).values(**kwargs)
            await session.execute(stmt)
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False

async def create_user(telegram_id: int, full_name: str, username: str = None, is_admin: bool = False, referrer_id: int = None) -> Dict[str, Any]:
    """Create new user"""
    try:
        async with async_session() as session:
            # Generate referral code
            referral_code = hashlib.sha256(f"{telegram_id}{datetime.utcnow().timestamp()}".encode()).hexdigest()[:8]
            
            user_data = {
                "telegram_id": telegram_id,
                "full_name": full_name,
                "username": username,
                "is_admin": is_admin,
                "trial_started_at": datetime.utcnow() if not is_admin else None,
                "created_at": datetime.utcnow(),
                "referral_code": referral_code,
                "referrer_id": referrer_id
            }

            result = await session.execute(
                users.insert().values(**user_data).returning(users)
            )
            await session.commit()
            user = dict(result.mappings().first())
            
            # Apply referral rewards if applicable
            if referrer_id:
                await apply_referral_rewards(referrer_id, telegram_id)
            
            return user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise

async def create_diary_entry(user_id: int, entry_text: str, mood: str = None):
    """Создает запись в дневнике"""
    try:
        async with async_session() as session:
            await session.execute(
                diary_entries.insert().values(
                    user_id=user_id,
                    entry_text=entry_text,
                    mood=mood
                )
            )
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Error creating diary entry: {e}")
        return False

async def get_diary_entries(user_id: int, limit: int = 10):
    """Получает записи дневника пользователя"""
    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT * FROM diary_entries WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit"),
                {"user_id": user_id, "limit": limit}
            )
            return [dict(row) for row in result.mappings()]
    except Exception as e:
        logger.error(f"Error getting diary entries: {e}")
        return []

async def create_habit(user_id: int, title: str, description: str, reminder_time: str = None):
    """Создает новую привычку"""
    try:
        async with async_session() as session:
            result = await session.execute(
                habits.insert().values(
                    user_id=user_id,
                    title=title,
                    description=description,
                    reminder_time=reminder_time
                ).returning(habits)
            )
            await session.commit()
            return dict(result.mappings().first())
    except Exception as e:
        logger.error(f"Error creating habit: {e}")
        return None

async def get_user_habits(user_id: int):
    """Получает привычки пользователя"""
    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT * FROM habits WHERE user_id = :user_id ORDER BY created_at DESC"),
                {"user_id": user_id}
            )
            return [dict(row) for row in result.mappings()]
    except Exception as e:
        logger.error(f"Error getting habits: {e}")
        return []

async def complete_habit(habit_id: int):
    """Отмечает привычку как выполненную"""
    try:
        async with async_session() as session:
            await session.execute(
                habit_completions.insert().values(
                    habit_id=habit_id,
                    completed_at=datetime.utcnow()
                )
            )
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Error completing habit: {e}")
        return False

async def save_wheel_balance(user_id: int, scores: Dict[str, int]):
    """Сохраняет результаты колеса баланса"""
    try:
        async with async_session() as session:
            await session.execute(
                wheel_balance.insert().values(
                    user_id=user_id,
                    **scores
                )
            )
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving wheel balance: {e}")
        return False
    
async def apply_referral_rewards(referrer_id: int, new_user_id: int):
    """Apply rewards for referral"""
    try:
        async with async_session() as session:
            # Check if referrer hasn't exceeded monthly limit
            referrer = await get_user(referrer_id)
            if not referrer:
                return
                
            # Check last referral date
            now = datetime.utcnow()
            last_ref_date = referrer.get('last_referral_date')
            
            if last_ref_date and (now - last_ref_date).days < 30:
                if referrer.get('referrals_count', 0) >= Config.MAX_REFERRALS_PER_MONTH:
                    return
            
            # Update referrer stats
            await session.execute(
                users.update()
                .where(users.c.telegram_id == referrer_id)
                .values(
                    referrals_count=users.c.referrals_count + 1,
                    last_referral_date=now,
                    hearts=users.c.hearts + Config.REFERRAL_REWARD_HEARTS,
                    subscription_expires_at=users.c.subscription_expires_at + timedelta(days=Config.REFERRAL_REWARD_DAYS)
                )
            )
            
            # Give new user trial if they don't have one
            new_user = await get_user(new_user_id)
            if not new_user.get('trial_started_at'):
                await session.execute(
                    users.update()
                    .where(users.c.telegram_id == new_user_id)
                    .values(
                        trial_started_at=now,
                        subscription_expires_at=now + timedelta(days=Config.TRIAL_DAYS)
                    )
                )
            
            await session.commit()
    except Exception as e:
        logger.error(f"Error applying referral rewards: {e}")

async def get_user_account_status(user_id: int) -> str:
    """Get user account status (free, trial, premium)"""
    user = await get_user(user_id)
    if not user:
        return "free"
    
    if user.get('is_premium'):
        return "premium"
    
    if user.get('trial_started_at'):
        trial_end = user['trial_started_at'] + timedelta(days=Config.TRIAL_DAYS)
        if datetime.utcnow() < trial_end:
            return "trial"
    
    return "free"

async def check_diary_entry_today(user_id: int) -> bool:
    """Check if user made diary entry today"""
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT 1 FROM diary_entries 
                WHERE user_id = :user_id 
                AND DATE(created_at) = CURRENT_DATE
            """),
            {"user_id": user_id}
        )
        return bool(result.scalar())

async def get_diary_entries_by_period(user_id: int, days: int = None, date: datetime = None):
    """Get diary entries for specific period"""
    try:
        async with async_session() as session:
            query = text("""
                SELECT * FROM diary_entries 
                WHERE user_id = :user_id
            """)
            params = {"user_id": user_id}
            
            if days:
                query = text(f"""
                    {query.text} AND created_at >= NOW() - INTERVAL '{days} days'
                    ORDER BY created_at DESC
                """)
            elif date:
                query = text(f"""
                    {query.text} AND DATE(created_at) = :date
                    ORDER BY created_at DESC
                """)
                params["date"] = date
            else:
                query = text(f"{query.text} ORDER BY created_at DESC LIMIT 7")
            
            result = await session.execute(query, params)
            return [dict(row) for row in result.mappings()]
    except Exception as e:
        logger.error(f"Error getting diary entries: {e}")
        return []

def hash_password(password: str) -> str:
    """Хеширует пароль"""
    return hashlib.sha256(password.encode()).hexdigest()

async def check_diary_password(user_id: int, password: str) -> bool:
    """Проверяет пароль дневника"""
    user = await get_user(user_id)
    if not user or not user.get('diary_password'):
        return False
    return user['diary_password'] == hash_password(password)

# В разделе "Ежедневные активности"
DAILY_TASKS = {
    "diary": {"reward": 10, "min_length": 50},
    "habits": {"reward": 5, "min_count": 1},
    "challenge": {"reward": 20}
}

async def check_daily_tasks(user_id: int):
    """Проверяет выполнение дневных заданий"""
    tasks = {
        "diary": await check_diary_entry(user_id),
        "habits": await check_habits(user_id),
        "challenge": await check_challenge(user_id)
    }
    
    total_reward = 0
    for task, completed in tasks.items():
        if completed:
            total_reward += DAILY_TASKS[task]["reward"]
    
    if total_reward > 0:
        await add_hearts(user_id, total_reward)
        await bot.send_message(
            user_id,
            f"🎉 Вы выполнили задания! Получено: {total_reward}💖"
        )
    
async def check_diary_entry(user_id: int) -> bool:
    """Проверяет, сделал ли пользователь запись в дневнике сегодня"""
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT 1 FROM diary_entries 
                WHERE user_id = :user_id 
                AND DATE(created_at) = CURRENT_DATE
                AND LENGTH(entry_text) >= :min_length
            """),
            {"user_id": user_id, "min_length": DAILY_TASKS["diary"]["min_length"]}
        )
        return bool(result.scalar())

async def check_habits(user_id: int) -> bool:
    """Проверяет, выполнил ли пользователь привычки сегодня"""
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT COUNT(*) FROM habit_completions hc
                JOIN habits h ON hc.habit_id = h.id
                WHERE h.user_id = :user_id
                AND DATE(hc.completed_at) = CURRENT_DATE
            """),
            {"user_id": user_id}
        )
        count = result.scalar()
        return count >= DAILY_TASKS["habits"]["min_count"]

async def check_challenge(user_id: int) -> bool:
    """Проверяет участие в текущем челлендже"""
    # Здесь должна быть логика проверки участия в челлендже
    # В демо-версии возвращаем False
    return False
    
async def add_hearts(user_id: int, amount: int) -> bool:
    """Добавляет сердечки пользователю"""
    user = await get_user(user_id)
    if not user:
        return False
    return await update_user(user_id, hearts=user.get('hearts', 0) + amount)

# Клавиатуры
def get_main_menu_keyboard(user_id: Optional[int] = None):
    """Главное меню со всеми доступными функциями"""
    buttons = [
        # Основные функции
        [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu"),
         InlineKeyboardButton(text="📔 Дневник", callback_data="personal_diary")],
        [InlineKeyboardButton(text="✅ Привычки", callback_data="habits"),
        InlineKeyboardButton(text="📊 Прогресс", callback_data="progress")],
        # Магазин и премиум
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop"),
         InlineKeyboardButton(text="💎 Премиум", callback_data="premium_shop")],
        # Дополнительно
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referral_system"),
         InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ]
    
    buttons.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard():
    """Полная клавиатура администратора"""
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="💎 Выдать премиум", callback_data="admin_premium"),
         InlineKeyboardButton(text="💖 Начислить сердца", callback_data="admin_hearts")],
        [InlineKeyboardButton(text="🚫 Забанить", callback_data="admin_ban"),
         InlineKeyboardButton(text="✅ Разбанить", callback_data="admin_unban")],
        [InlineKeyboardButton(text="📝 Создать задание", callback_data="admin_create_task"),
         InlineKeyboardButton(text="🎁 Создать промо", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_gender_keyboard():
    """Gender selection keyboard"""
    buttons = [
        [InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male")],
        [InlineKeyboardButton(text="👩 Женский", callback_data="gender_female")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_diary_period_keyboard():
    """Diary period selection keyboard"""
    buttons = [
        [InlineKeyboardButton(text="📅 Последние 7 дней", callback_data="diary_7")],
        [InlineKeyboardButton(text="🗓 Последние 30 дней", callback_data="diary_30")],
        [InlineKeyboardButton(text="📆 Выбрать дату", callback_data="diary_custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="personal_diary")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_habit_schedule_keyboard():
    """Habit schedule selection keyboard"""
    buttons = [
        [InlineKeyboardButton(text="⏰ Сегодня", callback_data="habit_today")],
        [InlineKeyboardButton(text="📅 Выбрать дату", callback_data="habit_custom_date")],
        [InlineKeyboardButton(text="🔄 Ежедневно", callback_data="habit_daily")],
        [InlineKeyboardButton(text="🚫 Без напоминания", callback_data="habit_no_reminder")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_payment_keyboard(item_id: str):
    """Premium payment methods keyboard"""
    buttons = [
        [InlineKeyboardButton(text="💳 Криптовалюта (USDT)", callback_data=f"premium_crypto_{item_id}")],
        [InlineKeyboardButton(text="🟣 ЮMoney", callback_data=f"premium_yoomoney_{item_id}")],
        [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data=f"premium_promo_{item_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="premium_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_profile_keyboard():
    """Меню профиля"""
    buttons = [
        [InlineKeyboardButton(text="📔 Личный дневник", callback_data="personal_diary")],
        [InlineKeyboardButton(text="✅ Цели и привычки", callback_data="habits")],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="premium_shop")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_psychology_menu_keyboard():
    """Меню психологии"""
    buttons = [
        [InlineKeyboardButton(text="⚖️ Колесо баланса", callback_data="wheel_of_life")],
        [InlineKeyboardButton(text="🌀 Детокс тревоги", callback_data="detox_anxiety")],
        [InlineKeyboardButton(text="🦸 Тест архетипов", callback_data="archetype_test")],
        [InlineKeyboardButton(text="🙏 Дневник благодарности", callback_data="gratitude_journal")],
        [InlineKeyboardButton(text="🌙 Анализ сна", callback_data="sleep_analyzer")],
        [InlineKeyboardButton(text="🧪 Тест стресса", callback_data="stress_test")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_diary_keyboard():
    """Меню дневника"""
    buttons = [
        [InlineKeyboardButton(text="✍️ Новая запись", callback_data="new_diary_entry")],
        [InlineKeyboardButton(text="📖 Мои записи", callback_data="my_diary_entries")],
        [InlineKeyboardButton(text="🔐 Установить пароль", callback_data="set_diary_password")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_habits_keyboard():
    """Меню привычек"""
    buttons = [
        [InlineKeyboardButton(text="➕ Новая привычка", callback_data="new_habit")],
        [InlineKeyboardButton(text="📊 Мои привычки", callback_data="my_habits")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_shop_keyboard():
    """Меню магазина"""
    buttons = [
        [InlineKeyboardButton(text="💎 Премиум за сердечки", callback_data="premium_shop")],
        [InlineKeyboardButton(text="💰 Платные функции", callback_data="paid_shop")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_premium_shop_keyboard():
    """Магазин премиума"""
    buttons = [
        [InlineKeyboardButton(text=item["title"], callback_data=f"buy_premium_{item['id']}")]
        for item in PREMIUM_SHOP_ITEMS
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_paid_shop_keyboard():
    """Магазин платных функций"""
    buttons = [
        [InlineKeyboardButton(text=item["title"], callback_data=f"buy_paid_{item['id']}")]
        for item in PAID_SHOP_ITEMS
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_methods_keyboard(item_id: str):
    """Методы оплаты"""
    buttons = [
        [InlineKeyboardButton(text="💳 Криптовалюта (USDT)", callback_data=f"pay_crypto_{item_id}")],
        [InlineKeyboardButton(text="🟣 ЮMoney", callback_data=f"pay_yoomoney_{item_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="paid_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Handlers ---
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command with new onboarding flow"""
    try:
        # Обновляем last_activity_at при каждом старте
        await update_user(message.from_user.id, last_activity_at=datetime.utcnow())
        
        loading_msg = await message.answer("🔄 Загрузка настроения...")
        
        # Check if user exists
        user = await get_user(message.from_user.id)
        
        if not user:
            # New user flow
            await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
            
            # Send bot introduction
            intro_text = (
                f"{hide_link('https://example.com/bot-preview.jpg')}"
                "🌟 <b>Добро пожаловать в MindHelper — вашего персонального психологического помощника!</b>\n\n"
                "Я использую передовую технологию GPT-4o, чтобы помочь вам:\n"
                "• Разобраться в своих эмоциях и мыслях\n"
                "• Развить полезные привычки\n"
                "• Улучшить качество жизни\n"
                "• Найти баланс во всех сферах\n\n"
                "📌 <b>Основные функции:</b>\n"
                "🧠 <i>Психологические тесты и анализы</i>\n"
                "📔 <i>Личный дневник с анализом</i>\n"
                "✅ <i>Трекер привычек и целей</i>\n"
                "🎯 <i>Ежедневные задания</i>\n"
                "💎 <i>Премиум-функции</i>\n\n"
                "<b>⚠️ Важно:</b> Я не заменяю профессионального психолога. "
                "В кризисных ситуациях обратитесь к специалисту.\n\n"
                "Для начала, укажите ваш пол:"
            )
            
            await message.answer(
                intro_text,
                reply_markup=get_gender_keyboard()
            )
            await state.set_state(UserStates.waiting_for_gender)
        else:
            # Existing user
            await bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
            await show_main_menu(message.from_user.id, message)
            
    except Exception as e:
        logger.error(f"Error in /start handler: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@router.message(StateFilter(UserStates.waiting_for_name))
async def process_user_name(message: Message, state: FSMContext):
    """Обработка ввода имени пользователя"""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя должно содержать минимум 2 символа. Попробуйте еще раз:")
        return

    await update_user(message.from_user.id, name=name)
    await state.clear()
    
    await message.answer(
        f"✨ Отлично, {name}! Теперь вы можете пользоваться всеми функциями бота.",
        reply_markup=get_main_menu_keyboard()
    )

async def show_main_menu(user_id: int, message: Message):
    """Показывает главное меню с полным доступом ко всем функциям"""
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала используйте /start")
        return

    name = user.get('name', 'друг')
    time_of_day = "доброе утро" if 5 <= datetime.now().hour < 12 else \
                 "добрый день" if 12 <= datetime.now().hour < 18 else \
                 "добрый вечер" if 18 <= datetime.now().hour < 23 else \
                 "доброй ночи"

    # Проверка бана
    if user.get('is_banned'):
        await message.answer(f"⛔ {name}, ваш аккаунт заблокирован.")
        return

    # Админ-панель
    if user.get('is_admin'):
        # Получаем статистику для админа
        async with async_session() as session:
            total_users = (await session.execute(text("SELECT COUNT(*) FROM users"))).scalar()
            active_today = (await session.execute(text(
                "SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE"
            ))).scalar()

        admin_text = (
            f"👑 {time_of_day.capitalize()}, {name} (Админ)\n\n"
            f"📊 Пользователей: {total_users}\n"
            f"🟢 Активных сегодня: {active_today}\n\n"
            "Админ-панель:"
        )

        await message.answer(
            admin_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                # Управление пользователями
                [InlineKeyboardButton(text="👤 Найти пользователя", callback_data="admin_find_user"),
                 InlineKeyboardButton(text="💎 Выдать премиум", callback_data="admin_premium")],
                [InlineKeyboardButton(text="💖 Начислить сердца", callback_data="admin_hearts"),
                 InlineKeyboardButton(text="🚫 Забанить", callback_data="admin_ban")],
                # Управление контентом
                [InlineKeyboardButton(text="📝 Создать задание", callback_data="admin_create_task"),
                 InlineKeyboardButton(text="🎁 Создать промо", callback_data="admin_create_promo")],
                # Аналитика
                [InlineKeyboardButton(text="📊 Полная статистика", callback_data="admin_stats"),
                 InlineKeyboardButton(text="📈 Аналитика", callback_data="admin_analytics")],
                # Система
                [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"),
                 InlineKeyboardButton(text="📦 Бэкап данных", callback_data="admin_backup")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
        return

    # Меню для обычного пользователя
    account_status = await get_user_account_status(user_id)
    status_icon = "💎" if account_status == "premium" else \
                 "🟢" if account_status == "trial" else \
                 "🔹"

    main_menu_text = (
        f"{time_of_day.capitalize()}, {name}! {status_icon}\n\n"
        f"💖 Баланс: {user.get('hearts', 0)}\n"
        f"📅 В системе с: {user['created_at'].strftime('%d.%m.%Y')}\n\n"
        "Выберите раздел:"
    )

    await message.answer(
        main_menu_text,
        reply_markup=get_main_menu_keyboard(user_id)
    )
        
@router.callback_query(F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Process gender selection"""
    gender = "male" if callback.data == "gender_male" else "female"
    salutation = "Дорогой" if gender == "male" else "Дорогая"
    
    await update_user(callback.from_user.id, gender=gender)
    await state.clear()
    
    user = await get_user(callback.from_user.id)
    name = user.get('name', 'друг')
    
    await callback.message.edit_text(
        f"{salutation} {name}, рад приветствовать вас!\n\n"
        "Теперь вы можете пользоваться всеми функциями бота. "
        "Начните с главного меню:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Show enhanced user profile"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return

    name = user.get('name', 'друг')
    hearts = user.get('hearts', 0)
    gender_emoji = "👨" if user.get('gender') == "male" else "👩"
    
    # Get account status
    status = await get_user_account_status(callback.from_user.id)
    status_text = {
        "free": "🆓 Бесплатный",
        "trial": "🟢 Пробный",
        "premium": "💎 Премиум"
    }.get(status, "🆓 Бесплатный")
    
    # Get requests info
    daily_requests = user.get('daily_requests', 0)
    total_requests = user.get('total_requests', 0)
    
    if status == "trial":
        trial_end = user['trial_started_at'] + timedelta(days=Config.TRIAL_DAYS)
        days_left = (trial_end - datetime.utcnow()).days
        status_text += f" ({days_left} дн. осталось)"
        requests_limit = Config.TRIAL_DAILY_LIMIT
    elif status == "premium":
        requests_limit = Config.PREMIUM_DAILY_LIMIT
    else:
        requests_limit = Config.FREE_WEEKLY_LIMIT
    
    # Get habits and diary stats
    habits = await get_user_habits(callback.from_user.id)
    completed_habits = sum(1 for _ in habits)
    
    diary_entries = await get_diary_entries(callback.from_user.id, 7)
    
    # Get referral info if available
    referral_info = ""
    if user.get('referral_code'):
        referral_info = (
            f"\n\n👥 <b>Реферальная система</b>\n"
            f"Ваш код: <code>{user['referral_code']}</code>\n"
            f"Приглашено: {user.get('referrals_count', 0)}/{Config.MAX_REFERRALS_PER_MONTH} (мес.)\n"
            f"Награда: {Config.REFERRAL_REWARD_DAYS} дн. премиума + {Config.REFERRAL_REWARD_HEARTS}💖 за каждого"
        )
    
    text = (
        f"{gender_emoji} <b>Профиль {name}</b>\n\n"
        f"📊 <b>Статус:</b> {status_text}\n"
        f"💖 <b>Сердечки:</b> {hearts}\n"
        f"📝 <b>Запросы:</b> {daily_requests}/{requests_limit} (сегодня)\n"
        f"📚 <b>Всего запросов:</b> {total_requests}\n\n"
        f"📔 <b>Дневник:</b> {len(diary_entries)} записей\n"
        f"✅ <b>Привычки:</b> {completed_habits} активных\n"
        f"{referral_info}"
    )
    
    buttons = [
        [InlineKeyboardButton(text="📔 Личный дневник", callback_data="personal_diary")],
        [InlineKeyboardButton(text="✅ Цели и привычки", callback_data="habits")],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="premium_shop")],
        [InlineKeyboardButton(text="👥 Реферальная система", callback_data="referral_system")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await show_main_menu(callback.from_user.id, callback.message)
    await callback.answer()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показывает профиль пользователя"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return

    name = user.get('name', 'друг')
    hearts = user.get('hearts', 0)
    
    habits = await get_user_habits(callback.from_user.id)
    completed_habits = sum(1 for _ in habits)
    
    diary_entries = await get_diary_entries(callback.from_user.id, 1)
    
    text = (
        f"👤 <b>Профиль {name}</b>\n\n"
        f"💖 Сердечек: {hearts}\n"
        f"📝 Записей в дневнике: {len(diary_entries)}\n"
        f"✅ Привычек: {completed_habits}\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_profile_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# --- Diary handlers ---
@router.callback_query(F.data == "personal_diary")
async def personal_diary_menu(callback: CallbackQuery):
    """Diary menu with info"""
    diary_info = (
        "📔 <b>Личный дневник</b>\n\n"
        "Здесь вы можете записывать свои мысли, эмоции и события дня. "
        "Я помогу вам их проанализировать и найти закономерности.\n\n"
        "✨ <b>Особенности:</b>\n"
        "• Запись с эмоциями (😊, 😢 и др.) автоматически анализируется\n"
        "• Можно установить пароль для конфиденциальности\n"
        "• Награда за ежедневные записи: +{Config.DIARY_REWARD}💖 (1 раз в день)\n\n"
        "Выберите действие:"
    )
    
    await callback.message.edit_text(
        diary_info,
        reply_markup=get_diary_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "new_diary_entry")
async def new_diary_entry(callback: CallbackQuery, state: FSMContext):
    """Новая запись в дневнике"""
    await callback.message.edit_text(
        "✍️ <b>Новая запись в дневнике</b>\n\n"
        "Напишите свои мысли, чувства или события дня. "
        "Вы можете добавить эмоцию в конце сообщения, например:\n\n"
        "<i>Сегодня был продуктивный день! Я закончил важный проект. 😊</i>",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_diary_entry)
    await callback.answer()
    
@router.message(StateFilter(UserStates.waiting_for_diary_entry))
async def process_diary_entry(message: Message, state: FSMContext):
    """Обработка записи в дневнике"""
    entry_text = message.text.strip()
    if len(entry_text) < 5:
        await message.answer("Запись должна содержать минимум 5 символов. Попробуйте еще раз:")
        return

    # Извлекаем эмоцию из текста
    mood = None
    emotions = ["😊", "😢", "😠", "😍", "😐", "😨", "😭", "🤔"]
    for emoji in emotions:
        if emoji in entry_text:
            mood = emoji
            entry_text = entry_text.replace(emoji, "").strip()
            break

    if await create_diary_entry(message.from_user.id, entry_text, mood):
        await add_hearts(message.from_user.id, 5)  # Награда за запись
        await message.answer(
            "📔 Запись успешно сохранена! +5💖",
            reply_markup=get_diary_keyboard()
        )
    else:
        await message.answer("⚠️ Произошла ошибка при сохранении записи.")
    
    await state.clear()
    
@router.callback_query(F.data == "my_diary_entries")
async def show_diary_entries(callback: CallbackQuery):
    """Show diary entries with period selection"""
    entries = await get_diary_entries_by_period(callback.from_user.id, days=7)
    if not entries:
        await callback.message.edit_text(
            "📖 У вас пока нет записей в дневнике.",
            reply_markup=get_diary_keyboard()
        )
    else:
        text = "📖 <b>Ваши последние записи:</b>\n\n"
        for entry in entries[:7]:  # Show last 7 entries by default
            date = entry['created_at'].strftime("%d.%m.%Y %H:%M")
            mood = entry.get('mood', '')
            preview = entry['entry_text'][:50] + ("..." if len(entry['entry_text']) > 50 else "")
            text += f"📅 <b>{date}</b> {mood}\n{preview}\n\n"

        text += "\nВы можете просмотреть записи за другой период:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_diary_period_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_diary_password))
async def process_diary_password(message: Message, state: FSMContext):
    """Обработка пароля дневника"""
    password = message.text.strip()
    if len(password) < 6:
        await message.answer("Пароль должен содержать минимум 6 символов. Попробуйте еще раз:")
        return

    hashed = hash_password(password)
    if await update_user(message.from_user.id, diary_password=hashed):
        await message.answer("🔐 Пароль успешно установлен!", reply_markup=get_diary_keyboard())
    else:
        await message.answer("⚠️ Ошибка при установке пароля.")
    
    await state.clear()

@router.callback_query(F.data == "set_diary_password")
async def set_diary_password(callback: CallbackQuery, state: FSMContext):
    """Установка пароля на дневник"""
    await callback.message.edit_text(
        "🔐 <b>Установка пароля на дневник</b>\n\n"
        "Введите новый пароль (минимум 6 символов):",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_diary_password)
    await callback.answer()
    
@router.callback_query(F.data.startswith("diary_"))
async def show_diary_by_period(callback: CallbackQuery):
    """Show diary entries for specific period"""
    period = callback.data.replace("diary_", "")
    
    if period == "custom":
        await callback.message.edit_text("Введите дату в формате ДД.ММ.ГГГГ:")
        # Here you would set state to wait for date input
        await callback.answer()
        return
    
    days = int(period) if period.isdigit() else 7
    entries = await get_diary_entries_by_period(callback.from_user.id, days=days)
    
    if not entries:
        await callback.message.edit_text(
            f"📖 У вас нет записей за последние {days} дней.",
            reply_markup=get_diary_period_keyboard()
        )
    else:
        text = f"📖 <b>Ваши записи за последние {days} дней:</b>\n\n"
        for entry in entries:
            date = entry['created_at'].strftime("%d.%m.%Y %H:%M")
            mood = entry.get('mood', '')
            preview = entry['entry_text'][:50] + ("..." if len(entry['entry_text']) > 50 else "")
            text += f"📅 <b>{date}</b> {mood}\n{preview}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_diary_period_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()

# --- Обработчики привычек ---
@router.callback_query(F.data == "habits")
async def habits_menu(callback: CallbackQuery):
    """Меню привычек"""
    await callback.message.edit_text(
        "✅ <b>Цели и привычки</b>\n\n"
        "Здесь вы можете работать над своими привычками.",
        reply_markup=get_habits_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "new_habit")
async def new_habit(callback: CallbackQuery, state: FSMContext):
    """Новая привычка"""
    await callback.message.edit_text(
        "➕ <b>Новая привычка</b>\n\n"
        "Введите название привычки:",
        parse_mode="HTML"
    )
    await state.set_state(HabitCreation.waiting_for_title)
    await callback.answer()

@router.message(StateFilter(HabitCreation.waiting_for_title))
async def process_habit_title(message: Message, state: FSMContext):
    """Обработка названия привычки"""
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("Название должно содержать минимум 3 символа. Попробуйте еще раз:")
        return

    await state.update_data(title=title)
    await state.set_state(HabitCreation.waiting_for_description)
    await message.answer(
        "📝 Теперь введите описание привычки:"
    )

@router.message(StateFilter(HabitCreation.waiting_for_description))
async def process_habit_description(message: Message, state: FSMContext):
    """Обработка описания привычки"""
    description = message.text.strip()
    if len(description) < 5:
        await message.answer("Описание должно содержать минимум 5 символов. Попробуйте еще раз:")
        return

    await state.update_data(description=description)
    await state.set_state(HabitCreation.waiting_for_time)
    await message.answer(
        "⏰ Введите время напоминания (например, 09:00) или 'нет', если не нужно:"
    )

@router.message(StateFilter(HabitCreation.waiting_for_time))
async def process_habit_time(message: Message, state: FSMContext):
    """Обработка времени привычки"""
    time_input = message.text.strip()
    reminder_time = None if time_input.lower() == 'нет' else time_input

    data = await state.get_data()
    habit = await create_habit(
        user_id=message.from_user.id,
        title=data['title'],
        description=data['description'],
        reminder_time=reminder_time
    )

    if habit:
        await message.answer(
            f"✅ Привычка '{data['title']}' создана!",
            reply_markup=get_habits_keyboard()
        )
        await add_hearts(message.from_user.id, 10)  # Награда за создание привычки
    else:
        await message.answer("⚠️ Ошибка при создании привычки.")
    
    await state.clear()

@router.callback_query(F.data == "my_habits")
async def show_user_habits(callback: CallbackQuery):
    """Показывает привычки пользователя"""
    habits = await get_user_habits(callback.from_user.id)
    if not habits:
        await callback.message.edit_text(
            "📊 У вас пока нет привычек.",
            reply_markup=get_habits_keyboard()
        )
    else:
        text = "📊 <b>Ваши привычки:</b>\n\n"
        for habit in habits:
            reminder = f"⏰ {habit['reminder_time']}" if habit['reminder_time'] else ""
            text += f"• {habit['title']} {reminder}\n"

        await callback.message.edit_text(
            text,
            reply_markup=get_habits_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()
    
# --- Обработчики психологического раздела ---
@router.callback_query(F.data == "psychology_menu")
async def psychology_menu(callback: CallbackQuery):
    """Меню психологического раздела"""
    text = (
        "🧠 <b>Психологический раздел</b>\n\n"
        "Здесь вы можете работать над своим ментальным здоровьем:\n\n"
        "⚖️ <b>Колесо баланса</b> - оценка 8 сфер жизни\n"
        "🌀 <b>Детокс тревоги</b> - 3-дневный курс по КПТ\n"
        "🦸 <b>Тест архетипов</b> - определите свой психотип\n"
        "🙏 <b>Дневник благодарности</b> - практика благодарности\n"
        "🌙 <b>Анализ сна</b> - оценка качества сна\n"
        "🧪 <b>Тест стресса</b> - определение уровня стресса\n\n"
        "Выполняйте задания и получайте сердечки!"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "wheel_of_life")
async def wheel_of_life_start(callback: CallbackQuery, state: FSMContext):
    """Начало работы с колесом баланса"""
    await callback.message.edit_text(
        "⚖️ <b>Колесо баланса</b>\n\n"
        "Оцените по 10-балльной шкале следующие сферы вашей жизни:\n\n"
        "1. Здоровье\n2. Отношения\n3. Карьера\n4. Финансы\n"
        "5. Духовность\n6. Хобби\n7. Окружение\n8. Личностный рост\n\n"
        "Введите оценки через запятую (например: 7,8,5,6,4,7,8,6):",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_wheel)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_wheel))
async def process_wheel_scores(message: Message, state: FSMContext):
    """Обработка оценок колеса баланса"""
    try:
        scores = list(map(int, message.text.strip().split(',')))
        if len(scores) != 8 or any(score < 0 or score > 10 for score in scores):
            raise ValueError
        
        categories = [
            "health", "relationships", "career", "finance",
            "spirit", "hobbies", "environment", "growth"
        ]
        scores_dict = dict(zip(categories, scores))
        
        if await save_wheel_balance(message.from_user.id, scores_dict):
            await add_hearts(message.from_user.id, 30)  # Награда за выполнение
            await message.answer(
                "✅ Ваши оценки сохранены! +30💖\n\n"
                "Рекомендации:\n"
                "1. Обратите внимание на сферы с низкими оценками\n"
                "2. Поставьте цели по улучшению 1-2 сфер",
                reply_markup=get_psychology_menu_keyboard()
            )
        else:
            await message.answer("⚠️ Ошибка при сохранении оценок.")
    
    except ValueError:
        await message.answer("⚠️ Введите 8 чисел от 0 до 10 через запятую.")
        return
    
    await state.clear()

@router.callback_query(F.data == "detox_anxiety")
async def detox_anxiety_start(callback: CallbackQuery, state: FSMContext):
    """Начало детокса тревоги"""
    await callback.message.edit_text(
        "🌀 <b>Детокс тревоги</b>\n\n"
        "Это 3-дневный курс по когнитивно-поведенческой терапии.\n\n"
        "День 1: Определите триггеры тревоги\n"
        "День 2: Техники дыхания\n"
        "День 3: Когнитивное реструктурирование\n\n"
        "Готовы начать? (да/нет)",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_detox)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_detox))
async def process_detox_start(message: Message, state: FSMContext):
    """Обработка начала детокса"""
    answer = message.text.strip().lower()
    if answer == 'да':
        await add_hearts(message.from_user.id, 50)  # Награда за начало курса
        await message.answer(
            "🌀 <b>День 1: Определение триггеров</b>\n\n"
            "1. Запишите 3 ситуации, когда вы чувствовали тревогу\n"
            "2. Отметьте, что происходило перед этим\n"
            "3. Оцените уровень тревоги от 1 до 10\n\n"
            "Пришлите ответы в формате:\n"
            "1. Ситуация: ..., Триггер: ..., Уровень: ...\n"
            "2. ...",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Вы можете начать курс позже.",
            reply_markup=get_psychology_menu_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "archetype_test")
async def archetype_test_start(callback: CallbackQuery, state: FSMContext):
    """Начало теста архетипов"""
    await callback.message.edit_text(
        "🦸 <b>Тест архетипов</b>\n\n"
        "Ответьте на 5 вопросов, чтобы определить ваш доминирующий архетип:\n\n"
        "1. В сложной ситуации я обычно:\n"
        "а) Действую решительно\nб) Ищу поддержку\nв) Анализирую\nг) Ухожу в себя\n\n"
        "Введите ответы (например: а,б,в,г,а):",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_archetype)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_archetype))
async def process_archetype_test(message: Message, state: FSMContext):
    """Обработка теста архетипов"""
    answers = message.text.strip().lower().split(',')
    if len(answers) != 5 or any(a not in ['а', 'б', 'в', 'г'] for a in answers):
        await message.answer("⚠️ Введите 5 ответов (а,б,в,г) через запятую.")
        return
    
    # Простая логика определения архетипа
    archetypes = {
        'а': 'Герой', 'б': 'Опекун', 'в': 'Мудрец', 'г': 'Искатель'
    }
    main_archetype = archetypes[max(set(answers), key=answers.count)]
    
    await add_hearts(message.from_user.id, 20)  # Награда за прохождение теста
    await message.answer(
        f"🦸 <b>Ваш архетип: {main_archetype}</b>\n\n"
        f"Описание: {get_archetype_description(main_archetype)}\n\n"
        "Рекомендации:\n"
        "1. Используйте свои сильные стороны\n"
        "2. Развивайте слабые аспекты",
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()
    
# --- Обработчики магазина ---
@router.callback_query(F.data == "shop")
async def shop_menu(callback: CallbackQuery):
    """Меню магазина"""
    user = await get_user(callback.from_user.id)
    hearts = user.get('hearts', 0) if user else 0
    
    await callback.message.edit_text(
        f"🛍 <b>Магазин</b>\n\n"
        f"💖 Ваш баланс: {hearts}\n\n"
        "Выберите раздел:",
        reply_markup=get_shop_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
    
@router.callback_query(F.data == "premium_shop")
async def premium_shop_menu(callback: CallbackQuery):
    """Premium shop menu"""
    user = await get_user(callback.from_user.id)
    hearts = user.get('hearts', 0) if user else 0
    
    premium_info = (
        "💎 <b>Премиум подписка</b>\n\n"
        "Преимущества премиум-аккаунта:\n"
        "• Неограниченные запросы к GPT-4o\n"
        "• Доступ ко всем психологическим тестам\n"
        "• Персональные рекомендации\n"
        "• Расширенный анализ данных\n"
        "• Приоритетная поддержка\n\n"
        f"💖 Ваш баланс: {hearts}\n\n"
        "Выберите вариант подписки:"
    )
    
    await callback.message.edit_text(
        premium_info,
        reply_markup=get_premium_shop_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_premium_"))
async def buy_premium_item(callback: CallbackQuery):
    """Buy premium with hearts"""
    item_id = callback.data.replace("buy_premium_", "")
    item = next((i for i in PREMIUM_SHOP_ITEMS if i['id'] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return

    if user.get('hearts', 0) < item['price']:
        await callback.answer("Недостаточно сердечек")
        return

    # Process premium purchase
    days = 1 if item_id == "premium_1_day" else (7 if item_id == "premium_7_days" else 30)
    expires_at = datetime.utcnow() + timedelta(days=days)
    
    if await update_user(
        callback.from_user.id,
        is_premium=True,
        subscription_expires_at=expires_at,
        hearts=user.get('hearts', 0) - item['price']
    ):
        await callback.message.edit_text(
            f"🎉 Вы успешно приобрели {item['title']}!\n\n"
            f"Премиум-доступ активен до {expires_at.strftime('%d.%m.%Y')}",
            reply_markup=get_premium_shop_keyboard()
        )
    else:
        await callback.message.edit_text(
            "⚠️ Ошибка при покупке. Попробуйте позже.",
            reply_markup=get_premium_shop_keyboard()
        )
    
    await callback.answer()

@router.callback_query(F.data == "paid_shop")
async def paid_shop(callback: CallbackQuery):
    """Магазин платных функций"""
    await callback.message.edit_text(
        "💰 <b>Платные функции</b>\n\n"
        "Доступны за реальные деньги:\n"
        "• Экстренная помощь - 99₽\n"
        "• Персональный гид - 149₽\n"
        "• Анализ эмоций - 129₽\n"
        "• Гороскоп - 99₽\n"
        "• Детокс тревоги - 149₽\n"
        "• Глубинный анализ - 149₽",
        reply_markup=get_paid_shop_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_paid_"))
async def buy_paid_item(callback: CallbackQuery):
    """Покупка платной функции"""
    item_id = callback.data.replace("buy_paid_", "")
    item = next((i for i in PAID_SHOP_ITEMS if i['id'] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return

    await callback.message.edit_text(
        f"💰 <b>{item['title']}</b>\n\n"
        f"{item['description']}\n\n"
        f"Цена: {item['price']}₽\n\n"
        "Выберите способ оплаты:",
        reply_markup=get_payment_methods_keyboard(item_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery):
    """Оплата криптовалютой"""
    item_id = callback.data.replace("pay_crypto_", "")
    item = next((i for i in PAID_SHOP_ITEMS if i['id'] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return

    await callback.message.edit_text(
        f"💳 <b>Оплата {item['title']}</b>\n\n"
        f"Отправьте {item['price']}₽ эквивалент в USDT (TRC20) на адрес:\n\n"
        "<code>TMrLxEVr1sd5UCYB2iQXpj7GM3K5KdXTCP</code>\n\n"
        "После оплаты нажмите кнопку 'Проверить оплату'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{item_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"buy_paid_{item_id}")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()
    
@router.callback_query(F.data.startswith("pay_yoomoney_"))
async def pay_with_yoomoney(callback: CallbackQuery):
    """Оплата через ЮMoney"""
    item_id = callback.data.replace("pay_yoomoney_", "")
    item = next((i for i in PAID_SHOP_ITEMS if i['id'] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return

    await callback.message.edit_text(
        f"💳 <b>Оплата {item['title']}</b>\n\n"
        f"1. Переведите {item['price']}₽ на ЮMoney:\n"
        "<code>4100119110059662</code>\n\n"
        "2. В комментарии укажите ваш @username\n\n"
        "После оплаты нажмите кнопку 'Проверить оплату'",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{item_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"buy_paid_{item_id}")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()
    
@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery):
    """Проверка оплаты"""
    item_id = callback.data.replace("check_payment_", "")
    item = next((i for i in PAID_SHOP_ITEMS if i['id'] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return

    # Здесь должна быть логика проверки платежа
    # В демо-версии просто имитируем успешную оплату
    
    try:
        async with async_session() as session:
            await session.execute(
                payments.insert().values(
                    user_id=callback.from_user.id,
                    amount=item['price'],
                    currency=item['currency'],
                    item_id=item_id,
                    status="completed"
                )
            )
            await session.commit()
        
        await callback.message.edit_text(
            f"🎉 <b>Оплата подтверждена!</b>\n\n"
            f"Вы получили доступ к: {item['title']}\n\n"
            "Спасибо за покупку!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍 В магазин", callback_data="paid_shop")]
            ]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при подтверждении платежа: {e}")
        await callback.message.edit_text(
            "⚠️ Платеж не найден. Попробуйте позже или свяжитесь с поддержкой.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"buy_paid_{item_id}")]
            ])
        )
    
    await callback.answer()
    
# --- Фоновые задачи ---
async def check_payments():
    """Проверка платежей в фоне"""
    while True:
        try:
            async with async_session() as session:
                result = await session.execute(
                    text("SELECT * FROM payments WHERE status = 'pending'")
                )
                payments = result.mappings().all()

                for payment in payments:
                    # Логика проверки платежа
                    # В демо-версии пропускаем
                    pass

        except Exception as e:
            logger.error(f"Ошибка в check_payments: {e}")

        await asyncio.sleep(300)  # Проверка каждые 5 минут
        
async def send_reminders():
    """Отправка напоминаний"""
    while True:
        try:
            now = datetime.now()
            async with async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT h.user_id, h.title, h.description 
                        FROM habits h
                        WHERE h.reminder_time IS NOT NULL
                        AND h.reminder_time = :now
                    """),
                    {"now": now.strftime("%H:%M")}
                )
                habits = result.mappings().all()

                for habit in habits:
                    try:
                        await bot.send_message(
                            habit['user_id'],
                            f"⏰ Напоминание: {habit['title']}\n{habit['description']}"
                        )
                    except Exception as e:
                        logger.error(f"Не удалось отправить напоминание: {e}")

        except Exception as e:
            logger.error(f"Ошибка в send_reminders: {e}")

        await asyncio.sleep(60)  # Проверка каждую минуту
        
# Админ обработкики
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Полная статистика бота"""
    async with async_session() as session:
        # Общая статистика
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        total_users = result.scalar()
        
        result = await session.execute(text("SELECT COUNT(*) FROM users WHERE is_premium = TRUE"))
        premium_users = result.scalar()
        
        result = await session.execute(text("SELECT COUNT(*) FROM users WHERE is_banned = TRUE"))
        banned_users = result.scalar()
        
        # Активность
        result = await session.execute(text("""
            SELECT COUNT(*) FROM users 
            WHERE last_activity_at >= NOW() - INTERVAL '1 day'
        """))
        active_today = result.scalar()

    text = (
        "📊 <b>Полная статистика бота</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💎 Премиум: {premium_users}\n"
        f"🚫 Забанено: {banned_users}\n"
        f"🟢 Активных за сутки: {active_today}\n"
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Управление пользователями"""
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_find_user")],
            [InlineKeyboardButton(text="📋 Последние регистрации", callback_data="admin_recent_users")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()
    
@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Admin panel"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    async with async_session() as session:
        # Total users
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        total_users = result.scalar()
        
        # Active today
        result = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE last_activity_at >= CURRENT_DATE")
        )
        active_today = result.scalar()
        
        # Premium users
        result = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE is_premium = TRUE")
        )
        premium_users = result.scalar()
        
        # Latest users
        result = await session.execute(
            text("SELECT username, created_at FROM users ORDER BY created_at DESC LIMIT 5")
        )
        latest_users = result.mappings().all()
        
        # Pending payments
        result = await session.execute(
            text("""
                SELECT p.id, u.username, p.amount, p.currency, p.item_id 
                FROM payments p
                JOIN users u ON p.user_id = u.telegram_id
                WHERE p.status = 'pending'
                ORDER BY p.created_at DESC
                LIMIT 5
            """)
        )
        pending_payments = result.mappings().all()
    
    # Format latest users
    latest_users_text = "\n".join(
        f"• @{user['username']} ({user['created_at'].strftime('%d.%m')})"
        for user in latest_users
    ) if latest_users else "Нет данных"
    
    # Format pending payments
    payments_text = "\n".join(
        f"• @{pay['username']} - {pay['amount']}{pay['currency']} ({pay['item_id']})"
        for pay in pending_payments
    ) if pending_payments else "Нет ожидающих платежей"
    
    admin_text = (
        f"👑 <b>Админ-панель</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"• Всего пользователей: {total_users}\n"
        f"• Активных сегодня: {active_today}\n"
        f"• Премиум пользователей: {premium_users}\n\n"
        f"🆕 <b>Последние регистрации:</b>\n"
        f"{latest_users_text}\n\n"
        f"💳 <b>Ожидающие платежи:</b>\n"
        f"{payments_text}\n\n"
        "Выберите действие:"
    )
    
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить платежи", callback_data="admin_confirm_payments")],
        [InlineKeyboardButton(text="💎 Активировать премиум", callback_data="admin_premium")],
        [InlineKeyboardButton(text="💖 Начислить сердечки", callback_data="admin_hearts")],
        [InlineKeyboardButton(text="🚫 Заблокировать пользователя", callback_data="admin_ban")],
        [InlineKeyboardButton(text="📊 Полная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="➕ Создать задание", callback_data="admin_create_task")],
        [InlineKeyboardButton(text="🎁 Создать промокод", callback_data="admin_create_promo")]
    ]
    
    await message.answer(
        admin_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_ban")
async def admin_ban_user(callback: CallbackQuery, state: FSMContext):
    """Начало процесса бана пользователя"""
    await callback.message.edit_text(
        "🚫 <b>Бан пользователя</b>\n\n"
        "Введите username или ID пользователя:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_ban_user)
    await callback.answer()

@router.callback_query(F.data == "admin_unban")
async def admin_unban_user(callback: CallbackQuery, state: FSMContext):
    """Начало процесса разбана пользователя"""
    await callback.message.edit_text(
        "✅ <b>Разбан пользователя</b>\n\n"
        "Введите username или ID пользователя:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_unban_user)
    await callback.answer()
    
@router.callback_query(F.data == "admin_confirm_payments")
async def admin_confirm_payments(callback: CallbackQuery):
    """Show pending payments for confirmation"""
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT p.id, u.username, p.amount, p.currency, p.item_id, p.created_at
                FROM payments p
                JOIN users u ON p.user_id = u.telegram_id
                WHERE p.status = 'pending'
                ORDER BY p.created_at DESC
            """)
        )
        payments = result.mappings().all()
    
    if not payments:
        await callback.message.edit_text("Нет платежей для подтверждения.")
        await callback.answer()
        return
    
    text = "💳 <b>Ожидающие платежи:</b>\n\n"
    for payment in payments:
        date = payment['created_at'].strftime("%d.%m %H:%M")
        text += (
            f"🆔 {payment['id']}\n"
            f"👤 @{payment['username']}\n"
            f"💰 {payment['amount']}{payment['currency']}\n"
            f"📦 {payment['item_id']}\n"
            f"📅 {date}\n\n"
        )
    
    buttons = [
        [InlineKeyboardButton(text=f"✅ Подтвердить {payment['id']}", callback_data=f"confirm_pay_{payment['id']}")]
        for payment in payments
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()
    
@router.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_payment(callback: CallbackQuery):
    """Confirm specific payment"""
    payment_id = int(callback.data.replace("confirm_pay_", ""))
    
    async with async_session() as session:
        # Get payment details
        result = await session.execute(
            text("""
                SELECT p.*, u.telegram_id, u.username 
                FROM payments p
                JOIN users u ON p.user_id = u.telegram_id
                WHERE p.id = :payment_id
            """),
            {"payment_id": payment_id}
        )
        payment = result.mappings().first()
        
        if not payment:
            await callback.answer("Платеж не найден")
            return
        
        # Update payment status
        await session.execute(
            text("UPDATE payments SET status = 'completed' WHERE id = :payment_id"),
            {"payment_id": payment_id}
        )
        
        # Apply premium if it's a premium purchase
        if payment['item_id'].startswith("premium_"):
            days = 30 if "1_month" in payment['item_id'] else (
                7 if "7_days" in payment['item_id'] else 1
            )
            
            # Get current expiry
            result = await session.execute(
                text("SELECT subscription_expires_at FROM users WHERE telegram_id = :user_id"),
                {"user_id": payment['user_id']}
            )
            current_expiry = result.scalar()
            
            new_expiry = (
                max(current_expiry, datetime.utcnow()) if current_expiry 
                else datetime.utcnow()
            ) + timedelta(days=days)
            
            await session.execute(
                text("""
                    UPDATE users 
                    SET is_premium = TRUE, 
                        subscription_expires_at = :expiry 
                    WHERE telegram_id = :user_id
                """),
                {"expiry": new_expiry, "user_id": payment['user_id']}
            )
        
        await session.commit()
        
        # Notify user
        try:
            await bot.send_message(
                payment['user_id'],
                f"🎉 Ваш платеж {payment['amount']}{payment['currency']} подтвержден!\n\n"
                f"Товар: {payment['item_id']}\n"
                "Спасибо за покупку!"
            )
        except Exception as e:
            logger.error(f"Could not notify user: {e}")
        
        await callback.answer(f"Платеж {payment_id} подтвержден")
        await admin_confirm_payments(callback)  # Refresh list
        
@router.message(F.photo)
async def handle_payment_proof(message: Message):
    """Handle payment proof photos"""
    user = await get_user(message.from_user.id)
    if not user:
        return
    
    # Check if user has pending payments
    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT id, item_id FROM payments 
                WHERE user_id = :user_id AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"user_id": message.from_user.id}
        )
        payment = result.mappings().first()
    
    if not payment:
        await message.answer("У вас нет ожидающих платежей.")
        return
    
    # Save photo info (in real bot you would save the photo file_id)
    await message.answer(
        "✅ Ваш чек получен. Ожидайте подтверждения платежа в течение 5-10 минут.\n\n"
        f"ID платежа: {payment['id']}\n"
        f"Товар: {payment['item_id']}"
    )
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo=message.photo[-1].file_id,
                caption=(
                    f"🆔 Платеж: {payment['id']}\n"
                    f"👤 Пользователь: @{user.get('username', 'N/A')} ({message.from_user.id})\n"
                    f"📦 Товар: {payment['item_id']}\n\n"
                    "Для подтверждения нажмите кнопку ниже"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"✅ Подтвердить {payment['id']}",
                        callback_data=f"confirm_pay_{payment['id']}"
                    )]
                ])
            )
        except Exception as e:
            logger.error(f"Could not notify admin {admin_id}: {e}")

# Обновим обработчик оплаты криптовалютой
@router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery):
    """Оплата криптовалютой"""
    item_id = callback.data.replace("pay_crypto_", "")
    item = next((i for i in PAID_SHOP_ITEMS if i['id'] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return

    # Create payment record
    async with async_session() as session:
        result = await session.execute(
            payments.insert().values(
                user_id=callback.from_user.id,
                amount=item['price'],
                currency=item['currency'],
                item_id=item_id,
                status="pending"
            ).returning(payments)
        )
        payment = dict(result.mappings().first())
        await session.commit()
    
    await callback.message.edit_text(
        f"💳 <b>Оплата {item['title']}</b>\n\n"
        f"Отправьте {item['price']}₽ эквивалент в USDT (TRC20) на адрес:\n\n"
        "<code>TMrLxEVr1sd5UCYB2iQXpj7GM3K5KdXTCP</code>\n\n"
        "После оплаты:\n"
        "1. Отправьте хэш транзакции в ответном сообщении\n"
        "2. Или отправьте скриншот перевода\n\n"
        "Подтверждение займет 5-10 минут.\n\n"
        f"ID вашего платежа: <code>{payment['id']}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"buy_paid_{item_id}")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

# Обновим обработчик оплаты через ЮMoney
@router.callback_query(F.data.startswith("pay_yoomoney_"))
async def pay_with_yoomoney(callback: CallbackQuery):
    """Оплата через ЮMoney"""
    item_id = callback.data.replace("pay_yoomoney_", "")
    item = next((i for i in PAID_SHOP_ITEMS if i['id'] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return

    # Create payment record
    async with async_session() as session:
        result = await session.execute(
            payments.insert().values(
                user_id=callback.from_user.id,
                amount=item['price'],
                currency=item['currency'],
                item_id=item_id,
                status="pending"
            ).returning(payments)
        )
        payment = dict(result.mappings().first())
        await session.commit()
    
    await callback.message.edit_text(
        f"💳 <b>Оплата {item['title']}</b>\n\n"
        f"1. Переведите {item['price']}₽ на ЮMoney:\n"
        "<code>4100119110059662</code>\n\n"
        "2. В комментарии укажите:\n"
        f"<code>@{callback.from_user.username} {payment['id']}</code>\n\n"
        "3. После оплаты отправьте скриншот чека в этот чат\n\n"
        "Подтверждение займет 5-10 минут.\n\n"
        f"ID вашего платежа: <code>{payment['id']}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"buy_paid_{item_id}")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()
    
@router.callback_query(F.data == "admin_premium")
async def admin_premium_handler(callback: CallbackQuery, state: FSMContext):
    """Admin premium activation"""
    await callback.message.edit_text(
        "💎 <b>Активация премиума</b>\n\n"
        "Введите username пользователя и срок (в днях) в формате:\n"
        "<code>@username 30</code>\n\n"
        "Пример: <code>@ivanov 30</code> - активирует премиум на 30 дней",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_premium_username)
    await callback.answer()

@router.callback_query(F.data == "referral_system")
async def show_referral_system(callback: CallbackQuery):
    """Показывает реферальную систему"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return

    text = (
        "👥 <b>Реферальная система</b>\n\n"
        f"Ваш реферальный код: <code>{user['referral_code']}</code>\n\n"
        "Приглашайте друзей и получайте:\n"
        f"• {Config.REFERRAL_REWARD_HEARTS}💖 за каждого приглашенного\n"
        f"• {Config.REFERRAL_REWARD_DAYS} дня премиума\n\n"
        f"Максимум {Config.MAX_REFERRALS_PER_MONTH} приглашений в месяц.\n\n"
        "Ваша ссылка для приглашений:\n"
        f"https://t.me/{(await bot.get_me()).username}?start={user['referral_code']}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "sleep_analyzer")
async def sleep_analyzer_start(callback: CallbackQuery, state: FSMContext):
    """Начало анализа сна"""
    await callback.message.edit_text(
        "🌙 <b>Анализ сна</b>\n\n"
        "Ответьте на вопросы о вашем сне:\n\n"
        "1. Во сколько вы легли спать?\n"
        "2. Сколько часов спали?\n"
        "3. Как оцениваете качество сна (1-10)?\n\n"
        "Введите ответы через запятую (например: 23:00,7,6):",
        parse_mode="HTML"
    )
    await state.set_state(UserStates.waiting_for_sleep_data)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_for_sleep_data))
async def process_sleep_data(message: Message, state: FSMContext):
    """Обработка данных о сне"""
    try:
        bedtime, hours, quality = message.text.strip().split(',')
        hours = float(hours)
        quality = int(quality)
        
        if not (0 < quality <= 10):
            raise ValueError
        
        analysis = "Хороший сон" if quality >= 7 else "Плохой сон"
        
        await add_hearts(message.from_user.id, 25)
        await message.answer(
            f"🌙 <b>Результаты анализа:</b>\n\n"
            f"• Время отхода ко сну: {bedtime}\n"
            f"• Продолжительность: {hours} часов\n"
            f"• Качество: {quality}/10\n\n"
            f"<b>Вывод:</b> {analysis}\n\n"
            "Рекомендации:\n"
            "1. Старайтесь ложиться в одно время\n"
            "2. Избегайте экранов перед сном",
            reply_markup=get_psychology_menu_keyboard(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("Неверный формат. Используйте: время,часы,качество (1-10)")
        return
    
    await state.clear()
    
@router.message(StateFilter(UserStates.waiting_for_sleep_data))
async def process_sleep_data(message: Message, state: FSMContext):
    """Обработка данных о сне"""
    try:
        bedtime, hours, quality = message.text.strip().split(',')
        hours = float(hours)
        quality = int(quality)
        
        if not (0 < quality <= 10):
            raise ValueError
        
        analysis = "Хороший сон" if quality >= 7 else "Плохой сон"
        
        await add_hearts(message.from_user.id, 25)
        await message.answer(
            f"🌙 <b>Результаты анализа:</b>\n\n"
            f"• Время отхода ко сну: {bedtime}\n"
            f"• Продолжительность: {hours} часов\n"
            f"• Качество: {quality}/10\n\n"
            f"<b>Вывод:</b> {analysis}\n\n"
            "Рекомендации:\n"
            "1. Старайтесь ложиться в одно время\n"
            "2. Избегайте экранов перед сном",
            reply_markup=get_psychology_menu_keyboard(),
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer("Неверный формат. Используйте: время,часы,качество (1-10)")
        return
    
    await state.clear()
    
@router.message(StateFilter(AdminStates.waiting_for_premium_username))
async def process_admin_premium(message: Message, state: FSMContext):
    """Process admin premium activation"""
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            raise ValueError
        
        username = parts[0].lstrip('@')
        days = int(parts[1])
        
        if days <= 0:
            raise ValueError
        
        # Find user by username
        async with async_session() as session:
            result = await session.execute(
                text("SELECT telegram_id FROM users WHERE username = :username"),
                {"username": username}
            )
            user = result.mappings().first()
            
            if not user:
                await message.answer("Пользователь не найден")
                return
            
            # Calculate new expiration date
            user_id = user['telegram_id']
            current_expiry = await session.execute(
                text("SELECT subscription_expires_at FROM users WHERE telegram_id = :user_id"),
                {"user_id": user_id}
            )
            current_expiry = current_expiry.scalar()
            
            new_expiry = (
                max(current_expiry, datetime.utcnow()) if current_expiry 
                else datetime.utcnow()
            ) + timedelta(days=days)
            
            # Update user
            await session.execute(
                text("""
                    UPDATE users 
                    SET is_premium = TRUE, 
                        subscription_expires_at = :expiry 
                    WHERE telegram_id = :user_id
                """),
                {"expiry": new_expiry, "user_id": user_id}
            )
            await session.commit()
            
            await message.answer(
                f"✅ Премиум активирован для @{username} до {new_expiry.strftime('%d.%m.%Y')}"
            )
            
            # Notify user
            try:
                await bot.send_message(
                    user_id,
                    f"🎉 Вам активирована премиум-подписка на {days} дней!\n"
                    f"Действует до {new_expiry.strftime('%d.%m.%Y')}"
                )
            except Exception as e:
                logger.error(f"Could not notify user: {e}")
    
    except ValueError:
        await message.answer("Неверный формат. Используйте: @username дни")
    
    await state.clear()

# ... [other admin handlers]

# --- Background tasks ---
async def reset_daily_limits():
    """Reset daily request limits"""
    while True:
        try:
            now = datetime.utcnow()
            async with async_session() as session:
                # Reset daily requests for all users
                await session.execute(
                    text("UPDATE users SET daily_requests = 0")
                )
                await session.commit()
                
                logger.info(f"Reset daily requests at {now}")
                
        except Exception as e:
            logger.error(f"Error in reset_daily_limits: {e}")
        
        # Run once per day at midnight UTC
        await asyncio.sleep(24 * 60 * 60)

async def check_subscriptions():
    """Check and update expired subscriptions"""
    while True:
        try:
            now = datetime.utcnow()
            async with async_session() as session:
                # Find expired premium users
                result = await session.execute(
                    text("""
                        SELECT telegram_id FROM users 
                        WHERE is_premium = TRUE 
                        AND subscription_expires_at < :now
                    """),
                    {"now": now}
                )
                expired_users = result.mappings().all()
                
                if expired_users:
                    # Disable premium for expired users
                    await session.execute(
                        text("""
                            UPDATE users 
                            SET is_premium = FALSE 
                            WHERE is_premium = TRUE 
                            AND subscription_expires_at < :now
                        """),
                        {"now": now}
                    )
                    await session.commit()
                    
                    # Notify users
                    for user in expired_users:
                        try:
                            await bot.send_message(
                                user['telegram_id'],
                                "⚠️ Ваша премиум-подписка истекла. "
                                "Вы можете продлить её в магазине."
                            )
                        except Exception as e:
                            logger.error(f"Could not notify user {user['telegram_id']}: {e}")
                
                logger.info(f"Checked subscriptions at {now}, expired: {len(expired_users)}")
                
        except Exception as e:
            logger.error(f"Error in check_subscriptions: {e}")
        
        # Run once per hour
        await asyncio.sleep(60 * 60)

async def check_user_ban(user_id: int) -> bool:
    """Проверяет, забанен ли пользователь"""
    user = await get_user(user_id)
    return user and user.get('is_banned', False)

@router.message()
async def check_banned_user(message: Message):
    """Проверяет забаненных пользователей"""
    if await check_user_ban(message.from_user.id):
        await message.answer("🚫 Вы заблокированы в этом боте")
        return
    await message.answer("Используйте кнопки меню для навигации")
    
# --- Startup ---
async def on_startup(dp: Dispatcher):
    """Bot startup actions"""
    # Set bot commands
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="profile", description="Ваш профиль"),
        BotCommand(command="tasks", description="Ежедневные задания"),
        BotCommand(command="help", description="Помощь")
    ])
    
    # Start background tasks
    asyncio.create_task(reset_daily_limits())
    asyncio.create_task(check_subscriptions())
    asyncio.create_task(send_reminders())
    
    logger.info("🚀 Бот запущен!")

if __name__ == "__main__":
    async def main():
        await on_startup(dp)
        await dp.start_polling(bot)

    asyncio.run(main())