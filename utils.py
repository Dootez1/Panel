import html
import time
import asyncio
from pathlib import Path
from aiogram import Bot
from aiogram.types import FSInputFile, CallbackQuery
from config import BANNER_PATH
from database import (
    get_user, 
    get_kassa, 
    is_admin_user, 
    is_user_banned, 
    get_setting, 
    set_setting,
    get_project_links,
    set_user_subscription
)
from keyboards import worker_panel_keyboard, subscription_keyboard

_LAST_BOT_MSGS: dict[int, int] = {}

async def safe_delete_message(bot: Bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def get_last_bot_msg(chat_id: int) -> int | None:
    if chat_id in _LAST_BOT_MSGS:
        return _LAST_BOT_MSGS[chat_id]
    val = await get_setting(f"last_msg_{chat_id}")
    if val and val.isdigit():
        _LAST_BOT_MSGS[chat_id] = int(val)
        return int(val)
    return None

async def set_last_bot_msg(chat_id: int, message_id: int):
    _LAST_BOT_MSGS[chat_id] = message_id
    try:
        await set_setting(f"last_msg_{chat_id}", str(message_id))
    except Exception:
        pass

async def clean_render(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup=None,
    photo_path: str | Path | None = None,
    photo_id: str | None = None,
    call: CallbackQuery | None = None,
    disable_web_page_preview: bool = True
) -> int | None:
    """
    Renders or edits a message in-place ensuring the chat always retains exactly ONE active bot message.
    """
    # 1. When called via CallbackQuery
    if call and call.message and call.message.chat.id == chat_id:
        has_media = bool(photo_path or photo_id)
        msg_has_photo = bool(call.message.photo)

        if has_media:
            photo = photo_id if photo_id else FSInputFile(str(photo_path))
            if msg_has_photo:
                try:
                    await call.message.edit_caption(
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                    await set_last_bot_msg(chat_id, call.message.message_id)
                    return call.message.message_id
                except Exception:
                    pass
            # If caption edit failed or message had no photo: replace message
            await safe_delete_message(bot, chat_id, call.message.message_id)
            new_msg = await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            await set_last_bot_msg(chat_id, new_msg.message_id)
            return new_msg.message_id

        else:
            # Pure text required
            if msg_has_photo:
                # Cannot edit photo to text; delete previous photo message
                await safe_delete_message(bot, chat_id, call.message.message_id)
                new_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    disable_web_page_preview=disable_web_page_preview
                )
                await set_last_bot_msg(chat_id, new_msg.message_id)
                return new_msg.message_id
            else:
                try:
                    await call.message.edit_text(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup,
                        disable_web_page_preview=disable_web_page_preview
                    )
                    await set_last_bot_msg(chat_id, call.message.message_id)
                    return call.message.message_id
                except Exception:
                    pass
                await safe_delete_message(bot, chat_id, call.message.message_id)
                new_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    disable_web_page_preview=disable_web_page_preview
                )
                await set_last_bot_msg(chat_id, new_msg.message_id)
                return new_msg.message_id

    # 2. When called outside CallbackQuery (e.g. from user Message, /start, /admin)
    last_id = await get_last_bot_msg(chat_id)
    if last_id:
        await safe_delete_message(bot, chat_id, last_id)

    if photo_path or photo_id:
        photo = photo_id if photo_id else FSInputFile(str(photo_path))
        new_msg = await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        new_msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview
        )

    await set_last_bot_msg(chat_id, new_msg.message_id)
    return new_msg.message_id

def format_panel_caption(user_id: int, reg_date: str, profits_count: int, total_earned: float, total_payouts: float, kassa: float) -> str:
    earned_str = f"{total_earned:g}" if isinstance(total_earned, (int, float)) else str(total_earned)
    payouts_str = f"{total_payouts:g}" if isinstance(total_payouts, (int, float)) else str(total_payouts)
    kassa_str = f"{kassa:g}" if isinstance(kassa, (int, float)) else str(kassa)
    balance = max(0.0, round(float(total_earned or 0.0) - float(total_payouts or 0.0), 2))
    balance_str = f"{balance:g}"

    return (
        "👋 <b>Добро пожаловать в панель — Haster TEAM</b>\n\n"
        f"🆔 <b>ID-аккаунта воркера</b> — [<code>{user_id}</code>]\n\n"
        f"📅 <b>Дата твоей регистрации в нашей команде</b> — <b>{reg_date}</b>\n\n"
        f"🔢 <b>Количество твоих профитов в нашей команде</b> — <b>{profits_count}</b>\n\n"
        f"💸 <b>Количество заработанной суммы в нашей команде</b> — <b>{earned_str} GRAM</b>\n\n"
        f"💳 <b>Сумма твоих выплат</b> — <b>{payouts_str} GRAM</b>\n\n"
        f"💰 <b>Доступно к выводу</b> — <b>{balance_str} GRAM</b>\n\n"
        f"🏦 <b>Общая касса команды</b> — <b>{kassa_str} GRAM</b>"
    )

