import html
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from database import register_initial_user, get_user, is_user_banned, set_user_subscription
from keyboards import start_keyboard
from utils import (
    show_worker_panel, 
    safe_delete_message, 
    clean_render, 
    check_user_subscription, 
    send_subscription_prompt
)

router = Router()

@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    # Always delete incoming /start message immediately to keep chat clean
    await safe_delete_message(bot, message.chat.id, message.message_id)

    user_name = message.from_user.full_name or message.from_user.first_name
    username = message.from_user.username

    if await is_user_banned(user_id):
        await clean_render(bot, user_id, "⛔️ <b>Ваш аккаунт заблокирован администрацией команды Haster TEAM.</b>")
        return

    await register_initial_user(user_id, username, user_name)
    user = await get_user(user_id)

    status = user["status"] if user else "new"

    if status == "approved":
        await show_worker_panel(bot, user_id)
    elif status == "pending":
        await clean_render(
            bot,
            user_id,
            "⏳ <b>Ваша заявка уже находится на модерации!</b>\n\n"
            "Пожалуйста, ожидайте решения руководства команды."
        )
    elif status == "rejected":
        await clean_render(
            bot,
            user_id,
            "❌ <b>К сожалению, ваша заявка была отклонена руководством.</b>"
        )
    else:
        text = (
            f"👋 <b>{html.escape(user_name)}</b>, добро пожаловать в <b>Haster TEAM</b>!\n\n"
            "Для вступления в нашу команду тебе нужно заполнить анкету. Начнём?"
        )
        await clean_render(bot, user_id, text, reply_markup=start_keyboard())

@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    # Live check with verification flag
    is_sub, missing = await check_user_subscription(bot, user_id, bypass_cache=True, is_verifying=True)

    if not is_sub:
        try:
            await call.answer("❌ Вы подписаны не на все каналы!", show_alert=True)
        except Exception:
            pass
        await send_subscription_prompt(bot, user_id, call=call)
        return

    # Mark verified in DB
    await set_user_subscription(user_id, True)
    try:
        await call.answer("✅ Подписка успешно подтверждена!", show_alert=False)
    except Exception:
        pass

    user_name = call.from_user.full_name or call.from_user.first_name
    username = call.from_user.username
    await register_initial_user(user_id, username, user_name)

    user = await get_user(user_id)
    status = user["status"] if user else "new"

    if status == "approved":
        await show_worker_panel(bot, user_id, call=call)
    elif status == "pending":
        await clean_render(
            bot,
            user_id,
            "⏳ <b>Ваша заявка уже находится на модерации!</b>\n\n"
            "Пожалуйста, ожидайте решения руководства команды.",
            call=call
        )
    elif status == "rejected":
        await clean_render(
            bot,
            user_id,
            "❌ <b>К сожалению, ваша заявка была отклонена руководством.</b>",
            call=call
        )
    else:
        text = (
            f"👋 <b>{html.escape(user_name)}</b>, добро пожаловать в <b>Haster TEAM</b>!\n\n"
            "Для вступления в нашу команду тебе нужно заполнить анкету. Начнём?"
        )
        await clean_render(bot, user_id, text, reply_markup=start_keyboard(), call=call)
