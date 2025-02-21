import time
from itertools import count

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from bot.database.main import engine
from bot.database.methods.get import _get_person, _get_server
from bot.database.models.main import Persons, WithdrawalRequests
from bot.misc.util import CONFIG


async def add_balance_person(tgid, deposit):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.balance += int(deposit)
            await db.commit()
            return True
        return False


async def reduce_balance_person(deposit, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.balance -= int(deposit)
            await db.commit()
            return True
        return False


async def reduce_referral_balance_person(amount, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.referral_balance -= int(amount)
            if person.referral_balance < 0:
                return False
            await db.commit()
            return True
        return False


async def update_balance_person(amount, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.balance = int(amount)
            if person.balance < 0:
                return False
            await db.commit()
            return True
        return False


async def add_referral_balance_person(amount, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.referral_balance += int(amount)
            await db.commit()
            return True
        return False


async def add_time_person(tgid, count_time):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            now_time = int(time.time()) + count_time
            if person.banned:
                person.subscription = int(now_time)
                person.banned = False
            else:
                person.subscription += count_time
            await db.commit()
            return True
        return False


async def person_banned_true(tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.server = None
            person.banned = True
            person.notion_oneday = False
            person.subscription = int(time.time())
            await db.commit()
            return True
        return False


async def person_one_day_true(tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.notion_oneday = True
            await db.commit()
            return True
        return False


async def person_delete_server(tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.server = None
            await db.commit()
            return True
        return False


async def server_work_update(name, work):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        server = await _get_server(db, name)
        if server is not None:
            server.work = work
            await db.commit()
            return True
        return False


async def server_space_update(name, new_space):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        server = await _get_server(db, name)
        if server is not None:
            server.space = new_space
            await db.commit()
            return True
        return False


async def add_user_in_server(telegram_id, server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await db.execute(
            select(Persons).filter(Persons.tgid == telegram_id)
        )
        person = person.scalar_one_or_none()
        person.server = server.id
        await db.commit()


async def add_pomo_code_person(tgid, promo_code):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        async with db.begin():
            statement = select(Persons).options(
                joinedload(Persons.promocode)).filter(Persons.tgid == tgid)
            result = await db.execute(statement)
            person = result.unique().scalar_one_or_none()
            count_time = promo_code.add_balance * CONFIG.COUNT_SECOND_DAY

            if person is not None:
                now_time = int(time.time()) + count_time
                if person.banned:
                    person.subscription = int(now_time)
                    person.banned = False
                else:
                    person.subscription += count_time
                person.promocode.append(promo_code)
                await db.commit()
                return True
            return False


async def succes_aplication(id_application):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        application = await db.execute(
            select(WithdrawalRequests)
            .filter(WithdrawalRequests.id == id_application)
        )
        application_instance = application.scalar_one_or_none()
        if application_instance is not None:
            application_instance.check_payment = True
            await db.commit()
            return True
        return False


async def update_delete_users_server(server):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        await db.execute(
            update(Persons)
            .where(Persons.server == server.id)
            .values({"server": None})
        )
        await db.commit()


async def update_lang(lang, tgid):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        person = await _get_person(db, tgid)
        if person is not None:
            person.lang = lang
            await db.commit()
            return True
        return False


async def persons_add_group(list_input, name_group=None):
    async with AsyncSession(autoflush=False, bind=engine()) as db:
        statement = select(Persons).filter(Persons.tgid.in_(list_input))
        result = await db.execute(statement)
        persons = result.scalars().all()
        if persons is not None:
            for person in persons:
                person.group = name_group
                person.server = None
            await db.commit()
            return len(persons)
        return 0


async def update_paid_status_and_give_bonus(user_id: int) -> bool:
    """
    Обновляет статус paid пользователя и начисляет бонус реферреру
    """
    try:
        async with AsyncSession(autoflush=False, bind=engine()) as db:
            # Получаем пользователя
            user = await db.execute(
                select(Persons).where(Persons.tgid == user_id)
            )
            user = user.scalar_one_or_none()
            if not user or user.paid:  # Если пользователь уже оплачивал, не даем бонус повторно
                return False
                
            # Обновляем статус paid
            user.paid = True
            
            # Если есть реферрер, начисляем ему бонусные дни
            if user.referral_user_tgid:
                referrer = await db.execute(
                    select(Persons).where(Persons.tgid == user.referral_user_tgid)
                )
                referrer = referrer.scalar_one_or_none()
                if referrer:
                    # Начисляем дни
                    bonus_days = CONFIG.referral_day * CONFIG.COUNT_SECOND_DAY
                    referrer.subscription += bonus_days
            
            await db.commit()
            return True
    except Exception as e:
        log.error(f'Error in update_paid_status_and_give_bonus: {e}')
        return False
