from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.methods.update import add_balance_person
from bot.misc.texts import _
from bot.misc.states import get_lang

admin_payment_router = Router()


@admin_payment_router.callback_query(F.data.startswith('confirm_sbp_'))
async def confirm_sbp_payment(call: CallbackQuery) -> None:
    """Handle admin confirmation of SBP payment"""
    user_id, amount = call.data.split('_')[2:]
    user_id = int(user_id)
    amount = float(amount)
    
    # Add balance to user
    await add_balance_person(amount, user_id)
    
    # Notify admin
    admin_lang = await get_lang(call.from_user.id)
    await call.message.edit_caption(
        caption=_('sbp_payment_confirmed_admin', admin_lang).format(
            user_id=user_id,
            amount=amount
        ),
        reply_markup=None
    )
    
    # Notify user
    user_lang = await get_lang(user_id)
    await call.bot.send_message(
        chat_id=user_id,
        text=_('sbp_payment_confirmed_user', user_lang).format(
            amount=amount
        )
    )


@admin_payment_router.callback_query(F.data.startswith('reject_sbp_'))
async def reject_sbp_payment(call: CallbackQuery) -> None:
    """Handle admin rejection of SBP payment"""
    user_id, amount = call.data.split('_')[2:]
    user_id = int(user_id)
    
    # Notify admin
    admin_lang = await get_lang(call.from_user.id)
    await call.message.edit_caption(
        caption=_('sbp_payment_rejected_admin', admin_lang).format(
            user_id=user_id,
            amount=amount
        ),
        reply_markup=None
    )
    
    # Notify user
    user_lang = await get_lang(user_id)
    await call.bot.send_message(
        chat_id=user_id,
        text=_('sbp_payment_rejected_user', user_lang)
    )
