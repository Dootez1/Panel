from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHAT_URL, RESERV_URL, PEREHODNIK_URL

def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Заполнить заявку", callback_data="start_survey")]
        ]
    )

def subscription_keyboard(links: dict = None) -> InlineKeyboardMarkup:
    if links is None:
        links = {}
    reserv_url = links.get("reserv_url") or RESERV_URL
    perehodnik_url = links.get("perehodnik_url") or PEREHODNIK_URL
    chat_url = links.get("chat_url") or CHAT_URL
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Резервный канал", url=reserv_url)],
            [InlineKeyboardButton(text="🔗 Переходник", url=perehodnik_url)],
            [InlineKeyboardButton(text="💬 Чат команды", url=chat_url)],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")]
        ]
    )

def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Отправить на модерацию", callback_data="submit_app")],
            [InlineKeyboardButton(text="🔄 Заполнить заново", callback_data="restart_app")]
        ]
    )

# Group moderation keyboards (Chat group)
def admin_moderation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve:{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject:{user_id}")
            ]
        ]
    )

def profit_moderation_keyboard(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить профит", callback_data=f"admin_profit_appr:{report_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_profit_rejc:{report_id}")
            ]
        ]
    )

def payout_moderation_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выплачено", callback_data=f"admin_payout_appr:{request_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_payout_rejc:{request_id}")
            ]
        ]
    )

# Worker panel
def worker_panel_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📩 Подать заявку на профит", callback_data="panel_submit_profit")],
        [InlineKeyboardButton(text="📩 Подать заявку на выплату", callback_data="panel_payout")],
        [InlineKeyboardButton(text="📰 Просмотреть статус отправленных заявок", callback_data="panel_status")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="panel_profile")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="open_admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def work_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤖 1. OTC-бот", callback_data="work_type:otc")],
            [InlineKeyboardButton(text="🏷 2. Оффер", callback_data="work_type:offer")],
            [InlineKeyboardButton(text="🛡 3. Гарант", callback_data="work_type:guarantor")],
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_panel")]
        ]
    )

def confirm_profit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Отправить на проверку", callback_data="send_profit_report")],
            [InlineKeyboardButton(text="🔄 Заполнить заново", callback_data="panel_submit_profit")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )

def profile_keyboard(chat_url: str = CHAT_URL, reserv_url: str = RESERV_URL, perehodnik_url: str = PEREHODNIK_URL) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Чат команды", url=chat_url)],
            [
                InlineKeyboardButton(text="📢 Резерв", url=reserv_url),
                InlineKeyboardButton(text="🔗 Переходник", url=perehodnik_url)
            ],
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_panel")]
        ]
    )

def back_to_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_panel")]
        ]
    )

def cancel_fsm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )

# ==================== In-Bot Admin Panel Keyboards ====================

def admin_main_keyboard(stats: dict) -> InlineKeyboardMarkup:
    p_apps = stats.get("pending_apps_count", 0)
    p_profs = stats.get("pending_profits_count", 0)
    p_pays = stats.get("pending_payouts_count", 0)
    badge = f"📝{p_apps} | 💰{p_profs} | 💳{p_pays}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📥 Очередь модерации ({badge})", callback_data="adm_mod_menu")],
            [
                InlineKeyboardButton(text="👥 Воркеры", callback_data="adm_workers_menu"),
                InlineKeyboardButton(text="🏆 Топ воркеров", callback_data="adm_top_workers")
            ],
            [
                InlineKeyboardButton(text="🏦 Касса команды", callback_data="adm_kassa_menu"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast_menu")
            ],
            [
                InlineKeyboardButton(text="⚙️ Ссылки и настройки", callback_data="adm_settings_menu"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="adm_refresh")
            ],
            [InlineKeyboardButton(text="◀️ В панель воркера", callback_data="back_to_panel")]
        ]
    )

def admin_moderation_menu_keyboard(stats: dict) -> InlineKeyboardMarkup:
    p_apps = stats.get("pending_apps_count", 0)
    p_profs = stats.get("pending_profits_count", 0)
    p_pays = stats.get("pending_payouts_count", 0)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📝 Анкеты на вступление [{p_apps}]", callback_data="adm_mod_apps:0")],
            [InlineKeyboardButton(text=f"💰 Заявки на профит [{p_profs}]", callback_data="adm_mod_profits:0")],
            [InlineKeyboardButton(text=f"💳 Заявки на выплату [{p_pays}]", callback_data="adm_mod_payouts:0")],
            [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="adm_back_main")]
        ]
    )

