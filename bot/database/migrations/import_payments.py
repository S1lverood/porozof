import re
from datetime import datetime
from sqlalchemy import select
from bot.database.main import async_session_maker
from bot.database.models.main import Persons, Payments
import os
import time

async def import_subscriptions():
    async with async_session_maker() as session:
        # Читаем данные из файла с подписками
        with open('subscription_user.txt', 'r', encoding='utf-8') as f:
            subscription_data = f.read()
        
        pattern = r'Пользователь: @?([^(]+)?\((\d+)\)'
        
        for line in subscription_data.strip().split('\n'):
            if not line.strip() or line.startswith('#'):
                continue
                
            match = re.search(pattern, line)
            if not match:
                print(f"Не удалось разобрать строку: {line}")
                continue
                
            username, tgid = match.groups()
            tgid = int(tgid)
            
            # Проверяем существование пользователя
            stmt = select(Persons).where(Persons.tgid == tgid)
            user = await session.execute(stmt)
            user = user.scalar()
            
            if not user:
                # Создаем нового пользователя с подпиской на 30 дней
                current_time = int(time.time())
                user = Persons(
                    tgid=tgid,
                    username=username if username != 'None' else None,
                    subscription=current_time + (30 * 24 * 60 * 60),  # +30 дней
                    paid=True
                )
                session.add(user)
                print(f"Создан новый пользователь: {username}({tgid})")
            else:
                # Обновляем подписку существующего пользователя
                current_time = int(time.time())
                if not user.subscription or user.subscription < current_time:
                    user.subscription = current_time + (30 * 24 * 60 * 60)  # +30 дней
                user.paid = True
                print(f"Обновлена подписка пользователя: {username}({tgid})")
        
        await session.commit()
        print("Импорт подписок завершен успешно")

async def migrate():
    await import_subscriptions()
