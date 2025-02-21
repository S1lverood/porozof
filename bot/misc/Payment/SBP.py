import asyncio
import logging
import random
import uuid

from aiohttp import client_exceptions
from yoomoney_async import Quickpay, Client

from bot.keyboards.inline.user_inline import check_payment_sbp
from bot.misc.Payment.payment_systems import PaymentSystem
from bot.misc.language import get_lang, Localization

log = logging.getLogger(__name__)

_ = Localization.text


class SBP(PaymentSystem):
    def __init__(self, config, message, user_id, price, check_id=None):
        super().__init__(message, user_id, price)
        self.SBP_WALLET = config.sbp_wallet

    async def to_pay(self):
        try:
            lang_user = await get_lang(self.user_id)
            await self.message.delete()
            
            log.info(f"Creating SBP payment for user {self.user_id} with amount {self.price}")
            
            # Send payment info
            await self.message.answer(
                _('sbp_payment_text', lang_user).format(amount=self.price,wallet=self.SBP_WALLET),
                reply_markup=await check_payment_sbp(self.price, lang_user)
            )
            log.info(f"Payment message sent to user {self.user_id}")
            
        except Exception as e:
            log.error(f"Error in SBP to_pay: {e}", exc_info=True)
            raise

    def __str__(self):
        return 'Платежная система SBP'
