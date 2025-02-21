# bot/database/importBD/restore_database.py
import asyncio
from import_BD import import_all

async def restore_database():
    try:
        print("Начинаем восстановление базы данных...")
        await import_all()
        print("База данных успешно восстановлена!")
    except Exception as e:
        print(f"Ошибка при восстановлении базы данных: {e}")

if __name__ == "__main__":
    asyncio.run(restore_database())