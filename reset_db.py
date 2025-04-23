import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from main import Base, DB_URL

async def reset_database():
    engine = create_async_engine(DB_URL)
    
    async with engine.begin() as conn:
        # Удаляем все таблицы с каскадом
        print("Удаляю все таблицы...")
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(sync_conn, checkfirst=False)
        )
        
        # Создаем таблицы заново
        print("Создаю новые таблицы...")
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("База данных успешно сброшена!")

if __name__ == "__main__":
    asyncio.run(reset_database())