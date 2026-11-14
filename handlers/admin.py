import html
import math
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, 
    CallbackQuery, 
    ChatMemberUpdated, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from config import ADMIN_CHAT_ID, CHAT_URL, RESERV_URL, PEREHODNIK_URL
from states import AdminApproveProfitState
from database import (
    set_user_status, 
    update_application_status, 
    get_user,
    add_user_profit,
    add_user_payout,
    get_kassa,
    set_setting,
    get_payout_request,
    approve_payout_and_add_to_kassa,
    update_payout_request_status,
    get_profit_report,
    update_profit_report_status,
    approve_profit_report,
    get_project_links,
    log_activity
)
from utils import show_worker_panel

router = Router()

@router.callback_query(F.data == "none")
async def cb_none(call: CallbackQuery):
    await call.answer()

# Защита от добавления бота в чужие группы
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_bot_joined_group(event: ChatMemberUpdated):
    if event.chat.id != ADMIN_CHAT_ID:
        try:
            await event.bot.send_message(
                chat_id=event.chat.id,
                text="⛔️ <b>Доступ запрещён.</b>\nЭтот бот является приватным и принадлежит исключительно команде Haster TEAM.",
                parse_mode="HTML"
            )
            await event.bot.leave_chat(event.chat.id)
        except Exception:
            pass

# Команда /help в ЛС воркера (скрываем админ-инструкцию)
@router.message(Command("help"), F.chat.type == "private")
async def cmd_private_help(message: Message, bot: Bot):
    from utils import safe_delete_message, clean_render
    await safe_delete_message(bot, message.chat.id, message.message_id)
    await clean_render(
        bot,
        message.chat.id,
        "👋 Для перехода в рабочую панель воркера Haster TEAM используйте команду /start."
    )

# ----------------- Команды только для группы админов (доступны ВСЕМ участникам группы) -----------------

@router.message(Command("help", "adminhelp"), F.chat.id == ADMIN_CHAT_ID)
async def cmd_admin_help(message: Message):
    help_text = (
        "🛠 <b>Инструкция для кураторов и администрации — Haster TEAM</b>\n\n"
        "<i>Все участники этой группы имеют полные права модератора.</i>\n\n"
        "<b>1️⃣ Модерация заявок кандидатов:</b>\n"
        "• Новые анкеты воркеров поступают в этот чат с кнопками <code>[✅ Одобрить]</code> и <code>[❌ Отклонить]</code>.\n"
        "• При одобрении воркер получает ссылки на чат, резерв, переходник и доступ в личный кабинет.\n\n"
        "<b>2️⃣ Начисление профитов:</b>\n"
        "• Проверили сделку/NFT воркера? Начислите ему деньги на баланс командой:\n"
        "  <code>/profit @username 150</code> — начислить профит по юзернейму\n"
        "  <code>/profit 123456789 150</code> — по Telegram ID воркера\n"
        "  <code>/profit 150</code> — ответом (reply) на сообщение воркера\n"
        "<i>(Счётчик профитов воркера увеличивается на +1, а сумма добавляется ему на баланс в панели).</i>\n\n"
        "<b>3️⃣ Выплаты воркерам и касса:</b>\n"
        "• Воркер нажимает в боте кнопку «Подать заявку на выплату» и указывает реквизиты.\n"
        "• Заявка прилетает в этот чат с кнопками <code>[✅ Выплачено]</code> и <code>[❌ Отклонить]</code>.\n"
        "• Переводите средства воркеру и жмёте <code>[✅ Выплачено]</code>:\n"
        "  1. Воркеру засчитывается выплата.\n"
        "  2. <b>Сумма профита АВТОМАТИЧЕСКИ зачисляется в общую кассу команды!</b>\n\n"
        "<b>4️⃣ Быстрая фиксация выплаты вручную:</b>\n"
        "  <code>/payout @username 150</code> — зафиксировать выплату воркеру и пополнить кассу\n"
        "  <code>/payout 150</code> — ответом (reply) на сообщение воркера\n\n"
        "<b>5️⃣ Общая касса команды:</b>\n"
        "• <code>/kassa</code> — проверить баланс общей кассы\n"
        "• <code>/setkassa &lt;сумма&gt;</code> — вручную скорректировать баланс кассы"
    )
    await message.reply(help_text, parse_mode="HTML")

