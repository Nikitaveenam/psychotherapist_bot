import os
import logging
import asyncio
import random
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base
from aiogram import Dispatcher
from aiogram.types import ErrorEvent
from aiogram.fsm.state import State, StatesGroup
<<<<<<< HEAD
from aiogram import
=======
from aiogram import F
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
<<<<<<< HEAD
=======
from aiogram import Bot, Dispatcher, Router, F
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Boolean, DateTime, BigInteger, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import httpx
from decimal import Decimal, getcontext
<<<<<<< HEAD
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
=======
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6

# --- Конфигурация ---
load_dotenv()

# Настройка точности для Decimal
getcontext().prec = 8

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

# Параметры
TRIAL_DAYS = 3
TRIAL_DAILY_LIMIT = 12
PREMIUM_DAILY_LIMIT = 20
FREE_WEEKLY_LIMIT = 20
HEARTS_PER_DAY = 3
CHALLENGE_REWARD = 5  # Увеличено количество сердечек за челлендж
CHALLENGE_DURATION = 120  # Длительность челленджа в секундах (2 минуты)
REFERRAL_REWARD = 10
REFERRAL_TRIAL_DAYS = 3
MAX_REFERRALS_PER_MONTH = 5  # Максимум 5 приглашений в месяц

# Челленджи с описанием и временем выполнения
CHALLENGES = [
    {
        "title": "🌬️ Дыхательная практика",
        "description": "Выполните 4-7-8 дыхание: 4 сек вдох, 7 сек задержка, 8 сек выдох. Повторите 5 циклов.",
        "duration": 120
    },
    {
        "title": "🚶‍♂️ Прогулка с осознанностью",
        "description": "Прогуляйтесь 2 минуты, обращая внимание на каждый шаг и окружающие звуки.",
        "duration": 120
    },
    {
        "title": "💪 Мини-зарядка",
        "description": "Сделайте 10 приседаний, 10 наклонов и 10 вращений руками.",
        "duration": 120
    },
    {
        "title": "🧘‍♀️ Медитация",
        "description": "Сядьте удобно и сосредоточьтесь на дыхании в течение 2 минут.",
        "duration": 120
    },
    {
        "title": "🔄 Переосмысление",
        "description": "Запишите 3 положительных момента дня и 1 ситуацию, которую можно улучшить.",
        "duration": 120
    },
    {
        "title": "🎵 Осознанное слушание",
        "description": "Включите спокойную музыку и слушайте ее 2 минуты, концентрируясь на звуках.",
        "duration": 120
    },
    {
        "title": "💧 Питьевая пауза",
        "description": "Медленно выпейте стакан воды, концентрируясь на каждом глотке.",
        "duration": 120
    },
    {
        "title": "📝 Планирование дня",
        "description": "Запишите 3 главные задачи на сегодня и как вы их выполните.",
        "duration": 120
    },
    {
        "title": "🌿 Контакт с природой",
        "description": "Проведите 2 минуты на свежем воздухе, наблюдая за природой.",
        "duration": 120
    },
    {
        "title": "💭 Визуализация успеха",
        "description": "Закройте глаза и представьте себя успешным и счастливым.",
        "duration": 120
    }
]

# Цены подписки в рублях
SUBSCRIPTION_PRICES = {
    "1_month": 299,
    "3_months": 749,
    "6_months": 1299,
    "1_year": 2199
}

# Цены подписки в сердечках
SUBSCRIPTION_HEARTS_PRICES = {
    "1_day": 100,
    "7_days": 600,
    "1_month": 2000
}

# Скидки за сердечки (максимум 15%)
HEARTS_DISCOUNTS = {
    100: 5,
    200: 10,
    300: 15
}

# Дополнительные товары в магазине
SHOP_ITEMS = [
    {
        "id": "extra_requests",
        "title": "📈 Доп. запросы",
        "description": "10 дополнительных запросов к ИИ\n\nПозволит вам получить больше ответов от бота, когда закончатся основные лимиты.",
        "price": 100,
        "type": "requests"
    },
    {
        "id": "motivation",
        "title": "💌 Мотивационное письмо",
        "description": "Персональное мотивационное письмо от ИИ\n\nПоможет вам найти вдохновение и силы для достижения целей.",
        "price": 150,
        "type": "content"
    },
    {
        "id": "analysis",
        "title": "🔍 Анализ настроения",
        "description": "Подробный анализ вашего эмоционального состояния\n\nПоможет лучше понять свои чувства и найти пути улучшения настроения.",
        "price": 200,
        "type": "analysis"
    },
    {
        "id": "therapy_session",
        "title": "🧠 Сессия с ИИ-терапевтом",
        "description": "30-минутная сессия с ИИ-терапевтом\n\nПоможет разобраться в сложных эмоциях и найти решения.",
        "price": 300,
        "type": "therapy"
    },
    {
        "id": "sleep_guide",
        "title": "🌙 Гид по улучшению сна",
        "description": "Персонализированный план по улучшению качества сна\n\nСоветы и техники для глубокого восстановительного сна.",
        "price": 250,
        "type": "guide"
    },
    {
        "id": "stress_relief",
        "title": "🌀 Антистресс программа",
        "description": "7-дневная программа по снижению стресса\n\nЕжедневные упражнения и рекомендации.",
        "price": 400,
        "type": "program"
    },
    {
        "id": "premium_1_day",
        "title": "💎 Премиум на 1 день",
        "description": "Премиум доступ на 1 день\n\nНеограниченные запросы и доступ ко всем функциям.",
        "price": 100,
        "type": "premium"
    },
    {
        "id": "premium_7_days",
        "title": "💎 Премиум на 7 дней",
        "description": "Премиум доступ на 7 дней\n\nНеограниченные запросы и доступ ко всем функциям.",
        "price": 600,
        "type": "premium"
    },
    {
        "id": "premium_1_month",
        "title": "💎 Премиум на 1 месяц",
        "description": "Премиум доступ на 1 месяц\n\nНеограниченные запросы и доступ ко всем функциям.",
        "price": 2000,
        "type": "premium"
    }
]

# Реквизиты для оплаты
PAYMENT_DETAILS = {
    "crypto": {
        "TRC20_USDT": "TMrLxEVr1sd5UCYB2iQXpj7GM3K5KdXTCP"
    },
    "yoomoney": {
        "account": "4100119110059662",
        "comment": "ПОДДЕРЖКА и ваш @username.\n"
        "ПРИМЕР: ПОДДЕРЖКА Ivansokolov"
    }
}

# Медитации
MEDITATIONS = [
    {
        "id": 1,
        "title": "🧘‍♀️ Медитация осознанности",
        "description": "10-минутная практика осознанности. Сосредоточьтесь на дыхании и наблюдайте за своими мыслями без оценки.",
        "duration": 10,
        "hearts_reward": 20
    },
    {
        "id": 2,
        "title": "🌊 Медитация для снятия стресса",
        "description": "10-минутная медитация, помогающая снять напряжение и расслабиться. Представьте себя у океана.",
        "duration": 10,
        "hearts_reward": 20
    },
    {
        "id": 3,
        "title": "💖 Медитация любящей доброты",
        "description": "10-минутная практика, направленная на развитие сострадания к себе и другим.",
        "duration": 10,
        "hearts_reward": 20
    },
    {
        "id": 4,
        "title": "🌳 Медитация в природе",
        "description": "10-минутная визуализация природы. Представьте себя в лесу или у горного ручья.",
        "duration": 10,
        "hearts_reward": 20
    },
    {
        "id": 5,
        "title": "🌙 Медитация перед сном",
        "description": "10-минутная практика для расслабления перед сном. Помогает улучшить качество сна.",
        "duration": 10,
        "hearts_reward": 20
    },
    {
        "id": 6,
        "title": "☀️ Утренняя медитация",
        "description": "10-минутная практика для начала дня с ясным умом и позитивным настроем.",
        "duration": 10,
        "hearts_reward": 20
    },
    {
        "id": 7,
        "title": "🌀 Медитация для концентрации",
        "description": "10-минутная практика, улучшающая концентрацию и внимание.",
        "duration": 10,
        "hearts_reward": 20
    }
]

# Проверка переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_URL")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
CRYPTO_API_KEY = os.getenv("CRYPTO_API_KEY")

if not all([BOT_TOKEN, DB_URL]):
    logger.critical("Отсутствуют обязательные переменные окружения!")
    exit(1)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Подключение к БД
