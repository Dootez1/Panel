import html
from datetime import datetime
import html
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states import ApplicationState
from config import ADMIN_CHAT_ID
from database import (
    get_user, 
    set_user_status, 
    save_application,
    is_user_banned,
    log_activity
)
from keyboards import confirm_keyboard, admin_moderation_keyboard
from utils import show_worker_panel, safe_delete_message, clean_render

router = Router()

@router.callback_query(F.data == "start_survey")
async def cb_start_survey(call: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = call.from_user.id
    if await is_user_banned(user_id):
        await call.answer("⛔️ Ваш аккаунт заблокирован!", show_alert=True)
        return
    user = await get_user(user_id)

    if user and user["status"] == "approved":
        await call.answer("Вы уже состоите в команде!", show_alert=True)
        await show_worker_panel(bot, user_id, call=call)
        return

    if user and user["status"] == "pending":
        await call.answer("Ваша заявка уже на рассмотрении!", show_alert=True)
        return

    await state.set_state(ApplicationState.q1_source)
    await clean_render(bot, user_id, "<b>1. Откуда ты узнал о нашей команде?</b>", call=call)
    await call.answer()

@router.message(ApplicationState.q1_source, F.chat.type == "private")
async def step_q1(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    text = (message.text or "").strip()
    if not text:
        await clean_render(bot, message.chat.id, "Пожалуйста, отправьте текстовый ответ:\n\n<b>1. Откуда ты узнал о нашей команде?</b>")
        return

    await state.update_data(q1=text)
    await state.set_state(ApplicationState.q2_time)
    await clean_render(bot, message.chat.id, "<b>2. Сколько времени ты готов уделять нашему проекту?</b>")

@router.message(ApplicationState.q2_time, F.chat.type == "private")
async def step_q2(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    text = (message.text or "").strip()
    if not text:
        await clean_render(bot, message.chat.id, "Пожалуйста, отправьте текстовый ответ:\n\n<b>2. Сколько времени ты готов уделять нашему проекту?</b>")
        return

    await state.update_data(q2=text)
    await state.set_state(ApplicationState.q3_experience)
    await clean_render(
        bot,
        message.chat.id,
        "<b>3. Есть ли у тебя опыт работы в данной сфере и опыт общения с людьми?</b>\n<i>Если его нет — не скрывай этого.</i>"
    )

@router.message(ApplicationState.q3_experience, F.chat.type == "private")
async def step_q3(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    text = (message.text or "").strip()
    if not text:
        await clean_render(bot, message.chat.id, "Пожалуйста, отправьте текстовый ответ на вопрос о вашем опыте:")
        return

    await state.update_data(q3=text)
    await state.set_state(ApplicationState.confirm)

    data = await state.get_data()
    q1 = data.get("q1", "")
    q2 = data.get("q2", "")
    q3 = data.get("q3", "")

    summary_text = (
        "📋 <b>Правильно ли вы заполнили заявку?</b>\n\n"
        "<blockquote>"
        f"<b>1. Откуда узнал:</b>\n{html.escape(q1)}\n\n"
        f"<b>2. Время проекту:</b>\n{html.escape(q2)}\n\n"
        f"<b>3. Опыт:</b>\n{html.escape(q3)}"
        "</blockquote>\n\n"
        "Если всё верно — отправьте на модерацию. Если хотите изменить ответы — начните заново."
    )
    await clean_render(bot, message.chat.id, summary_text, reply_markup=confirm_keyboard())

@router.callback_query(F.data == "restart_app")
async def cb_restart_app(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await state.set_state(ApplicationState.q1_source)
    await clean_render(bot, call.from_user.id, "🔄 <b>Заполняем анкету заново.</b>\n\n1. Откуда ты узнал о нашей команде?", call=call)
    await call.answer()

@router.callback_query(F.data == "submit_app")
async def cb_submit_app(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    q1 = data.get("q1")
    q2 = data.get("q2")
    q3 = data.get("q3")

    if not q1 or not q2 or not q3:
        await call.answer("Анкета не заполнена!", show_alert=True)
        await state.clear()
        return

    user_id = call.from_user.id
    user_name = call.from_user.full_name or call.from_user.first_name
    username = f"@{call.from_user.username}" if call.from_user.username else "нет username"

    await save_application(user_id, q1, q2, q3)
    await set_user_status(user_id, "pending")
    await log_activity("application_new", username, f"Подана новая анкета кандидата {user_name} (ID: {user_id})")
    await state.clear()

    await clean_render(
        bot=bot,
        chat_id=user_id,
        text=(
            "⏳ <b>Ваша заявка успешно отправлена на модерацию!</b>\n\n"
            "Ожидайте решения руководства команды."
        ),
        call=call
    )
    await call.answer()

    if ADMIN_CHAT_ID:
        try:
            admin_msg = (
                f"📝 <b>Новая анкета кандидата!</b>\n\n"
                f"👤 <b>Кандидат:</b> {html.escape(user_name)} ({username})\n"
                f"🆔 <b>ID аккаунта:</b> <code>{user_id}</code>\n\n"
                f"<b>1. Откуда узнали:</b> {html.escape(q1)}\n"
                f"<b>2. Готов уделять:</b> {html.escape(q2)}\n"
                f"<b>3. Опыт работы:</b> {html.escape(q3)}"
            )
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_msg,
                reply_markup=admin_moderation_keyboard(user_id),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending application to admin chat: {e}")
