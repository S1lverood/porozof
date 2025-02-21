from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.misc.texts import btn_text


async def admin_confirm_sbp(user_id: int, amount: str) -> InlineKeyboardMarkup:
    """Create keyboard for admin to confirm SBP payment"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=btn_text('confirm_payment'),
            callback_data=f'confirm_sbp_{user_id}_{amount}'
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=btn_text('reject_payment'),
            callback_data=f'reject_sbp_{user_id}_{amount}'
        )
    )
    return keyboard.as_markup()
