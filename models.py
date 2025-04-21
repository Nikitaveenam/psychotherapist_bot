from datetime import datetime  # Добавьте этот импорт

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    trial_started_at = Column(DateTime, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # Теперь правильно используется datetime.utcnow
    daily_requests = {}  # Словарь для отслеживания запросов

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, name={self.name})>"