engine = create_async_engine(DB_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Определяем таблицу users
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("telegram_id", BigInteger, unique=True, nullable=False),
    Column("full_name", String(100)),  # Убедитесь, что это поле есть
    Column("username", String(100)),
    Column("is_premium", Boolean, default=False),
    Column("weekly_requests", Integer, default=0),
    Column("is_admin", Boolean, default=False),
    Column("trial_started_at", DateTime),
    Column("subscription_expires_at", DateTime),
    Column("hearts", Integer, default=HEARTS_PER_DAY),
    Column("total_requests", Integer, default=0),
    Column("last_request_date", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("is_banned", Boolean, default=False),
    Column("completed_challenges", Integer, default=0),
    Column("last_challenge_time", DateTime),
    Column("active_challenge", String(200), nullable=True),
    Column("challenge_started_at", DateTime, nullable=True),
    Column("extra_requests", Integer, default=0),
    Column("referral_code", String(20), nullable=True),
    Column("referred_by", BigInteger, nullable=True),
    Column("ip_address", BigInteger, nullable=True),
    Column("referral_count", Integer, default=0),
    Column("name", String(100), nullable=True),
    Column("last_referral_month", Integer, default=datetime.now().month),
    Column("current_month_referrals", Integer, default=0)
)

# Таблица платежей
payments = Table(
    "payments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("amount", Float),
    Column("currency", String(10)),
    Column("payment_method", String(20)),
    Column("transaction_id", String(100)),
    Column("status", String(20), default="pending"),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("completed_at", DateTime, nullable=True),
)

# Таблица админских действий
admin_actions = Table(
    "admin_actions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("admin_id", BigInteger),
    Column("action", String(50)),
    Column("target_user_id", BigInteger),
    Column("details", String(200)),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Таблица сообщений пользователей
user_messages = Table(
    "user_messages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("message_text", String(1000)),
    Column("is_ai_response", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Таблица акций
promotions = Table(
    "promotions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(100)),
    Column("description", String(500)),
    Column("promo_code", String(20), unique=True),
    Column("discount_percent", Integer),
    Column("hearts_reward", Integer),
    Column("start_date", DateTime),
    Column("end_date", DateTime),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("tasks", String(500), nullable=True),
    Column("reward_type", String(10))  # 'hearts' или 'discount'
)

# Таблица выполненных заданий акций
promotion_tasks = Table(
    "promotion_tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("promotion_id", Integer),
    Column("task", String(100)),
    Column("completed", Boolean, default=False),
    Column("completed_at", DateTime, nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow)
)

# Таблица рефералов
referrals = Table(
    "referrals",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("referrer_id", BigInteger),
    Column("referred_id", BigInteger),
    Column("reward_paid", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.utcnow)
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
    Column("password", String(100), nullable=True)
)

# Таблица медитаций
meditations = Table(
    "meditations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(100)),
    Column("description", String(500)),
    Column("duration", Integer),
    Column("hearts_reward", Integer),
    Column("audio_file_id", String(200), nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow)
)

# Таблица привычек
habits = Table(
    "habits",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("title", String(100)),
    Column("description", String(500)),
    Column("reminder_enabled", Boolean, default=False),
    Column("reminder_time", String(10), nullable=True),
    Column("reminder_frequency", String(20), nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("completed", Boolean, default=False),
    Column("completed_at", DateTime, nullable=True)
)

# Таблица выполненных привычек
habit_completions = Table(
    "habit_completions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("habit_id", Integer),
    Column("completed_at", DateTime, default=datetime.utcnow)
)

# Таблица напоминаний
reminders = Table(
    "reminders",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("habit_id", Integer),
    Column("reminder_time", String(10)),
    Column("next_reminder", DateTime),
    Column("frequency", String(20)),
    Column("is_active", Boolean, default=True)
)

# --- Вспомогательные функции ---
async def setup_db():
    """Создает таблицы при первом запуске"""
    try:
        async with engine.begin() as conn:
            # Удаляем все таблицы, если они существуют
            await conn.run_sync(metadata.drop_all)
            # Создаем таблицы заново
            await conn.run_sync(metadata.create_all)
            logger.info("✅ Таблицы БД успешно пересозданы")
    except Exception as e:
        logger.critical(f"❌ Ошибка при создании таблиц: {e}")
        raise

async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получает пользователя из БД"""
    try:
        async with async_session() as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE telegram_id = :telegram_id"),
                {"telegram_id": telegram_id}
            )
            user = result.mappings().first()
            return dict(user) if user else None
    except Exception as e:
<<<<<<< HEAD
        logger.error(f"Error in get_user for telegram_id {telegram_id}: {e}", exc_info=True)
        return None

async def get_user_by_username(username: str):
    """Получение пользователя по его username"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username}
        )
        user = result.fetchone()
        if user:
            return user
        return None

async def save_user(user):
    """Сохранение данных пользователя в базу данных"""
    async with async_session() as session:
        session.add(user)
        await session.commit()

async def get_user_message_history(user_id: int, days: int, page: int = 1, page_size: int = 10):
    """Получение истории сообщений пользователя за последние N дней с пагинацией"""
    async with async_session() as session:
        query = text("""
            SELECT * FROM user_messages
            WHERE user_id = :user_id
            AND created_at >= NOW() - INTERVAL :days DAY
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await session.execute(query, {"user_id": user_id, "days": days, "limit": page_size, "offset": (page - 1) * page_size})
        messages = result.fetchall()
        return messages



async def create_user(telegram_id: int, full_name: str, username: str = None, is_admin: bool = False):
    """Создание пользователя с дополнительной валидацией"""
=======
        logger.error(f"Error in get_user: {e}", exc_info=True)
        return None

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Получает пользователя по username"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username.replace('@', '')}
        )
        row = result.mappings().first()
        return dict(row) if row else None

async def create_user(telegram_id: int, full_name: str, username: str = None, 
                     is_admin: bool = False, referred_by: int = None, 
                     ip_address: int = None) -> Dict[str, Any]:
    """Создает нового пользователя"""
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
    try:
        async with async_session() as session:
            # Проверяем текущий месяц
            current_month = datetime.now().month
<<<<<<< HEAD
            referral_code = f"REF{random.randint(1000, 9999)}"

=======
            
            referral_code = f"REF{random.randint(1000, 9999)}"
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
            user_data = {
                "telegram_id": telegram_id,
                "full_name": full_name,
                "username": username,
                "is_admin": is_admin,
                "trial_started_at": datetime.utcnow() if not is_admin else None,
<<<<<<< HEAD
                "hearts": HEARTS_PER_DAY,
                "created_at": datetime.utcnow(),
                "referral_code": referral_code
            }

=======
                "hearts": HEARTS_PER_DAY + (REFERRAL_REWARD if referred_by else 0),
                "last_request_date": datetime.utcnow(),
                "referral_code": referral_code,
                "referred_by": referred_by,
                "ip_address": ip_address,
                "referral_count": 0,
                "last_referral_month": current_month,
                "current_month_referrals": 0,
                "created_at": datetime.utcnow()
            }
            
            # Создание пользователя
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
            result = await session.execute(
                users.insert().values(**user_data).returning(users)
            )
            await session.commit()
<<<<<<< HEAD

            created_user = result.mappings().first()
            return dict(created_user)
    except Exception as e:
        logger.error(f"Critical error in create_user: {e}", exc_info=True)
        raise


=======
            
            created_user = result.mappings().first()
            if not created_user:
                raise ValueError("User creation returned empty result")
            
            created_user_dict = dict(created_user)

            # Обработка реферала (если есть)
            if referred_by:
                try:
                    # Проверяем месяц последнего реферала у пригласившего
                    referrer = await get_user(referred_by)
                    if referrer:
                        current_month = datetime.now().month
                        if referrer['last_referral_month'] != current_month:
                            # Сброс счетчика, если месяц изменился
                            await update_user(
                                referred_by,
                                last_referral_month=current_month,
                                current_month_referrals=0
                            )
                        
                        # Проверяем лимит рефералов в текущем месяце
                        if referrer['current_month_referrals'] < MAX_REFERRALS_PER_MONTH:
                            # Обновляем данные пригласившего
                            await update_user(
                                referred_by,
                                hearts=referrer.get('hearts', 0) + REFERRAL_REWARD,
                                referral_count=referrer.get('referral_count', 0) + 1,
                                current_month_referrals=referrer.get('current_month_referrals', 0) + 1
                            )
                            
                            # Добавляем запись в рефералы
                            await session.execute(
                                referrals.insert().values(
                                    referrer_id=referred_by,
                                    referred_id=telegram_id,
                                    created_at=datetime.utcnow()
                                )
                            )
                            await session.commit()
                            logger.info(f"Referral bonus applied for {referred_by}")
                except Exception as ref_error:
                    logger.error(f"Referral processing failed: {ref_error}")
                    await session.rollback()

            return created_user_dict
            
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
    except Exception as e:
        logger.error(f"Critical error in create_user: {e}", exc_info=True)
        if 'session' in locals():
            await session.rollback()
        raise

async def update_user(telegram_id: int, **kwargs) -> bool:
    """Обновляет данные пользователя"""
    try:
        async with async_session() as session:
            # Удаляем weekly_requests из kwargs, если он есть и не используется в таблице
            if 'weekly_requests' in kwargs:
                kwargs.pop('weekly_requests')
                
            stmt = users.update().where(users.c.telegram_id == telegram_id).values(**kwargs)
            await session.execute(stmt)
            await session.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False

async def log_admin_action(admin_id: int, action: str, target_user_id: int = None, details: str = None):
    """Логирует действия админа"""
    async with async_session() as session:
        await session.execute(
            admin_actions.insert().values(
                admin_id=admin_id,
                action=action,
                target_user_id=target_user_id,
                details=details
            )
        )
        await session.commit()

async def check_subscription(user: Dict[str, Any]) -> bool:
    """Проверяет активность подписки"""
    if not user or user.get('is_banned'):
        return False
    if user.get('is_admin'):
        return True
    if user.get('is_premium') and user.get('subscription_expires_at') and user['subscription_expires_at'] > datetime.utcnow():
        return True
    if user.get('trial_started_at') and (datetime.utcnow() - user['trial_started_at']).days <= TRIAL_DAYS:
        return True
    return False

async def check_request_limit(user: Dict[str, Any]) -> bool:
    """Проверяет лимиты запросов"""
    if not user:
        return False

    now = datetime.now(timezone.utc)
    today = now.date()
    last_request = user.get('last_request_date')

    # Для премиум: сброс daily (используем total_requests) ежедневно
    if user.get('is_premium'):
        if last_request is None or last_request.replace(tzinfo=timezone.utc).date() != today:
            await update_user(
                user['telegram_id'],
                total_requests=0,
                last_request_date=now
            )
        return user.get('total_requests', 0) < PREMIUM_DAILY_LIMIT + user.get('extra_requests', 0)

    # Для обычных: сброс weekly_requests раз в неделю
    else:
        if last_request is None or (now - last_request.replace(tzinfo=timezone.utc)).days >= 7:
            await update_user(
                user['telegram_id'],
                total_requests=0,
                last_request_date=now
            )
        return user.get('total_requests', 0) < FREE_WEEKLY_LIMIT

async def get_ai_response(prompt: str, user: Dict[str, Any]) -> str:
    """Получает ответ от ИИ с учетом лимитов пользователя и кризисных сообщений"""
    if not OPENAI_API_KEY:
        return (
            "🧠 <b>Технические работы</b>\n\n"
            "В данный момент ИИ-ассистент временно недоступен.\n"
            "Попробуйте выполнить один из наших челленджей или вернитесь позже.\n\n"
            "Используйте команду /challenge для получения задания!"
        )
    
    crisis_keywords = ["суицид", "самоубийство", "покончить с собой", "депрессия", "не хочу жить"]
    if any(keyword in prompt.lower() for keyword in crisis_keywords):
        return (
            "💙 <b>Я вижу, что вам сейчас тяжело</b>\n\n"
            "К сожалению, я не могу оказать профессиональную психологическую помощь. "
            "Пожалуйста, обратитесь к специалистам:\n\n"
            "📞 Телефон доверия: 8-800-2000-122 (круглосуточно, бесплатно)\n"
            "👨‍⚕️ Психологическая помощь доступна в вашем городе.\n\n"
            "Вы не одни, помощь рядом!"
        )

    max_tokens = 500
    if user.get('is_premium'):
        max_tokens = 800

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Ты - доброжелательный ИИ-психолог. Отвечай с эмпатией и поддержкой. "
                        "Не ставь диагнозы, но мягко направляй к специалистам при необходимости. "
                        "Будь теплым и понимающим. Отвечай кратко (1-2 абзаца)."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content

<<<<<<< HEAD

    except httpx.RequestError as e:
        logger.error(f"Ошибка запроса к OpenAI: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при запросе к OpenAI: {e}", exc_info=True)
=======
    except Exception as e:
        logger.error(f"Ошибка OpenAI: {e}")
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
        return (
            "⚠️ <b>Произошла ошибка при обработке запроса</b>\n\n"
            "Попробуйте выполнить один из наших челленджей или вернитесь позже.\n\n"
            "Используйте команду /challenge для получения задания!"
        )

async def can_get_challenge(user: Dict[str, Any]) -> bool:
    """Проверяет, может ли пользователь получить новый челлендж"""
    if not user:
        return False
        
    last_challenge = user.get('last_challenge_time')
    if last_challenge is None:
        return True
        
    now = datetime.utcnow()
    # Челленджи обновляются в 9:00 и 18:00 по МСК (6:00 и 15:00 UTC)
    challenge_reset_time1 = now.replace(hour=6, minute=0, second=0, microsecond=0)
    challenge_reset_time2 = now.replace(hour=15, minute=0, second=0, microsecond=0)
    
    if now.hour < 6:
        challenge_reset_time1 -= timedelta(days=1)
    elif now.hour < 15:
        challenge_reset_time2 -= timedelta(days=1)
    
    return last_challenge < challenge_reset_time1 or last_challenge < challenge_reset_time2

async def complete_challenge(user_id: int):
    """Завершает активный челлендж и награждает пользователя"""
    async with async_session() as session:
        user = await get_user(user_id)
        if user and user.get('active_challenge'):
            new_hearts = user.get('hearts', 0) + CHALLENGE_REWARD
            await session.execute(
                users.update()
                .where(users.c.telegram_id == user_id)
                .values(
                    hearts=new_hearts,
                    completed_challenges=user.get('completed_challenges', 0) + 1,
                    last_challenge_time=datetime.utcnow(),
                    active_challenge=None,
                    challenge_started_at=None
                )
            )
            await session.commit()
            return new_hearts
    return None

async def get_crypto_rate(crypto: str) -> Optional[Decimal]:
    """Получает текущий курс криптовалюты"""
    try:
        async with httpx.AsyncClient() as client:
            if crypto == "USDT":
                url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub"
                response = await client.get(url)
                data = response.json()
                return Decimal(str(data["tether"]["rub"]))
    except Exception as e:
        logger.error(f"Ошибка получения курса {crypto}: {e}")
        return None

async def calculate_crypto_amount(rub_amount: Decimal, crypto: str) -> Optional[Decimal]:
    """Рассчитывает сумму в криптовалюте"""
    rate = await get_crypto_rate(crypto)
    if not rate:
        return None
    return (rub_amount / rate).quantize(Decimal('0.00000001'))

async def check_crypto_payment(address: str, expected_amount: Decimal, crypto: str) -> bool:
    """Проверяет поступление платежа"""
    return True

async def get_recent_users(limit: int = 10) -> List[Dict[str, Any]]:
    """Получает последних зарегистрированных пользователей"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT username, created_at FROM users ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit}
        )
        return [dict(row) for row in result.mappings()]

async def get_user_messages(user_id: int, days: int = 1) -> List[Dict[str, Any]]:
    """Получает сообщения пользователя за последние дни"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT message_text, created_at FROM user_messages WHERE user_id = :user_id AND created_at >= NOW() - INTERVAL ':days days' ORDER BY created_at DESC"),
            {"user_id": user_id, "days": days}
        )
        return [dict(row) for row in result.mappings()]

<<<<<<< HEAD
async def create_promotion(title: str, description: str, promo_code: str, discount_percent: int, hearts_reward: int,
                           start_date: datetime, end_date: datetime, tasks: str = None, reward_type: str = "hearts"):
    try:
        # Логирование данных перед вставкой
        logger.info(f"Создание акции с данными: title={title}, description={description}, promo_code={promo_code}, "
                    f"discount_percent={discount_percent}, hearts_reward={hearts_reward}, start_date={start_date}, "
                    f"end_date={end_date}, tasks={tasks}, reward_type={reward_type}")

        # Проверка на пустые даты
        if not start_date or not end_date:
            logger.error("Ошибка: дата начала или дата окончания акции не может быть пустой!")
            raise ValueError("Дата начала или дата окончания акции не может быть пустой.")

        if start_date >= end_date:
            logger.error("Ошибка: дата начала акции не может быть больше или равна дате окончания!")
            raise ValueError("Дата начала акции не может быть больше или равна дате окончания.")

        # Проверка на уникальность промокода
        async with async_session() as session:
            existing_promo = await session.execute(
                text("SELECT * FROM promotions WHERE promo_code = :promo_code"),
                {"promo_code": promo_code}
            )
            if existing_promo.first():
                logger.error(f"Промокод {promo_code} уже существует!")
                raise ValueError(f"Промокод {promo_code} уже существует!")

        # Вставка новой акции
        async with async_session() as session:
            await session.execute(
                promotions.insert().values(
                    title=title,
                    description=description,
                    promo_code=promo_code,
                    discount_percent=discount_percent,
                    hearts_reward=hearts_reward,
                    start_date=start_date,
                    end_date=end_date,
                    tasks=tasks,
                    reward_type=reward_type
                )
            )
            await session.commit()
            logger.info(f"Акция {title} успешно создана!")
    except Exception as e:
        # Логирование ошибок и откат транзакции
        logger.error(f"Ошибка при создании акции: {e}")
        await session.rollback()  # откат транзакции
        raise


=======
async def create_promotion(title: str, description: str, promo_code: str, discount_percent: int, hearts_reward: int, start_date: datetime, end_date: datetime, tasks: str = None, reward_type: str = "hearts"):
    """Создает новую акцию"""
    async with async_session() as session:
        await session.execute(
            promotions.insert().values(
                title=title,
                description=description,
                promo_code=promo_code,
                discount_percent=discount_percent,
                hearts_reward=hearts_reward,
                start_date=start_date,
                end_date=end_date,
                tasks=tasks,
                reward_type=reward_type
            )
        )
        await session.commit()
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6

async def get_promotions() -> List[Dict[str, Any]]:
    """Получает список активных акций"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM promotions WHERE end_date >= NOW()")
        )
        return [dict(row) for row in result.mappings()]

async def get_user_referrals(user_id: int) -> List[Dict[str, Any]]:
    """Получает список рефералов пользователя"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM referrals WHERE referrer_id = :user_id"),
            {"user_id": user_id}
        )
        return [dict(row) for row in result.mappings()]

async def get_diary_entries(user_id: int) -> List[Dict[str, Any]]:
    """Получает записи дневника пользователя"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM diary_entries WHERE user_id = :user_id ORDER BY created_at DESC"),
            {"user_id": user_id}
        )
        return [dict(row) for row in result.mappings()]

