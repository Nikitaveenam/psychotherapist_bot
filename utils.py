from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from models import User

async def check_user_subscription(user: User, session: AsyncSession):
    """Функция для проверки состояния подписки пользователя."""
    if user.is_premium:
        return "✅ Активная подписка"
    elif user.trial_started_at and (datetime.utcnow() - user.trial_started_at).days <= 3:
        return "🆓 Пробный период"
    else:
        return "🔒 Доступ ограничен"

async def is_user_allowed_to_chat(session: AsyncSession, user: User) -> bool:
    """Функция для проверки, имеет ли пользователь право на общение."""
    now = datetime.now()
    if user.is_premium:
        return True
    if user.trial_started_at and (now - user.trial_started_at).days < 3:
        # Пробный период
        return True
    if not user.trial_started_at:
        # Начинаем пробный
        user.trial_started_at = now
        await session.commit()
        return True
    # Проверка лимита 3 запроса в день
    if not hasattr(user, "daily_requests"):
        user.daily_requests = {}
    today = now.strftime("%Y-%m-%d")
    requests_today = user.daily_requests.get(today, 0)
    return requests_today < 3
