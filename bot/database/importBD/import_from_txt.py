import re
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select

from bot.database.models.main import Base, Persons, Payments
from bot.misc.util import CONFIG

# Используем тот же engine, что и в основном приложении
ENGINE = (
    f'postgresql+asyncpg://'
    f'{CONFIG.postgres_user}:'
    f'{CONFIG.postgres_password}'
    f'@postgres_db_container/{CONFIG.postgres_db}'
)

engine = create_async_engine(ENGINE)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def parse_subscription_line(line):
    # Парсинг строки из файла subscription_user.txt
    pattern = r'(\d+\)) (.+?) - \(@(.+?)\|(\d+)\) - \(Язык в ТГ:(.+?)\) \(\[Баланс:(\d+) руб\.\] / \[Реф\.баланс: (\d+) руб\.\] \) - (\d{2}\.\d{2}\.\d{4} \d{2}:\d{2})'
    match = re.match(pattern, line.strip())
    if match:
        _, name, username, tgid, lang, balance, ref_balance, subscription = match.groups()
        username = None if username == 'None' else username
        subscription_date = datetime.strptime(subscription, '%d.%m.%Y %H:%M')
        return {
            'fullname': name.strip(),
            'username': username,
            'tgid': int(tgid),
            'lang_tg': lang if lang != '❌' else None,
            'balance': int(balance),
            'referral_balance': int(ref_balance),
            'subscription': int(subscription_date.timestamp())
        }
    return None

def parse_payment_line(line):
    # Парсинг строки из файла payments.txt
    pattern = r'(\d+\)) Пользователь: @(.+?)\((\d+)\) - Платежная система: (.+?) - Сумма: \((\d+\.\d+) руб\.\) \| Дата: (.+)$'
    match = re.match(pattern, line.strip())
    if match:
        _, username, tgid, payment_system, amount, date = match.groups()
        username = None if username == 'None' else username
        payment_date = datetime.strptime(date.strip(), '%Y-%m-%d %H:%M:%S.%f')
        return {
            'tgid': int(tgid),
            'payment_system': payment_system,
            'amount': float(amount),
            'data': payment_date
        }
    return None

async def import_users():
    async with AsyncSession(engine) as session:
        with open('subscription_user.txt', 'r', encoding='utf-8') as f:
            added_users = 0
            skipped_users = 0
            for line in f:
                if line.strip():
                    user_data = parse_subscription_line(line)
                    if user_data:
                        # Проверяем, существует ли пользователь
                        stmt = select(Persons).where(Persons.tgid == user_data['tgid'])
                        result = await session.execute(stmt)
                        existing_user = result.scalar_one_or_none()
                        
                        if existing_user:
                            # Обновляем данные существующего пользователя
                            existing_user.username = user_data['username']
                            existing_user.fullname = user_data['fullname']
                            existing_user.balance = user_data['balance']
                            existing_user.referral_balance = user_data['referral_balance']
                            existing_user.subscription = user_data['subscription']
                            existing_user.lang_tg = user_data['lang_tg']
                            skipped_users += 1
                        else:
                            # Создаем нового пользователя
                            user = Persons(
                                tgid=user_data['tgid'],
                                username=user_data['username'],
                                fullname=user_data['fullname'],
                                balance=user_data['balance'],
                                referral_balance=user_data['referral_balance'],
                                subscription=user_data['subscription'],
                                lang_tg=user_data['lang_tg'],
                                date_reg=datetime.now()
                            )
                            session.add(user)
                            added_users += 1
        await session.commit()
        print(f"Добавлено новых пользователей: {added_users}")
        print(f"Обновлено существующих пользователей: {skipped_users}")

async def import_payments():
    async with AsyncSession(engine) as session:
        with open('payments.txt', 'r', encoding='utf-8') as f:
            added_payments = 0
            skipped_payments = 0
            for line in f:
                if line.strip():
                    payment_data = parse_payment_line(line)
                    if payment_data:
                        # Получаем пользователя по tgid
                        stmt = select(Persons).where(Persons.tgid == payment_data['tgid'])
                        result = await session.execute(stmt)
                        user = result.scalar_one_or_none()
                        
                        if user:
                            # Проверяем, существует ли платеж
                            stmt = select(Payments).where(
                                (Payments.user == user.id) &
                                (Payments.data == payment_data['data']) &
                                (Payments.amount == payment_data['amount'])
                            )
                            result = await session.execute(stmt)
                            existing_payment = result.scalar_one_or_none()
                            
                            if not existing_payment:
                                payment = Payments(
                                    user=user.id,
                                    payment_system=payment_data['payment_system'],
                                    amount=payment_data['amount'],
                                    data=payment_data['data']
                                )
                                session.add(payment)
                                added_payments += 1
                            else:
                                skipped_payments += 1
        await session.commit()
        print(f"Добавлено новых платежей: {added_payments}")
        print(f"Пропущено существующих платежей: {skipped_payments}")

async def main():
    print("Создание таблиц...")
    await create_tables()
    
    print("Импорт пользователей...")
    await import_users()
    
    print("\nИмпорт платежей...")
    await import_payments()
    
    print("\nИмпорт завершен!")

if __name__ == '__main__':
    asyncio.run(main())