async def create_diary_entry(user_id: int, entry_text: str, mood: str = None):
    """Создает запись в дневнике"""
    async with async_session() as session:
        await session.execute(
            diary_entries.insert().values(
                user_id=user_id,
                entry_text=entry_text,
                mood=mood
            )
        )
        await session.commit()
        
        # Награждаем пользователя за запись в дневнике
        user = await get_user(user_id)
        if user:
            new_hearts = user.get('hearts', 0) + 5  # 5 сердечек за запись
            await update_user(user_id, hearts=new_hearts)

async def set_diary_password(user_id: int, password: str):
    """Устанавливает пароль на дневник"""
    async with async_session() as session:
<<<<<<< HEAD
        hashed_password = pwd_context.hash(password)
        await session.execute(
            diary_entries.update()
            .where(diary_entries.c.user_id == user_id)
            .values(password=hashed_password)
=======
        await session.execute(
            diary_entries.update()
            .where(diary_entries.c.user_id == user_id)
            .values(password=password)
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
        )
        await session.commit()

async def get_meditations() -> List[Dict[str, Any]]:
    """Получает список медитаций"""
    return MEDITATIONS

async def get_habit(user_id: int, habit_id: int) -> Optional[Dict[str, Any]]:
    """Получает привычку пользователя"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM habits WHERE user_id = :user_id AND id = :habit_id"),
            {"user_id": user_id, "habit_id": habit_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None

async def get_user_habits(user_id: int) -> List[Dict[str, Any]]:
    """Получает привычки пользователя"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM habits WHERE user_id = :user_id ORDER BY created_at DESC"),
            {"user_id": user_id}
        )
        return [dict(row) for row in result.mappings()]

async def create_habit(user_id: int, title: str, description: str, reminder_enabled: bool = False, 
                      reminder_time: str = None, reminder_frequency: str = None):
    """Создает новую привычку"""
    async with async_session() as session:
        result = await session.execute(
            habits.insert().values(
                user_id=user_id,
                title=title,
                description=description,
                reminder_enabled=reminder_enabled,
                reminder_time=reminder_time,
                reminder_frequency=reminder_frequency
            ).returning(habits)
        )
        await session.commit()
        
        habit = result.mappings().first()
        if habit and reminder_enabled and reminder_time and reminder_frequency:
            # Создаем напоминание
            await create_reminder(user_id, habit['id'], reminder_time, reminder_frequency)
        
        return dict(habit) if habit else None

async def complete_habit(habit_id: int):
    """Отмечает привычку как выполненную"""
    async with async_session() as session:
        await session.execute(
            habits.update()
            .where(habits.c.id == habit_id)
            .values(completed=True, completed_at=datetime.utcnow())
        )
        
        await session.execute(
            habit_completions.insert().values(
                habit_id=habit_id,
                completed_at=datetime.utcnow()
            )
        )
        await session.commit()

async def create_reminder(user_id: int, habit_id: int, reminder_time: str, frequency: str):
    """Создает напоминание для привычки"""
    async with async_session() as session:
        # Рассчитываем следующее напоминание
        now = datetime.now()
        reminder_hour, reminder_minute = map(int, reminder_time.split(':'))
        
        if frequency == "daily":
            next_reminder = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
            if next_reminder < now:
                next_reminder += timedelta(days=1)
        elif frequency == "weekly":
            next_reminder = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
            while next_reminder < now:
                next_reminder += timedelta(days=7)
        elif frequency == "monthly":
            next_reminder = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
            while next_reminder < now:
                next_reminder += timedelta(days=30)
        else:
            next_reminder = now.replace(hour=reminder_hour, minute=reminder_minute, second=0, microsecond=0)
            if next_reminder < now:
                next_reminder += timedelta(days=1)
        
        await session.execute(
            reminders.insert().values(
                user_id=user_id,
                habit_id=habit_id,
                reminder_time=reminder_time,
                next_reminder=next_reminder,
                frequency=frequency
            )
        )
        await session.commit()

async def get_habit_completions(habit_id: int) -> List[Dict[str, Any]]:
    """Получает историю выполнения привычки"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM habit_completions WHERE habit_id = :habit_id ORDER BY completed_at DESC"),
            {"habit_id": habit_id}
        )
        return [dict(row) for row in result.mappings()]

async def get_user_stats(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Получает статистику пользователя за указанный период"""
    async with async_session() as session:
        # Получаем количество выполненных челленджей
        result = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE telegram_id = :user_id AND last_challenge_time >= NOW() - INTERVAL ':days days'"),
            {"user_id": user_id, "days": days}
        )
        challenges_completed = result.scalar() or 0
        
        # Получаем количество записей в дневнике
        result = await session.execute(
            text("SELECT COUNT(*) FROM diary_entries WHERE user_id = :user_id AND created_at >= NOW() - INTERVAL ':days days'"),
            {"user_id": user_id, "days": days}
        )
        diary_entries = result.scalar() or 0
        
        # Получаем количество выполненных привычек
        result = await session.execute(
            text("SELECT COUNT(*) FROM habit_completions WHERE habit_id IN (SELECT id FROM habits WHERE user_id = :user_id) AND completed_at >= NOW() - INTERVAL ':days days'"),
            {"user_id": user_id, "days": days}
        )
        habits_completed = result.scalar() or 0
        
        # Получаем заработанные сердечки
        result = await session.execute(
            text("SELECT hearts FROM users WHERE telegram_id = :user_id"),
            {"user_id": user_id}
        )
        hearts = result.scalar() or 0
        
        return {
            "challenges_completed": challenges_completed,
            "diary_entries": diary_entries,
            "habits_completed": habits_completed,
            "hearts_earned": hearts
        }

