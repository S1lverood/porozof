from datetime import datetime, timedelta
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.database.methods.get import get_all_user, get_all_subscription, get_payments
from bot.misc.language import get_lang
from bot.filters.main import IsAdmin
from bot.keyboards.reply.admin_reply import admin_menu

log = logging.getLogger(__name__)

statistics_router = Router()
statistics_router.message.filter(IsAdmin())

@statistics_router.message(F.text == "Статистика📊")
async def show_statistics(message: Message, state: FSMContext) -> None:
    """Show bot statistics to admin"""
    try:
        # Get all users
        all_users = await get_all_user()
        total_users = len(all_users)
        
        # Get new users in last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        new_users_30d = len([u for u in all_users if u.date_reg and u.date_reg > thirty_days_ago])
        
        # Get new users today
        today = datetime.now().date()
        new_users_today = len([u for u in all_users if u.date_reg and u.date_reg.date() == today])
        
        # Get active subscriptions
        active_subs = await get_all_subscription()
        active_subs_count = len(active_subs)
        
        # Calculate earnings
        payments = await get_payments()
        total_earnings = sum(p.amount for p in payments) if payments else 0
        today_earnings = sum(p.amount for p in payments if p.data and p.data.date() == today) if payments else 0
        
        # Format statistics message
        stats_msg = (
            "📊 Статистика бота:\n\n"
            f"📈 Всего пользователей: {total_users}\n"
            f"📅 Новых пользователей за 30 дней: {new_users_30d}\n"
            f"🗓 Пользователей за день: {new_users_today}\n\n"
            f"🟢 Активных подписок: {active_subs_count}\n\n"
            f"💰 Заработано за сегодня: {today_earnings:.2f}₽\n"
            f"💰 Заработано за всё время: {total_earnings:.2f}₽"
        )
        
        # Send statistics
        await message.answer(stats_msg)
        
        # Return to admin menu
        lang = await get_lang(message.from_user.id)
        await message.answer(
            "Выберите действие:",
            reply_markup=await admin_menu(lang)
        )
        
    except Exception as e:
        log.error(f"Error in statistics handler: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при получении статистики")
