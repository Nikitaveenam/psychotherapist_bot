from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any, Callable

TRIAL_DAYS = 3

async def check_user_subscription(user: Dict[str, Any]) -> bool:
    """Проверяет активность подписки."""
    if not user or user.get('is_banned'):
        return False
    if user.get('is_admin'):
        return True
    if user.get('is_premium') and user.get('subscription_expires_at') and user['subscription_expires_at'] > datetime.utcnow():
        return True
    if is_trial_active(user):
        return True
    return False

def is_trial_active(user: Dict[str, Any], trial_days: int = TRIAL_DAYS) -> bool:
    """Проверка активности пробного периода."""
    start = user.get('trial_started_at')
    if start:
        return (datetime.utcnow() - start).days <= trial_days
    return False

async def check_request_limit_and_update(
    user: Dict[str, Any],
    is_premium: bool,
    daily_limit: int,
    weekly_limit: int,
    update_func: Callable[[int, Dict[str, Any]], Any]
) -> bool:
    """
    Проверяет лимит и при необходимости сбрасывает счётчики через `update_func`.
    update_func: async функция, например: update_user(user_id, {total_requests: 0, ...})
    """
    if not user:
        return False

    now = datetime.now(timezone.utc)
    last_request = user.get('last_request_date')
    telegram_id = user.get('telegram_id')

    if is_premium:
        if not last_request or last_request.date() != now.date():
            await update_func(telegram_id, {
                "total_requests": 0,
                "last_request_date": now
            })
            return True
        return user.get("total_requests", 0) < daily_limit

    # Не премиум
    if not last_request or (now - last_request).days >= 7:
        await update_func(telegram_id, {
            "weekly_requests": 0,
            "last_request_date": now
        })
        return True

    return user.get("weekly_requests", 0) < weekly_limit