@router.message(Command("id", "chatid"), F.chat.id == ADMIN_CHAT_ID)
async def cmd_get_id(message: Message):
    await message.reply(
        f"🆔 <b>ID этого чата:</b> <code>{message.chat.id}</code>\n"
        f"👤 <b>Ваш ID:</b> <code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )

@router.message(Command("kassa"), F.chat.id == ADMIN_CHAT_ID)
async def cmd_kassa(message: Message):
    kassa = await get_kassa()
    await message.reply(
        f"🏦 <b>Общая касса команды Haster TEAM:</b> <b>{kassa:g} GRAM</b>",
        parse_mode="HTML"
    )

@router.message(Command("setkassa"), F.chat.id == ADMIN_CHAT_ID)
async def cmd_set_kassa(message: Message):
    args = message.text.split()[1:]
    if not args:
        await message.reply("ℹ️ Использование: <code>/setkassa 1000</code>", parse_mode="HTML")
        return
    try:
        val = float(args[0].replace(",", "."))
        if val < 0 or not math.isfinite(val):
            raise ValueError()
    except (ValueError, TypeError):
        await message.reply("⚠️ Введите корректное положительное число для кассы.", parse_mode="HTML")
        return

    await set_setting("total_kassa", str(round(val, 2)))
    await message.reply(f"✅ Общая касса установлена на <b>{val:g} GRAM</b>", parse_mode="HTML")

@router.message(Command("profit"), F.chat.id == ADMIN_CHAT_ID)
async def cmd_add_profit(message: Message, bot: Bot):
    args = message.text.split()[1:]
    target_user = None
    amount = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
        if args:
            try:
                val = float(args[0].replace(",", "."))
                if val > 0 and math.isfinite(val):
                    amount = round(val, 2)
            except (ValueError, TypeError):
                pass
    elif len(args) >= 2:
        target_user = args[0]
        try:
            val = float(args[1].replace(",", "."))
            if val > 0 and math.isfinite(val):
                amount = round(val, 2)
        except (ValueError, TypeError):
            pass

    if not target_user or amount is None:
        await message.reply(
            "ℹ️ <b>Формат начисления профита:</b>\n"
            "<code>/profit &lt;ID_или_@username&gt; &lt;сумма&gt;</code>\n"
            "<i>Или ответом (reply) на сообщение воркера:</i>\n"
            "<code>/profit &lt;сумма&gt;</code>\n\n"
            "<b>Пример:</b> <code>/profit @WusV5W 150</code>",
            parse_mode="HTML"
        )
        return

    result = await add_user_profit(target_user, amount)
    if not result:
        await message.reply(f"❌ Пользователь <code>{target_user}</code> не найден в базе данных.", parse_mode="HTML")
        return

    worker_mention = f"@{result['username']}" if result['username'] else result['full_name']
    await message.reply(
        "🎉 <b>Профит успешно начислен воркеру!</b>\n\n"
        f"👤 <b>Воркер:</b> {html.escape(worker_mention)} (<code>{result['user_id']}</code>)\n"
        f"➕ <b>Начислено:</b> +{amount:g} GRAM\n"
        f"🔢 <b>Всего профитов:</b> {result['profits_count']}\n"
        f"💸 <b>Всего заработано:</b> {result['total_earned']:g} GRAM\n"
        f"💰 <b>Доступно к выводу:</b> {result['balance']:g} GRAM\n\n"
        "<i>Воркер может подать заявку на выплату в боте. После подтверждения выплаты сумма автоматически пополнит кассу тимы.</i>",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            chat_id=result["user_id"],
            text=(
                "🎉 <b>Поздравляем! Вам начислен новый профит!</b>\n\n"
                f"➕ <b>Сумма профита:</b> +{amount:g} GRAM\n"
                f"💰 <b>Доступно к выводу:</b> {result['balance']:g} GRAM\n"
                f"🔢 <b>Всего профитов в команде:</b> {result['profits_count']}\n"
                f"💸 <b>Всего заработано:</b> {result['total_earned']:g} GRAM\n\n"
                "<i>Вы можете подать заявку на вывод средств прямо в панели бота!</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление о профите воркеру {result['user_id']}: {e}")

@router.message(Command("payout"), F.chat.id == ADMIN_CHAT_ID)
async def cmd_add_payout(message: Message, bot: Bot):
    args = message.text.split()[1:]
    target_user = None
    amount = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user.id
        if args:
            try:
                val = float(args[0].replace(",", "."))
                if val > 0 and math.isfinite(val):
                    amount = round(val, 2)
            except (ValueError, TypeError):
                pass
    elif len(args) >= 2:
        target_user = args[0]
        try:
            val = float(args[1].replace(",", "."))
            if val > 0 and math.isfinite(val):
                amount = round(val, 2)
        except (ValueError, TypeError):
            pass

    if not target_user or amount is None:
        await message.reply(
            "ℹ️ <b>Формат фиксации выплаты:</b>\n"
            "<code>/payout &lt;ID_или_@username&gt; &lt;сумма&gt;</code>\n"
            "<i>Или ответом (reply) на сообщение воркера:</i>\n"
            "<code>/payout &lt;сумма&gt;</code>\n\n"
            "<b>Пример:</b> <code>/payout @WusV5W 150</code>",
            parse_mode="HTML"
        )
        return

    result = await add_user_payout(target_user, amount)
    if not result:
        await message.reply(f"❌ Пользователь <code>{target_user}</code> не найден в базе данных.", parse_mode="HTML")
        return

    worker_mention = f"@{result['username']}" if result['username'] else result['full_name']
    await message.reply(
        "💳 <b>Выплата успешно зафиксирована!</b>\n\n"
        f"👤 <b>Воркер:</b> {html.escape(worker_mention)} (<code>{result['user_id']}</code>)\n"
        f"➕ <b>Выплачено сейчас:</b> {amount:g} GRAM\n"
        f"💳 <b>Всего выплат воркеру:</b> {result['total_payouts']:g} GRAM\n"
        f"🏦 <b>Касса команды (авто):</b> {result['total_kassa']:g} GRAM",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            chat_id=result["user_id"],
            text=(
                "💳 <b>Вам произведена выплата!</b>\n\n"
                f"➕ <b>Сумма выплаты:</b> {amount:g} GRAM\n"
                f"💳 <b>Всего выплат за всё время:</b> {result['total_payouts']:g} GRAM\n\n"
                "<i>Средства отправлены администрацией. Спасибо за отличную работу!</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление о выплате воркеру {result['user_id']}: {e}")

# ----------------- Модерация заявки на вступление -----------------

@router.callback_query(F.data.startswith("admin_approve:"))
async def cb_admin_approve(call: CallbackQuery, bot: Bot):
    if call.message.chat.id != ADMIN_CHAT_ID:
        await call.answer("⛔️ Модерация разрешена только в чате администрации!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    admin_name = f"@{call.from_user.username}" if call.from_user.username else (call.from_user.full_name or "Администратор")

    today_str = datetime.now().strftime("%d.%m.%Y")
    await set_user_status(user_id, "approved", reg_date=today_str)
    await update_application_status(user_id, "approved")
    admin_name = f"@{call.from_user.username}" if call.from_user.username else str(call.from_user.id)
    await log_activity("application_approve", admin_name, f"Одобрена анкета пользователя ID {user_id}")

    current_text = call.message.html_text or call.message.text
    new_text = f"{current_text}\n\n✅ <b>Заявка ОДОБРЕНА ({html.escape(admin_name)})</b>"
    
    status_kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"✅ Одобрено: {admin_name}", callback_data="none")
        ]]
    )

    try:
        await call.message.edit_text(new_text, parse_mode="HTML", reply_markup=status_kb)
    except Exception as e:
        print(f"Не удалось обновить сообщение модерации: {e}")

    await call.answer("Заявка одобрена!")

    try:
        links = await get_project_links()
        welcome_text = (
            "🎉 <b>Поздравляем! Ваша заявка в команду Haster TEAM одобрена!</b>\n\n"
            "⚠️ <b>Обязательно вступи в наши ресурсы:</b>\n\n"
            f"💬 <b>Чат команды:</b> <a href=\"{links['chat_url']}\">Вступить в чат</a>\n"
            f"📢 <b>Резервный канал:</b> <a href=\"{links['reserv_url']}\">Подписаться на канал</a>\n"
            f"🔗 <b>Переходник:</b> <a href=\"{links['perehodnik_url']}\">Перейти в переходник</a>\n\n"
            "Ниже открыта твоя рабочая панель воркера 👇"
        )
        await bot.send_message(
            chat_id=user_id,
            text=welcome_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        await show_worker_panel(bot, user_id=user_id)
    except Exception as e:
        print(f"Не удалось отправить уведомление воркеру {user_id}: {e}")

@router.callback_query(F.data.startswith("admin_reject:"))
async def cb_admin_reject(call: CallbackQuery, bot: Bot):
    if call.message.chat.id != ADMIN_CHAT_ID:
        await call.answer("⛔️ Модерация разрешена только в чате администрации!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    admin_name = f"@{call.from_user.username}" if call.from_user.username else (call.from_user.full_name or "Администратор")

    await set_user_status(user_id, "rejected")
    await update_application_status(user_id, "rejected")
    admin_name = f"@{call.from_user.username}" if call.from_user.username else str(call.from_user.id)
    await log_activity("application_reject", admin_name, f"Отклонена анкета пользователя ID {user_id}")

    current_text = call.message.html_text or call.message.text
    new_text = f"{current_text}\n\n❌ <b>Заявка ОТКЛОНЕНА ({html.escape(admin_name)})</b>"

    status_kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"❌ Отклонено: {admin_name}", callback_data="none")
        ]]
    )

    try:
        await call.message.edit_text(new_text, parse_mode="HTML", reply_markup=status_kb)
    except Exception as e:
        print(f"Не удалось обновить сообщение модерации: {e}")

    await call.answer("Заявка отклонена!")

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "❌ <b>К сожалению, ваша заявка была отклонена администрацией.</b>\n\n"
                "Если хотите попробовать снова или дополнить информацию, отправьте команду /start."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление об отклонении воркеру {user_id}: {e}")

