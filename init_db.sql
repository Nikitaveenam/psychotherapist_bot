
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    gender TEXT,
    subscription_expires_at TIMESTAMP,
    trial_started_at TIMESTAMP,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entries (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    model TEXT NOT NULL,
    prompt TEXT,
    response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id),
    method TEXT, -- 'trial', 'manual', 'promo', etc.
    amount NUMERIC,
    currency TEXT,
    activated_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS promocodes (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    days INTEGER NOT NULL,
    used_by BIGINT REFERENCES users(telegram_id),
    used_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    action TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