# --- Клавиатуры ---
def get_challenge_keyboard(challenge_id: str):
    """Клавиатура для челленджа"""
    buttons = [
        [InlineKeyboardButton(text="✅ Начать челлендж", callback_data=f"start_{challenge_id}")],
        [InlineKeyboardButton(text="🔔 Включить уведомления", callback_data="enable_challenge_notifications")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_challenge_timer_keyboard():
    """Клавиатура с таймером челленджа"""
    buttons = [
        [InlineKeyboardButton(text="⏳ Завершить", callback_data="complete_challenge")],
        [InlineKeyboardButton(text="❌ Выйти (без награды)", callback_data="cancel_challenge")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_shop_keyboard():
    """Клавиатура магазина"""
    buttons = []
    for item in SHOP_ITEMS:
        buttons.append([InlineKeyboardButton(text=item["title"], callback_data=f"shop_{item['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_subscription_keyboard():
    """Клавиатура выбора подписки"""
    buttons = [
        [InlineKeyboardButton(text="1 месяц - 299₽", callback_data="sub_1_month")],
        [InlineKeyboardButton(text="3 месяца - 749₽", callback_data="sub_3_months")],
        [InlineKeyboardButton(text="6 месяцев - 1299₽", callback_data="sub_6_months")],
        [InlineKeyboardButton(text="1 год - 2199₽", callback_data="sub_1_year")],
        [InlineKeyboardButton(text="💖 Купить за сердечки", callback_data="buy_with_hearts")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_hearts_subscription_keyboard():
    """Клавиатура подписки за сердечки"""
    buttons = [
        [InlineKeyboardButton(text="1 день - 100💖", callback_data="hearts_sub_1_day")],
        [InlineKeyboardButton(text="7 дней - 600💖", callback_data="hearts_sub_7_days")],
        [InlineKeyboardButton(text="1 месяц - 2000💖", callback_data="hearts_sub_1_month")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_method_keyboard():
    """Клавиатура выбора способа оплаты"""
    buttons = [
        [InlineKeyboardButton(text="💳 Криптовалюта (USDT)", callback_data="pay_crypto")],
        [InlineKeyboardButton(text="🟣 ЮMoney", callback_data="pay_yoomoney")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard():
    """Клавиатура админа"""
    buttons = [
        [InlineKeyboardButton(text="👤 Активировать премиум", callback_data="admin_premium")],
        [InlineKeyboardButton(text="💖 Начислить сердечки", callback_data="admin_hearts")],
        [InlineKeyboardButton(text="🚫 Заблокировать пользователя", callback_data="admin_ban")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🎁 Акции", callback_data="admin_promotions")],
        [InlineKeyboardButton(text="📝 История сообщений", callback_data="admin_user_messages")],
        [InlineKeyboardButton(text="🔄 Сбросить активность", callback_data="admin_reset_activity")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_shop_keyboard():
    """Клавиатура возврата в магазин"""
    buttons = [
        [InlineKeyboardButton(text="🔙 В магазин", callback_data="back_to_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_psychology_menu_keyboard():
    """Клавиатура психологического раздела"""
    buttons = [
        [InlineKeyboardButton(text="💬 Чат с ИИ-психологом", callback_data="ai_psychologist")],
        [InlineKeyboardButton(text="📔 Личный дневник", callback_data="personal_diary")],
        [InlineKeyboardButton(text="🧘‍♀️ Медитации", callback_data="meditations")],
        [InlineKeyboardButton(text="🎯 Цели и привычки", callback_data="habits")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_diary_keyboard():
    """Клавиатура дневника"""
    buttons = [
        [InlineKeyboardButton(text="✍️ Новая запись", callback_data="new_diary_entry")],
        [InlineKeyboardButton(text="📖 Мои записи", callback_data="my_diary_entries")],
        [InlineKeyboardButton(text="🔐 Установить пароль", callback_data="set_diary_password")],
        [InlineKeyboardButton(text="📊 Анализ записей (20💖)", callback_data="analyze_diary")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_diary_entries_keyboard():
    """Клавиатура для просмотра записей дневника"""
    buttons = [
        [InlineKeyboardButton(text="📅 За сегодня", callback_data="diary_today")],
        [InlineKeyboardButton(text="📆 За неделю", callback_data="diary_week")],
        [InlineKeyboardButton(text="🗓 За месяц", callback_data="diary_month")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="personal_diary")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_meditation_keyboard(meditation_id: int):
    """Клавиатура медитации"""
    buttons = [
        [InlineKeyboardButton(text="🧘‍♀️ Начать медитацию (20💖)", callback_data=f"start_meditation_{meditation_id}")],
        [InlineKeyboardButton(text="📖 Прочитать описание", callback_data=f"read_meditation_{meditation_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="meditations")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_meditation_timer_keyboard(meditation_id: int):
    """Клавиатура с таймером медитации"""
    buttons = [
        [InlineKeyboardButton(text="✅ Завершить медитацию", callback_data=f"complete_meditation_{meditation_id}")],
        [InlineKeyboardButton(text="❌ Выйти (без награды)", callback_data="cancel_meditation")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_habits_keyboard():
    """Клавиатура раздела привычек"""
    buttons = [
        [InlineKeyboardButton(text="➕ Новая привычка", callback_data="new_habit")],
        [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="habits_progress")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_habit_frequency_keyboard():
    """Клавиатура выбора частоты напоминаний"""
    buttons = [
        [InlineKeyboardButton(text="Ежедневно", callback_data="habit_frequency_daily")],
        [InlineKeyboardButton(text="Еженедельно", callback_data="habit_frequency_weekly")],
        [InlineKeyboardButton(text="Ежемесячно", callback_data="habit_frequency_monthly")],
        [InlineKeyboardButton(text="Без напоминаний", callback_data="habit_frequency_none")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_habits_keyboard():
    """Клавиатура возврата к привычкам"""
    buttons = [
        [InlineKeyboardButton(text="🔙 К привычкам", callback_data="habits")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_referral_keyboard():
    """Клавиатура реферальной системы"""
    buttons = [
        [InlineKeyboardButton(text="🔗 Получить реферальную ссылку", callback_data="get_referral_link")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="referral_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_keyboard(callback_data: str):
    """Универсальная кнопка Назад"""
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Команды для пользователей ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    try:
        # Принудительно пересоздаем таблицы при старте
        await setup_db()

        user = await get_user(message.from_user.id)

        if not user:
            is_admin = message.from_user.id in ADMIN_IDS
            try:
                user = await create_user(
                    telegram_id=message.from_user.id,
                    full_name=message.from_user.full_name,
                    username=message.from_user.username,
                    is_admin=is_admin
                )

                if is_admin:
                    await message.answer(
                        "👑 Добро пожаловать, администратор!\n\n"
                        "Используйте /admin для управления ботом")
                    return

                await message.answer("Добро пожаловать! Ваш профиль создан.")
            except Exception as e:
                logger.error(f"Ошибка при создании пользователя: {e}")
                await message.answer("Произошла ошибка при создании профиля. Пожалуйста, попробуйте еще раз.")
                return
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}", exc_info=True)
        await message.answer("Произошла критическая ошибка. Пожалуйста, сообщите администратору.")
        # Приветственное сообщение
        welcome_msg = (
            "🌸 <b>Добро пожаловать в психологический помощник!</b> 🌸\n\n"
            "Я здесь, чтобы помочь тебе на пути к гармонии и душевному равновесию. "
            "Вместе мы сможем:\n\n"
            "• Разобраться в своих эмоциях и переживаниях 💭\n"
            "• Научиться справляться со стрессом и тревогой 🌿\n"
            "• Развить полезные привычки для ментального здоровья 🎯\n"
            "• Вести личный дневник для самопознания 📔\n"
            "• Практиковать медитации для расслабления 🧘‍♀️\n\n"
            "Каждый день ты будешь получать сердечки 💖 за активность в боте, "
            "которые можно обменять на полезные функции в магазине.\n\n"
            "Давай начнем наш путь к гармонии вместе! Выбери раздел:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu")],
            [InlineKeyboardButton(text="💞 Реферальная система", callback_data="referral_system")],
            [InlineKeyboardButton(text="🏆 Челленджи", callback_data="get_challenge")],
            [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")]
        ])
        
        await message.answer(welcome_msg, reply_markup=keyboard, parse_mode="HTML")
        
        # Если это новый пользователь, запрашиваем имя
        if not user.get('name'):
            await message.answer("Как тебя зовут? Напиши свое имя для персонализации:")
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def show_main_menu(user_id: int, message: Message):
    """Показывает главное меню с учетом прав пользователя"""
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    
    if user.get('is_admin'):
        await message.answer(
            f"👑 Админ-панель, {name}",
            reply_markup=get_admin_keyboard()
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu")],
            [InlineKeyboardButton(text="💞 Реферальная система", callback_data="referral_system")],
            [InlineKeyboardButton(text="🏆 Челленджи", callback_data="get_challenge")],
            [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")]
        ])
        
        await message.answer(
            f"Привет, {name}!\n\nВыберите раздел:",
            reply_markup=keyboard
        )

async def handle_name_input(message: Message):
    """Обработка ввода имени пользователя"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала используйте /start")
        return
    
    # Если имя еще не установлено
    if not user.get('name'):
        name = message.text.strip()
        if len(name) < 2:
            await message.answer("⚠️ Имя должно содержать минимум 2 символа. Попробуйте еще раз:")
            return
            
        await update_user(message.from_user.id, name=name)
        
        # Приветственное сообщение после установки имени
        welcome_msg = (
            f"✨ Привет, {name}! Добро пожаловать в психологический помощник. ✨\n\n"
            "Я здесь, чтобы помочь тебе с:\n"
            "• Консультациями с ИИ-психологом 💬\n"
            "• Ведением личного дневника 📔\n"
            "• Медитациями и упражнениями 🧘‍♀️\n"
            "• Анализом настроения и эмоций 🔍\n"
            "• Развитием полезных привычек 🎯\n\n"
            "📊 Твои текущие возможности:\n"
            f"- Пробный период: {TRIAL_DAYS} дня\n"
            f"- Лимит запросов: {TRIAL_DAILY_LIMIT}/день\n"
            f"- Сердечек в день: {HEARTS_PER_DAY}\n\n"
            "🏆 Выполняй челленджи и получай +{CHALLENGE_REWARD} сердечек за каждое задание!\n"
            "💖 Зарабатывай сердечки за активность и трать их в магазине на полезные функции.\n\n"
            "Рекомендую начать с раздела 'Психология' или посмотреть свой профиль:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu")],
            [InlineKeyboardButton(text="💞 Реферальная система", callback_data="referral_system")]
        ])
        
        await message.answer(welcome_msg, reply_markup=keyboard)
    else:
        await handle_text_message(message)

async def show_user_profile(user_id: int, message: Message):
    """Показывает профиль пользователя с красивым оформлением"""
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    days_left = TRIAL_DAYS - (datetime.utcnow() - user['trial_started_at']).days if user.get('trial_started_at') else 0
    days_left = max(0, days_left)
    
    # Определяем статус подписки
    if await check_subscription(user):
        if user.get('is_premium'):
            expires = user['subscription_expires_at'].strftime("%d.%m.%Y") if user.get('subscription_expires_at') else "∞"
            status = f"💎 Премиум (до {expires})"
            requests_left = PREMIUM_DAILY_LIMIT + user.get('extra_requests', 0) - user.get('total_requests', 0)
            requests_info = f"{user.get('total_requests', 0)}/{PREMIUM_DAILY_LIMIT + user.get('extra_requests', 0)}"
        else:
            status = f"🆓 Пробный период ({days_left} дн. осталось)"
            requests_left = TRIAL_DAILY_LIMIT - user.get('total_requests', 0)
            requests_info = f"{user.get('total_requests', 0)}/{TRIAL_DAILY_LIMIT}"
    else:
        status = "🌿 Бесплатный"
        requests_left = FREE_WEEKLY_LIMIT - user.get('total_requests', 0)
        requests_info = f"{user.get('total_requests', 0)}/{FREE_WEEKLY_LIMIT}"
    
    # Определяем прогресс привычек
    habits = await get_user_habits(user_id)
    completed_habits = sum(1 for h in habits if h.get('completed'))
    habits_progress = f"{completed_habits}/{len(habits)}" if habits else "0/0"
    
    # Формируем сообщение профиля
    profile_msg = (
        f"👤 <b>Профиль {name}</b>\n\n"
        f"🔹 Статус: {status}\n"
        f"🔹 Запросов осталось: {requests_left}\n"
        f"🔹 Сердечек: {user.get('hearts', 0)} 💖\n"
        f"🔹 Челленджей выполнено: {user.get('completed_challenges', 0)} 🏆\n"
        f"🔹 Привычек выполнено: {habits_progress} ✅\n"
        f"🔹 Рефералов: {user.get('referral_count', 0)} 👥\n\n"
        "<b>Достижения за последние 5 дней:</b>\n"
    )
    
    # Добавляем статистику за последние 5 дней
    stats = await get_user_stats(user_id, 5)
    if stats:
        profile_msg += (
            f"- Челленджей: {stats['challenges_completed']}\n"
            f"- Записей в дневнике: {stats['diary_entries']}\n"
            f"- Привычек выполнено: {stats['habits_completed']}\n"
            f"- Сердечек заработано: {stats['hearts_earned']}\n\n"
        )
    
    # Кнопки управления
    buttons = [
        [InlineKeyboardButton(text="💎 Оформить подписку", callback_data="premium_subscription")],
        [InlineKeyboardButton(text="🛍 Магазин сердечек", callback_data="shop")],
        [InlineKeyboardButton(text="🏆 Получить челлендж", callback_data="get_challenge")],
        [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu")],
        [InlineKeyboardButton(text="💞 Реферальная система", callback_data="referral_system")]
    ]
    
    await message.answer(
        profile_msg,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Команда профиля"""
    await show_user_profile(message.from_user.id, message)

@router.message(Command("psychology"))
async def cmd_psychology(message: Message):
    """Команда психологического раздела"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await message.answer(
        f"🧠 <b>Психологический раздел, {name}</b>\n\n"
        "Здесь вы можете получить профессиональную поддержку, вести дневник и улучшить свое ментальное здоровье.\n\n"
        "<b>Доступные функции:</b>\n"
        "💬 Чат с ИИ-психологом - обсудите свои мысли и чувства\n"
        "📔 Личный дневник - записывайте свои мысли и анализируйте их\n"
        "🧘‍♀️ Медитации - практики для расслабления и осознанности\n"
        "📅 План на неделю - поставьте цели и отслеживайте прогресс\n"
        "🎯 Цели и привычки - работайте над своими привычками\n"
        "💞 Реферальная система - приглашайте друзей и получайте бонусы\n\n"
        "Выберите опцию:",
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработка команды /admin"""
    user = await get_user(message.from_user.id)
    if not user or not user.get('is_admin'):
        await message.answer("Доступ запрещен")
        return
    
    await message.answer(
        "👑 Админ-панель",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Обработчик кнопки профиля пользователя"""
    try:
        user = await get_user(callback.from_user.id)
        if not user:
            await callback.answer("Сначала используйте /start")
            return
        
        name = user.get('name', 'друг')
        days_left = (user['trial_started_at'] + timedelta(days=TRIAL_DAYS) - datetime.utcnow()).days if user.get('trial_started_at') else 0
        
        # Формируем сообщение профиля
        profile_msg = (
            f"👤 Профиль {name}\n\n"
            f"🔹 Статус: {'Пробный период' if not user.get('is_premium') else 'Премиум'}\n"
            f"🔹 Осталось дней: {max(0, days_left)}\n"
            f"🔹 Сердечек: {user.get('hearts', 0)}\n"
            f"🔹 Запросов сегодня: {user.get('total_requests', 0)}/{TRIAL_DAILY_LIMIT}\n"
            f"🔹 Рефералов: {user.get('referral_count', 0)}\n\n"
            "Используй сердечки в магазине или приглашай друзей!"
        )
        
        # Создаем клавиатуру профиля
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")],
            [InlineKeyboardButton(text="💞 Рефералы", callback_data="referral_system")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(profile_msg, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике профиля: {e}")
        await callback.answer("Произошла ошибка при загрузке профиля")

<<<<<<< HEAD

@router.callback_query(F.data == "list_promotions")
async def list_promotions(callback: CallbackQuery):
    """Список активных акций с возможностью удаления"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        await callback.answer("Доступ запрещен")
        return

    promotions_list = await get_promotions()

    if not promotions_list:
        await callback.message.edit_text(
            "ℹ️ Нет активных акций",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Создать акцию", callback_data="create_promotion")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promotions")]
            ])
        )
    else:
        text = "🎁 <b>Активные акции:</b>\n\n"
        buttons = []

        for promo in promotions_list:
            end_date = promo['end_date'].strftime("%d.%m.%Y")
            reward = f"{promo['hearts_reward']}💖" if promo[
                                                         'reward_type'] == "hearts" else f"{promo['discount_percent']}% скидка"

            text += (
                f"<b>{promo['title']}</b>\n"
                f"🔠 Промокод: <code>{promo['promo_code']}</code>\n"
                f"🎁 Награда: {reward}\n"
                f"📅 До: {end_date}\n\n"
            )

            buttons.append([
                InlineKeyboardButton(
                    text=f"❌ Удалить {promo['promo_code']}",
                    callback_data=f"delete_promo_{promo['id']}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(text="🎁 Создать новую", callback_data="create_promotion"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promotions")
        ])

=======
@router.callback_query(F.data == "list_promotions")
async def list_promotions(callback: CallbackQuery):
    """Список активных акций"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        return
    
    promotions_list = await get_promotions()
    
    if not promotions_list:
        await callback.message.answer("🎁 Нет активных акций")
    else:
        text = "🎁 <b>Активные акции:</b>\n\n"
        buttons = []
        
        for promo in promotions_list:
            end_date = promo['end_date'].strftime("%d.%m.%Y")
            text += f"• {promo['title']} (до {end_date})\nПромокод: {promo['promo_code']}\n\n"
            buttons.append([
                InlineKeyboardButton(
                    text=f"Удалить {promo['promo_code']}",
                    callback_data=f"delete_promo_{promo['id']}"
                )
            ])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promotions")])
        
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    await callback.answer()

<<<<<<< HEAD

@router.callback_query(F.data.startswith("delete_promo_"))
async def delete_promotion(callback: CallbackQuery):
    """Удаление акции"""
    promo_id = int(callback.data.replace("delete_promo_", ""))
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        await callback.answer("Доступ запрещен")
        return

    try:
        async with async_session() as session:
            await session.execute(
                text("DELETE FROM promotions WHERE id = :id"),
                {"id": promo_id}
            )
            await session.commit()

        await callback.answer("✅ Акция удалена")
        await list_promotions(callback)  # Обновляем список
    except Exception as e:
        logger.error(f"Ошибка при удалении акции: {e}")
        await callback.answer("⚠️ Ошибка при удалении")

=======
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
@router.callback_query(F.data == "psychology_menu")
async def psychology_menu(callback: CallbackQuery):
    """Меню психологического раздела"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"🧠 <b>Психологический раздел, {name}</b>\n\n"
        "Здесь вы можете получить профессиональную поддержку, вести дневник и улучшить свое ментальное здоровье.\n\n"
        "Выберите опцию:",
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await show_main_menu(callback.from_user.id, callback.message)
    await callback.answer()

@router.callback_query(F.data == "ai_psychologist")
async def ai_psychologist(callback: CallbackQuery):
    """Чат с ИИ-психологом"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"💬 <b>Чат с ИИ-психологом, {name}</b>\n\n"
        "Вы можете обсудить здесь свои мысли, чувства и переживания. "
        "ИИ-психолог на базе GPT-4o поможет вам разобраться в себе.\n\n"
        "<i>Отправьте ваше сообщение, и я постараюсь помочь.</i>\n\n"
        "⚠️ <b>Важно:</b> ИИ не заменяет профессионального психолога. "
        "В сложных ситуациях обратитесь к специалисту.",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "personal_diary")
async def personal_diary(callback: CallbackQuery):
    """Личный дневник"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"📔 <b>Личный дневник, {name}</b>\n\n"
        "Здесь вы можете записывать свои мысли и переживания. "
        "Все записи хранятся анонимно и защищены.\n\n"
        "Выберите действие:",
        reply_markup=get_diary_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "new_diary_entry")
async def new_diary_entry(callback: CallbackQuery):
    """Новая запись в дневнике"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"✍️ <b>Новая запись в дневнике, {name}</b>\n\n"
        "Напишите свои мысли, чувства или события дня. Вы можете добавить эмоцию в конце сообщения, например:\n\n"
        "<i>Сегодня был продуктивный день! Я закончил важный проект. 😊</i>\n\n"
        "Доступные эмоции: 😊 😢 😠 😍 😐 😨 😭 🤔",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "my_diary_entries")
async def my_diary_entries(callback: CallbackQuery):
    """Мои записи в дневнике"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    entries = await get_diary_entries(user['telegram_id'])
    if not entries:
        await callback.message.edit_text(
            "📖 <b>У вас пока нет записей в дневнике</b>\n\n"
            "Создайте первую запись, нажав на кнопку ниже.",
            reply_markup=get_diary_keyboard(),
            parse_mode="HTML"
        )
    else:
        text = "📖 <b>Ваши последние записи:</b>\n\n"
        for entry in entries[:5]:  # Показываем последние 5 записей
            date = entry['created_at'].strftime("%d.%m.%Y %H:%M")
            mood = entry.get('mood', '')
            text += f"📅 <b>{date}</b> {mood}\n{entry['entry_text'][:100]}...\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_diary_keyboard(),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data == "set_diary_password")
async def set_diary_password(callback: CallbackQuery):
    """Установка пароля на дневник"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"🔐 <b>Установка пароля на дневник, {name}</b>\n\n"
        "Введите новый пароль для защиты вашего дневника. Пароль должен содержать не менее 6 символов.\n\n"
        "<i>Отправьте пароль в следующем сообщении.</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "meditations")
async def meditations_menu(callback: CallbackQuery):
    """Меню медитаций"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    meditations_list = await get_meditations()
    if not meditations_list:
        await callback.message.edit_text(
            "🧘‍♀️ <b>Медитации</b>\n\n"
            "В данный момент нет доступных медитаций. Пожалуйста, проверьте позже.",
            reply_markup=get_psychology_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        text = "🧘‍♀️ <b>Доступные медитации:</b>\n\n"
        for meditation in meditations_list:
            text += f"• {meditation['title']} ({meditation['duration']} мин.) - {meditation['hearts_reward']}💖\n"
        
        text += "\nВыберите медитацию для подробного просмотра:"
        
        buttons = []
        for meditation in meditations_list:
            buttons.append([InlineKeyboardButton(
                text=f"{meditation['title']} ({meditation['duration']} мин.)",
                callback_data=f"view_meditation_{meditation['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("view_meditation_"))
async def view_meditation(callback: CallbackQuery):
    """Просмотр медитации"""
    meditation_id = int(callback.data.replace("view_meditation_", ""))
    meditation = None
    meditations_list = await get_meditations()
    
    for m in meditations_list:
        if m['id'] == meditation_id:
            meditation = m
            break
    
    if not meditation:
        await callback.answer("Медитация не найдена")
        return
    
    await callback.message.edit_text(
        f"🧘‍♀️ <b>{meditation['title']}</b>\n\n"
        f"⏱ Длительность: {meditation['duration']} минут\n"
        f"💖 Награда: {meditation['hearts_reward']} сердечек\n\n"
        f"{meditation['description']}\n\n"
        "Выберите действие:",
        reply_markup=get_meditation_keyboard(meditation_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("start_meditation_"))
async def start_meditation(callback: CallbackQuery):
    """Начало медитации"""
    meditation_id = int(callback.data.replace("start_meditation_", ""))
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    meditation = None
    meditations_list = await get_meditations()
    
    for m in meditations_list:
        if m['id'] == meditation_id:
            meditation = m
            break
    
    if not meditation:
        await callback.answer("Медитация не найдена")
        return
    
    if user.get('hearts', 0) < meditation['hearts_reward']:
        await callback.answer(f"Недостаточно сердечек. Нужно: {meditation['hearts_reward']}")
        return
    
    # Начинаем медитацию
    await callback.message.edit_text(
        f"🧘‍♀️ <b>Начало медитации: {meditation['title']}</b>\n\n"
        f"⏱ Длительность: {meditation['duration']} минут\n"
        "Сядьте удобно, закройте глаза и сосредоточьтесь на своем дыхании...\n\n"
        "Я буду вести вас через этот процесс. Нажмите кнопку ниже, когда будете готовы завершить.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Завершить медитацию", callback_data=f"complete_meditation_{meditation_id}")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("complete_meditation_"))
async def complete_meditation(callback: CallbackQuery):
    """Завершение медитации"""
    meditation_id = int(callback.data.replace("complete_meditation_", ""))
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    meditation = None
    meditations_list = await get_meditations()
    
    for m in meditations_list:
        if m['id'] == meditation_id:
            meditation = m
            break
    
    if not meditation:
        await callback.answer("Медитация не найдена")
        return
    
    # Начисляем награду
    new_hearts = user.get('hearts', 0) + meditation['hearts_reward']
    await update_user(
        user['telegram_id'],
        hearts=new_hearts
    )
    
    await callback.message.edit_text(
        f"🎉 <b>Медитация завершена!</b>\n\n"
        f"Вы успешно выполнили: {meditation['title']}\n\n"
        f"💖 Получено: +{meditation['hearts_reward']} сердечек\n"
        f"💰 Ваш баланс: {new_hearts} сердечек",
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "weekly_plan")
async def weekly_plan(callback: CallbackQuery):
    """План на неделю"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    plan = await get_weekly_plan(user['telegram_id'])
    
    if plan:
        await callback.message.edit_text(
            "📅 <b>Ваш план на неделю</b>\n\n"
            f"Цели:\n{plan['goals']}\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Изменить план", callback_data="edit_weekly_plan")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
            ]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📅 <b>План на неделю</b>\n\n"
            "У вас еще нет плана на текущую неделю. Хотите создать его сейчас?\n\n"
            "Напишите свои цели на неделю в следующем сообщении.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
            ]),
            parse_mode="HTML"
        )
    await callback.answer()

@router.errors()
async def errors_handler(event: ErrorEvent):  # Для aiogram 3.x
    logger.error(f"Ошибка: {event.exception}")
    return True

@router.callback_query(F.data == "edit_weekly_plan")
async def edit_weekly_plan(callback: CallbackQuery):
    """Редактирование плана на неделю"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"✏️ <b>Редактирование плана на неделю, {name}</b>\n\n"
        "Напишите свои цели на неделю. Вы можете разделить их по дням или указать общие задачи.\n\n"
        "<i>Пример:</i>\n"
        "1. Каждый день медитировать 10 минут\n"
        "2. Пройти 3 челленджа\n"
        "3. Написать 5 записей в дневнике",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "habits")
async def habits(callback: CallbackQuery):
    """Цели и привычки"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"🎯 <b>Цели и привычки, {name}</b>\n\n"
        "Здесь вы можете работать над своими привычками и целями.\n\n"
        "1. <b>Трекер привычек</b> - отмечайте выполнение ежедневных привычек\n"
        "2. <b>Долгосрочные цели</b> - ставьте цели на месяц и более\n"
        "3. <b>Прогресс</b> - отслеживайте свои успехи\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Новая привычка", callback_data="new_habit")],
            [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="habits_progress")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "referral_system")
async def referral_system(callback: CallbackQuery):
    """Реферальная система с ограничением 5 приглашений в месяц"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    referrals_list = await get_user_referrals(callback.from_user.id)
    name = user.get('name', 'друг')
    
    # Получаем текущий месяц и год
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Фильтруем рефералов за текущий месяц
    monthly_referrals = [
        r for r in referrals_list 
        if r['created_at'].month == current_month and r['created_at'].year == current_year
    ]
    
    await callback.message.edit_text(
        f"💞 <b>Реферальная система, {name}</b>\n\n"
        f"👥 Всего приглашено друзей: {len(referrals_list)}\n"
        f"📅 Приглашено в этом месяце: {len(monthly_referrals)}/{MAX_REFERRALS_PER_MONTH}\n"
        f"💖 Доступно сердечек: {user.get('hearts', 0)}\n\n"
        f"🔗 Ваша реферальная ссылка:\n"
        f"https://t.me/{(await bot.get_me()).username}?start={user['telegram_id']}\n\n"
        f"За каждого приглашенного друга вы получаете {REFERRAL_REWARD} сердечек!\n"
        f"⚠️ Максимум {MAX_REFERRALS_PER_MONTH} приглашений в месяц.",
        reply_markup=get_referral_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ... (код между функциями остается без изменений до функции psychology_menu)

@router.callback_query(F.data == "psychology_menu")
async def psychology_menu(callback: CallbackQuery):
    """Меню психологического раздела с подробным описанием"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    await callback.message.edit_text(
        f"🧠 <b>Психологический раздел, {name}</b>\n\n"
        "Здесь вы можете получить профессиональную поддержку и улучшить свое ментальное здоровье.\n\n"
        "<b>Доступные функции:</b>\n"
        "💬 <b>Чат с ИИ-психологом</b> - обсудите свои мысли и чувства с искусственным интеллектом\n"
        "📔 <b>Личный дневник</b> - записывайте свои мысли и анализируйте их (получайте 5💖 за запись)\n"
        "🧘‍♀️ <b>Медитации</b> - практики для расслабления и осознанности (до 3 в день, 20💖 за выполнение)\n"
        "🎯 <b>Цели и привычки</b> - работайте над своими привычками с напоминаниями\n\n"
        "💖 За каждое действие вы получаете сердечки, которые можно потратить в магазине!",
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# ... (код между функциями остается без изменений до функции habits)

@router.callback_query(F.data == "habits")
async def habits(callback: CallbackQuery):
    """Раздел привычек с возможностью создания напоминаний"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    user_habits = await get_user_habits(callback.from_user.id)
    
    habits_text = ""
    if user_habits:
        habits_text = "\n\n<b>Ваши текущие привычки:</b>\n"
        for habit in user_habits[:5]:  # Показываем первые 5 привычек
            status = "✅" if habit.get('completed') else "⏳"
            reminder = f"⏰ {habit['reminder_time']} ({habit['reminder_frequency']})" if habit.get('reminder_enabled') else ""
            habits_text += f"{status} {habit['title']} {reminder}\n"
    
    await callback.message.edit_text(
        f"🎯 <b>Цели и привычки, {name}</b>\n\n"
        "Здесь вы можете работать над своими привычками и целями.\n"
        "Вы можете создать новую привычку и настроить напоминания."
        f"{habits_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Новая привычка", callback_data="new_habit")],
            [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="habits_progress")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "new_habit")
async def new_habit(callback: CallbackQuery):
    """Создание новой привычки с настройкой напоминаний"""
    await callback.message.edit_text(
        "✏️ <b>Создание новой привычки</b>\n\n"
        "Введите название привычки, которую хотите выработать.\n"
        "Пример: <i>Утренняя зарядка</i>",
        parse_mode="HTML"
    )
    await callback.answer()

<<<<<<< HEAD
class PromotionCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_promo_code = State()
    waiting_for_discount = State()
    waiting_for_hearts = State()
    waiting_for_end_date = State()
    waiting_for_reward_type = State()
    waiting_for_tasks = State()

=======
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
class HabitCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_time = State()

@router.callback_query(F.data == "create_habit")
async def start_habit_creation(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HabitCreation.waiting_for_title)
    await callback.message.edit_text("🧠 Введите название привычки")
    await callback.answer()

@router.message(HabitCreation.waiting_for_title)
async def habit_title_handler(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(HabitCreation.waiting_for_description)
    await message.answer("📝 Теперь введите описание привычки.\nПример: Выполнять 10 отжиманий и 20 приседаний каждое утро")

@router.message(HabitCreation.waiting_for_description)
async def habit_description_handler(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(HabitCreation.waiting_for_time)
    await message.answer("⏰ Укажите время напоминания (в формате ЧЧ:ММ, например 08:30)")

@router.message(HabitCreation.waiting_for_time)
async def habit_time_handler(message: Message, state: FSMContext):
    data = await state.update_data(time=message.text.strip())
    habit = await state.get_data()

    # Здесь сохранить в БД через save_habit(user_id, habit)
    await message.answer(f"✅ Привычка создана:\n{habit['title']} — {habit['description']} в {habit['time']}")
    await state.clear()

@router.message(F.text & ~F.text.startswith('/'))
async def handle_habit_description(message: Message):
    """Обработка описания привычки и предложение настроить напоминания"""
    user = await get_user(message.from_user.id)
    if not user or not user.get('temp_habit_title'):
        return
    
    habit_description = message.text.strip()
    if len(habit_description) < 5:
        await message.answer("⚠️ Описание привычки должно содержать минимум 5 символов. Попробуйте еще раз:")
        return
    
    # Сохраняем описание
    await update_user(
        message.from_user.id,
        temp_habit_description=habit_description
    )
    
    # Предлагаем настроить напоминания
    await message.answer(
        "⏰ Хотите настроить напоминания для этой привычки?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="set_habit_reminder")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="create_habit_no_reminder")]
        ])
    )

@router.callback_query(F.data == "set_habit_reminder")
async def set_habit_reminder(callback: CallbackQuery):
    """Настройка напоминаний для привычки"""
    await callback.message.edit_text(
        "🔄 Выберите частоту напоминаний:",
        reply_markup=get_habit_frequency_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("habit_frequency_"))
async def set_habit_frequency(callback: CallbackQuery):
    """Обработка выбора частоты напоминаний"""
    frequency = callback.data.replace("habit_frequency_", "")
    user = await get_user(callback.from_user.id)
    if not user or not user.get('temp_habit_title'):
        await callback.answer("Ошибка: данные привычки не найдены")
        return
    
    if frequency == "none":
        # Создаем привычку без напоминаний
        await create_habit(
            user_id=callback.from_user.id,
            title=user['temp_habit_title'],
            description=user.get('temp_habit_description', ''),
            reminder_enabled=False
        )
        
        await callback.message.edit_text(
            "🎉 Привычка создана без напоминаний!",
            reply_markup=get_back_to_habits_keyboard()
        )
    else:
        # Сохраняем частоту и запрашиваем время
        await update_user(
            callback.from_user.id,
            temp_habit_frequency=frequency
        )
        
        await callback.message.edit_text(
            "⏰ Введите время напоминания в формате ЧЧ:ММ (например, 09:00):"
        )
    
    await callback.answer()

@router.message(F.text.regexp(r'^\d{2}:\d{2}$'))
async def handle_habit_reminder_time(message: Message):
    """Обработка времени напоминания и создание привычки"""
    user = await get_user(message.from_user.id)
    if not user or not user.get('temp_habit_title'):
        return
    
    try:
        # Проверяем корректность времени
        hours, minutes = map(int, message.text.split(':'))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError
        
        # Создаем привычку с напоминанием
        habit = await create_habit(
            user_id=message.from_user.id,
            title=user['temp_habit_title'],
            description=user.get('temp_habit_description', ''),
            reminder_enabled=True,
            reminder_time=message.text,
            reminder_frequency=user.get('temp_habit_frequency', 'daily')
        )
        
        if habit:
            await message.answer(
                f"🎉 Привычка создана с напоминанием в {message.text} ({user.get('temp_habit_frequency', 'daily')})!",
                reply_markup=get_back_to_habits_keyboard()
            )
            
            # Очищаем временные данные
            await update_user(
                message.from_user.id,
                temp_habit_title=None,
                temp_habit_description=None,
                temp_habit_frequency=None
            )
        else:
            await message.answer("⚠️ Ошибка при создании привычки. Попробуйте позже.")
    
    except ValueError:
        await message.answer("⚠️ Неверный формат времени. Введите время в формате ЧЧ:ММ (например, 09:00):")

@router.callback_query(F.data == "habits_progress")
async def habits_progress(callback: CallbackQuery):
    """Прогресс выполнения привычек"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    habits = await get_user_habits(callback.from_user.id)
    if not habits:
        await callback.message.edit_text(
            "📊 У вас пока нет привычек для отслеживания.\n"
            "Создайте первую привычку, нажав на кнопку ниже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Новая привычка", callback_data="new_habit")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="habits")]
            ])
        )
        await callback.answer()
        return
    
    # Группируем привычки по статусу
    completed = [h for h in habits if h.get('completed')]
    in_progress = [h for h in habits if not h.get('completed')]
    
    text = "📊 <b>Ваш прогресс по привычкам:</b>\n\n"
    text += f"✅ <b>Выполнено:</b> {len(completed)}/{len(habits)}\n"
    
    if completed:
        text += "\n<b>Последние выполненные:</b>\n"
        for habit in completed[:3]:
            date = habit['completed_at'].strftime("%d.%m") if habit.get('completed_at') else "??.??"
            text += f"- {habit['title']} ({date})\n"
    
    if in_progress:
        text += "\n<b>В процессе:</b>\n"
        for habit in in_progress[:5]:
            reminder = f"⏰ {habit['reminder_time']} ({habit['reminder_frequency']})" if habit.get('reminder_enabled') else ""
            text += f"- {habit['title']} {reminder}\n"
    
    text += "\nПродолжайте в том же духе! 💪"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="habits")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

# ... (код между функциями остается без изменений до функции meditations_menu)

@router.callback_query(F.data == "meditations")
async def meditations_menu(callback: CallbackQuery):
    """Меню медитаций с предупреждением о лимите"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    # Проверяем, сколько медитаций пользователь уже выполнил сегодня
    today = datetime.now().date()
    completed_today = 0
    
    # Здесь должна быть логика подсчета выполненных сегодня медитаций
    # Временно используем заглушку
    if user.get('last_meditation_date'):
        last_date = user['last_meditation_date'].date()
        if last_date == today:
            completed_today = user.get('meditations_today', 0)
    
    meditations_list = MEDITATIONS
    
    text = (
        f"🧘‍♀️ <b>Медитации</b>\n\n"
        f"Выполнено сегодня: {completed_today}/3\n"
        "Каждая медитация длится 10 минут и приносит 20💖 за полное выполнение.\n\n"
        "<b>Доступные медитации:</b>\n"
    )
    
    buttons = []
    for meditation in meditations_list:
        buttons.append([
            InlineKeyboardButton(
                text=f"{meditation['title']} ({meditation['duration']} мин)",
                callback_data=f"view_meditation_{meditation['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()

# ... (код между функциями остается без изменений до функции set_diary_password)

@router.callback_query(F.data == "set_diary_password")
async def set_diary_password_handler(callback: CallbackQuery):
    """Установка пароля на дневник (исправленная версия)"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    await callback.message.edit_text(
        "🔐 <b>Установка пароля на дневник</b>\n\n"
        "Введите новый пароль (минимум 6 символов):",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_premium")
async def admin_activate_premium(callback: CallbackQuery):
    await callback.message.edit_text("Введите @username пользователя для активации премиума:")
    await callback.answer()

<<<<<<< HEAD
    @router.message(F.from_user.id == callback.from_user.id)
    async def activate_premium(message: Message):
        username = message.text.strip()
        user = await get_user_by_username(username)  # Получаем пользователя по username
        if user:
            # Активация премиума
            user.is_premium = True
            await save_user(user)  # Сохраняем изменения в базе
            # Уведомление пользователя
            await bot.send_message(user.telegram_id, "Вам был активирован премиум статус!")
            await callback.message.edit_text(f"Премиум статус был активирован для {username}.")
        else:
            await callback.message.edit_text("Пользователь с таким username не найден.")


=======
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
@router.callback_query(F.data == "admin_hearts")
async def admin_add_hearts(callback: CallbackQuery):
    await callback.message.edit_text("Введите @username и количество сердечек (пример: @user 100):")
    await callback.answer()

<<<<<<< HEAD
    @router.message(F.from_user.id == callback.from_user.id)
    async def add_hearts(message: Message):
        parts = message.text.strip().split()
        if len(parts) != 2:
            await callback.message.edit_text("Неверный формат. Пример: @user 100")
            return

        username, hearts = parts
        try:
            hearts = int(hearts)
        except ValueError:
            await callback.message.edit_text("Введите корректное количество сердечек (целое число).")
            return

        user = await get_user_by_username(username)
        if user:
            user.hearts += hearts
            await save_user(user)
            # Уведомление пользователя
            await bot.send_message(user.telegram_id, f"Вам было добавлено {hearts} сердечек!")
            await callback.message.edit_text(f"{hearts} сердечек были добавлены пользователю {username}.")
        else:
            await callback.message.edit_text("Пользователь с таким username не найден.")


@router.callback_query(F.data == "admin_stats")
async def show_admin_stats(callback: CallbackQuery):
    """Показывает подробную статистику для админа"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        await callback.answer("Доступ запрещен")
        return

    async with async_session() as session:
        # Количество пользователей
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        total_users = result.scalar()

        # Количество активных пользователей
        result = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE is_banned = FALSE AND (is_premium = TRUE OR trial_started_at IS NOT NULL)")
        )
        active_users = result.scalar()

        # Количество завершённых челленджей
        result = await session.execute(text("SELECT COUNT(*) FROM users WHERE completed_challenges > 0"))
        challenges_completed = result.scalar()

        # Количество использованных сердечек
        result = await session.execute(text("SELECT SUM(hearts) FROM users"))
        total_hearts = result.scalar() or 0

        # Количество записей в дневнике
        result = await session.execute(text("SELECT COUNT(*) FROM diary_entries"))
        total_diary_entries = result.scalar()

        # Количество выполненных привычек
        result = await session.execute(text("SELECT COUNT(*) FROM habit_completions"))
        total_habits_completed = result.scalar()

        # Формируем сообщение статистики
        stats_message = (
            f"📊 <b>Подробная статистика</b>\n\n"
            f"👥 <b>Общее количество пользователей:</b> {total_users}\n"
            f"💬 <b>Активных пользователей:</b> {active_users}\n"
            f"🏆 <b>Завершённых челленджей:</b> {challenges_completed}\n"
            f"💖 <b>Общее количество сердечек использовано:</b> {total_hearts}\n"
            f"📔 <b>Записей в дневнике:</b> {total_diary_entries}\n"
            f"✅ <b>Привычек выполнено:</b> {total_habits_completed}\n"
        )

        # Отправляем статистику администратору
        await callback.message.edit_text(stats_message, parse_mode="HTML")
        await callback.answer()

=======
@router.callback_query(F.data == "admin_stats")
async def admin_statistics(callback: CallbackQuery):
    await callback.message.edit_text("📊 Админ-статистика (заглушка — здесь можно вывести аналитику)")
    await callback.answer()
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6

@router.callback_query(F.data == "admin_user_messages")
async def admin_user_history(callback: CallbackQuery):
    await callback.message.edit_text("Введите @username и количество дней (пример: @user 7):")
    await callback.answer()

<<<<<<< HEAD
    @router.message(F.from_user.id == callback.from_user.id)
    async def get_user_history(message: Message):
        parts = message.text.strip().split()
        if len(parts) != 2:
            await callback.message.edit_text("Неверный формат. Пример: @user 7")
            return

        username, days = parts
        try:
            days = int(days)
        except ValueError:
            await callback.message.edit_text("Введите корректное количество дней (целое число).")
            return

        user = await get_user_by_username(username)  # Получаем пользователя по username
        if user:
            # Получаем историю сообщений за последние N дней
            history = await get_user_message_history(user.telegram_id, days)  # Функция для получения истории сообщений

            if history:
                history_text = "\n".join([f"Сообщение от {entry.timestamp}: {entry.text}" for entry in history])
                await callback.message.edit_text(f"История сообщений за последние {days} дней:\n{history_text}")
            else:
                await callback.message.edit_text(f"Нет сообщений за последние {days} дней.")
        else:
            await callback.message.edit_text("Пользователь с таким username не найден.")

=======
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
@router.callback_query(F.data == "admin_reset_activity")
async def admin_reset_data(callback: CallbackQuery):
    await callback.message.edit_text("Введите @username для сброса активности:")
    await callback.answer()

<<<<<<< HEAD
    @router.message(F.from_user.id == callback.from_user.id)
    async def reset_activity(message: Message):
        username = message.text.strip()  # Получаем username пользователя
        user = await get_user_by_username(username)  # Получаем пользователя по его username

        if user:
            # Сбрасываем активность пользователя
            user.completed_challenges = 0  # Пример: сброс количества завершённых челленджей
            user.diary_entries = 0  # Пример: сброс количества записей в дневнике
            user.completed_habits = 0  # Пример: сброс выполнения привычек
            await save_user(user)  # Сохраняем изменения в базе данных

            # Уведомление пользователю о сбросе активности
            await bot.send_message(user.telegram_id, "Ваша активность была сброшена администратором.")

            # Подтверждение администратору
            await callback.message.edit_text(f"Активность пользователя {username} была сброшена.")
        else:
            await callback.message.edit_text("Пользователь с таким username не найден.")

=======
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
@router.callback_query(F.data == "admin_ban")
async def admin_ban_user(callback: CallbackQuery):
    await callback.message.edit_text("Введите @username пользователя, которого нужно заблокировать:")
    await callback.answer()

<<<<<<< HEAD
    @router.message(F.from_user.id == callback.from_user.id)
    async def ban_user(message: Message):
        username = message.text.strip()
        user = await get_user_by_username(username)
        if user:
            user.is_banned = True
            await save_user(user)
            # Уведомление пользователю
            await bot.send_message(user.telegram_id, "Ваш аккаунт был заблокирован.")
            await callback.message.edit_text(f"Пользователь {username} был заблокирован.")
        else:
            await callback.message.edit_text("Пользователь с таким username не найден.")

@router.callback_query(F.data == "admin_promotions")
async def admin_promotions_menu(callback: CallbackQuery):
    """Меню управления акциями"""
=======
@router.callback_query(F.data == "admin_promotions")
async def admin_promotions(callback: CallbackQuery):
    """Управление акциями"""
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        await callback.answer("Доступ запрещен")
        return
<<<<<<< HEAD

    await callback.message.edit_text(
        "🎁 <b>Управление акциями</b>\n\n"
        "Здесь вы можете создавать и управлять акциями для пользователей.\n\n"
        "Акции могут предоставлять:\n"
        "💖 Бонусные сердечки за выполнение заданий\n"
        "💳 Скидки на подписки по промокоду\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать акцию", callback_data="create_promotion")],
            [InlineKeyboardButton(text="📋 Список акций", callback_data="list_promotions")],
            [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_menu")]
        ]),
        parse_mode="HTML"
=======
    
    await callback.message.edit_text(
        "🎁 Управление акциями\n\n"
        "1. Создать новую акцию\n"
        "2. Просмотреть активные\n"
        "3. Удалить акцию",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать акцию", callback_data="create_promotion")],
            [InlineKeyboardButton(text="📋 Список акций", callback_data="list_promotions")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
        ])
>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
    )
    await callback.answer()

@router.callback_query(F.data == "create_promotion")
<<<<<<< HEAD
async def create_promotion_handler(callback: CallbackQuery, state: FSMContext):
    """Начало создания новой акции"""
    try:
        user = await get_user(callback.from_user.id)
        if not user or not user.get('is_admin'):
            await callback.answer("Доступ запрещен")
            return

        await state.set_state(PromotionCreation.waiting_for_title)
        await callback.message.edit_text(
            "🎁 <b>Создание новой акции</b>\n\n"
            "Введите название акции (минимум 3 символа):",
            parse_mode="HTML"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при начале создания акции: {e}")
        await callback.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

        # Обрабатываем введённое название
        @router.message(F.from_user.id == callback.from_user.id)
        async def promotion_name_input(message: Message):
            promotion_name = message.text.strip()

            if len(promotion_name) < 3:
                await message.answer("Название должно быть хотя бы из 3 символов. Попробуйте снова.")
                return

            # Запоминаем название и переходим к следующему шагу
            promotion_data = {"name": promotion_name}
            await ask_for_description()
            return promotion_data

        # Обрабатываем введённое описание
        @router.message(F.from_user.id == callback.from_user.id)
        async def promotion_description_input(message: Message, promotion_data):
            promotion_description = message.text.strip()

            if len(promotion_description) < 5:
                await message.answer("Описание должно быть хотя бы из 5 символов. Попробуйте снова.")
                return

            promotion_data['description'] = promotion_description
            await ask_for_start_date()
            return promotion_data

        # Обрабатываем дату начала
        @router.message(F.from_user.id == callback.from_user.id)
        async def promotion_start_date_input(message: Message, promotion_data):
            try:
                start_date = datetime.strptime(message.text, "%Y-%m-%d")
            except ValueError:
                await message.answer("Неверный формат даты. Попробуйте снова.")
                return

            promotion_data['start_date'] = start_date
            await ask_for_end_date()
            return promotion_data

        # Обрабатываем дату окончания
        @router.message(F.from_user.id == callback.from_user.id)
        async def promotion_end_date_input(message: Message, promotion_data):
            try:
                end_date = datetime.strptime(message.text, "%Y-%m-%d")
            except ValueError:
                await message.answer("Неверный формат даты. Попробуйте снова.")
                return

            promotion_data['end_date'] = end_date
            # Добавляем новую акцию в базу данных
            await create_promotion_in_db(promotion_data)

        async def create_promotion_in_db(promotion_data):
            """Создает акцию в базе данных"""
            async with async_session() as session:
                try:
                    await session.execute(
                        promotions.insert().values(
                            title=promotion_data['name'],
                            description=promotion_data['description'],
                            promo_code=f"PROMO{random.randint(1000, 9999)}",
                            discount_percent=0,  # По умолчанию без скидки
                            hearts_reward=100,  # Сначала назначаем 100 сердечек
                            start_date=promotion_data['start_date'],
                            end_date=promotion_data['end_date'],
                            created_at=datetime.utcnow()
                        )
                    )
                    await session.commit()
                    await callback.message.answer(f"Акция '{promotion_data['name']}' успешно создана!")
                except Exception as db_error:
                    logger.error(f"Ошибка при вставке в базу данных: {db_error}")
                    await session.rollback()
                    await callback.message.answer("Произошла ошибка при создании акции. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка при создании акции: {e}")
        await callback.answer("Произошла ошибка при создании акции. Пожалуйста, попробуйте позже.")


@router.message(PromotionCreation.waiting_for_title)
async def process_promotion_title(message: Message, state: FSMContext):
    """Обработка названия акции"""
    if len(message.text.strip()) < 3:
        await message.answer("⚠️ Название должно содержать минимум 3 символа. Попробуйте еще раз:")
        return

    await state.update_data(title=message.text.strip())
    await state.set_state(PromotionCreation.waiting_for_description)
    await message.answer(
        "📝 Теперь введите описание акции (минимум 5 символов):\n"
        "(Что получат пользователи, условия и т.д.)"
    )


@router.message(PromotionCreation.waiting_for_description)
async def process_promotion_description(message: Message, state: FSMContext):
    """Обработка описания акции"""
    if len(message.text.strip()) < 5:
        await message.answer("⚠️ Описание должно содержать минимум 5 символа. Попробуйте еще раз:")
        return

    await state.update_data(description=message.text.strip())
    await state.set_state(PromotionCreation.waiting_for_reward_type)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💖 Награда сердечками", callback_data="reward_hearts")],
        [InlineKeyboardButton(text="💳 Скидка на подписку", callback_data="reward_discount")]
    ])

    await message.answer(
        "🎁 Выберите тип награды:",
        reply_markup=keyboard
    )


@router.message(PromotionCreation.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    """Обработка промокода"""
    if not message.text.strip().isalnum():
        await message.answer("⚠️ Промокод должен содержать только буквы и цифры. Попробуйте еще раз:")
        return

    await state.update_data(promo_code=message.text.strip().upper())
    await state.set_state(PromotionCreation.waiting_for_reward_type)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💖 Награда сердечками", callback_data="reward_hearts")],
        [InlineKeyboardButton(text="💳 Скидка на подписку", callback_data="reward_discount")]
    ])

    await message.answer(
        "🎁 Выберите тип награды:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("reward_"), PromotionCreation.waiting_for_reward_type)
async def process_reward_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа награды"""
    reward_type = "hearts" if callback.data == "reward_hearts" else "discount"
    await state.update_data(reward_type=reward_type)

    if reward_type == "hearts":
        await state.set_state(PromotionCreation.waiting_for_hearts)
        await callback.message.edit_text(
            "💖 Введите количество сердечек для награды (например, 50):"
        )
    else:
        await state.set_state(PromotionCreation.waiting_for_discount)
        await callback.message.edit_text(
            "💳 Введите размер скидки в процентах (например, 15):"
        )
    await callback.answer()

@router.message(PromotionCreation.waiting_for_hearts)
async def process_hearts_reward(message: Message, state: FSMContext):
    """Обработка награды в сердечках"""
    try:
        hearts = int(message.text.strip())
        if hearts <= 0:
            raise ValueError
        await state.update_data(hearts_reward=hearts, discount_percent=0)
        await state.set_state(PromotionCreation.waiting_for_end_date)
        await message.answer(
            "📅 Введите дату окончания акции в формате ДД.ММ.ГГГГ:\n"
            "Пример: 31.12.2023"
        )
    except ValueError:
        await message.answer("⚠️ Введите корректное число сердечек (больше 0):")

@router.message(PromotionCreation.waiting_for_discount)
async def process_discount(message: Message, state: FSMContext):
    """Обработка скидки"""
    try:
        discount = int(message.text.strip())
        if not 1 <= discount <= 100:
            raise ValueError
        await state.update_data(discount_percent=discount, hearts_reward=0)
        await state.set_state(PromotionCreation.waiting_for_end_date)
        await message.answer(
            "📅 Введите дату окончания акции в формате ДД.ММ.ГГГГ:\n"
            "Пример: 31.12.2023"
        )
    except ValueError:
        await message.answer("⚠️ Введите корректный процент скидки (от 1 до 100):")

@router.message(PromotionCreation.waiting_for_end_date)
async def process_end_date(message: Message, state: FSMContext):
    """Обработка даты окончания"""
    try:
        day, month, year = map(int, message.text.strip().split('.'))
        end_date = datetime(year, month, day)
        if end_date <= datetime.now():
            raise ValueError

        await state.update_data(end_date=end_date)
        await state.set_state(PromotionCreation.waiting_for_tasks)
        await message.answer(
            "📝 Введите задания для акции (через запятую):\n"
            "Пример: Подписаться на канал, Пригласить друга, Выполнить челлендж\n"
            "Или отправьте 'нет', если задания не требуются"
        )
    except Exception:
        await message.answer("⚠️ Неверный формат даты или дата уже прошла. Введите в формате ДД.ММ.ГГГГ:")


@router.message(PromotionCreation.waiting_for_tasks)
async def process_tasks(message: Message, state: FSMContext):
    """Обработка заданий и завершение создания акции"""
    tasks = None if message.text.strip().lower() == 'нет' else message.text.strip()
    data = await state.get_data()

    try:
        promo_code = f"PROMO{random.randint(1000, 9999)}"

        await create_promotion(
            title=data['title'],
            description=data['description'],
            promo_code=promo_code,
            discount_percent=data.get('discount_percent', 0),
            hearts_reward=data.get('hearts_reward', 0),
            start_date=datetime.now(),
            end_date=data['end_date'],
            tasks=tasks,
            reward_type=data['reward_type']
        )

        reward_text = ""
        if data['reward_type'] == "hearts":
            reward_text = f"💖 Награда: {data['hearts_reward']} сердечек"
        else:
            reward_text = f"💳 Скидка: {data['discount_percent']}%"

        await message.answer(
            f"🎉 <b>Акция создана!</b>\n\n"
            f"Название: {data['title']}\n"
            f"Промокод: <code>{promo_code}</code>\n"
            f"{reward_text}\n"
            f"Дата окончания: {data['end_date'].strftime('%d.%m.%Y')}\n\n"
            "Вы можете просмотреть все акции в списке.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Список акций", callback_data="list_promotions")],
                [InlineKeyboardButton(text="🎁 Создать еще", callback_data="create_promotion")]
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка при создании акции: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при создании акции. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_promotions")]
            ])
        )

    await state.clear()

=======
async def create_promotion_handler(callback: CallbackQuery):
    """Создание акции"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        await callback.answer("Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "Введите данные акции в формате:\n\n"
        "Название|Описание|Промокод|Скидка%|Награда в сердечках|Дата окончания (ДД.ММ.ГГГГ)\n\n"
        "Пример:\n"
        "Новогодняя акция|Специальное предложение|NEWYEAR2023|15|50|31.12.2023"
    )
    await callback.answer()

>>>>>>> 18fbeedce0645dd9c3f916acc311418f9ed1f0d6
@router.message(F.text & ~F.text.startswith('/'))
async def handle_diary_password(message: Message):
    """Обработка пароля для дневника (исправленная версия)"""
    user = await get_user(message.from_user.id)
    if not user:
        return
    
    password = message.text.strip()
    if len(password) < 6:
        await message.answer("⚠️ Пароль должен содержать минимум 6 символов. Попробуйте еще раз:")
        return
    
    try:
        async with async_session() as session:
            # Обновляем пароль для всех записей пользователя
            await session.execute(
                diary_entries.update()
                .where(diary_entries.c.user_id == message.from_user.id)
                .values(password=password)
            )
            await session.commit()
        
        await message.answer(
            "🔐 Пароль успешно установлен! Теперь ваш дневник защищен.",
            reply_markup=get_diary_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при установке пароля: {e}")
        await message.answer("⚠️ Произошла ошибка при установке пароля. Попробуйте позже.")

# ... (код между функциями остается без изменений до функции create_diary_entry)

async def create_diary_entry(user_id: int, entry_text: str, mood: str = None):
    """Создание записи в дневнике (исправленная версия)"""
    try:
        async with async_session() as session:
            await session.execute(
                diary_entries.insert().values(
                    user_id=user_id,
                    entry_text=entry_text,
                    mood=mood,
                    created_at=datetime.utcnow()
                )
            )
            await session.commit()
            
            # Награждаем пользователя за запись в дневнике
            user = await get_user(user_id)
            if user:
                new_hearts = user.get('hearts', 0) + 5  # 5 сердечек за запись
                await update_user(user_id, hearts=new_hearts)
                return True
    except Exception as e:
        logger.error(f"Ошибка при создании записи в дневнике: {e}")
    
    return False

# ... (код между функциями остается без изменений до функции get_diary_entries)

async def get_diary_entries(user_id: int, period: str = "all") -> List[Dict[str, Any]]:
    """Получение записей дневника за указанный период (исправленная версия)"""
    try:
        async with async_session() as session:
            query = diary_entries.select().where(diary_entries.c.user_id == user_id)
            
            now = datetime.utcnow()
            if period == "today":
                today = now.date()
                query = query.where(diary_entries.c.created_at >= today)
            elif period == "week":
                week_ago = now - timedelta(days=7)
                query = query.where(diary_entries.c.created_at >= week_ago)
            elif period == "month":
                month_ago = now - timedelta(days=30)
                query = query.where(diary_entries.c.created_at >= month_ago)
            
            query = query.order_by(diary_entries.c.created_at.desc())
            
            result = await session.execute(query)
            return [dict(row) for row in result.mappings()]
    except Exception as e:
        logger.error(f"Ошибка при получении записей дневника: {e}")
        return []

# ... (остальной код остается без изменений)

# --- ДОБАВЛЕНО: weekly_plans таблица ---

weekly_plans = Table(
    "weekly_plans",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", BigInteger),
    Column("goals", String(1000)),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("week_start", DateTime)
)


# --- ДОБАВЛЕНО: weekly_plan функции ---

async def get_weekly_plan(user_id: int) -> Optional[Dict[str, Any]]:
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM weekly_plans WHERE user_id = :user_id ORDER BY week_start DESC LIMIT 1"),
            {"user_id": user_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None

async def create_weekly_plan(user_id: int, goals: str):
    async with async_session() as session:
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        await session.execute(
            weekly_plans.insert().values(
                user_id=user_id,
                goals=goals,
                week_start=week_start
            )
        )
        await session.commit()


# --- ДОБАВЛЕНО: Клавиатуры ---
def get_challenge_keyboard(challenge_id: str):
    """Клавиатура для челленджа"""
    buttons = [
        [InlineKeyboardButton(text="✅ Начать челлендж", callback_data=f"start_{challenge_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_challenge_timer_keyboard():
    """Клавиатура с таймером челленджа"""
    buttons = [
        [InlineKeyboardButton(text="⏳ Завершить", callback_data="complete_challenge")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_shop_keyboard():
    """Клавиатура магазина"""
    buttons = []
    for item in SHOP_ITEMS:
        buttons.append([InlineKeyboardButton(text=item["title"], callback_data=f"shop_{item['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_subscription_keyboard():
    """Клавиатура выбора подписки"""
    buttons = [
        [InlineKeyboardButton(text="1 месяц - 299₽", callback_data="sub_1_month")],
        [InlineKeyboardButton(text="3 месяца - 749₽", callback_data="sub_3_months")],
        [InlineKeyboardButton(text="6 месяцев - 1299₽", callback_data="sub_6_months")],
        [InlineKeyboardButton(text="1 год - 2199₽", callback_data="sub_1_year")],
        [InlineKeyboardButton(text="💖 Купить за сердечки", callback_data="buy_with_hearts")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_hearts_subscription_keyboard():
    """Клавиатура подписки за сердечки"""
    buttons = [
        [InlineKeyboardButton(text="1 день - 50💖", callback_data="hearts_sub_1_day")],
        [InlineKeyboardButton(text="7 дней - 300💖", callback_data="hearts_sub_7_days")],
        [InlineKeyboardButton(text="1 месяц - 1000💖", callback_data="hearts_sub_1_month")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_method_keyboard():
    """Клавиатура выбора способа оплаты"""
    buttons = [
        [InlineKeyboardButton(text="💳 Криптовалюта (USDT)", callback_data="pay_crypto")],
        [InlineKeyboardButton(text="🟣 ЮMoney", callback_data="pay_yoomoney")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard():
    """Клавиатура админа"""
    buttons = [
        [InlineKeyboardButton(text="👤 Активировать премиум", callback_data="admin_premium")],
        [InlineKeyboardButton(text="💖 Начислить сердечки", callback_data="admin_hearts")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🎁 Акции", callback_data="admin_promotions")],
        [InlineKeyboardButton(text="📝 История сообщений", callback_data="admin_user_messages")],
        [InlineKeyboardButton(text="🔄 Сбросить активность", callback_data="admin_reset_activity")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_shop_keyboard():
    """Клавиатура возврата в магазин"""
    buttons = [
        [InlineKeyboardButton(text="🔙 В магазин", callback_data="back_to_shop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_psychology_menu_keyboard():
    """Клавиатура психологического раздела"""
    buttons = [
        [InlineKeyboardButton(text="💬 Чат с ИИ-психологом", callback_data="ai_psychologist")],
        [InlineKeyboardButton(text="📔 Личный дневник", callback_data="personal_diary")],
        [InlineKeyboardButton(text="🧘‍♀️ Медитации", callback_data="meditations")],
        [InlineKeyboardButton(text="📅 План на неделю", callback_data="weekly_plan")],
        [InlineKeyboardButton(text="🎯 Цели и привычки", callback_data="habits")],
        [InlineKeyboardButton(text="💞 Реферальная система", callback_data="referral_system")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_diary_keyboard():
    """Клавиатура дневника"""
    buttons = [
        [InlineKeyboardButton(text="✍️ Новая запись", callback_data="new_diary_entry")],
        [InlineKeyboardButton(text="📖 Мои записи", callback_data="my_diary_entries")],
        [InlineKeyboardButton(text="🔐 Установить пароль", callback_data="set_diary_password")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_meditation_keyboard(meditation_id: int):
    """Клавиатура медитации"""
    buttons = [
        [InlineKeyboardButton(text="🧘‍♀️ Начать медитацию (10💖)", callback_data=f"start_meditation_{meditation_id}")],
        [InlineKeyboardButton(text="📖 Прочитать описание", callback_data=f"read_meditation_{meditation_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="meditations")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_referral_keyboard():

    """Клавиатура реферальной системы"""
    buttons = [
        [InlineKeyboardButton(text="🔗 Получить реферальную ссылку", callback_data="get_referral_link")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def check_payments():
    """Фоновая задача для проверки платежей"""
    while True:
        try:
            async with async_session() as session:
                result = await session.execute(
                    text("SELECT * FROM payments WHERE status = 'pending'")
                )
                payments = result.mappings().all()
                
                for payment in payments:
                    if payment['payment_method'] == 'crypto':
                        verified = await check_crypto_payment(
                            payment['transaction_id'],
                            payment['amount'],
                            'USDT'
                        )
                        if verified:
                            await session.execute(
                                text("UPDATE payments SET status = 'completed' WHERE id = :id"),
                                {"id": payment['id']}
                            )
                            await session.commit()
        
        except Exception as e:
            logger.error(f"Ошибка в check_payments: {e}")
        
        await asyncio.sleep(300)  # Проверка каждые 5 минут

# --- Команды для пользователей ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    try:
        await setup_db()
        user = await get_user(message.from_user.id)
        
        if not user:
            is_admin = message.from_user.id in ADMIN_IDS
            user = await create_user(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                is_admin=is_admin,
                ip_address=message.from_user.id  # Число, а не строка
            )
            
            if is_admin:
                await message.answer(
                    "👑 Добро пожаловать, администратор!\n\n"
                    "Используйте /admin для управления ботом")
                return
            
            # Запрашиваем имя пользователя
            await message.answer(
                "🌿 Добро пожаловать в бота-психолога!\n\n"
                "Я помогу вам с:\n"
                "- Анализом настроения\n"
                "- Медитациями и релаксацией\n"
                "- Ведением дневника\n"
                "- Психологической поддержкой\n\n"
                "📌 Лимиты использования:\n"
                f"- Пробный период: {TRIAL_DAYS} дня\n"
                f"- Запросов в день: {TRIAL_DAILY_LIMIT}\n"
                f"- Сердечек в день: {HEARTS_PER_DAY}\n\n"
                "Как вас зовут? Напишите свое имя для персонализации:")
            return
        
        # Если пользователь уже есть, но имя не указано
        if not user.get('name'):
            await message.answer("Пожалуйста, введите ваше имя для продолжения:")
            return
            
        await show_main_menu(message.from_user.id, message)
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def show_main_menu(user_id: int, message: Message):
    """Показывает главное меню с учетом прав пользователя"""
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    name = user.get('name', 'друг')
    
    if user.get('is_admin'):
        # Меню для администратора
        await message.answer(
            f"👑 Админ-панель, {name}",
            reply_markup=get_admin_keyboard()
        )
    else:
        # Меню для обычного пользователя
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu")],
            [InlineKeyboardButton(text="💞 Реферальная система", callback_data="referral_system")],
            [InlineKeyboardButton(text="🏆 Челленджи", callback_data="get_challenge")],
            [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")]
        ])
        
        await message.answer(
            f"Привет, {name}!\n\nВыберите раздел:",
            reply_markup=keyboard
        )

async def check_reminders():
    """Проверка и отправка напоминаний"""
    while True:
        try:
            now = datetime.now()
            async with async_session() as session:
                result = await session.execute(
                    text("SELECT * FROM reminders WHERE next_reminder <= :now AND is_active = TRUE"),
                    {"now": now}
                )
                reminders = result.mappings().all()
                
                for reminder in reminders:
                    habit = await get_habit(reminder['user_id'], reminder['habit_id'])
                    if habit:
                        await bot.send_message(
                            reminder['user_id'],
                            f"⏰ Напоминание: {habit['title']}\n{habit['description']}"
                        )
                    
                    # Обновляем следующее напоминание
                    if reminder['frequency'] == "daily":
                        next_reminder = now + timedelta(days=1)
                    elif reminder['frequency'] == "weekly":
                        next_reminder = now + timedelta(weeks=1)
                    elif reminder['frequency'] == "monthly":
                        next_reminder = now + timedelta(days=30)
                    
                    await session.execute(
                        text("UPDATE reminders SET next_reminder = :next WHERE id = :id"),
                        {"next": next_reminder, "id": reminder['id']}
                    )
                    await session.commit()
        
        except Exception as e:
            logger.error(f"Ошибка в check_reminders: {e}")
        
        await asyncio.sleep(60)  # Проверка каждую минуту

if __name__ == "__main__":
    async def main():
        await setup_db()
        logger.info("🚀 Бот запущен!")
        await dp.start_polling(bot)

    asyncio.run(main())