# ----------------- Модерация заявок на профит -----------------

@router.callback_query(F.data.startswith("admin_profit_appr:"))
async def cb_admin_profit_approve(call: CallbackQuery, state: FSMContext, bot: Bot):
    if call.message.chat.id != ADMIN_CHAT_ID:
        await call.answer("⛔️ Модерация разрешена только в чате администрации!", show_alert=True)
        return

    report_id = int(call.data.split(":")[1])
    report = await get_profit_report(report_id)
    if not report or report["status"] != "pending":
        await call.answer("Этот отчёт уже обработан!", show_alert=True)
        return

    admin_name = f"@{call.from_user.username}" if call.from_user.username else (call.from_user.full_name or "Администратор")

    await state.set_state(AdminApproveProfitState.waiting_amount)
    await state.update_data(
        report_id=report_id,
        orig_chat_id=call.message.chat.id,
        orig_msg_id=call.message.message_id,
        orig_has_photo=bool(call.message.photo),
        orig_text=call.message.caption or call.message.html_text or call.message.text,
        admin_name=admin_name
    )

    await call.message.reply(
        f"💰 <b>Куратор {html.escape(admin_name)}, укажите сумму профита в GRAM:</b>\n\n"
        "<i>Отправьте число (например: <code>150</code> или <code>85.5</code>) ответом на это сообщение:</i>",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(AdminApproveProfitState.waiting_amount, F.chat.id == ADMIN_CHAT_ID)
async def step_admin_profit_amount(message: Message, state: FSMContext, bot: Bot):
    text = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(text)
        if math.isnan(amount) or math.isinf(amount) or amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        await message.reply("⚠️ Пожалуйста, введите положительное число в GRAM (например: <code>150</code>):")
        return

    data = await state.get_data()
    report_id = data.get("report_id")
    orig_chat_id = data.get("orig_chat_id")
    orig_msg_id = data.get("orig_msg_id")
    orig_has_photo = data.get("orig_has_photo", False)
    orig_text = data.get("orig_text", "")
    admin_name = data.get("admin_name") or (f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name)

    await state.clear()

    result = await approve_profit_report(report_id, amount)
    if not result:
        await message.reply("❌ Заявка уже была обработана ранее.")
        return

    user_id = result["user_id"]
    new_balance = result["balance"]
    worker_mention = f"@{result['username']}" if result['username'] else result['full_name']

    status_kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"✅ Одобрено: {amount:g} GRAM ({admin_name})", callback_data="none")
        ]]
    )

    new_card_text = (
        f"{orig_text}\n\n"
        f"✅ <b>Профит {amount:g} GRAM ОДОБРЕН ({html.escape(admin_name)})!</b>\n"
        f"💰 <i>Сумма начислена на баланс воркера.</i>"
    )

    try:
        if orig_has_photo:
            await bot.edit_message_caption(
                chat_id=orig_chat_id,
                message_id=orig_msg_id,
                caption=new_card_text,
                parse_mode="HTML",
                reply_markup=status_kb
            )
        else:
            await bot.edit_message_text(
                chat_id=orig_chat_id,
                message_id=orig_msg_id,
                text=new_card_text,
                parse_mode="HTML",
                reply_markup=status_kb
            )
    except Exception as e:
        print(f"Не удалось обновить карточку профита: {e}")

    await message.reply(
        f"✅ <b>Профит {amount:g} GRAM успешно начислен воркеру {html.escape(worker_mention)}!</b>\n"
        f"💰 Баланс воркера к выводу: <b>{new_balance:g} GRAM</b>\n"
        f"🔢 Всего профитов: <b>{result['profits_count']}</b>",
        parse_mode="HTML"
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Ваша заявка на профит успешно проверена и одобрена!</b>\n\n"
                f"➕ <b>Сумма профита:</b> +{amount:g} GRAM\n"
                f"💰 <b>Начислено на баланс:</b> {amount:g} GRAM\n"
                f"🔢 <b>Всего твоих профитов:</b> {result['profits_count']}\n"
                f"💸 <b>Всего заработано:</b> {result['total_earned']:g} GRAM\n"
                f"💰 <b>Текущий баланс к выводу:</b> {result['balance']:g} GRAM\n\n"
                "<i>Теперь вы можете подать заявку на выплату средств в панели!</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить воркера {user_id}: {e}")

