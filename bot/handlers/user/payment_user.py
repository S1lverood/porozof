import logging
import re

from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram.utils.formatting import Text

from bot.keyboards.reply.user_reply import back_menu_balance, balance_menu
from bot.misc.Payment.CryptoBot import CryptoBot
from bot.misc.Payment.Cryptomus import Cryptomus
from bot.misc.Payment.KassaSmart import KassaSmart
from bot.misc.Payment.Lava import Lava
from bot.misc.Payment.Stars import Stars, stars_router
from bot.misc.Payment.YooMoney import YooMoney
from bot.misc.Payment.SBP import SBP
from bot.misc.language import Localization, get_lang
from bot.misc.util import CONFIG
from bot.misc.callbackData import (
    ChoosingMonths,
    ChoosingPyment,
    ChoosingPrise,
)

from bot.keyboards.inline.user_inline import price_menu

from bot.database.methods.update import (
    add_time_person,
    reduce_balance_person
)
from bot.database.methods.get import get_person

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

callback_user = Router()
callback_user.include_router(stars_router)
CONVERT_PANY_RUBLS = 100

types_of_payments = {
    'KassaSmart': KassaSmart,
    'YooMoney': YooMoney,
    'Lava': Lava,
    'Cryptomus': Cryptomus,
    'CryptoBot': CryptoBot,
    'SBP_payment': SBP,
    'Stars': Stars
}


class Email(StatesGroup):
    input_email = State()


@callback_user.callback_query(ChoosingMonths.filter())
async def my_callback_foo(
        call: CallbackQuery,
        callback_data: ChoosingMonths,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    try:
        if await check_balance(callback_data.price, call.from_user.id):
            if await add_time_person(
                    call.from_user.id,
                    callback_data.month_count * CONFIG.COUNT_SECOND_MOTH):
                await reduce_balance_person(
                    callback_data.price,
                    call.from_user.id
                )
                await call.message.answer(
                    _('success_payment_exist', lang)
                    .format(month_count=callback_data.month_count)
                )
                await call.message.answer(_('update_data_connect_vpn', lang))
                text = Text(
                    _(
                        'success_payment_exist_admin',
                        await get_lang(CONFIG.admin_tg_id)
                    ).format(
                        full_name=call.from_user.full_name,
                        user_id=call.from_user.id,
                        count_m=callback_data.month_count
                    )
                )
                await call.message.bot.send_message(
                    CONFIG.admin_tg_id,
                    **text.as_kwargs(),
                )
            else:
                await call.message.answer(_('error_send_admin', lang))
        else:
            await call.message.answer(_('yo_have_enough_funds_balance', lang))
    except Exception as e:
        log.error(e, 'error payment month')
    await call.answer()


async def check_balance(price, telegram_id):
    person = await get_person(telegram_id)
    if person.balance >= price:
        return True
    return False


@callback_user.callback_query(ChoosingPyment.filter())
async def callback_price(
        call: CallbackQuery,
        callback_data: ChoosingPyment,
        state: FSMContext
):
    lang = await get_lang(call.from_user.id, state)
    await call.message.edit_text(
        _('choosing_amount_menu', lang),
        call.inline_message_id,
        reply_markup=await price_menu(CONFIG, callback_data.payment))
    await call.answer()


@callback_user.callback_query(ChoosingPrise.filter(F.payment == 'SBP_payment'))
async def callback_payment_sbp(
        call: CallbackQuery,
        callback_data: ChoosingPrise,
        state: FSMContext
):
    try:
        lang = await get_lang(call.from_user.id, state)
        from bot.handlers.user.main import SBP_Confirm
        
        # Set state and save amount
        await state.set_state(SBP_Confirm.photo)
        await state.update_data(amount=callback_data.price)
        
        # Create payment
        payment = SBP(CONFIG, call.message, call.from_user.id, callback_data.price)
        await payment.to_pay()
        
        log.info(f"SBP payment initialized for user {call.from_user.id} with amount {callback_data.price}")
        
    except Exception as e:
        log.error(f"Error in SBP payment callback: {e}", exc_info=True)
        await call.message.answer(_('error_payment', lang))


@callback_user.callback_query(ChoosingPrise.filter(F.payment == 'KassaSmart'))
async def callback_payment(
        call: CallbackQuery,
        state: FSMContext,
        callback_data: ChoosingPrise
):
    lang = await get_lang(call.from_user.id, state)
    await call.message.answer(
        _('input_email_check', lang),
        reply_markup=await back_menu_balance(lang)
    )
    await state.update_data(price=callback_data.price)
    await state.set_state(Email.input_email)
    await call.answer()


@callback_user.message(Email.input_email)
async def input_email(message: Message, state: FSMContext):
    lang = await get_lang(message.from_user.id, state)
    email = message.text.strip()
    data = await state.get_data()
    price = data['price']
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    if email_pattern.match(email):
        person = await get_person(message.from_user.id)
        await message.answer(
            _('think_email_check', lang),
            reply_markup=await balance_menu(person, lang)
        )
        await state.clear()
        await pay_payment(
            'KassaSmart',
            message,
            message.from_user,
            price,
            email
        )
    else:
        await message.answer(_('error_email_input', lang))


@callback_user.callback_query(ChoosingPrise.filter())
async def callback_payment(
        call: CallbackQuery,
        callback_data: ChoosingPrise,
        state: FSMContext
):
    await state.clear()
    if types_of_payments.get(callback_data.payment):
        await pay_payment(
            callback_data.payment,
            call.message,
            call.from_user,
            callback_data.price,
            call.data
        )
    else:
        raise NameError(callback_data.payment)


async def pay_payment(payment, message, from_user, price, data, ):
    payment = types_of_payments[payment](
        CONFIG,
        message,
        from_user.id,
        price,
        data
    )
    await payment.to_pay()
