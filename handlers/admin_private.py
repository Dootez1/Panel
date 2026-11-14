import html
import asyncio
import math
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, 
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from database import (
    get_stats_summary,
    get_user,
    is_admin_user,
    set_user_status,
    set_user_ban_status,
    set_user_balance,
    search_users,
    get_top_workers,
    get_kassa,
    set_kassa,
    add_to_kassa,
    add_user_profit,
    add_user_payout,
    get_pending_applications_list,
    update_application_status,
    get_pending_profit_reports_list,
    approve_profit_report,
    update_profit_report_status,
    get_pending_payout_requests_list,
    get_payout_request,
    approve_payout_and_add_to_kassa,
    update_payout_request_status,
    get_all_broadcast_users,
    get_project_links,
    set_project_link,
    get_admin_ids,
    add_admin_id,
    remove_admin_id
)
from keyboards import (
    admin_main_keyboard,
    admin_moderation_menu_keyboard,
    admin_mod_app_card_keyboard,
    admin_mod_profit_card_keyboard,
    admin_mod_payout_card_keyboard,
    admin_workers_menu_keyboard,
    admin_user_search_results_keyboard,
    admin_user_card_keyboard,
    admin_kassa_menu_keyboard,
    admin_broadcast_menu_keyboard,
    admin_broadcast_confirm_keyboard,
    admin_settings_keyboard,
    admin_cancel_inline_keyboard
)
from states import (
    AdminSearchUserState,
    AdminUserActionState,
    AdminKassaActionState,
    AdminBroadcastState,
    AdminSettingsActionState
)
from utils import show_worker_panel, safe_delete_message, clean_render

router = Router()

# ==================== Helper Functions ====================

async def check_admin_access(user_id: int, bot: Bot) -> bool:
    return await is_admin_user(user_id, bot)

def format_admin_dashboard_text(stats: dict) -> str:
    kassa = stats.get("kassa", 0.0)
    total_users = stats.get("total_users", 0)
    approved = stats.get("approved_workers", 0)
    pending_u = stats.get("pending_users", 0)
    banned = stats.get("banned_users", 0)
    profits_cnt = stats.get("total_profits_count", 0)
    earned_sum = stats.get("total_earned_sum", 0.0)
    payouts_sum = stats.get("total_payouts_sum", 0.0)
    balance_unpaid = stats.get("total_balance_unpaid", 0.0)
    
    p_apps = stats.get("pending_apps_count", 0)
    p_profs = stats.get("pending_profits_count", 0)
    p_pays = stats.get("pending_payouts_count", 0)

    text = (
        "👑 <b>Панель управления командой — Haster TEAM</b>\n\n"
        "📊 <b>Финансы и касса тимы:</b>\n"
        f"🏦 <b>Общая касса:</b> <code>{kassa:g} GRAM</code>\n"
        f"💸 <b>Всего заработано воркерами:</b> <code>{earned_sum:g} GRAM</code>\n"
        f"💳 <b>Всего выплачено:</b> <code>{payouts_sum:g} GRAM</code>\n"
        f"💰 <b>К выводу на руках (балансы):</b> <code>{balance_unpaid:g} GRAM</code>\n\n"
        "👥 <b>Статистика команды:</b>\n"
        f"• Всего зарегистрировано: <b>{total_users}</b>\n"
        f"• Активных воркеров: <b>{approved}</b>\n"
        f"• Ожидают решения: <b>{pending_u}</b>\n"
        f"• Заблокировано (бан): <b>{banned}</b>\n"
        f"• Успешных профитов: <b>{profits_cnt}</b> шт.\n\n"
        "📥 <b>Очередь на модерацию:</b>\n"
        f"• 📝 Новых анкет: <b>{p_apps}</b>\n"
        f"• 💰 Отчётов по профитам: <b>{p_profs}</b>\n"
        f"• 💳 Запросов на выплату: <b>{p_pays}</b>\n\n"
        "<i>Выберите интересующий раздел в меню ниже 👇</i>"
    )
    return text

async def show_user_profile_admin_card(bot: Bot, target_user_id: int, chat_id: int, call: CallbackQuery | None = None):
    user = await get_user(target_user_id)
    if not user:
        text = f"❌ Пользователь с ID <code>{target_user_id}</code> не найден в базе данных."
        await clean_render(bot, chat_id, text, reply_markup=admin_cancel_inline_keyboard("adm_workers_menu"), call=call)
        return

    uname = f"@{user['username']}" if user["username"] else "нет username"
    fullname = html.escape(user["full_name"] or "Без имени")
    reg_date = user["reg_date"] or user["created_at"] or "Не указана"
    profits_cnt = user["profits_count"] or 0
    total_earned = float(user["total_earned"] or 0.0)
    total_payouts = float(user["total_payouts"] or 0.0)
    balance = max(0.0, round(total_earned - total_payouts, 2))
    is_banned = bool(user["is_banned"] or user["status"] == "banned")

    status_str = "🚫 Заблокирован" if is_banned else ("✅ В команде" if user["status"] == "approved" else f"⏳ {user['status']}")

    card_text = (
        "👤 <b>Карточка воркера — Haster TEAM</b>\n\n"
        f"🆔 <b>Telegram ID:</b> <code>{user['user_id']}</code>\n"
        f"🏷 <b>Юзернейм:</b> {uname}\n"
        f"📝 <b>Имя:</b> {fullname}\n"
        f"⚡️ <b>Статус:</b> <b>{status_str}</b>\n"
        f"📅 <b>Дата регистрации:</b> {reg_date}\n\n"
        f"🔢 <b>Профитов в тиме:</b> <b>{profits_cnt}</b>\n"
        f"💸 <b>Всего заработано:</b> <b>{total_earned:g} GRAM</b>\n"
        f"💳 <b>Всего выплачено:</b> <b>{total_payouts:g} GRAM</b>\n"
        f"💰 <b>Доступно к выводу:</b> <b>{balance:g} GRAM</b>\n\n"
        "<i>Выберите действие с воркером:</i>"
    )
    keyboard = admin_user_card_keyboard(user["user_id"], is_banned=is_banned)
    await clean_render(bot, chat_id, card_text, reply_markup=keyboard, call=call)

