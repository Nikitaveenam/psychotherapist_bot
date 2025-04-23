import os
import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Boolean, DateTime, BigInteger, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import httpx
from decimal import Decimal, getcontext

# --- Конфигурация ---
load_dotenv()

# Настройка точности для Decimal
getcontext().prec = 8

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Параметры
TRIAL_DAYS = 3
TRIAL_DAILY_LIMIT = 12
PREMIUM_DAILY_LIMIT = 20
FREE_WEEKLY_LIMIT = 20
HEARTS_PER_DAY = 5
CHALLENGE_REWARD = 5  # Сердечек за выполнение челленджа
CHALLENGE_DURATION = 120  # Длительность челленджа в секундах (2 минуты)
REFERRAL_REWARD = 20  # Сердечек за приглашение
REFERRAL_TRIAL_DAYS = 3  # Дней пробного периода для приглашенного

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
    }
]

# Цены подписки в рублях
SUBSCRIPTION_PRICES = {
    "1_month": 299,
    "3_months": 749,
    "6_months": 1299,
    "1_year": 2199
}

# Скидки за сердечки (максимум 15%)
HEARTS_DISCOUNTS = {
    100: 5,   # 5% скидка за 100 сердечек
    200: 10,  # 10% скидка за 200 сердечек
    300: 15   # 15% скидка за 300 сердечек
}

# Дополнительные товары в магазине
SHOP_ITEMS = [
    {
        "id": "extra_requests",
        "title": "📈 Доп. запросы",
        "description": "10 дополнительных запросов к ИИ\n\nПозволит вам получить больше ответов от бота, когда закончатся основные лимиты.",
        "price": 30,
        "type": "requests"
    },
    {
        "id": "motivation",
        "title": "💌 Мотивационное письмо",
        "description": "Персональное мотивационное письмо от ИИ\n\nПоможет вам найти вдохновение и силы для достижения целей.",
        "price": 50,
        "type": "content"
    },
    {
        "id": "analysis",
        "title": "🔍 Анализ настроения",
        "description": "Подробный анализ вашего эмоционального состояния\n\nПоможет лучше понять свои чувства и найти пути улучшения настроения.",
        "price": 70,
        "type": "analysis"
    },
    {
        "id": "therapy_session",
        "title": "🧠 Сессия с ИИ-терапевтом",
        "description": "30-минутная сессия с ИИ-терапевтом\n\nПоможет разобраться в сложных эмоциях и найти решения.",
        "price": 100,
        "type": "therapy"
    },
    {
        "id": "sleep_guide",
        "title": "🌙 Гид по улучшению сна",
        "description": "Персонализированный план по улучшению качества сна\n\nСоветы и техники для глубокого восстановительного сна.",
        "price": 80,
        "type": "guide"
    },
    {
        "id": "stress_relief",
        "title": "🌀 Антистресс программа",
        "description": "7-дневная программа по снижению стресса\n\nЕжедневные упражнения и рекомендации.",
        "price": 120,
        "type": "program"
    }
]

# Реквизиты для оплаты
PAYMENT_DETAILS = {
    "crypto": {
        "TRC20_USDT": "TMrLxEVr1sd5UCYB2iQXpj7GM3K5KdXTCP",
        "BTC": "1LsTXcXRzRQyjixURhPRRAPCe4qJb8pEmG"
    },
    "yoomoney": {
        "account": "4100119110059662",
        "comment": "ПОДДЕРЖКА и ваш @username.\n"
        "ПРИМЕР: ПОДДЕРЖКА Ivansokolov"
    }
}

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

# Определяем таблицу users
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("telegram_id", BigInteger, unique=True, nullable=False),
    Column("full_name", String(100)),
    Column("username", String(100)),
    Column("is_premium", Boolean, default=False),
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
    Column("ip_address", String(45), nullable=True)
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
)

# --- Вспомогательные функции ---
async def setup_db():
    """Создает таблицы при первом запуске"""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        logger.info("Таблицы БД проверены/созданы")

