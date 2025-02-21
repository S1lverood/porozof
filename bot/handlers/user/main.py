import json
import logging
import os
import subprocess
import time
from datetime import datetime

import requests
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.payload import decode_payload

from bot.misc.util import CONFIG
from .referral_user import referral_router
from .payment_user import callback_user

from bot.database.methods.get import (
    get_person,
    get_server,
    get_free_servers,
    get_count_users,
    get_all_server,
    get_server_id
)
from bot.database.methods.insert import add_new_person
from bot.database.methods.update import (
    person_delete_server,
    add_user_in_server,
    server_space_update, add_time_person, update_lang
)
from bot.keyboards.inline.user_inline import (
    replenishment,
    renew,
    instruction_manual,
    choose_server,
    choose_server_wg,
    choosing_lang, choose_type_vpn
)
from bot.keyboards.inline.admin_inline import (
confirm_sbp
)
from bot.keyboards.reply.user_reply import (
    user_menu,
    subscription_menu,
    balance_menu
)
from bot.misc.VPN.ServerManager import ServerManager
from bot.misc.VPN.WG import WireGuard
from bot.misc.language import Localization, get_lang
from bot.misc.callbackData import ChooseServer, ChoosingLang, ChooseTypeVpn,ChooseServerWG

log = logging.getLogger(__name__)

_ = Localization.text
btn_text = Localization.get_reply_button

user_router = Router()
user_router.include_routers(callback_user, referral_router)


class SBP_Confirm(StatesGroup):
    photo = State()

@user_router.message(Command("start"))
async def command(m: Message, state: FSMContext, command: Command = None):
    if m.from_user.is_bot:
        return
    lang = await get_lang(m.from_user.id, state)
    await state.clear()
    if not await get_person(m.from_user.id):
        try:
            user_name = f'@{str(m.from_user.username)}'
        except Exception as e:
            log.error(e)
            user_name = str(m.from_user.username)
        reference = decode_payload(command.args) if command.args else None
        if reference is not None:
            if reference.isdigit():
                reference = int(reference)
            else:
                reference = None
            if reference != str(m.from_user.id):
                await add_new_person(
                    m.from_user,
                    user_name,
                    CONFIG.trial_period,
                    reference
                )
                users_count = await get_count_users()
                await m.answer_photo(
                    photo=FSInputFile('bot/img/hello_bot.jpg'),
                    caption=_('hello_message', lang).format(name_bot=CONFIG.name,users_count=users_count)
                )
                if CONFIG.trial_period != 0:
                    await m.answer(_('trial_message', lang))
            else:
                await m.answer(_('referral_error', lang))
                reference = None
        else:
            await add_new_person(
                m.from_user,
                user_name,
                CONFIG.trial_period,
                reference
            )
            users_count = await get_count_users()
            await m.answer_photo(
                photo=FSInputFile('bot/img/hello_bot.jpg'),
                caption=_('hello_message', lang).format(name_bot=CONFIG.name,users_count=users_count)
            )
            if CONFIG.trial_period != 0:
                await m.answer(_('trial_message', lang))
    person = await get_person(m.from_user.id)
    await m.answer_photo(
        photo=FSInputFile('bot/img/main_menu.jpg'),
        caption=_('main_message', lang),
        reply_markup=await user_menu(person, lang)
    )


async def give_bonus_invitee(m, reference, lang):
    if reference is None:
        return
    await m.bot.send_message(reference, _('referral_new_user', lang))


@user_router.message(F.text.in_(btn_text('vpn_connect_btn')))
async def choose_server_user(message: Message, state: FSMContext) -> None:
    lang = await get_lang(message.from_user.id, state)
    await message.answer_photo(
        photo=FSInputFile('bot/img/protokol.jpg'),
        caption=_('choosing_connect_type', lang),
        reply_markup=await choose_type_vpn()
    )