# ==================== Entry Points ====================

@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin_private(message: Message, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        await clean_render(bot, message.chat.id, "⛔️ <b>Доступ запрещён.</b>\nУ вас нет прав администратора бота.")
        return

    stats = await get_stats_summary()
    text = format_admin_dashboard_text(stats)
    await clean_render(bot, message.chat.id, text, reply_markup=admin_main_keyboard(stats))

@router.callback_query(F.data == "open_admin_panel")
async def cb_open_admin_panel(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ У вас нет прав администратора!", show_alert=True)
        return

    stats = await get_stats_summary()
    text = format_admin_dashboard_text(stats)
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_main_keyboard(stats), call=call)
    await call.answer()

@router.callback_query(F.data.in_(["adm_back_main", "adm_refresh"]))
async def cb_adm_back_main(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    stats = await get_stats_summary()
    text = format_admin_dashboard_text(stats)
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_main_keyboard(stats), call=call)
    await call.answer("Данные обновлены")

# ==================== Moderation Hub ====================

@router.callback_query(F.data == "adm_mod_menu")
async def cb_adm_mod_menu(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    stats = await get_stats_summary()
    text = (
        "📥 <b>Центр модерации заявок — Haster TEAM</b>\n\n"
        f"📝 <b>Анкеты на вступление:</b> <b>{stats.get('pending_apps_count', 0)}</b>\n"
        f"💰 <b>Отчёты по профитам:</b> <b>{stats.get('pending_profits_count', 0)}</b>\n"
        f"💳 <b>Заявки на выплату средств:</b> <b>{stats.get('pending_payouts_count', 0)}</b>\n\n"
        "<i>Выберите категорию для проверки:</i>"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_moderation_menu_keyboard(stats), call=call)
    await call.answer()

# --- 1. Модерация анкет ---

@router.callback_query(F.data.startswith("adm_mod_apps:"))
async def cb_adm_mod_apps(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    idx = int(call.data.split(":")[1])
    apps = await get_pending_applications_list(limit=50)

    if not apps:
        text = "📝 <b>Очередь анкет пуста!</b>\n\nВсе поданные заявки на вступление уже проверены."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ В меню модерации", callback_data="adm_mod_menu")]])
        await clean_render(bot, call.from_user.id, text, reply_markup=kb, call=call)
        await call.answer()
        return

    if idx >= len(apps):
        idx = len(apps) - 1
    if idx < 0:
        idx = 0

    app = apps[idx]
    uname = f"@{app['username']}" if app['username'] else "нет username"
    fname = html.escape(app['full_name'] or "Кандидат")

    text = (
        f"📝 <b>Анкета кандидата #{app['id']} ({idx + 1} из {len(apps)})</b>\n\n"
        f"👤 <b>Кандидат:</b> {fname} ({uname})\n"
        f"🆔 <b>ID аккаунта:</b> <code>{app['user_id']}</code>\n"
        f"📅 <b>Дата подачи:</b> {app['created_at']}\n\n"
        "📋 <b>Ответы на вопросы:</b>\n"
        "<blockquote>"
        f"<b>1. Откуда узнал:</b>\n{html.escape(app['q1_source'] or '—')}\n\n"
        f"<b>2. Готов уделять времени:</b>\n{html.escape(app['q2_time'] or '—')}\n\n"
        f"<b>3. Опыт работы и общения:</b>\n{html.escape(app['q3_experience'] or '—')}"
        "</blockquote>"
    )
    keyboard = admin_mod_app_card_keyboard(app["id"], app["user_id"], idx, len(apps))
    await clean_render(bot, call.from_user.id, text, reply_markup=keyboard, call=call)
    await call.answer()

@router.callback_query(F.data.startswith("adm_app_ok:"))
async def cb_adm_app_ok(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    parts = call.data.split(":")
    user_id = int(parts[2])
    idx = int(parts[3])

    today_str = datetime.now().strftime("%d.%m.%Y")
    await set_user_status(user_id, "approved", reg_date=today_str)
    await update_application_status(user_id, "approved")

    # Send welcome to worker cleanly
    links = await get_project_links()
    try:
        welcome_text = (
            "🎉 <b>Поздравляем! Ваша заявка в команду Haster TEAM одобрена!</b>\n\n"
            "⚠️ <b>Обязательно вступи в наши ресурсы:</b>\n\n"
            f"💬 <b>Чат команды:</b> <a href=\"{links['chat_url']}\">Вступить в чат</a>\n"
            f"📢 <b>Резервный канал:</b> <a href=\"{links['reserv_url']}\">Подписаться на канал</a>\n"
            f"🔗 <b>Переходник:</b> <a href=\"{links['perehodnik_url']}\">Перейти в переходник</a>\n\n"
            "Ниже открыта твоя рабочая панель воркера 👇"
        )
        await clean_render(bot, user_id, welcome_text)
        await show_worker_panel(bot, user_id=user_id)
    except Exception as e:
        print(f"Error sending welcome to worker {user_id}: {e}")

    await call.answer("✅ Кандидат одобрен!", show_alert=True)
    call.data = f"adm_mod_apps:{idx}"
    await cb_adm_mod_apps(call, bot)

@router.callback_query(F.data.startswith("adm_app_no:"))
async def cb_adm_app_no(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    parts = call.data.split(":")
    user_id = int(parts[2])
    idx = int(parts[3])

    await set_user_status(user_id, "rejected")
    await update_application_status(user_id, "rejected")

    try:
        await clean_render(
            bot,
            user_id,
            "❌ <b>К сожалению, ваша заявка была отклонена администрацией.</b>\nДля повторной подачи отправьте /start."
        )
    except Exception:
        pass

    await call.answer("❌ Заявка отклонена!", show_alert=True)
    call.data = f"adm_mod_apps:{idx}"
    await cb_adm_mod_apps(call, bot)

# --- 2. Модерация профитов ---

@router.callback_query(F.data.startswith("adm_mod_profits:"))
async def cb_adm_mod_profits(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    idx = int(call.data.split(":")[1])
    profs = await get_pending_profit_reports_list(limit=50)

    if not profs:
        text = "💰 <b>Очередь профитов пуста!</b>\n\nВсе отчёты воркеров уже проверены."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ В меню модерации", callback_data="adm_mod_menu")]])
        await clean_render(bot, call.from_user.id, text, reply_markup=kb, call=call)
        await call.answer()
        return

    if idx >= len(profs):
        idx = len(profs) - 1
    if idx < 0:
        idx = 0

    p = profs[idx]
    uname = f"@{p['username']}" if p['username'] else "нет username"
    fname = html.escape(p['full_name'] or "Воркер")
    wtype = html.escape(p['work_type'] or "Оффер")
    dcode = html.escape(p['deal_code'] or "—")
    nft_links = html.escape(p['nft_links'] or "—")
    photo_id = p['photo_id']

    caption = (
        f"💰 <b>Заявка на профит #{p['id']} ({idx + 1} из {len(profs)})</b>\n\n"
        f"👤 <b>Воркер:</b> {fname} ({uname})\n"
        f"🆔 <b>ID аккаунта:</b> <code>{p['user_id']}</code>\n"
        f"💼 <b>Способ ворка:</b> <b>{wtype}</b>\n"
        f"🔢 <b>Код сделки:</b> <code>{html.escape(dcode)}</code>\n"
        f"📅 <b>Дата:</b> {p['created_at']}\n\n"
        f"🔗 <b>Ссылки на NFT:</b>\n<blockquote>{nft_links}</blockquote>"
    )
    keyboard = admin_mod_profit_card_keyboard(p["id"], p["user_id"], idx, len(profs))

    await clean_render(
        bot=bot,
        chat_id=call.from_user.id,
        text=caption,
        reply_markup=keyboard,
        photo_id=photo_id if photo_id else None,
        call=call
    )
    await call.answer()

@router.callback_query(F.data.startswith("adm_prof_ok:"))
async def cb_adm_prof_ok(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    parts = call.data.split(":")
    report_id = int(parts[1])
    user_id = int(parts[2])
    idx = int(parts[3])

    await state.set_state(AdminUserActionState.waiting_profit_amount)
    await state.update_data(target_user_id=user_id, report_id=report_id, return_idx=idx, from_mod=True)

    text = (
        f"💰 <b>Введите сумму профита в GRAM для воркера (ID: <code>{user_id}</code>):</b>\n\n"
        "<i>Например: <code>150</code> или <code>85.5</code></i>"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_mod_menu"), call=call)
    await call.answer()

@router.callback_query(F.data.startswith("adm_prof_no:"))
async def cb_adm_prof_no(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    parts = call.data.split(":")
    report_id = int(parts[1])
    user_id = int(parts[2])
    idx = int(parts[3])

    await update_profit_report_status(report_id, "rejected")

    try:
        await clean_render(bot, user_id, "❌ <b>Ваша заявка на профит была отклонена администрацией.</b>")
    except Exception:
        pass

    await call.answer("❌ Профит отклонён!", show_alert=True)
    call.data = f"adm_mod_profits:{idx}"
    await cb_adm_mod_profits(call, bot)

# --- 3. Модерация выплат ---

@router.callback_query(F.data.startswith("adm_mod_payouts:"))
async def cb_adm_mod_payouts(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    idx = int(call.data.split(":")[1])
    pays = await get_pending_payout_requests_list(limit=50)

    if not pays:
        text = "💳 <b>Очередь выплат пуста!</b>\n\nВсе заявки на выплату обработаны."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ В меню модерации", callback_data="adm_mod_menu")]])
        await clean_render(bot, call.from_user.id, text, reply_markup=kb, call=call)
        await call.answer()
        return

    if idx >= len(pays):
        idx = len(pays) - 1
    if idx < 0:
        idx = 0

    p = pays[idx]
    uname = f"@{p['username']}" if p['username'] else "нет username"
    fname = html.escape(p['full_name'] or "Воркер")
    earned = float(p["total_earned"] or 0.0)
    payouts = float(p["total_payouts"] or 0.0)
    balance = max(0.0, round(earned - payouts, 2))

    text = (
        f"💳 <b>Заявка на выплату #{p['id']} ({idx + 1} из {len(pays)})</b>\n\n"
        f"👤 <b>Воркер:</b> {fname} ({uname})\n"
        f"🆔 <b>ID аккаунта:</b> <code>{p['user_id']}</code>\n"
        f"💰 <b>Текущий баланс:</b> {balance:g} GRAM\n"
        f"💸 <b>Запрошено к выводу:</b> <b>{p['amount']:g} GRAM</b>\n"
        f"📅 <b>Дата заявки:</b> {p['created_at']}\n\n"
        f"👛 <b>Криптокошелёк TON:</b>\n<code>{html.escape(p['wallet'])}</code>"
    )
    keyboard = admin_mod_payout_card_keyboard(p["id"], p["user_id"], idx, len(pays))
    await clean_render(bot, call.from_user.id, text, reply_markup=keyboard, call=call)
    await call.answer()

@router.callback_query(F.data.startswith("adm_pay_ok:"))
async def cb_adm_pay_ok(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    parts = call.data.split(":")
    req_id = int(parts[1])
    user_id = int(parts[2])
    idx = int(parts[3])

    result = await approve_payout_and_add_to_kassa(req_id)
    if not result:
        await call.answer("Заявка уже обработана или не найдена!", show_alert=True)
        return

    amount = result["amount"]
    try:
        user_text = (
            "💳 <b>Ваша заявка на выплату средств выполнена!</b>\n\n"
            f"➕ <b>Выплачено:</b> {amount:g} GRAM\n"
            f"👛 <b>На кошелёк:</b> <code>{html.escape(result['wallet'])}</code>\n"
            f"💰 <b>Остаток к выводу:</b> {result['balance']:g} GRAM\n\n"
            "<i>Средства успешно отправлены. Спасибо за работу!</i>"
        )
        await clean_render(bot, user_id, user_text)
    except Exception:
        pass

    await call.answer(f"✅ Выплата {amount:g} GRAM подтверждена! Касса пополнена.", show_alert=True)
    call.data = f"adm_mod_payouts:{idx}"
    await cb_adm_mod_payouts(call, bot)

@router.callback_query(F.data.startswith("adm_pay_no:"))
async def cb_adm_pay_no(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    parts = call.data.split(":")
    req_id = int(parts[1])
    user_id = int(parts[2])
    idx = int(parts[3])

    req = await get_payout_request(req_id)
    await update_payout_request_status(req_id, "rejected")

    if req:
        try:
            await clean_render(bot, user_id, f"❌ <b>Ваша заявка на выплату {req['amount']:g} GRAM была отклонена.</b>")
        except Exception:
            pass

    await call.answer("❌ Выплата отклонена!", show_alert=True)
    call.data = f"adm_mod_payouts:{idx}"
    await cb_adm_mod_payouts(call, bot)

# ==================== Workers Hub ====================

@router.callback_query(F.data == "adm_workers_menu")
async def cb_adm_workers_menu(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    text = (
        "👥 <b>Управление воркерами — Haster TEAM</b>\n\n"
        "Здесь вы можете найти любого воркера, посмотреть подробную статистику, начислить профит, зафиксировать выплату, скорректировать баланс или заблокировать."
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_workers_menu_keyboard(), call=call)
    await call.answer()

@router.callback_query(F.data == "adm_top_workers")
async def cb_adm_top_workers(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    top = await get_top_workers(10)
    if not top:
        text = "🏆 <b>Топ воркеров пуст</b> (пока нет активных профитов)."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="adm_workers_menu")]])
        await clean_render(bot, call.from_user.id, text, reply_markup=kb, call=call)
        await call.answer()
        return

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    text = "🏆 <b>Топ-10 воркеров команды Haster TEAM:</b>\n\n"

    buttons = []
    for i, u in enumerate(top):
        m = medals[i] if i < len(medals) else f"{i+1}."
        uname = f"@{u['username']}" if u["username"] else u["full_name"]
        earned = float(u["total_earned"] or 0.0)
        p_cnt = u["profits_count"] or 0
        text += f"{m} <b>{html.escape(uname)}</b> — <b>{earned:g} GRAM</b> ({p_cnt} проф.)\n"
        buttons.append([InlineKeyboardButton(text=f"👤 {uname} ({u['user_id']})", callback_data=f"adm_view_u:{u['user_id']}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm_workers_menu")])

    await clean_render(bot, call.from_user.id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), call=call)
    await call.answer()

@router.callback_query(F.data == "adm_user_search")
async def cb_adm_user_search(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    await state.set_state(AdminSearchUserState.waiting_query)
    text = (
        "🔍 <b>Поиск воркера в базе данных:</b>\n\n"
        "Отправьте в чат <b>Telegram ID</b> (например: <code>8702037658</code>) или <b>@username</b> (например: <code>@WusV5W</code>):"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_workers_menu"), call=call)
    await call.answer()

@router.message(AdminSearchUserState.waiting_query, F.chat.type == "private")
async def step_admin_search_query(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    query = (message.text or "").strip()
    if not query:
        await clean_render(bot, message.chat.id, "Пожалуйста, отправьте текст для поиска:", reply_markup=admin_cancel_inline_keyboard("adm_workers_menu"))
        return

    await state.clear()
    users = await search_users(query, limit=10)

    if not users:
        await clean_render(
            bot,
            message.chat.id,
            f"❌ Пользователь по запросу <code>{html.escape(query)}</code> не найден.",
            reply_markup=admin_cancel_inline_keyboard("adm_workers_menu")
        )
        return

    if len(users) == 1:
        await show_user_profile_admin_card(bot, users[0]["user_id"], message.chat.id)
    else:
        text = f"🔍 <b>Найдено совпадений: {len(users)}</b>\nВыберите воркера для просмотра карточки:"
        await clean_render(bot, message.chat.id, text, reply_markup=admin_user_search_results_keyboard(users))

@router.callback_query(F.data.startswith("adm_view_u:"))
async def cb_adm_view_u(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    await show_user_profile_admin_card(bot, user_id, call.from_user.id, call=call)
    await call.answer()

# --- Действия с воркером ---

@router.callback_query(F.data.startswith("adm_u_ban:"))
async def cb_adm_u_ban(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    await set_user_ban_status(user_id, is_banned=True)
    await call.answer("🚫 Воркер успешно заблокирован!", show_alert=True)
    await show_user_profile_admin_card(bot, user_id, call.from_user.id, call=call)

@router.callback_query(F.data.startswith("adm_u_unban:"))
async def cb_adm_u_unban(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    await set_user_ban_status(user_id, is_banned=False)
    await call.answer("🟢 Воркер успешно разблокирован!", show_alert=True)
    await show_user_profile_admin_card(bot, user_id, call.from_user.id, call=call)

@router.callback_query(F.data.startswith("adm_u_prof:"))
async def cb_adm_u_prof(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    await state.set_state(AdminUserActionState.waiting_profit_amount)
    await state.update_data(target_user_id=user_id, from_mod=False)

    text = (
        f"💰 <b>Начисление профита воркеру (ID: <code>{user_id}</code>)</b>\n\n"
        "Введите сумму профита в <b>GRAM</b> (например: <code>150</code>):"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard(f"adm_view_u:{user_id}"), call=call)
    await call.answer()

@router.message(AdminUserActionState.waiting_profit_amount, F.chat.type == "private")
async def step_admin_profit_amount(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    text = (message.text or "").strip().replace(",", ".")
    try:
        val = float(text)
        if val <= 0 or not math.isfinite(val):
            raise ValueError()
    except (ValueError, TypeError):
        await clean_render(bot, message.chat.id, "⚠️ Введите положительное число в GRAM (например: <code>150</code>):")
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")
    report_id = data.get("report_id")
    from_mod = data.get("from_mod", False)
    await state.clear()

    if from_mod and report_id:
        result = await approve_profit_report(report_id, val)
    else:
        result = await add_user_profit(user_id, val)

    if not result:
        await clean_render(bot, message.chat.id, "❌ Ошибка при начислении профита. Пользователь не найден.")
        return

    try:
        user_notify = (
            "🎉 <b>Вам начислен профит!</b>\n\n"
            f"➕ <b>Сумма профита:</b> +{val:g} GRAM\n"
            f"💰 <b>Доступно к выводу:</b> {result['balance']:g} GRAM\n"
            f"🔢 <b>Всего твоих профитов:</b> {result['profits_count']}\n"
            f"💸 <b>Всего заработано:</b> {result['total_earned']:g} GRAM"
        )
        await clean_render(bot, user_id, user_notify)
    except Exception as e:
        print(f"Error notifying worker {user_id}: {e}")

    result_text = (
        f"✅ <b>Профит {val:g} GRAM успешно начислен!</b>\n\n"
        f"👤 Воркер: ID <code>{user_id}</code>\n"
        f"💰 Баланс воркера: <b>{result['balance']:g} GRAM</b>\n"
        f"🔢 Всего профитов: <b>{result['profits_count']}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👤 К карточке воркера", callback_data=f"adm_view_u:{user_id}"),
        InlineKeyboardButton(text="👑 В меню", callback_data="adm_back_main")
    ]])
    await clean_render(bot, message.chat.id, result_text, reply_markup=kb)

@router.callback_query(F.data.startswith("adm_u_pay:"))
async def cb_adm_u_pay(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    await state.set_state(AdminUserActionState.waiting_payout_amount)
    await state.update_data(target_user_id=user_id)

    text = (
        f"💳 <b>Фиксация выплаты воркеру (ID: <code>{user_id}</code>)</b>\n\n"
        "Введите выплаченную сумму в <b>GRAM</b> (например: <code>100</code>):\n"
        "<i>Сумма автоматически добавится в кассу команды.</i>"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard(f"adm_view_u:{user_id}"), call=call)
    await call.answer()

@router.message(AdminUserActionState.waiting_payout_amount, F.chat.type == "private")
async def step_admin_payout_amount(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    text = (message.text or "").strip().replace(",", ".")
    try:
        val = float(text)
        if val <= 0 or not math.isfinite(val):
            raise ValueError()
    except (ValueError, TypeError):
        await clean_render(bot, message.chat.id, "⚠️ Введите корректное положительное число в GRAM:")
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")
    await state.clear()

    result = await add_user_payout(user_id, val)
    if not result:
        await clean_render(bot, message.chat.id, "❌ Пользователь не найден.")
        return

    try:
        user_notify = (
            "💳 <b>Вам произведена выплата!</b>\n\n"
            f"➕ <b>Сумма выплаты:</b> {val:g} GRAM\n"
            f"💳 <b>Всего выплат за всё время:</b> {result['total_payouts']:g} GRAM\n"
            f"💰 <b>Остаток к выводу:</b> {result['balance']:g} GRAM"
        )
        await clean_render(bot, user_id, user_notify)
    except Exception:
        pass

    result_text = (
        f"💳 <b>Выплата {val:g} GRAM успешно зафиксирована!</b>\n\n"
        f"👤 Воркер: ID <code>{user_id}</code>\n"
        f"🏦 <b>Касса команды пополнена:</b> {result['total_kassa']:g} GRAM"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👤 К карточке воркера", callback_data=f"adm_view_u:{user_id}"),
        InlineKeyboardButton(text="👑 В меню", callback_data="adm_back_main")
    ]])
    await clean_render(bot, message.chat.id, result_text, reply_markup=kb)

@router.callback_query(F.data.startswith("adm_u_bal:"))
async def cb_adm_u_bal(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    await state.set_state(AdminUserActionState.waiting_balance)
    await state.update_data(target_user_id=user_id)

    text = (
        f"✏️ <b>Установка точного баланса воркера (ID: <code>{user_id}</code>)</b>\n\n"
        "Введите желаемый баланс в GRAM (например: <code>50</code> или <code>0</code>):"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard(f"adm_view_u:{user_id}"), call=call)
    await call.answer()

@router.message(AdminUserActionState.waiting_balance, F.chat.type == "private")
async def step_admin_set_balance(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    text = (message.text or "").strip().replace(",", ".")
    try:
        val = float(text)
        if val < 0 or not math.isfinite(val):
            raise ValueError()
    except (ValueError, TypeError):
        await clean_render(bot, message.chat.id, "⚠️ Введите неотрицательное число в GRAM:")
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")
    await state.clear()

    res = await set_user_balance(user_id, val)
    if not res:
        await clean_render(bot, message.chat.id, "❌ Ошибка при изменении баланса.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👤 К карточке воркера", callback_data=f"adm_view_u:{user_id}")
    ]])
    await clean_render(bot, message.chat.id, f"✅ <b>Баланс воркера {user_id} установлен на {val:g} GRAM!</b>", reply_markup=kb)

@router.callback_query(F.data.startswith("adm_u_msg:"))
async def cb_adm_u_msg(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    await state.set_state(AdminUserActionState.waiting_direct_message)
    await state.update_data(target_user_id=user_id)

    text = (
        f"💬 <b>Отправка сообщения воркеру (ID: <code>{user_id}</code>)</b>\n\n"
        "Отправьте текст сообщения, который будет доставлен воркеру в ЛС от имени администрации:"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard(f"adm_view_u:{user_id}"), call=call)
    await call.answer()

@router.message(AdminUserActionState.waiting_direct_message, F.chat.type == "private")
async def step_admin_send_user_message(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    data = await state.get_data()
    user_id = data.get("target_user_id")
    await state.clear()

    admin_name = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.full_name or "Администрация")
    msg_text = (
        "📩 <b>Сообщение от администрации Haster TEAM:</b>\n\n"
        f"{message.html_text or message.text}\n\n"
        f"<i>Отправил: {html.escape(admin_name)}</i>"
    )
    try:
        await clean_render(bot, user_id, msg_text)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👤 К карточке", callback_data=f"adm_view_u:{user_id}")
        ]])
        await clean_render(bot, message.chat.id, f"✅ Сообщение успешно отправлено воркеру <code>{user_id}</code>!", reply_markup=kb)
    except Exception as e:
        await clean_render(bot, message.chat.id, f"❌ Не удалось отправить сообщение: {e}")

# ==================== Kassa Management ====================

@router.callback_query(F.data == "adm_kassa_menu")
async def cb_adm_kassa_menu(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    kassa = await get_kassa()
    text = (
        "🏦 <b>Управление общей кассой — Haster TEAM</b>\n\n"
        f"💰 <b>Текущий баланс кассы:</b> <b>{kassa:g} GRAM</b>\n\n"
        "<i>Касса автоматически пополняется при подтверждении выплат воркерам. Также вы можете скорректировать баланс вручную:</i>"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_kassa_menu_keyboard(), call=call)
    await call.answer()

@router.callback_query(F.data == "adm_kassa_add")
async def cb_adm_kassa_add(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    await state.set_state(AdminKassaActionState.waiting_add)
    text = "➕ <b>Пополнение кассы</b>\n\nВведите сумму в GRAM для добавления в кассу:"
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_kassa_menu"), call=call)
    await call.answer()

@router.message(AdminKassaActionState.waiting_add, F.chat.type == "private")
async def step_admin_kassa_add(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    text = (message.text or "").strip().replace(",", ".")
    try:
        val = float(text)
        if val <= 0 or not math.isfinite(val):
            raise ValueError()
    except (ValueError, TypeError):
        await clean_render(bot, message.chat.id, "⚠️ Введите положительное число:")
        return

    await state.clear()
    new_kassa = await add_to_kassa(val)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏦 В меню кассы", callback_data="adm_kassa_menu")
    ]])
    await clean_render(bot, message.chat.id, f"✅ Касса пополнена на <b>{val:g} GRAM</b>!\nНовый баланс: <b>{new_kassa:g} GRAM</b>", reply_markup=kb)

@router.callback_query(F.data == "adm_kassa_sub")
async def cb_adm_kassa_sub(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    await state.set_state(AdminKassaActionState.waiting_sub)
    text = "➖ <b>Списание из кассы</b>\n\nВведите сумму в GRAM для списания из кассы:"
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_kassa_menu"), call=call)
    await call.answer()

@router.message(AdminKassaActionState.waiting_sub, F.chat.type == "private")
async def step_admin_kassa_sub(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    text = (message.text or "").strip().replace(",", ".")
    try:
        val = float(text)
        if val <= 0 or not math.isfinite(val):
            raise ValueError()
    except (ValueError, TypeError):
        await clean_render(bot, message.chat.id, "⚠️ Введите положительное число:")
        return

    await state.clear()
    new_kassa = await add_to_kassa(-val)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏦 В меню кассы", callback_data="adm_kassa_menu")
    ]])
    await clean_render(bot, message.chat.id, f"✅ Из кассы списано <b>{val:g} GRAM</b>.\nНовый баланс: <b>{new_kassa:g} GRAM</b>", reply_markup=kb)

@router.callback_query(F.data == "adm_kassa_set")
async def cb_adm_kassa_set(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    await state.set_state(AdminKassaActionState.waiting_set)
    text = "✏️ <b>Установка баланса кассы</b>\n\nВведите точную сумму кассы в GRAM:"
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_kassa_menu"), call=call)
    await call.answer()

@router.message(AdminKassaActionState.waiting_set, F.chat.type == "private")
async def step_admin_kassa_set(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    text = (message.text or "").strip().replace(",", ".")
    try:
        val = float(text)
        if val < 0 or not math.isfinite(val):
            raise ValueError()
    except (ValueError, TypeError):
        await clean_render(bot, message.chat.id, "⚠️ Введите неотрицательное число:")
        return

    await state.clear()
    new_kassa = await set_kassa(val)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏦 В меню кассы", callback_data="adm_kassa_menu")
    ]])
    await clean_render(bot, message.chat.id, f"✅ Касса команды установлена на <b>{new_kassa:g} GRAM</b>", reply_markup=kb)

# ==================== Broadcast Management ====================

@router.callback_query(F.data == "adm_broadcast_menu")
async def cb_adm_broadcast_menu(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    recipients = await get_all_broadcast_users()
    text = (
        "📢 <b>Центр рассылки сообщений — Haster TEAM</b>\n\n"
        f"👥 <b>Доступно получателей:</b> <b>{len(recipients)}</b> пользователей\n\n"
        "Вы можете отправить текстовое объявление или фото с текстом всем зарегистрированным воркерам. Перед отправкой бот покажет предпросмотр сообщения."
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_broadcast_menu_keyboard(), call=call)
    await call.answer()

@router.callback_query(F.data == "adm_bc_create")
async def cb_adm_bc_create(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    await state.set_state(AdminBroadcastState.waiting_content)
    text = (
        "✍️ <b>Создание рассылки:</b>\n\n"
        "Отправьте в этот чат сообщение для рассылки (текст или фото с описанием). Поддерживается HTML-разметка."
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_broadcast_menu"), call=call)
    await call.answer()

@router.message(AdminBroadcastState.waiting_content, F.chat.type == "private")
async def step_admin_broadcast_content(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    photo_id = message.photo[-1].file_id if message.photo else None
    content_text = message.caption or message.html_text or message.text or ""

    if not content_text and not photo_id:
        await clean_render(bot, message.chat.id, "Пожалуйста, отправьте сообщение с текстом или фото:")
        return

    await state.set_state(AdminBroadcastState.confirm_send)
    await state.update_data(photo_id=photo_id, content_text=content_text)

    recipients = await get_all_broadcast_users()
    preview_header = f"👁 <b>Предпросмотр рассылки (получателей: {len(recipients)}):</b>\n\n"
    full_text = preview_header + content_text

    await clean_render(
        bot=bot,
        chat_id=message.chat.id,
        text=full_text,
        reply_markup=admin_broadcast_confirm_keyboard(),
        photo_id=photo_id
    )

@router.callback_query(AdminBroadcastState.confirm_send, F.data == "adm_bc_start")
async def cb_adm_bc_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    data = await state.get_data()
    photo_id = data.get("photo_id")
    content_text = data.get("content_text", "")
    await state.clear()

    recipients = await get_all_broadcast_users()
    total = len(recipients)

    await clean_render(bot, call.from_user.id, f"⏳ <b>Идёт отправка рассылки...</b> [0/{total}]", call=call)
    await call.answer()

    success_cnt = 0
    fail_cnt = 0

    for idx, uid in enumerate(recipients, 1):
        try:
            if photo_id:
                await bot.send_photo(chat_id=uid, photo=photo_id, caption=content_text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=uid, text=content_text, parse_mode="HTML")
            success_cnt += 1
        except Exception:
            fail_cnt += 1

        if idx % 10 == 0 or idx == total:
            try:
                progress_text = (
                    f"⏳ <b>Идёт отправка рассылки...</b> [{idx}/{total}]\n"
                    f"✅ Успешно: {success_cnt} | ❌ Ошибок: {fail_cnt}"
                )
                await clean_render(bot, call.from_user.id, progress_text)
            except Exception:
                pass
        await asyncio.sleep(0.04)

    final_text = (
        "📢 <b>Рассылка успешно завершена!</b>\n\n"
        f"👥 <b>Всего получателей:</b> {total}\n"
        f"✅ <b>Доставлено:</b> {success_cnt}\n"
        f"⚠️ <b>Не доставлено (заблокировали):</b> {fail_cnt}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👑 В админку", callback_data="adm_back_main")
    ]])
    await clean_render(bot, call.from_user.id, final_text, reply_markup=kb)

@router.callback_query(F.data == "adm_bc_cancel")
async def cb_adm_bc_cancel(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👑 В админку", callback_data="adm_back_main")
    ]])
    await clean_render(bot, call.from_user.id, "❌ Рассылка отменена.", reply_markup=kb, call=call)
    await call.answer()

# ==================== Settings & Links Hub ====================

@router.callback_query(F.data == "adm_settings_menu")
async def cb_adm_settings_menu(call: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    links = await get_project_links()
    text = (
        "⚙️ <b>Настройки проекта и ссылок — Haster TEAM</b>\n\n"
        f"💬 <b>Чат команды:</b>\n<code>{html.escape(links['chat_url'])}</code>\n\n"
        f"📢 <b>Резервный канал:</b>\n<code>{html.escape(links['reserv_url'])}</code>\n\n"
        f"🔗 <b>Переходник:</b>\n<code>{html.escape(links['perehodnik_url'])}</code>\n\n"
        "<i>Нажмите на кнопку ниже, чтобы изменить нужную ссылку:</i>"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_settings_keyboard(), call=call)
    await call.answer()

@router.callback_query(F.data.startswith("adm_set_link:"))
async def cb_adm_set_link(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    link_key = call.data.split(":")[1]
    name_map = {
        "chat_url": "Чат команды",
        "reserv_url": "Резервный канал",
        "perehodnik_url": "Переходник"
    }
    await state.set_state(AdminSettingsActionState.waiting_link)
    await state.update_data(link_key=link_key)

    text = (
        f"✏️ <b>Изменение ссылки на «{name_map.get(link_key, link_key)}»</b>\n\n"
        "Отправьте новую ссылку (например: <code>https://t.me/...</code>):"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_settings_menu"), call=call)
    await call.answer()

@router.message(AdminSettingsActionState.waiting_link, F.chat.type == "private")
async def step_admin_set_link(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    url = (message.text or "").strip()
    if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("tg://"):
        await clean_render(bot, message.chat.id, "⚠️ Пожалуйста, введите корректный URL (начинающийся с <code>https://t.me/</code>):")
        return

    data = await state.get_data()
    link_key = data.get("link_key")
    await state.clear()

    await set_project_link(link_key, url)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚙️ В настройки", callback_data="adm_settings_menu")
    ]])
    await clean_render(bot, message.chat.id, f"✅ Ссылка успешно обновлена на:\n<code>{html.escape(url)}</code>", reply_markup=kb)

@router.callback_query(F.data == "adm_admins_list")
async def cb_adm_admins_list(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    admin_ids = await get_admin_ids()
    text = "👥 <b>Список администраторов бота:</b>\n\n"
    buttons = []

    for aid in admin_ids:
        u = await get_user(aid)
        uname = f"@{u['username']}" if u and u["username"] else (u["full_name"] if u else "Admin")
        text += f"• <code>{aid}</code> ({html.escape(uname)})\n"
        buttons.append([InlineKeyboardButton(text=f"❌ Удалить {aid}", callback_data=f"adm_del_admin:{aid}")])

    buttons.append([InlineKeyboardButton(text="➕ Добавить администратора", callback_data="adm_add_admin")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад в настройки", callback_data="adm_settings_menu")])

    await clean_render(bot, call.from_user.id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), call=call)
    await call.answer()

@router.callback_query(F.data == "adm_add_admin")
async def cb_adm_add_admin(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    await state.set_state(AdminSettingsActionState.waiting_add_admin)
    text = (
        "➕ <b>Добавление администратора:</b>\n\n"
        "Отправьте числовой <b>Telegram ID</b> пользователя, которого хотите назначить администратором:"
    )
    await clean_render(bot, call.from_user.id, text, reply_markup=admin_cancel_inline_keyboard("adm_admins_list"), call=call)
    await call.answer()

@router.message(AdminSettingsActionState.waiting_add_admin, F.chat.type == "private")
async def step_admin_add_admin(message: Message, state: FSMContext, bot: Bot):
    await safe_delete_message(bot, message.chat.id, message.message_id)

    if not await check_admin_access(message.from_user.id, bot):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await clean_render(bot, message.chat.id, "⚠️ Введите корректный числовой Telegram ID:")
        return

    target_id = int(text)
    await state.clear()
    await add_admin_id(target_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👥 К списку админов", callback_data="adm_admins_list")
    ]])
    await clean_render(bot, message.chat.id, f"✅ Пользователь с ID <code>{target_id}</code> успешно добавлен в администраторы бота!", reply_markup=kb)

@router.callback_query(F.data.startswith("adm_del_admin:"))
async def cb_adm_del_admin(call: CallbackQuery, bot: Bot):
    if not await check_admin_access(call.from_user.id, bot):
        await call.answer("⛔️ Доступ запрещён!", show_alert=True)
        return

    target_id = int(call.data.split(":")[1])
    if target_id == call.from_user.id:
        await call.answer("❌ Вы не можете удалить самого себя из администраторов!", show_alert=True)
        return

    await remove_admin_id(target_id)
    await call.answer(f"Администратор {target_id} удалён.")
    await cb_adm_admins_list(call, bot)