@router.callback_query(F.data.startswith("admin_profit_rejc:"))
async def cb_admin_profit_reject(call: CallbackQuery, bot: Bot):
    if call.message.chat.id != ADMIN_CHAT_ID:
        await call.answer("⛔️ Модерация разрешена только в чате администрации!", show_alert=True)
        return

    report_id = int(call.data.split(":")[1])
    admin_name = f"@{call.from_user.username}" if call.from_user.username else (call.from_user.full_name or "Администратор")

    report = await get_profit_report(report_id)
    if not report or report["status"] != "pending":
        await call.answer("Этот отчёт уже обработан!", show_alert=True)
        return

    user_id = report["user_id"]
    await update_profit_report_status(report_id, "rejected")

    current_text = call.message.caption or call.message.html_text or call.message.text
    new_text = f"{current_text}\n\n❌ <b>Профит ОТКЛОНЁН ({html.escape(admin_name)})</b>"

    status_kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"❌ Отклонено: {admin_name}", callback_data="none")
        ]]
    )
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=new_text, parse_mode="HTML", reply_markup=status_kb)
        else:
            await call.message.edit_text(text=new_text, parse_mode="HTML", reply_markup=status_kb)
    except Exception as e:
        print(f"Не удалось обновить сообщение профита: {e}")

    await call.answer("Профит отклонён!")

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ <b>Ваш отчёт о профите на сумму {report['amount']:g} GRAM был отклонён администратором.</b>\n\n"
                "Если произошла ошибка, свяжитесь с куратором в командном чате."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить воркера {user_id}: {e}")