async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получает пользователя из БД"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE telegram_id = :telegram_id"),
            {"telegram_id": telegram_id}
        )
        row = result.mappings().first()
        return dict(row) if row else None

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Получает пользователя по username"""
    async with async_session() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username.replace('@', '')}
        )
        row = result.mappings().first()
        return dict(row) if row else None

async def create_user(telegram_id: int, full_name: str, username: str = None, is_admin: bool = False, referred_by: int = None, ip_address: str = None) -> Dict[str, Any]:
    """Создает нового пользователя"""
    async with async_session() as session:
        referral_code = f"REF{random.randint(1000, 9999)}"
        user_data = {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "username": username,
            "is_admin": is_admin,
            "trial_started_at": datetime.utcnow() if not is_admin else None,
            "hearts": HEARTS_PER_DAY,
            "last_request_date": datetime.utcnow(),
            "referral_code": referral_code,
            "referred_by": referred_by,
            "ip_address": ip_address
        }
        
        # Если пользователь пришел по реферальной ссылке, добавляем бонусные дни
        if referred_by:
            user_data["trial_started_at"] = datetime.utcnow()
            user_data["hearts"] = HEARTS_PER_DAY + REFERRAL_REWARD
            
            # Начисляем бонус пригласившему
            referrer = await get_user(referred_by)
            if referrer:
                await session.execute(
                    text("UPDATE users SET hearts = hearts + :reward WHERE telegram_id = :telegram_id"),
                    {"reward": REFERRAL_REWARD, "telegram_id": referred_by}
                )
        
        result = await session.execute(
            users.insert().values(**user_data).returning(users)
        )
        await session.commit()
        return dict(result.mappings().first())

async def update_user(telegram_id: int, **kwargs) -> bool:
    """Обновляет данные пользователя"""
    async with async_session() as session:
        await session.execute(
            users.update()
            .where(users.c.telegram_id == telegram_id)
            .values(**kwargs)
        )
        await session.commit()
        return True

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
    """Проверяет лимит запросов"""
    if not user:
        return False
    if user.get('is_admin'):
        return True
        
    today = datetime.utcnow().date()
    last_request = user.get('last_request_date')
    
    # Сброс дневного лимита
    if last_request is None or last_request.date() != today:
        await update_user(
            user['telegram_id'], 
            total_requests=0,
            last_request_date=datetime.utcnow(),
            hearts=HEARTS_PER_DAY
        )
        return True
    
    # Проверка дневного лимита для премиум и trial пользователей
    if user.get('is_premium'):
        return user.get('total_requests', 0) < (PREMIUM_DAILY_LIMIT + user.get('extra_requests', 0))
    elif user.get('trial_started_at'):
        return user.get('total_requests', 0) < TRIAL_DAILY_LIMIT
    
    return False

async def get_ai_response(prompt: str, max_tokens: int = 500) -> str:
    """Получает ответ от ИИ или использует заглушку"""
    if not OPENAI_API_KEY:
        return (
            "🧠 <b>Технические работы</b>\n\n"
            "В данный момент ИИ-ассистент временно недоступен.\n"
            "Попробуйте выполнить один из наших челленджей или вернитесь позже.\n\n"
            "Используйте команду /challenge для получения задания!"
        )
    
    # Проверка на кризисные сообщения
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
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты - доброжелательный ИИ-психолог. Отвечай с эмпатией и поддержкой. "
                 "Не ставь диагнозы, но мягко направляй к специалистам при необходимости. Будь теплым и понимающим."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка OpenAI: {e}")
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
    return (now - last_challenge) >= timedelta(hours=12)

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
            if crypto == "BTC":
                url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=rub"
                response = await client.get(url)
                data = response.json()
                return Decimal(str(data["bitcoin"]["rub"]))
            elif crypto == "USDT":
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
    # Здесь должна быть реализация проверки транзакций через API блокчейна
    # Для примера возвращаем True
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

async def create_promotion(title: str, description: str, promo_code: str, discount_percent: int, hearts_reward: int, start_date: datetime, end_date: datetime):
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
                end_date=end_date
            )
        )
        await session.commit()

# --- Клавиатуры ---
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
    buttons = [
        [InlineKeyboardButton(text="📈 Доп. запросы", callback_data="shop_extra_requests")],
        [InlineKeyboardButton(text="💌 Мотивационное письмо", callback_data="shop_motivation")],
        [InlineKeyboardButton(text="🔍 Анализ настроения", callback_data="shop_analysis")],
        [InlineKeyboardButton(text="🧠 Сессия с ИИ-терапевтом", callback_data="shop_therapy_session")],
        [InlineKeyboardButton(text="🌙 Гид по улучшению сна", callback_data="shop_sleep_guide")],
        [InlineKeyboardButton(text="🌀 Антистресс программа", callback_data="shop_stress_relief")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_subscription_keyboard():
    """Клавиатура выбора подписки"""
    buttons = [
        [InlineKeyboardButton(text="1 месяц - 299₽", callback_data="sub_1_month")],
        [InlineKeyboardButton(text="3 месяца - 749₽", callback_data="sub_3_months")],
        [InlineKeyboardButton(text="6 месяцев - 1299₽", callback_data="sub_6_months")],
        [InlineKeyboardButton(text="1 год - 2199₽", callback_data="sub_1_year")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_payment_method_keyboard():
    """Клавиатура выбора способа оплаты"""
    buttons = [
        [InlineKeyboardButton(text="💳 Криптовалюта (USDT/BTC)", callback_data="pay_crypto")],
        [InlineKeyboardButton(text="🟣 ЮMoney", callback_data="pay_yoomoney")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_crypto_choice_keyboard():
    """Клавиатура выбора криптовалюты"""
    buttons = [
        [InlineKeyboardButton(text="USDT (TRC20)", callback_data="crypto_usdt")],
        [InlineKeyboardButton(text="Bitcoin (BTC)", callback_data="crypto_btc")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_payment")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard():
    """Клавиатура админа"""
    buttons = [
        [InlineKeyboardButton(text="👤 Активировать премиум", callback_data="admin_premium")],
        [InlineKeyboardButton(text="💖 Начислить сердечки", callback_data="admin_hearts")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🎁 Акции", callback_data="admin_promotions")]
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
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Команды для пользователей ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка команды /start"""
    try:
        await setup_db()
        user = await get_user(message.from_user.id)
        
        # Проверяем реферальную ссылку
        referred_by = None
        if len(message.text.split()) > 1:
            try:
                referred_by = int(message.text.split()[1])
            except ValueError:
                pass
        
        if not user:
            is_admin = message.from_user.id in ADMIN_IDS
            user = await create_user(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username,
                is_admin=is_admin,
                referred_by=referred_by,
                ip_address=message.from_user.id  # В реальном боте нужно получать IP
            )
            
            if is_admin:
                reply = (
                    "👑 <b>Добро пожаловать, администратор!</b>\n\n"
                    "Вам доступны специальные команды:\n"
                    "/admin - Панель администратора\n\n"
                    "Используйте кнопки ниже для управления ботом:"
                )
                await message.answer(reply, reply_markup=get_admin_keyboard(), parse_mode="HTML")
            else:
                reply = (
                    "🌿✨ <b>Привет, дорогой друг!</b> ✨🌿\n\n"
                    "Я - твой персональный помощник для заботы о ментальном здоровье.\n\n"
                    "📌 <b>Что я могу для тебя сделать:</b>\n"
                    "• Провести сессию с ИИ-психологом (на базе GPT-4o)\n"
                    "• Вести личный дневник с защитой паролем\n"
                    "• Давать полезные задания (челленджи)\n"
                    "• Помогать анализировать твои мысли и эмоции\n\n"
                    "🎁 <b>Бонусы:</b>\n"
                    f"• Пробный период {TRIAL_DAYS} дня ({TRIAL_DAILY_LIMIT} запросов/день)\n"
                    f"• {HEARTS_PER_DAY} сердечек ежедневно\n"
                    f"• +{CHALLENGE_REWARD} сердечек за каждый выполненный челлендж\n"
                    f"• +{REFERRAL_REWARD} сердечек за каждого приглашенного друга\n\n"
                    "💡 Начни с команды /psychology и открой для себя все возможности!"
                )
                await message.answer(reply, parse_mode="HTML")
                
                # Если пользователь пришел по реферальной ссылке
                if referred_by:
                    await message.answer(
                        f"🎉 <b>Вы получили бонус за регистрацию по приглашению!</b>\n\n"
                        f"• +{REFERRAL_REWARD} сердечек\n"
                        f"• Пробный период увеличен до {TRIAL_DAYS + REFERRAL_TRIAL_DAYS} дней\n\n"
                        "Поделитесь своей ссылкой и получайте бонусы за друзей: "
                        f"https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}",
                        parse_mode="HTML"
                    )
        else:
            if user.get('is_admin'):
                await message.answer("👑 <b>С возвращением, администратор!</b>", reply_markup=get_admin_keyboard(), parse_mode="HTML")
            else:
                await show_user_profile(message.from_user.id, message)
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def show_user_profile(user_id: int, message: Message):
    """Показывает профиль пользователя"""
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    days_left = TRIAL_DAYS - (datetime.utcnow() - user['trial_started_at']).days if user.get('trial_started_at') else 0
    days_left = max(0, days_left)
    
    if await check_subscription(user):
        status = "💎 Премиум"
        if user.get('subscription_expires_at'):
            expires = user['subscription_expires_at'].strftime("%d.%m.%Y")
            status += f" (до {expires})"
        requests_left = PREMIUM_DAILY_LIMIT + user.get('extra_requests', 0) - user.get('total_requests', 0)
        requests_info = f"{user.get('total_requests', 0)}/{PREMIUM_DAILY_LIMIT + user.get('extra_requests', 0)}"
    elif user.get('trial_started_at'):
        status = f"🆓 Пробный период ({days_left} дн.)"
        requests_left = TRIAL_DAILY_LIMIT - user.get('total_requests', 0)
        requests_info = f"{user.get('total_requests', 0)}/{TRIAL_DAILY_LIMIT}"
    else:
        status = "🌿 Бесплатный"
        requests_left = FREE_WEEKLY_LIMIT - user.get('total_requests', 0)
        requests_info = f"{user.get('total_requests', 0)}/{FREE_WEEKLY_LIMIT}"
    
    buttons = [
        [InlineKeyboardButton(text="💎 Оформить подписку", callback_data="premium_subscription")],
        [InlineKeyboardButton(text="🛍 Магазин сердечек", callback_data="shop")],
        [InlineKeyboardButton(text="🏆 Получить челлендж", callback_data="get_challenge")],
        [InlineKeyboardButton(text="🧠 Психология", callback_data="psychology_menu")]
    ]
    
    reply = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"📛 Имя: {user.get('full_name')}\n"
        f"🎯 Статус: {status}\n"
        f"📊 Запросов: {requests_info}\n"
        f"💖 Сердечек: {user.get('hearts', 0)}\n"
        f"🏆 Челленджей: {user.get('completed_challenges', 0)}\n\n"
        f"🔗 Реферальная ссылка: https://t.me/{(await bot.get_me()).username}?start={user_id}"
    )
    
    await message.answer(
        reply,
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
    await message.answer(
        "🧠 <b>Психологический раздел</b>\n\n"
        "Здесь вы можете получить профессиональную поддержку, вести дневник и улучшить свое ментальное здоровье.\n\n"
        "Выберите опцию:",
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "psychology_menu")
async def psychology_menu(callback: CallbackQuery):
    """Меню психологического раздела"""
    await callback.message.edit_text(
        "🧠 <b>Психологический раздел</b>\n\n"
        "Здесь вы можете получить профессиональную поддержку, вести дневник и улучшить свое ментальное здоровье.\n\n"
        "Выберите опцию:",
        reply_markup=get_psychology_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "ai_psychologist")
async def ai_psychologist(callback: CallbackQuery):
    """Чат с ИИ-психологом"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    await callback.message.edit_text(
        "💬 <b>Чат с ИИ-психологом</b>\n\n"
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
    await callback.message.edit_text(
        "📔 <b>Личный дневник</b>\n\n"
        "Здесь вы можете записывать свои мысли и переживания. "
        "Все записи хранятся анонимно и защищены.\n\n"
        "Вы можете установить пароль для дополнительной защиты.\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Новая запись", callback_data="new_diary_entry")],
            [InlineKeyboardButton(text="🔐 Установить пароль", callback_data="set_diary_password")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="psychology_menu")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    """Команда информации о подписке"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    if user.get('is_admin'):
        await message.answer("👑 Вы администратор. Подписка не требуется.")
        return
    
    if user.get('is_banned'):
        await message.answer("🔐 Ваш аккаунт заблокирован.")
        return
    
    if user.get('is_premium') and user.get('subscription_expires_at'):
        days_left = (user['subscription_expires_at'] - datetime.utcnow()).days
        if days_left > 0:
            await message.answer(
                f"💎 <b>У вас премиум подписка!</b>\n\n"
                f"🔹 Осталось дней: {days_left}\n"
                f"🔹 Действует до: {user['subscription_expires_at'].strftime('%d.%m.%Y')}\n\n"
                f"🔹 Лимит запросов: {PREMIUM_DAILY_LIMIT} в день",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "⚠️ <b>Ваша премиум подписка истекла</b>\n\n"
                "Продлите подписку для продолжения использования.",
                parse_mode="HTML"
            )
    elif user.get('trial_started_at'):
        days_used = (datetime.utcnow() - user['trial_started_at']).days
        days_left = max(0, TRIAL_DAYS - days_used)
        
        await message.answer(
            f"🆓 <b>У вас пробный период</b>\n\n"
            f"🔹 Использовано дней: {days_used}\n"
            f"🔹 Осталось дней: {days_left}\n\n"
            f"🔹 Лимит запросов: {TRIAL_DAILY_LIMIT} в день\n\n"
            "💎 <b>Премиум подписка дает:</b>\n"
            "• Неограниченные запросы\n"
            "• Доступ к дополнительным функциям\n"
            "• Приоритетную поддержку",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🔒 <b>У вас нет активной подписки</b>\n\n"
            f"🔹 Лимит запросов: {FREE_WEEKLY_LIMIT} в неделю\n\n"
            "💎 <b>Премиум подписка дает:</b>\n"
            "• Неограниченные запросы\n"
            "• Доступ к дополнительным функциям\n"
            "• Приоритетную поддержку\n\n"
            "Используйте кнопки ниже для оформления подписки:",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )

@router.message(Command("challenge"))
async def cmd_challenge(message: Message):
    """Команда получения челленджа"""
    await handle_challenge(message.from_user.id, message)

async def handle_challenge(user_id: int, message: Message):
    """Обработка запроса на получение челленджа"""
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    if user.get('active_challenge'):
        await message.answer(
            "⏳ <b>У вас уже есть активный челлендж!</b>\n\n"
            f"Текущее задание: {user['active_challenge']}\n\n"
            "Завершите его перед получением нового.",
            parse_mode="HTML"
        )
        return
    
    if not await can_get_challenge(user):
        next_time = (user['last_challenge_time'] + timedelta(hours=12)).strftime("%H:%M")
        await message.answer(
            f"⏳ <b>Следующий челлендж будет доступен после {next_time}</b>\n\n"
            "Челленджи обновляются 2 раза в день - утром и вечером.",
            parse_mode="HTML"
        )
        return
    
    challenge = random.choice(CHALLENGES)
    challenge_id = str(hash(frozenset(challenge.items())))
    
    await update_user(
        user['telegram_id'],
        active_challenge=challenge["title"],
        challenge_started_at=None
    )
    
    await message.answer(
        f"🏆 <b>Ваш челлендж:</b> {challenge['title']}\n\n"
        f"{challenge['description']}\n\n"
        f"⏱ Длительность: {challenge['duration']} секунд\n"
        f"💖 Награда: +{CHALLENGE_REWARD} сердечек",
        reply_markup=get_challenge_keyboard(challenge_id),
        parse_mode="HTML"
    )

@router.message(Command("shop"))
async def cmd_shop(message: Message):
    """Команда магазина"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    await message.answer(
        "🛍 <b>Магазин сердечек</b>\n\n"
        f"💖 Ваш баланс: {user.get('hearts', 0)} сердечек\n\n"
        "Выберите товар:",
        reply_markup=get_shop_keyboard(),
        parse_mode="HTML"
    )

# --- Обработка колбэков ---
@router.callback_query(F.data == "get_challenge")
async def callback_get_challenge(callback: CallbackQuery):
    """Колбэк для получения челленджа"""
    await handle_challenge(callback.from_user.id, callback.message)
    await callback.answer()

@router.callback_query(F.data.startswith("start_"))
async def start_challenge(callback: CallbackQuery):
    """Начало выполнения челленджа"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    challenge_id = callback.data.replace("start_", "")
    challenge = next((c for c in CHALLENGES if str(hash(frozenset(c.items()))) == challenge_id), None)
    
    if not challenge:
        await callback.answer("Челлендж не найден")
        return
    
    await update_user(
        user['telegram_id'],
        challenge_started_at=datetime.utcnow()
    )
    
    # Отправляем сообщение с таймером
    msg = await callback.message.edit_text(
        f"⏳ <b>Челлендж начат:</b> {challenge['title']}\n\n"
        f"{challenge['description']}\n\n"
        f"⏱ Осталось: {challenge['duration']} секунд",
        parse_mode="HTML"
    )
    
    # Запускаем таймер
    remaining = challenge['duration']
    while remaining > 0:
        await asyncio.sleep(1)
        remaining -= 1
        
        # Проверяем, не отменил ли пользователь челлендж
        updated_user = await get_user(user['telegram_id'])
        if not updated_user or not updated_user.get('active_challenge'):
            return
        
        # Обновляем сообщение каждые 10 секунд
        if remaining % 10 == 0 or remaining <= 5:
            try:
                await bot.edit_message_text(
                    f"⏳ <b>Челлендж начат:</b> {challenge['title']}\n\n"
                    f"{challenge['description']}\n\n"
                    f"⏱ Осталось: {remaining} секунд",
                    chat_id=msg.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except:
                pass
    
    # По окончании времени добавляем кнопку завершения
    await bot.edit_message_text(
        f"⏳ <b>Челлендж завершен:</b> {challenge['title']}\n\n"
        f"{challenge['description']}\n\n"
        "✅ Время вышло! Нажмите кнопку ниже для получения награды",
        chat_id=msg.chat.id,
        message_id=msg.message_id,
        reply_markup=get_challenge_timer_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "complete_challenge")
async def finish_challenge(callback: CallbackQuery):
    """Завершение челленджа"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('active_challenge'):
        await callback.answer("Нет активного челленджа")
        return
    
    challenge = next((c for c in CHALLENGES if c['title'] == user['active_challenge']), None)
    if not challenge:
        await callback.answer("Ошибка: челлендж не найден")
        return
    
    new_hearts = await complete_challenge(user['telegram_id'])
    if new_hearts is not None:
        await callback.message.edit_text(
            f"🎉 <b>Челлендж завершен!</b>\n\n"
            f"Вы успешно выполнили: {challenge['title']}\n\n"
            f"💖 Получено: +{CHALLENGE_REWARD} сердечек\n"
            f"💰 Ваш баланс: {new_hearts} сердечек",
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data == "premium_subscription")
async def premium_subscription(callback: CallbackQuery):
    """Колбэк для премиум подписки"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    await callback.message.edit_text(
        "💎 <b>Премиум подписка</b>\n\n"
        "Преимущества подписки:\n"
        "• Неограниченные запросы к боту\n"
        "• Доступ к дополнительным функциям\n"
        "• Приоритетная поддержка\n\n"
        "Выберите срок подписки:",
        reply_markup=get_subscription_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sub_"))
async def select_subscription(callback: CallbackQuery):
    """Выбор срока подписки"""
    sub_type = callback.data.replace("sub_", "")
    price = SUBSCRIPTION_PRICES.get(sub_type)
    
    if not price:
        await callback.answer("Неверный тип подписки")
        return
    
    duration_map = {
        "1_month": "1 месяц",
        "3_months": "3 месяца",
        "6_months": "6 месяцев",
        "1_year": "1 год"
    }
    
    await callback.message.edit_text(
        f"💎 <b>Премиум подписка на {duration_map[sub_type]}</b>\n\n"
        f"Стоимость: {price}₽\n\n"
        "Выберите способ оплаты:",
        reply_markup=get_payment_method_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "pay_crypto")
async def pay_with_crypto(callback: CallbackQuery):
    """Оплата криптовалютой"""
    text = (
        "💳 <b>Оплата криптовалютой</b>\n\n"
        "Для оплаты отправьте средства на один из адресов:\n\n"
        f"<b>USDT (TRC20):</b>\n<code>{PAYMENT_DETAILS['crypto']['TRC20_USDT']}</code>\n\n"
        f"<b>Bitcoin (BTC):</b>\n<code>{PAYMENT_DETAILS['crypto']['BTC']}</code>\n\n"
        "После оплаты отправьте хеш транзакции в ответ на это сообщение.\n"
        "Ваша подписка будет активирована после подтверждения платежа в теченее 5-10 минут."
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "pay_yoomoney")
async def pay_with_yoomoney(callback: CallbackQuery):
    """Оплата через ЮMoney"""
    text = (
        "🟣 <b>Оплата через ЮMoney</b>\n\n"
        f"Для оплаты отправьте перевод на номер: <code>{PAYMENT_DETAILS['yoomoney']['account']}</code>\n\n"
        f"<b>Обязательно укажите комментарий:</b>\n"
        f"<code>{PAYMENT_DETAILS['yoomoney']['comment']}</code>\n\n"
        "После оплаты отправьте скриншот перевода в ответ на это сообщение.\n"
        "Ваша подписка будет активирована после подтверждения платежа в теченее 5-10 минут."
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "shop")
async def callback_shop(callback: CallbackQuery):
    """Колбэк для магазина"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    await callback.message.edit_text(
        "🛍 <b>Магазин сердечек</b>\n\n"
        f"💖 Ваш баланс: {user.get('hearts', 0)} сердечек\n\n"
        "Выберите товар:",
        reply_markup=get_shop_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("shop_"))
async def shop_item(callback: CallbackQuery):
    """Обработка выбора товара в магазине"""
    item_id = callback.data.replace("shop_", "")
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    if user.get('hearts', 0) < item['price']:
        await callback.answer(f"Недостаточно сердечек. Нужно: {item['price']}")
        return
    
    buttons = [
        [InlineKeyboardButton(text=f"✅ Купить за {item['price']} сердечек", callback_data=f"buy_{item_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_shop")]
    ]
    
    await callback.message.edit_text(
        f"🛍 <b>{item['title']}</b>\n\n"
        f"{item['description']}\n\n"
        f"💖 Стоимость: {item['price']} сердечек",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def buy_item(callback: CallbackQuery):
    """Покупка товара в магазине"""
    item_id = callback.data.replace("buy_", "")
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    
    if not item:
        await callback.answer("Товар не найден")
        return
    
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    if user.get('hearts', 0) < item['price']:
        await callback.answer(f"Недостаточно сердечек. Нужно: {item['price']}")
        return
    
    # Обновляем баланс пользователя
    new_hearts = user.get('hearts', 0) - item['price']
    await update_user(
        user['telegram_id'],
        hearts=new_hearts
    )
    
    # В зависимости от типа товара выполняем действие
    if item['type'] == "requests":
        extra_requests = user.get('extra_requests', 0) + 10
        await update_user(
            user['telegram_id'],
            extra_requests=extra_requests
        )
        result = "🔹 Получено +10 дополнительных запросов"
    elif item['type'] == "content":
        # Генерируем мотивационное письмо
        motivation_text = await get_ai_response("Напиши мотивационное письмо для пользователя, который хочет улучшить свое ментальное здоровье.")
        result = f"💌 <b>Ваше мотивационное письмо:</b>\n\n{motivation_text}"
    elif item['type'] == "analysis":
        # Генерируем анализ настроения
        analysis_text = await get_ai_response("Проведи анализ эмоционального состояния пользователя и дай рекомендации по улучшению настроения.")
        result = f"🔍 <b>Анализ вашего настроения:</b>\n\n{analysis_text}"
    elif item['type'] == "therapy":
        # Сессия с ИИ-терапевтом
        result = "🧠 <b>Сессия с ИИ-терапевтом</b>\n\nОтправьте ваше сообщение, и я постараюсь помочь."
    elif item['type'] == "guide":
        # Гид по улучшению сна
        guide_text = await get_ai_response("Составь персонализированный план по улучшению качества сна с советами и техниками.")
        result = f"🌙 <b>Гид по улучшению сна:</b>\n\n{guide_text}"
    elif item['type'] == "program":
        # Антистресс программа
        program_text = await get_ai_response("Создай 7-дневную программу по снижению стресса с ежедневными упражнениями.")
        result = f"🌀 <b>Антистресс программа:</b>\n\n{program_text}"
    else:
        result = "🛍 Товар получен!"
    
    await callback.message.edit_text(
        f"🎉 <b>Покупка совершена!</b>\n\n"
        f"Вы приобрели: {item['title']}\n\n"
        f"{result}\n\n"
        f"💖 Остаток сердечек: {new_hearts}",
        reply_markup=get_back_to_shop_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await show_user_profile(callback.from_user.id, callback.message)
    await callback.answer()

@router.callback_query(F.data == "back_to_shop")
async def back_to_shop(callback: CallbackQuery):
    """Возврат в магазин"""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используйте /start")
        return
    
    try:
        await callback.message.edit_text(
            "🛍 <b>Магазин сердечек</b>\n\n"
            f"💖 Ваш баланс: {user.get('hearts', 0)} сердечек\n\n"
            "Выберите товар:",
            reply_markup=get_shop_keyboard(),
            parse_mode="HTML"
        )
    except:
        await callback.answer()
    await callback.answer()

@router.callback_query(F.data == "back_to_subscription")
async def back_to_subscription(callback: CallbackQuery):
    """Возврат к выбору подписки"""
    await premium_subscription(callback)
    await callback.answer()

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery):
    """Возврат к профилю"""
    await show_user_profile(callback.from_user.id, callback.message)
    await callback.answer()

# --- Админские функции ---
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда админ-панели"""
    user = await get_user(message.from_user.id)
    if not user or not user.get('is_admin'):
        return
    
    await message.answer(
        "👑 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика для админов"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        return
    
    async with async_session() as session:
        total_users = await session.scalar(text("SELECT COUNT(*) FROM users"))
        premium_users = await session.scalar(text("SELECT COUNT(*) FROM users WHERE is_premium = TRUE"))
        challenges_completed = await session.scalar(text("SELECT SUM(completed_challenges) FROM users"))
        total_hearts = await session.scalar(text("SELECT SUM(hearts) FROM users"))
        pending_payments = await session.scalar(text("SELECT COUNT(*) FROM payments WHERE status = 'pending'"))
        
        # Получаем последних пользователей
        recent_users = await get_recent_users()
    
    stats = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💎 Премиум: {premium_users}\n"
        f"🏆 Челленджей выполнено: {challenges_completed or 0}\n"
        f"💖 Всего сердечек у пользователей: {total_hearts or 0}\n"
        f"💰 Ожидает оплаты: {pending_payments or 0}\n\n"
        "🆕 <b>Последние пользователи:</b>\n"
    )
    
    for i, user in enumerate(recent_users, 1):
        stats += f"{i}. @{user['username']} - {user['created_at'].strftime('%d.%m.%Y')}\n"
    
    await callback.message.answer(stats, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_premium")
async def admin_premium(callback: CallbackQuery):
    """Активация премиума админом"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        return
    
    await callback.message.answer(
        "👤 <b>Активация премиум подписки</b>\n\n"
        "Введите username пользователя и срок подписки (в днях) в формате:\n"
        "<code>@username 30</code>\n\n"
        "Пример: <code>@ivan 30</code> - активирует премиум на 30 дней",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_hearts")
async def admin_hearts(callback: CallbackQuery):
    """Начисление сердечек админом"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        return
    
    await callback.message.answer(
        "💖 <b>Начисление сердечек</b>\n\n"
        "Введите username пользователя и количество сердечек в формате:\n"
        "<code>@username 50</code>\n\n"
        "Пример: <code>@ivan 50</code> - начислит 50 сердечек",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_promotions")
async def admin_promotions(callback: CallbackQuery):
    """Управление акциями"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        return
    
    await callback.message.answer(
        "🎁 <b>Управление акциями</b>\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать акцию", callback_data="create_promotion")],
            [InlineKeyboardButton(text="📋 Список акций", callback_data="list_promotions")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    """Возврат в админ-панель"""
    user = await get_user(callback.from_user.id)
    if not user or not user.get('is_admin'):
        return
    
    await callback.message.edit_text(
        "👑 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# --- Обработка сообщений ---
@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработка текстовых сообщений"""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используйте /start")
        return
    
    # Сохраняем сообщение пользователя
    async with async_session() as session:
        await session.execute(
            user_messages.insert().values(
                user_id=user['telegram_id'],
                message_text=message.text,
                is_ai_response=False
            )
        )
        await session.commit()
    
    # Проверяем лимиты
    if not await check_request_limit(user):
        await message.answer(
            "⚠️ <b>Лимит запросов исчерпан</b>\n\n"
            "Вы можете:\n"
            "1. Купить дополнительные запросы в магазине (/shop)\n"
            "2. Дождаться обновления лимитов\n"
            "3. Оформить премиум подписку (/subscription)",
            parse_mode="HTML"
        )
        return
    
    # Увеличиваем счетчик запросов
    await update_user(
        user['telegram_id'],
        total_requests=user.get('total_requests', 0) + 1,
        last_request_date=datetime.utcnow()
    )
    
    # Получаем ответ от ИИ
    response = await get_ai_response(message.text)
    await message.answer(response, parse_mode="HTML")
    
    # Сохраняем ответ ИИ
    async with async_session() as session:
        await session.execute(
            user_messages.insert().values(
                user_id=user['telegram_id'],
                message_text=response,
                is_ai_response=True
            )
        )
        await session.commit()

# --- Запуск бота ---
async def on_startup():
    """Действия при запуске"""
    await setup_db()
    
    # Команды для обычных пользователей
    user_commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="profile", description="Ваш профиль"),
        BotCommand(command="subscription", description="Подписка"),
        BotCommand(command="challenge", description="Получить челлендж"),
        BotCommand(command="shop", description="Магазин"),
        BotCommand(command="psychology", description="Психологическая помощь")
    ]
    
    # Команды для админов
    admin_commands = [
        BotCommand(command="admin", description="Панель администратора"),
    ]
    
    # Устанавливаем команды для всех пользователей
    await bot.set_my_commands(user_commands)
    
    # Устанавливаем дополнительные команды для админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(
                admin_commands,
                scope={"type": "chat", "chat_id": admin_id}
            )
        except Exception as e:
            logger.error(f"Ошибка установки команд для админа {admin_id}: {e}")
    
    logger.info("Бот запущен")

async def on_shutdown():
    """Действия при выключении"""
    logger.info("Выключение бота...")
    await bot.close()
    await engine.dispose()

async def main():
    """Основная функция"""
    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")