def admin_mod_app_card_keyboard(app_id: int, user_id: int, current_idx: int, total_count: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_app_ok:{app_id}:{user_id}:{current_idx}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_app_no:{app_id}:{user_id}:{current_idx}")
        ]
    ]
    nav_row = []
    if current_idx > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"adm_mod_apps:{current_idx - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{current_idx + 1} / {total_count}", callback_data="none"))
    if current_idx < total_count - 1:
        nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"adm_mod_apps:{current_idx + 1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="◀️ В меню модерации", callback_data="adm_mod_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_mod_profit_card_keyboard(report_id: int, user_id: int, current_idx: int, total_count: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="💰 Одобрить и начислить GRAM", callback_data=f"adm_prof_ok:{report_id}:{user_id}:{current_idx}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_prof_no:{report_id}:{user_id}:{current_idx}")
        ]
    ]
    nav_row = []
    if current_idx > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"adm_mod_profits:{current_idx - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{current_idx + 1} / {total_count}", callback_data="none"))
    if current_idx < total_count - 1:
        nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"adm_mod_profits:{current_idx + 1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="◀️ В меню модерации", callback_data="adm_mod_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_mod_payout_card_keyboard(req_id: int, user_id: int, current_idx: int, total_count: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Выплачено (в кассу)", callback_data=f"adm_pay_ok:{req_id}:{user_id}:{current_idx}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_pay_no:{req_id}:{user_id}:{current_idx}")
        ]
    ]
    nav_row = []
    if current_idx > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"adm_mod_payouts:{current_idx - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{current_idx + 1} / {total_count}", callback_data="none"))
    if current_idx < total_count - 1:
        nav_row.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"adm_mod_payouts:{current_idx + 1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="◀️ В меню модерации", callback_data="adm_mod_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_workers_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти воркера по ID / @username", callback_data="adm_user_search")],
            [InlineKeyboardButton(text="🏆 Топ-10 воркеров по заработку", callback_data="adm_top_workers")],
            [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="adm_back_main")]
        ]
    )

def admin_user_search_results_keyboard(users: list) -> InlineKeyboardMarkup:
    buttons = []
    for u in users:
        uid = u["user_id"]
        uname = f"@{u['username']}" if u["username"] else u["full_name"]
        ban_mark = "🚫 " if u["is_banned"] else ""
        buttons.append([InlineKeyboardButton(text=f"{ban_mark}{uname} ({uid})", callback_data=f"adm_view_u:{uid}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад к поиску", callback_data="adm_workers_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_user_card_keyboard(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_btn_text = "🟢 Разблокировать воркера" if is_banned else "🚫 Заблокировать воркера"
    ban_callback = f"adm_u_unban:{user_id}" if is_banned else f"adm_u_ban:{user_id}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Начислить профит", callback_data=f"adm_u_prof:{user_id}"),
                InlineKeyboardButton(text="💳 Зафиксировать выплату", callback_data=f"adm_u_pay:{user_id}")
            ],
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data=f"adm_u_bal:{user_id}"),
                InlineKeyboardButton(text="🏆 Заработано (Топ)", callback_data=f"adm_u_earned:{user_id}")
            ],
            [
                InlineKeyboardButton(text="💬 Написать в ЛС", callback_data=f"adm_u_msg:{user_id}"),
                InlineKeyboardButton(text=ban_btn_text, callback_data=ban_callback)
            ],
            [
                InlineKeyboardButton(text="🔍 Другой воркер", callback_data="adm_user_search"),
                InlineKeyboardButton(text="👑 В админку", callback_data="adm_back_main")
            ]
        ]
    )

def admin_kassa_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Пополнить кассу", callback_data="adm_kassa_add"),
                InlineKeyboardButton(text="➖ Списать из кассы", callback_data="adm_kassa_sub")
            ],
            [InlineKeyboardButton(text="✏️ Установить баланс кассы", callback_data="adm_kassa_set")],
            [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="adm_back_main")]
        ]
    )

def admin_broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Создать новую рассылку", callback_data="adm_bc_create")],
            [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="adm_back_main")]
        ]
    )

def admin_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать отправку", callback_data="adm_bc_start")],
            [InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="adm_bc_cancel")]
        ]
    )

def admin_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Ссылка на Чат команды", callback_data="adm_set_link:chat_url")],
            [InlineKeyboardButton(text="✏️ Ссылка на Резерв", callback_data="adm_set_link:reserv_url")],
            [InlineKeyboardButton(text="✏️ Ссылка на Переходник", callback_data="adm_set_link:perehodnik_url")],
            [
                InlineKeyboardButton(text="👥 Список админов", callback_data="adm_admins_list"),
                InlineKeyboardButton(text="➕ Добавить админа", callback_data="adm_add_admin")
            ],
            [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="adm_back_main")]
        ]
    )

def admin_cancel_inline_keyboard(callback_target: str = "adm_back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=callback_target)]
        ]
    )
