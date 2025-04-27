from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from sqlalchemy import text
from bot import bot, async_session, payments, users
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/yoomoney_webhook")
async def yoomoney_webhook(request: Request):
    """Обработчик вебхуков от ЮMoney"""
    try:
        data = await request.form()
        if data.get("notification_type") != "card-incoming":
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": "error"})
        
        # Проверяем подпись
        sha1_hash = data.get("sha1_hash")
        if not verify_yoomoney_signature(data, sha1_hash):
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"status": "invalid_signature"})
        
        # Обрабатываем платеж
        amount = float(data.get("withdraw_amount"))
        user_id = int(data.get("label"))
        await process_yoomoney_payment(user_id, amount)
        
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"status": "error"})

def verify_yoomoney_signature(data: dict, sha1_hash: str) -> bool:
    """Проверить подпись уведомления от ЮMoney"""
    # Замените на реальную проверку подписи
    from hashlib import sha1
    secret = "ваш_секретный_ключ_из_настроек_юmoney"
    check_str = f"{data['notification_type']}&{data['operation_id']}&{data['amount']}&{data['currency']}&{data['datetime']}&{data['sender']}&{data['codepro']}&{secret}&{data['label']}"
    return sha1(check_str.encode()).hexdigest() == sha1_hash

async def extend_premium(user_id: int, days: int):
    """Продлить премиум (должен быть импортирован из основного файла или продублирован здесь)"""
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        result = await session.execute(
            text("SELECT subscription_expires_at FROM users WHERE telegram_id = :user_id"),
            {"user_id": user_id}
        )
        expires_at = result.scalar()
        
        if expires_at and expires_at > now:
            new_expires = expires_at + timedelta(days=days)
        else:
            new_expires = now + timedelta(days=days)
        
        await session.execute(
            text("UPDATE users SET is_premium=true, user_type='premium', subscription_expires_at=:expires WHERE telegram_id = :user_id"),
            {"expires": new_expires, "user_id": user_id}
        )
        await session.commit()

async def process_yoomoney_payment(user_id: int, amount: float):
    """Обработка платежа через ЮMoney"""
    subscriptions = {
        299: 1,
        799: 3,
        1399: 6,
        2399: 12
    }
    
    months = subscriptions.get(amount, 0)
    if months > 0:
        await extend_premium(user_id, months * 30)
        await bot.send_message(
            user_id,
            f"🎉 Спасибо за оплату премиум-подписки на {months} месяцев!"
        )
    
    async with async_session.begin() as session:
        await session.execute(
            payments.insert().values(
                user_id=user_id,
                amount=amount,
                currency="RUB",
                item_id=f"premium_{months}",
                status="completed",
                payment_method="yoomoney",
                created_at=datetime.now(timezone.utc),
                confirmed_at=datetime.now(timezone.utc)
            )
        )