# ----------------- Модерация заявок на выплату -----------------

@router.callback_query(F.data.startswith("admin_payout_appr:"))
async def cb_admin_payout_approve(call: CallbackQuery, bot: Bot):
    if call.message.chat.id != ADMIN_CHAT_ID:
        await call.answer("⛔️ Доступно только в чате администрации!", show_alert=True)
        return

    request_id = int(call.data.split(":")[1])
    admin_name = f"@{call.from_user.username}" if call.from_user.username else (call.from_user.full_name or "Администратор")

    result = await approve_payout_and_add_to_kassa(request_id)
    if not result:
        await call.answer("Эта заявка уже обработана или воркер не найден!", show_alert=True)
        return

    amount = result["amount"]
    user_id = result["user_id"]
    new_kassa = result["total_kassa"]

    current_text = call.message.html_text or call.message.text
    new_text = (
        f"{current_text}\n\n"
        f"✅ <b>Выплата {amount:g} GRAM ВЫПОЛНЕНА ({html.escape(admin_name)})!</b>\n"
        f"🏦 <i>Профит автоматически зачислен в общую кассу команды: {new_kassa:g} GRAM</i>"
    )

    status_kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"✅ Выплачено и в кассе: {amount:g} GRAM", callback_data="none")
        ]]
    )
    try:
        await call.message.edit_text(new_text, parse_mode="HTML", reply_markup=status_kb)
    except Exception as e:
        print(f"Не удалось обновить сообщение выплаты: {e}")

    await call.answer("Выплата подтверждена и касса пополнена!")

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "💳 <b>Ваша заявка на выплату выполнена!</b>\n\n"
                f"➕ <b>Выплачено:</b> {amount:g} GRAM\n"
                f"💳 <b>Всего выплат за всё время:</b> {result['total_payouts']:g} GRAM\n"
                f"💰 <b>Остаток к выводу:</b> {result['balance']:g} GRAM\n\n"
                "<i>Средства переведены на указанные реквизиты. Спасибо за отличную работу!</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить воркера {user_id}: {e}")

