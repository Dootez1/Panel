import html
import math
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states import (
    RequestPayoutState, 
    ProfitOTCState, 
    ProfitOfferState, 
    ProfitGuarantorState
)
from config import ADMIN_CHAT_ID
from database import (
    get_user, 
    get_kassa,
    create_profit_report,
    create_payout_request,
    get_user_recent_activity,
    is_user_banned,
    get_project_links,
    has_pending_payout,
    log_activity
)
from keyboards import (
    back_to_panel_keyboard, 
    cancel_fsm_keyboard,
    work_type_keyboard,
    confirm_profit_keyboard,
    profit_moderation_keyboard,
    payout_moderation_keyboard,
    profile_keyboard
)
from utils import show_worker_panel, safe_delete_message, clean_render

router = Router()

@router.callback_query(F.data == "cancel_action")
async def cb_cancel_action(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await call.answer("❌ Действие отменено.")
    await show_worker_panel(bot, call.from_user.id, call=call)

# ----------------- Выбор способа ворка для заявки на профит -----------------

@router.callback_query(F.data == "panel_submit_profit")
async def cb_select_work_type(call: CallbackQuery, state: FSMContext, bot: Bot):
    if await is_user_banned(call.from_user.id):
        await call.answer("⛔️ Ваш аккаунт заблокирован!", show_alert=True)
        return

    user = await get_user(call.from_user.id)
    if not user or user["status"] != "approved":
        await call.answer("⛔️ Доступно только одобренным воркерам команды!", show_alert=True)
        return

    await state.clear()
    text = (
        "💼 <b>Подача заявки на профит — Haster TEAM</b>\n\n"
        "Выберите способ, через который вы провели ворк:"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=work_type_keyboard(), call=call)
    await call.answer()

# ================= 1. OTC-бот =================

@router.callback_query(F.data == "work_type:otc")
async def cb_work_otc(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await state.set_state(ProfitOTCState.deal_code)
    await state.update_data(work_type="OTC-бот")

    text = (
        "🤖 <b>Вы выбрали способ ворка через OTC-бот.</b>\n"
        "Заполните заявку для успешного начисления профита:\n\n"
        "<b>1.</b> Укажите код сделки, по которой был получен NFT-подарок:"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=cancel_fsm_keyboard(), call=call)
    await call.answer()

@router.message(ProfitOTCState.deal_code, F.chat.type == "private")
async def step_otc_code(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    code = (message.text or "").strip()
    if not code:
        await clean_render(bot, message.chat.id, "Пожалуйста, укажите корректный код сделки:", reply_markup=cancel_fsm_keyboard())
        return

    await state.update_data(deal_code=code)
    await state.set_state(ProfitOTCState.nft_links)
    text = (
        "<b>2.</b> Укажите ссылку на полученный NFT-подарок\n"
        "<i>(если их несколько — укажите каждую ссылку с новой строки):</i>"
    )
    await clean_render(bot, message.chat.id, text, reply_markup=cancel_fsm_keyboard())

@router.message(ProfitOTCState.nft_links, F.chat.type == "private")
async def step_otc_links(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    links = (message.text or "").strip()
    if not links:
        await clean_render(bot, message.chat.id, "Пожалуйста, укажите ссылку на полученный подарок:", reply_markup=cancel_fsm_keyboard())
        return

    await state.update_data(nft_links=links)
    await state.set_state(ProfitOTCState.screenshot)
    text = "<b>3.</b> Прикрепите скриншот(ы), подтверждающие передачу подарка менеджеру и отображающие код сделки:"
    await clean_render(bot, message.chat.id, text, reply_markup=cancel_fsm_keyboard())

@router.message(ProfitOTCState.screenshot, F.chat.type == "private")
async def step_otc_screenshot(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    photo_id = message.photo[-1].file_id if message.photo else ""
    caption_or_text = message.caption or message.text or "Скриншот прикреплён"
    await state.update_data(photo_id=photo_id, details=caption_or_text)
    await state.set_state(ProfitOTCState.confirm)

    data = await state.get_data()
    summary = (
        "📋 <b>Проверьте вашу заявку на профит:</b>\n\n"
        f"💼 <b>Способ:</b> OTC-бот\n"
        f"🔢 <b>Код сделки:</b> <code>{html.escape(data.get('deal_code', ''))}</code>\n"
        f"🔗 <b>Ссылки на NFT:</b>\n<blockquote>{html.escape(data.get('nft_links', ''))}</blockquote>\n"
        f"📸 <b>Скриншот:</b> {'Прикреплён ✅' if photo_id else 'Текстовое подтверждение'}\n\n"
        "Отправляем заявку на проверку кураторам?"
    )
    await clean_render(bot, message.chat.id, summary, reply_markup=confirm_profit_keyboard())

# ================= 2. Оффер =================

@router.callback_query(F.data == "work_type:offer")
async def cb_work_offer(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await state.set_state(ProfitOfferState.nft_links)
    await state.update_data(work_type="Оффер", deal_code="—")

    text = (
        "🏷 <b>Вы выбрали способ ворка через Оффер.</b>\n"
        "Заполните заявку для успешного начисления профита:\n\n"
        "<b>1.</b> Укажите ссылку на полученный NFT-подарок\n"
        "<i>(если их несколько — укажите каждую ссылку с новой строки):</i>"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=cancel_fsm_keyboard(), call=call)
    await call.answer()

@router.message(ProfitOfferState.nft_links, F.chat.type == "private")
async def step_offer_links(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    links = (message.text or "").strip()
    if not links:
        await clean_render(bot, message.chat.id, "Пожалуйста, укажите ссылку на полученный подарок:", reply_markup=cancel_fsm_keyboard())
        return

    await state.update_data(nft_links=links)
    await state.set_state(ProfitOfferState.screenshot)
    text = "<b>2.</b> Прикрепите скриншот(ы), подтверждающие передачу подарка менеджеру:"
    await clean_render(bot, message.chat.id, text, reply_markup=cancel_fsm_keyboard())

@router.message(ProfitOfferState.screenshot, F.chat.type == "private")
async def step_offer_screenshot(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    photo_id = message.photo[-1].file_id if message.photo else ""
    caption_or_text = message.caption or message.text or "Скриншот прикреплён"
    await state.update_data(photo_id=photo_id, details=caption_or_text)
    await state.set_state(ProfitOfferState.confirm)

    data = await state.get_data()
    summary = (
        "📋 <b>Проверьте вашу заявку на профит:</b>\n\n"
        f"💼 <b>Способ:</b> Оффер\n"
        f"🔗 <b>Ссылки на NFT:</b>\n<blockquote>{html.escape(data.get('nft_links', ''))}</blockquote>\n"
        f"📸 <b>Скриншот:</b> {'Прикреплён ✅' if photo_id else 'Текстовое подтверждение'}\n\n"
        "Отправляем заявку на проверку кураторам?"
    )
    await clean_render(bot, message.chat.id, summary, reply_markup=confirm_profit_keyboard())

# ================= 3. Гарант =================

@router.callback_query(F.data == "work_type:guarantor")
async def cb_work_guarantor(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await state.set_state(ProfitGuarantorState.nft_links)
    await state.update_data(work_type="Гарант", deal_code="—")

    text = (
        "🛡 <b>Вы выбрали способ ворка через Гаранта.</b>\n"
        "Заполните заявку для успешного начисления профита:\n\n"
        "<b>1.</b> Укажите ссылку на полученный NFT-подарок\n"
        "<i>(если их несколько — укажите каждую ссылку с новой строки):</i>"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=cancel_fsm_keyboard(), call=call)
    await call.answer()

@router.message(ProfitGuarantorState.nft_links, F.chat.type == "private")
async def step_guarantor_links(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    links = (message.text or "").strip()
    if not links:
        await clean_render(bot, message.chat.id, "Пожалуйста, укажите ссылку на полученный подарок:", reply_markup=cancel_fsm_keyboard())
        return

    await state.update_data(nft_links=links)
    await state.set_state(ProfitGuarantorState.screenshot)
    text = "<b>2.</b> Прикрепите скриншот(ы), подтверждающие передачу подарка гаранту:"
    await clean_render(bot, message.chat.id, text, reply_markup=cancel_fsm_keyboard())

@router.message(ProfitGuarantorState.screenshot, F.chat.type == "private")
async def step_guarantor_screenshot(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    photo_id = message.photo[-1].file_id if message.photo else ""
    caption_or_text = message.caption or message.text or "Скриншот прикреплён"
    await state.update_data(photo_id=photo_id, details=caption_or_text)
    await state.set_state(ProfitGuarantorState.confirm)

    data = await state.get_data()
    summary = (
        "📋 <b>Проверьте вашу заявку на профит:</b>\n\n"
        f"💼 <b>Способ:</b> Гарант\n"
        f"🔗 <b>Ссылки на NFT:</b>\n<blockquote>{html.escape(data.get('nft_links', ''))}</blockquote>\n"
        f"📸 <b>Скриншот:</b> {'Прикреплён ✅' if photo_id else 'Текстовое подтверждение'}\n\n"
        "Отправляем заявку на проверку кураторам?"
    )
    await clean_render(bot, message.chat.id, summary, reply_markup=confirm_profit_keyboard())

# ================= Отправка подтверждённой заявки на профит =================

@router.callback_query(F.data == "send_profit_report")
async def cb_send_profit_report(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = call.from_user.id
    user_name = call.from_user.full_name or call.from_user.first_name
    username = f"@{call.from_user.username}" if call.from_user.username else "нет username"

    work_type = data.get("work_type", "Оффер")
    deal_code = data.get("deal_code", "—")
    nft_links = data.get("nft_links", "—")
    photo_id = data.get("photo_id", "")

    report_id = await create_profit_report(
        user_id=user_id,
        work_type=work_type,
        deal_code=deal_code,
        nft_links=nft_links,
        photo_id=photo_id
    )
    username_str = f"@{call.from_user.username}" if call.from_user.username else str(user_id)
    await log_activity("profit_new", username_str, f"Отчёт на профит (#{report_id}): {work_type}, код: {deal_code}")
    await state.clear()

    text = (
        "⏳ <b>Ваша заявка на профит успешно отправлена кураторам!</b>\n\n"
        f"💼 <b>Способ ворка:</b> {work_type}\n\n"
        "После проверки администрацией сумма профита автоматически поступит на ваш баланс и в статистику."
    )
    await clean_render(bot, user_id, text, reply_markup=back_to_panel_keyboard(), call=call)
    await call.answer()

    if ADMIN_CHAT_ID:
        try:
            admin_caption = (
                f"💰 <b>Новый отчёт по профиту #{report_id}!</b>\n\n"
                f"👤 <b>Воркер:</b> {html.escape(user_name)} ({username})\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
                f"💼 <b>Способ ворка:</b> {html.escape(work_type)}\n"
                f"🏷 <b>Код сделки:</b> <code>{html.escape(deal_code)}</code>\n"
                f"🔗 <b>NFT ссылка:</b> {html.escape(nft_links)}"
            )
            if photo_id:
                await bot.send_photo(
                    chat_id=ADMIN_CHAT_ID,
                    photo=photo_id,
                    caption=admin_caption,
                    reply_markup=profit_moderation_keyboard(report_id),
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=admin_caption,
                    reply_markup=profit_moderation_keyboard(report_id),
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Error sending profit report to admin chat: {e}")

# ================= Подача заявки на выплату =================

@router.callback_query(F.data == "panel_payout")
async def cb_start_payout(call: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = call.from_user.id
    if await is_user_banned(user_id):
        await call.answer("⛔️ Ваш аккаунт заблокирован!", show_alert=True)
        return

    if await has_pending_payout(user_id):
        await call.answer(
            "⏳ У вас уже есть активная заявка на вывод средств!\nПожалуйста, дождитесь её проведения куратором перед созданием новой.",
            show_alert=True
        )
        return

    user = await get_user(user_id)
    if not user or user["status"] != "approved":
        await call.answer("⛔️ Доступно только одобренным воркерам команды!", show_alert=True)
        return

    total_earned = float(user["total_earned"] or 0.0) if user else 0.0
    total_payouts = float(user["total_payouts"] or 0.0) if user else 0.0
    balance = max(0.0, round(total_earned - total_payouts, 2))

    if balance < 1:
        await call.answer(
            f"❌ Минимальная сумма для выплаты — 1 GRAM. Ваш баланс: {balance:g} GRAM.",
            show_alert=True
        )
        return

    await state.set_state(RequestPayoutState.amount)
    await state.update_data(max_balance=balance)

    text = (
        "💳 <b>Заполните заявку в специальной форме для успешной выплаты:</b>\n\n"
        f"💰 <b>Доступно на вашем балансе:</b> <b>{balance:g} GRAM</b>\n\n"
        "<b>1.</b> Введите сумму в <b>GRAM</b>, которую вы хотите вывести <i>(минимум 1 GRAM)</i>:"
    )
    await clean_render(bot, user_id, text, reply_markup=cancel_fsm_keyboard(), call=call)
    await call.answer()

@router.message(RequestPayoutState.amount, F.chat.type == "private")
async def step_payout_amount(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    text = (message.text or "").strip().replace(",", ".")
    data = await state.get_data()
    max_balance = data.get("max_balance", 0.0)

    try:
        val = float(text)
        if math.isnan(val) or math.isinf(val) or val < 1.0:
            raise ValueError()
    except (ValueError, TypeError):
        msg_text = "⚠️ Минимальная сумма к выводу составляет 1 GRAM. Введите число (например: <code>10</code>):"
        await clean_render(bot, message.chat.id, msg_text, reply_markup=cancel_fsm_keyboard())
        return

    if val > max_balance:
        msg_text = (
            f"⚠️ Введённая сумма превышает ваш баланс (<b>{max_balance:g} GRAM</b>).\n"
            "Пожалуйста, введите сумму в пределах вашего баланса:"
        )
        await clean_render(bot, message.chat.id, msg_text, reply_markup=cancel_fsm_keyboard())
        return

    await state.update_data(amount=val)
    await state.set_state(RequestPayoutState.wallet)
    prompt = (
        f"Сумма к выводу: <b>{val:g} GRAM</b>.\n\n"
        "<b>2.</b> Укажите адрес своего криптокошелька в сети <b>TON</b>:"
    )
    await clean_render(bot, message.chat.id, prompt, reply_markup=cancel_fsm_keyboard())

@router.message(RequestPayoutState.wallet, F.chat.type == "private")
async def step_payout_wallet(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)
    wallet = (message.text or "").strip()
    if not wallet or len(wallet) < 10:
        await clean_render(bot, message.chat.id, "Пожалуйста, отправьте корректный адрес криптокошелька в сети TON:", reply_markup=cancel_fsm_keyboard())
        return

    data = await state.get_data()
    amount = data.get("amount", 0.0)
    user_id = message.from_user.id
    user_name = message.from_user.full_name or message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "нет username"

    # Atomic re-checks against double payout and balance manipulation
    if await has_pending_payout(user_id):
        await state.clear()
        await clean_render(bot, message.chat.id, "⏳ <b>У вас уже есть активная заявка на вывод средств!</b>\nДождитесь её проведения.", reply_markup=back_to_panel_keyboard())
        return

    user = await get_user(user_id)
    if not user or user["status"] != "approved":
        await state.clear()
        await clean_render(bot, message.chat.id, "⛔️ <b>Доступ запрещён.</b>", reply_markup=back_to_panel_keyboard())
        return

    cur_balance = max(0.0, round(float(user["total_earned"] or 0.0) - float(user["total_payouts"] or 0.0), 2))
    if amount > cur_balance or amount < 1.0 or math.isnan(amount) or math.isinf(amount):
        await state.clear()
        await clean_render(
            bot, 
            message.chat.id, 
            f"⚠️ Ошибка: сумма вывода ({amount:g} GRAM) превышает ваш текущий баланс ({cur_balance:g} GRAM). Заявка отменена.", 
            reply_markup=back_to_panel_keyboard()
        )
        return

    request_id = await create_payout_request(user_id, amount, wallet)
    await log_activity("payout_new", username, f"Заявка на вывод #{request_id}: {amount} GRAM на {wallet}")
    await state.clear()

    text = (
        "⏳ <b>Заявка на выплату успешно сформирована и отправлена кураторам!</b>\n\n"
        f"💸 <b>Сумма:</b> <b>{amount:g} GRAM</b>\n"
        f"👛 <b>Кошелёк TON:</b> <code>{html.escape(wallet)}</code>\n\n"
        "Ожидайте проведения перевода администратором."
    )
    await clean_render(bot, user_id, text, reply_markup=back_to_panel_keyboard())

    if ADMIN_CHAT_ID:
        try:
            admin_msg = (
                f"💳 <b>Новая заявка на выплату #{request_id}!</b>\n\n"
                f"👤 <b>Воркер:</b> {html.escape(user_name)} ({username})\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
                f"💰 <b>Сумма к выводу:</b> <b>{amount:g} GRAM</b>\n"
                f"👛 <b>Кошелёк TON:</b> <code>{html.escape(wallet)}</code>"
            )
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_msg,
                reply_markup=payout_moderation_keyboard(request_id),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending payout to admin chat: {e}")

# ================= Статус заявок =================

@router.callback_query(F.data == "panel_status")
async def cb_panel_status(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    profits, payouts = await get_user_recent_activity(user_id)

    status_icons = {
        "pending": "⏳ На проверке",
        "approved": "✅ Одобрено",
        "rejected": "❌ Отклонено"
    }

    text = "📰 <b>Статус ваших недавних заявок:</b>\n\n"

    text += "💰 <b>Заявки на профит:</b>\n"
    if profits:
        for p in profits:
            st = status_icons.get(p["status"], p["status"])
            wtype = p["work_type"] if "work_type" in p.keys() and p["work_type"] else "Профит"
            amount_str = f"+{p['amount']:g} GRAM" if p['amount'] and p['amount'] > 0 else "На оценке"
            text += f"• {p['created_at']} — <b>{amount_str}</b> [{wtype}] ({st})\n"
    else:
        text += "<i>Заявок на профиты пока нет</i>\n"

    text += "\n💳 <b>Заявки на выплату:</b>\n"
    if payouts:
        for pay in payouts:
            st = status_icons.get(pay["status"], pay["status"])
            text += f"• {pay['created_at']} — <b>{pay['amount']:g} GRAM</b> ({st})\n"
    else:
        text += "<i>Заявок на выплату пока не было.</i>\n"

    await clean_render(bot, user_id, text, reply_markup=back_to_panel_keyboard(), call=call)
    await call.answer()

# ================= Профиль =================

@router.callback_query(F.data == "panel_profile")
async def cb_panel_profile(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    user = await get_user(user_id)
    kassa = await get_kassa()
    links = await get_project_links()
    
    username = f"@{call.from_user.username}" if call.from_user.username else "не указан"
    reg_date = user["reg_date"] if user and user["reg_date"] else "Не указана"
    profits_count = user["profits_count"] if user else 0
    total_earned = float(user["total_earned"] or 0.0) if user else 0.0
    total_payouts = float(user["total_payouts"] or 0.0) if user else 0.0
    balance = max(0.0, round(total_earned - total_payouts, 2))

    text = (
        "👤 <b>Профиль воркера — Haster TEAM</b>\n\n"
        f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>\n"
        f"🏷 <b>Юзернейм:</b> {username}\n"
        f"📅 <b>Дата регистрации:</b> {reg_date}\n\n"
        f"🔢 <b>Количество твоих профитов:</b> <b>{profits_count}</b>\n"
        f"💸 <b>Всего заработано:</b> <b>{total_earned:g} GRAM</b>\n"
        f"💳 <b>Выплачено за всё время:</b> <b>{total_payouts:g} GRAM</b>\n"
        f"💰 <b>Доступно к выводу (баланс):</b> <b>{balance:g} GRAM</b>\n\n"
        f"🏦 <b>Общая касса команды:</b> <b>{kassa:g} GRAM</b>\n\n"
        "⚡️ <b>Статус:</b> Активный участник команды"
    )
    markup = profile_keyboard(
        chat_url=links["chat_url"],
        reserv_url=links["reserv_url"],
        perehodnik_url=links["perehodnik_url"]
    )
    await clean_render(bot, user_id, text, reply_markup=markup, call=call)
    await call.answer()

@router.callback_query(F.data == "back_to_panel")
async def cb_back_to_panel(call: CallbackQuery, bot: Bot):
    await show_worker_panel(bot, call.from_user.id, call=call)
    await call.answer()
