import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://postgres:Krass3701033@localhost:5432/anon_psych"

async def reset_database():
    engine = create_async_engine(DB_URL)
    
    async with engine.begin() as conn:
        # 1. Удаляем все ограничения внешних ключей
        print("Удаляю ограничения внешних ключей...")
        await conn.execute(text("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT table_name, constraint_name 
                    FROM information_schema.table_constraints
                    WHERE constraint_type = 'FOREIGN KEY' 
                    AND table_schema = 'public'
                ) LOOP
                    EXECUTE 'ALTER TABLE ' || quote_ident(r.table_name) || 
                           ' DROP CONSTRAINT ' || quote_ident(r.constraint_name);
                END LOOP;
            END $$;
        """))
        
        # 2. Удаляем все таблицы
        print("Удаляю все таблицы...")
        await conn.execute(text("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                ) LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """))
        
        # 3. Создаем таблицы заново
        print("Создаю новые таблицы...")
        from main import Base
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("База данных успешно сброшена!")

if __name__ == "__main__":
    asyncio.run(reset_database())