async def show_worker_panel(bot: Bot, user_id: int, target_chat_id: int | None = None, call: CallbackQuery | None = None):
    chat_id = target_chat_id or user_id

    # Check ban status
    if await is_user_banned(user_id):
        await clean_render(
            bot=bot,
            chat_id=chat_id,
            text="⛔️ <b>Ваш аккаунт заблокирован администрацией команды Haster TEAM.</b>",
            call=call
        )
        return

    user = await get_user(user_id)
    reg_date = user["reg_date"] if user and user["reg_date"] else "Не указана"
    profits_count = user["profits_count"] if user else 0
    total_earned = user["total_earned"] if user else 0.0
    total_payouts = user["total_payouts"] if user and "total_payouts" in user.keys() and user["total_payouts"] else 0.0
    kassa = await get_kassa()

    is_admin = await is_admin_user(user_id, bot)
    caption = format_panel_caption(user_id, reg_date, profits_count, total_earned, total_payouts, kassa)
    keyboard = worker_panel_keyboard(is_admin=is_admin)

    photo_path = BANNER_PATH if BANNER_PATH.exists() else None
    await clean_render(
        bot=bot,
        chat_id=chat_id,
        text=caption,
        reply_markup=keyboard,
        photo_path=photo_path,
        call=call
    )

# ==================== Mandatory Subscription ====================

_SUB_CACHE: dict[int, tuple[bool, float]] = {}  # user_id -> (is_sub, timestamp)
_INACCESSIBLE_TARGETS: dict[str | int, float] = {}  # target -> timestamp when 'inaccessible' was seen

def extract_chat_target(url: str) -> str | None:
    if not url:
        return None
    cleaned = url.strip()
    if cleaned.startswith("@"):
        return cleaned
    cleaned = cleaned.replace("https://t.me/", "").replace("http://t.me/", "")
    cleaned = cleaned.replace("t.me/", "").strip("/")
    if cleaned.startswith("+") or cleaned.startswith("joinchat/"):
        return None
    if cleaned and "/" not in cleaned and "?" not in cleaned:
        return f"@{cleaned}"
    return None

async def get_required_channels_list() -> list[dict]:
    links = await get_project_links()
    reserv_url = links.get("reserv_url") or "https://t.me/rezerv_haster_team"
    perehodnik_url = links.get("perehodnik_url") or "https://t.me/haster_tt"
    chat_url = links.get("chat_url") or "https://t.me/+C_PtTHkOsDExMGJi"

    return [
        {
            "key": "reserv",
            "name": "📢 Резервный канал",
            "url": reserv_url,
            "target": extract_chat_target(reserv_url) or -1003769326306
        },
        {
            "key": "perehodnik",
            "name": "🔗 Переходник",
            "url": perehodnik_url,
            "target": extract_chat_target(perehodnik_url) or -1003926846080
        },
        {
            "key": "chat",
            "name": "💬 Чат команды",
            "url": chat_url,
            "target": extract_chat_target(chat_url)
        }
    ]

async def check_user_subscription(
    bot: Bot, 
    user_id: int, 
    bypass_cache: bool = False,
    is_verifying: bool = False
) -> tuple[bool, list[dict]]:
    # Admins are exempt from subscription check
    if await is_admin_user(user_id, bot):
        return True, []

    now = time.time()
    if not bypass_cache and user_id in _SUB_CACHE:
        is_sub, cached_at = _SUB_CACHE[user_id]
        if now - cached_at < 180.0:
            return is_sub, []

    user = await get_user(user_id)
    has_confirmed_db = bool(user and "is_subscribed" in user.keys() and user["is_subscribed"])

    # If user already verified in DB, allow normal actions without stalling on Telegram API calls
    if has_confirmed_db and not is_verifying and not bypass_cache:
        _SUB_CACHE[user_id] = (True, now)
        return True, []

    channels = await get_required_channels_list()

    # If user hasn't verified before and is not currently clicking verify, block them immediately
    if not has_confirmed_db and not is_verifying:
        _SUB_CACHE[user_id] = (False, now)
        return False, channels

    unsubscribed = []

    for ch in channels:
        target = ch.get("target")
        if target:
            # Skip if we already know Telegram forbids inspecting member list on this channel (bot not admin)
            if target in _INACCESSIBLE_TARGETS:
                if now - _INACCESSIBLE_TARGETS[target] < 300.0:
                    continue

            try:
                member = await asyncio.wait_for(
                    bot.get_chat_member(chat_id=target, user_id=user_id),
                    timeout=2.0
                )
                # If Telegram confirmed status is left or kicked -> definitely not subscribed
                if member.status in ("left", "kicked"):
                    unsubscribed.append(ch)
            except asyncio.TimeoutError:
                # If network times out, do not stall user
                pass
            except Exception as e:
                err_str = str(e).lower()
                if "member list is inaccessible" in err_str:
                    _INACCESSIBLE_TARGETS[target] = now
        else:
            # Private invite links without target chat ID
            pass

    is_subscribed = (len(unsubscribed) == 0)

    # Sync with DB
    if not is_subscribed:
        if has_confirmed_db:
            await set_user_subscription(user_id, False)
    elif is_verifying:
        await set_user_subscription(user_id, True)

    _SUB_CACHE[user_id] = (is_subscribed, now)
    return is_subscribed, unsubscribed

async def send_subscription_prompt(bot: Bot, user_id: int, call: CallbackQuery | None = None):
    links = await get_project_links()
    kb = subscription_keyboard(links)
    text = (
        "⚠️ <b>Присоединитесь для работы бота!</b>\n\n"
        "Чтобы получить полный доступ ко всем функциям <b>Haster TEAM Bot</b>, "
        "обязательно подпишитесь на все ресурсы команды ниже:\n\n"
        "📢 <b>Резервный канал</b> — важные анонсы и новости команды\n"
        "🔗 <b>Переходник</b> — рабочие зеркала и контакты\n"
        "💬 <b>Чат команды</b> — пространство для воркеров\n\n"
        "После вступления нажмите кнопку «<b>✅ Проверить подписку</b>» 👇"
    )
    await clean_render(
        bot=bot,
        chat_id=user_id,
        text=text,
        reply_markup=kb,
        call=call
    )