@router.callback_query(F.data.startswith("admin_payout_rejc:"))
async def cb_admin_payout_reject(call: CallbackQuery, bot: Bot):
    if call.message.chat.id != ADMIN_CHAT_ID:
        await call.answer("⛔️ Доступно только в чате администрации!", show_alert=True)
        return

    request_id = int(call.data.split(":")[1])
    admin_name = f"@{call.from_user.username}" if call.from_user.username else (call.from_user.full_name or "Администратор")

    req = await get_payout_request(request_id)
    if not req or req["status"] != "pending":
        await call.answer("Эта заявка уже обработана!", show_alert=True)
        return

    user_id = req["user_id"]
    await update_payout_request_status(request_id, "rejected")

    current_text = call.message.html_text or call.message.text
    new_text = f"{current_text}\n\n❌ <b>Выплата ОТКЛОНЕНА ({html.escape(admin_name)})</b>"

    status_kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"❌ Отклонено: {admin_name}", callback_data="none")
        ]]
    )
    try:
        await call.message.edit_text(new_text, parse_mode="HTML", reply_markup=status_kb)
    except Exception as e:
        print(f"Не удалось обновить сообщение выплаты: {e}")

    await call.answer("Выплата отклонена!")

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ <b>Ваша заявка на выплату {req['amount']:g} GRAM была отклонена.</b>\n\n"
                "Свяжитесь с куратором в чате команды для уточнения деталей."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить воркера {user_id}: {e}")