@user_router.callback_query(F.data == 'back_type_vpn')
async def call_choose_server(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    await call.message.delete()
    await call.message.answer_photo(
        photo=FSInputFile('bot/img/protokol.jpg'),
        caption=_('choosing_connect_type', lang),
        reply_markup=await choose_type_vpn()
    )

@user_router.callback_query(F.data.startswith('checkSBP_'))
async def check_pay_sbp(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    await call.message.delete()
    await call.message.answer(
        text=_('sbp_confirm_text', lang)
    )
    await state.set_state(SBP_Confirm.photo)
    await state.update_data(amount=call.data.split("_")[1])

@user_router.callback_query(F.data == 'closeSBP')
async def close_pay_sbp(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(call.from_user.id, state)
    await call.message.delete()
    # await call.message.answer_photo(
    #     photo=FSInputFile('bot/img/locations.jpg'),
    #     caption=_('choosing_connect_type', lang),
    #     reply_markup=await choose_type_vpn()
    # )


@user_router.callback_query(ChooseTypeVpn.filter())
async def choose_server_free(
        call: CallbackQuery,
        callback_data: ChooseTypeVpn,
        state: FSMContext
) -> None:
    try:
        lang = await get_lang(call.from_user.id, state)
        user = await get_person(call.from_user.id)
        
        # Add subscription check here
        if user.banned or user.subscription <= int(time.time()):
            await call.message.answer(_('ended_sub_message', lang))
            await call.answer()
            return
            
        if callback_data.type_vpn == 3:  # WireGuard
            wg = WireGuard(call.from_user.id)
            wg_servers = await get_free_servers(user.group, 99999)
            wg_dict = {}
            for i in wg_servers:
                wg_dict[i.name.split("_")[1]] = {"space": i.space, 'id': i.id}
            wg_all_servers = await get_all_server()
            wg_all_dict = {}
            for i in wg_all_servers:
                if i.name.startswith("WG_"):
                    wg_all_dict[i.name.split("_")[1]] = {"space": i.space, 'id': i.id}

            await call.message.answer_photo(
                photo=FSInputFile('bot/img/locations.jpg'),
                caption=_('choosing_connect_location', lang),
                reply_markup=await choose_server_wg(
                    wg.servers, wg_dict, wg_all_dict,
                    lang, user.server
                )
            )
            await call.answer()
            await call.message.delete()
        else:
            try:
                all_active_server = await get_free_servers(
                    user.group, callback_data.type_vpn
                )
                if not all_active_server:
                    raise FileNotFoundError("No active servers found")
                    
                await call.message.delete()
                await call.message.answer_photo(
                    photo=FSInputFile('bot/img/locations.jpg'),
                    caption=_('choosing_connect_location', lang),
                    reply_markup=await choose_server(
                        all_active_server,
                        user.server,
                        lang
                    )
                )
            except FileNotFoundError as e:
                log.info('Error get free servers -- OK')
                await call.message.answer(_('not_server', lang))
                await call.answer()
                return
    except Exception as e:
        log.error(f'Error in choose_server_free: {e}')
        await call.message.answer(_('general_error', lang))
        await call.answer()

@user_router.callback_query(ChooseServer.filter())
async def connect_vpn(
        call: CallbackQuery,
        callback_data: ChooseServer,
        state: FSMContext
) -> None:
    try:
        lang = await get_lang(call.from_user.id, state)
        choosing_server_id = callback_data.id_server
        client = await get_person(call.from_user.id)
        
        if client.banned:
            await call.message.answer(_('ended_sub_message', lang))
            await call.answer()
            return
            
        old_m = await call.message.answer(_('connect_continue', lang))
        
        if client.server == choosing_server_id:
            try:
                server = await get_server_id(client.server)
                server_manager = ServerManager(server)
                await server_manager.login()
                config = await server_manager.get_key(
                    name=call.from_user.id,
                    name_key=CONFIG.name
                )
                if config is None:
                    raise Exception('Server Not Connected')
            except Exception as e:
                log.error(f'Error getting existing server config: {e}')
                await server_not_found(call, e, lang)
                await call.answer()
                return
        else:
            try:
                server = await get_server_id(choosing_server_id)
                if client.server is not None:
                    await delete_key_old_server(client.server, call.from_user.id)
            except Exception as e:
                log.error(f'Error deleting old key: {e}')
                await server_not_found(
                    call,
                    f'Error delete old key{e}',
                    lang
                )
                return
                
            try:
                server_manager = ServerManager(server)
                await server_manager.login()
                
                # Проверяем место на сервере
                server_parameters = await server_manager.get_all_user()
                if len(server_parameters) >= CONFIG.max_people_server:
                    await call.message.answer(_('server_full', lang))
                    await call.answer()
                    return
                
                if await server_manager.add_client(call.from_user.id) is None:
                    raise Exception('Failed to add client')
                    
                config = await server_manager.get_key(
                    call.from_user.id,
                    name_key=CONFIG.name
                )
                
                if await add_user_in_server(call.from_user.id, server):
                    raise Exception(_('error_add_server_client', lang))
                    
                await server_space_update(
                    server.name,
                    len(server_parameters) + 1
                )
                
            except Exception as e:
                log.error(f'Error setting up new connection: {e}')
                await person_delete_server(call.from_user.id)
                await server_not_found(call, e, lang)
                await call.answer()
                return
                
        try:
            await call.message.delete()
            await call.message.bot.delete_message(
                call.from_user.id,
                old_m.message_id
            )
        except Exception as e:
            log.info(f'Could not delete message: {e}')
            
        if server.type_vpn == 0:
            connect_message = _('how_to_connect_info_outline', lang)
            await call.message.answer_photo(
                photo=FSInputFile('bot/img/outline.jpg'),
                caption=connect_message,
                reply_markup=await instruction_manual(server.type_vpn, lang)
            )
        elif server.type_vpn in [1, 2]:
            connect_message = _('how_to_connect_info_vless', lang)
            photo_file = 'bot/img/vless.jpg' if server.type_vpn == 1 else 'bot/img/shadow_socks.jpg'
            await call.message.answer_photo(
                photo=FSInputFile(photo_file),
                caption=connect_message,
                reply_markup=await instruction_manual(server.type_vpn, lang)
            )
        else:
            raise ValueError(f'Unsupported VPN type: {server.type_vpn}')
            
        await call.message.answer(f'<code>{config}</code>')
        await call.message.answer(
            _('config_user', lang)
            .format(name_vpn=ServerManager.VPN_TYPES.get(server.type_vpn).NAME_VPN)
        )
        await call.answer()
        
    except Exception as e:
        log.error(f'Unexpected error in connect_vpn: {e}')
        await call.message.answer(_('general_error', lang))
        await call.answer()

@user_router.callback_query(ChooseServerWG.filter())
async def connect_vpn_wg(
        call: CallbackQuery,
        callback_data: ChooseServerWG,
        state: FSMContext
) -> None:
    try:
        lang = await get_lang(call.from_user.id, state)
        choosing_server_id = callback_data.id_server
        
        wg_server = await get_server("WG_" + str(choosing_server_id))
        if not wg_server:
            await call.answer(_('server_not_found', lang), show_alert=True)
            return
            
        if wg_server.space >= CONFIG.max_people_server_wg:
            await call.answer(_('server_full', lang), show_alert=True)
            return

        client = await get_person(call.from_user.id)
        if not client:
            await call.answer(_('user_not_found', lang), show_alert=True)
            return
            
        if client.banned:
            wg = WireGuard(call.from_user.id, choosing_server_id)
            wg.delete_user()
            await call.message.answer(_('ended_sub_message', lang))
            await call.answer()
            return
            
        if client.subscription <= int(time.time()):
            await call.answer(_('subscription_expired', lang), show_alert=True)
            return
            
        old_m = await call.message.answer(_('connect_continue', lang))
        wg = WireGuard(call.from_user.id, choosing_server_id)
        
        try:
            if await add_user_in_server(call.from_user.id, wg_server):
                raise Exception(_('error_add_server_client', lang))
                
            file = await wg.add_user()
            if not file:
                raise Exception('Failed to create WireGuard configuration')

            connect_message = _('how_to_connect_info_wg', lang)
            await call.message.answer_photo(
                photo=FSInputFile('bot/img/wireguard.jpg'),
                caption=connect_message,
                reply_markup=await instruction_manual(3, lang)
            )
            
            await call.message.answer_document(
                document=FSInputFile(
                    path=file,
                    filename=f"PorozoffVPN-{choosing_server_id}.conf"
                )
            )
            
            await call.message.answer(
                _('config_user', lang)
                .format(name_vpn="WireGuard")
            )
            
            # Обновляем количество пользователей на сервере
            await server_space_update(
                wg_server.name,
                wg_server.space + 1
            )
            
        except Exception as e:
            log.error(f'Error in WireGuard setup: {e}')
            wg.delete_user()
            await person_delete_server(call.from_user.id)
            await call.message.answer(_('config_creation_error', lang))
            return
            
        await call.answer()
        try:
            await call.message.delete()
            if old_m:
                await old_m.delete()
        except Exception as e:
            log.info(f'Could not delete messages: {e}')
            
    except Exception as e:
        log.error(f'Unexpected error in connect_vpn_wg: {e}')
        await call.message.answer(_('general_error', lang))
        await call.answer()

@user_router.message(
    (F.text.in_(btn_text('subscription_btn')))
    | (F.text.in_(btn_text('back_subscription_menu_btn')))
)
async def info_subscription(m: Message, state: FSMContext) -> None:
    lang = await get_lang(m.from_user.id, state)
    await m.answer(
        _('inform_subscription', lang),
        reply_markup=await subscription_menu(lang)
    )


@user_router.message(
    (F.text.in_(btn_text('balanced_btn')))
    | (F.text.in_(btn_text('back_balance_menu_btn')))
)
async def balance(m: Message, state: FSMContext) -> None:
    lang = await get_lang(m.from_user.id, state)
    person = await get_person(m.from_user.id)
    await m.answer_photo(
        photo=FSInputFile('bot/img/balance.jpg'),
        caption=_('balance_message', lang),
        reply_markup=await balance_menu(person, lang)
    )


@user_router.message(F.text.in_(btn_text('replenish_bnt')))
async def deposit_balance(m: Message, state: FSMContext) -> None:
    lang = await get_lang(m.from_user.id, state)
    await m.answer(
        _('method_replenishment', lang),
        reply_markup=await replenishment(CONFIG, lang)
    )


@user_router.message(F.text.in_(btn_text('to_extend_btn')))
async def renew_subscription(m: Message, state: FSMContext) -> None:
    lang = await get_lang(m.from_user.id, state)
    await m.answer_photo(
        photo=FSInputFile('bot/img/pay_subscribe.jpg'),
        caption=_('choosing_month_sub', lang),
        reply_markup=await renew(CONFIG, lang)
    )


@user_router.message(F.text.in_(btn_text('back_general_menu_btn')))
async def back_user_menu(m: Message, state: FSMContext) -> None:
    lang = await get_lang(m.from_user.id, state)
    await state.clear()
    person = await get_person(m.from_user.id)
    await m.answer(
        _('main_message', lang),
        reply_markup=await user_menu(person, lang)
    )


@user_router.message(F.text.in_(btn_text('about_vpn_btn')))
async def info_message_handler(m: Message, state: FSMContext) -> None:
    users_count = await get_count_users()
    await m.answer_photo(
        photo=FSInputFile('bot/img/about.jpg'),
        caption=_('about_message', await get_lang(m.from_user.id, state))
        .format(name_bot=CONFIG.name,users_count=users_count)
    )
    
@user_router.message(F.text.in_(btn_text('user_info_btn')))
async def info_message_prof(m: Message, state: FSMContext) -> None:
    try:
        user = await get_person(m.from_user.id)
        if not user:
            await m.answer("❌ Ваш профиль не найден. Пожалуйста, перезапустите бота командой /start")
            return
            
        lang = await get_lang(m.from_user.id, state)
        current_time = int(time.time())
        
        # Получаем имя сервера
        server_name = "Не выбран"
        if user.server:
            server = await get_server_id(user.server)
            if server:
                server_name = server.name
        
        if current_time < int(user.subscription):
            # Активная подписка
            subscription_time = datetime.fromtimestamp(int(user.subscription) + CONFIG.UTC_time * 3600).strftime('%d.%m.%Y %H:%M')
            days_left = max(0, (int(user.subscription) - current_time) // (24 * 3600))
            template = 'profile_info'
        else:
            # Истекшая подписка
            subscription_time = datetime.fromtimestamp(int(user.subscription) + CONFIG.UTC_time * 3600).strftime('%d.%m.%Y %H:%M')
            template = 'profile_expired_info'
            days_left = 0
        
        await m.answer_photo(
            photo=FSInputFile('bot/img/profil.jpg'),
            caption=_(
                template,
                lang
            ).format(
                full_name=user.fullname if user.fullname else m.from_user.full_name,
                tgid=user.tgid,
                balance=user.balance if hasattr(user, 'balance') else 0,
                referral_balance=user.referral_balance if hasattr(user, 'referral_balance') else 0,
                time_sub=subscription_time,
                days_left=days_left,
                server_name=server_name
            )
        )
    except Exception as e:
        logging.error(f"Error in profile handler: {e}", exc_info=True)
        await m.answer("❌ Произошла ошибка при получении информации профиля. Пожалуйста, попробуйте позже.")

@user_router.message(F.photo)
async def process_sbp_photo(message: Message, state: FSMContext) -> None:
    """Process photo message in SBP confirmation state"""
    current_state = await state.get_state()
    logging.info(f"Photo handler - Current state: {current_state}")
    
    if current_state != "SBP_Confirm:photo":
        logging.info("Photo handler - State mismatch, ignoring")
        return

    try:
        logging.info("Photo handler - Processing payment confirmation")
        lang = await get_lang(message.from_user.id, state)
        data = await state.get_data()
        amount = data.get('amount')
        logging.info(f"Photo handler - Amount from state: {amount}")
        
        # Send confirmation message to user
        await message.answer("💰 Заявка отправлена. Ожидайте подтверждение")
        
        # Forward payment confirmation to admin
        await message.bot.send_photo(
            chat_id=CONFIG.admin_tg_id,
            photo=message.photo[-1].file_id,
            caption=f"💰 Новое пополнение через СБП\n"\
                    f"От: {message.from_user.full_name} ({message.from_user.id})\n"\
                    f"Сумма: {amount}₽",
            reply_markup=await confirm_sbp(message.from_user.id, amount)
        )
        
        logging.info("Photo handler - Successfully processed payment")
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error in SBP payment handler: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже или обратитесь в поддержку.")
        await state.clear()

@user_router.message(SBP_Confirm.photo)
async def process_sbp_text(message: Message, state: FSMContext) -> None:
    """Process text message in SBP confirmation state"""
    try:
        lang = await get_lang(message.from_user.id, state)
        data = await state.get_data()
        amount = data.get('amount')
        
        # Send confirmation message to user
        await message.answer(
            text=_('sbp_confirm_sent_text', lang)
        )
        
        # Forward text payment confirmation to admin
        await message.bot.send_message(
            chat_id=CONFIG.admin_tg_id,
            text=f"💰 Новое пополнение через СБП\n"\
                 f"От: {message.from_user.full_name} ({message.from_user.id})\n"\
                 f"Сумма: {amount}₽\n"\
                 f"Информация об оплате:\n{message.text}",
            reply_markup=await confirm_sbp(message.from_user.id, amount)
        )
        
        # Clear state after processing
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error in SBP payment handler: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже или обратитесь в поддержку.")
        await state.clear()

async def delete_key_old_server(server_id, user_id):
    server = await get_server_id(server_id)
    if server.name.startswith('WG_'):
        wg = WireGuard(user_id)
        wg.delete_user()
    else:
        server_manager = ServerManager(server)
        await server_manager.login()
        await server_manager.delete_client(user_id)


async def server_not_found(call: CallbackQuery, e, lang):
    await call.message.answer(_('server_not_connected', lang))
    log.error(e)
