import time
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from database import is_user_banned, is_admin_user

class SecurityBanMiddleware(BaseMiddleware):
    """
    Globally blocks all interactions from banned users across all handlers and FSM states.
    """
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        if user:
            if await is_user_banned(user.id):
                state = data.get("state")
                if state:
                    await state.clear()
                
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⛔️ Ваш аккаунт заблокирован администрацией команды Haster TEAM.", show_alert=True)
                    except Exception:
                        pass
                elif isinstance(event, Message) and event.chat.type == "private":
                    try:
                        await event.answer("⛔️ <b>Ваш аккаунт заблокирован администрацией команды Haster TEAM.</b>")
                    except Exception:
                        pass
                return

        return await handler(event, data)

class AntiFloodMiddleware(BaseMiddleware):
    """
    Prevents button mashing, rapid race conditions, and message flooding (500ms throttle).
    """
    def __init__(self, rate_limit: float = 0.4):
        self.rate_limit = rate_limit
        self._user_timestamps: dict[int, float] = {}

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        if user:
            now = time.time()
            last = self._user_timestamps.get(user.id, 0.0)
            if now - last < self.rate_limit:
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⏳ Пожалуйста, не нажимайте кнопки так быстро.", show_alert=False)
                    except Exception:
                        pass
                return
            self._user_timestamps[user.id] = now

        return await handler(event, data)

class SubscriptionMiddleware(BaseMiddleware):
    """
    Enforces mandatory channel subscription for private chat interactions.
    If the user has not subscribed to all project channels, halts processing
    and displays the subscription prompt with channel links and verify button.
    """
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        user_id = user.id
        chat = getattr(event, "chat", None)
        if not chat and isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        # Only enforce in private 1-on-1 chats
        if chat and chat.type != "private":
            return await handler(event, data)

        bot: Bot = data.get("bot")
        if not bot:
            return await handler(event, data)

        # Administrators bypass the subscription check so they can manage the bot freely
        if await is_admin_user(user_id, bot):
            return await handler(event, data)

        # Allow the verification callback itself to execute
        if isinstance(event, CallbackQuery) and event.data and event.data == "check_subscription":
            return await handler(event, data)

        from utils import check_user_subscription, send_subscription_prompt, safe_delete_message

        is_sub, _ = await check_user_subscription(bot, user_id)
        if not is_sub:
            if isinstance(event, Message):
                await safe_delete_message(bot, event.chat.id, event.message_id)
                await send_subscription_prompt(bot, user_id)
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer("❌ Вы подписаны не на все каналы!", show_alert=True)
                except Exception:
                    pass
                await send_subscription_prompt(bot, user_id, call=event)
            return

        return await handler(event, data)
