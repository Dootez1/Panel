import aiosqlite
from datetime import datetime
from config import (
    DB_PATH, 
    ADMIN_CHAT_ID, 
    ADMIN_IDS,
    DEFAULT_CHAT_URL, 
    DEFAULT_RESERV_URL, 
    DEFAULT_PEREHODNIK_URL
)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                status TEXT DEFAULT 'new', -- new, pending, approved, rejected, banned
                is_banned INTEGER DEFAULT 0,
                reg_date TEXT,
                profits_count INTEGER DEFAULT 0,
                total_earned REAL DEFAULT 0.0,
                total_payouts REAL DEFAULT 0.0,
                created_at TEXT
            )
        """)
        # Migrations: ensure columns exist
        for col, col_def in [
            ("total_payouts", "REAL DEFAULT 0.0"),
            ("is_banned", "INTEGER DEFAULT 0"),
            ("is_subscribed", "INTEGER DEFAULT 0")
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
            except Exception:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                q1_source TEXT,
                q2_time TEXT,
                q3_experience TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS profit_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                work_type TEXT,
                deal_code TEXT,
                nft_links TEXT,
                amount REAL,
                photo_id TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                created_at TEXT
            )
        """)
        for col in ["work_type", "deal_code", "nft_links", "photo_id"]:
            try:
                await db.execute(f"ALTER TABLE profit_reports ADD COLUMN {col} TEXT")
            except Exception:
                pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payout_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                wallet TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action_type TEXT,
                actor TEXT,
                details TEXT
            )
        """)
        await db.commit()

# ==================== Settings & Links ====================

async def get_setting(key: str, default: str | None = None) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None:
                return row[0]
            return default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value)
        )
        await db.commit()

async def get_project_links() -> dict[str, str]:
    chat_url = await get_setting("chat_url", DEFAULT_CHAT_URL)
    reserv_url = await get_setting("reserv_url", DEFAULT_RESERV_URL)
    perehodnik_url = await get_setting("perehodnik_url", DEFAULT_PEREHODNIK_URL)
    return {
        "chat_url": chat_url or DEFAULT_CHAT_URL,
        "reserv_url": reserv_url or DEFAULT_RESERV_URL,
        "perehodnik_url": perehodnik_url or DEFAULT_PEREHODNIK_URL
    }

async def set_project_link(key: str, url: str):
    await set_setting(key, url.strip())

# ==================== Admins Management ====================

async def get_admin_ids() -> list[int]:
    stored = await get_setting("admin_ids", "")
    ids = set(ADMIN_IDS)
    if stored:
        for x in stored.split(","):
            val = x.strip()
            if val.isdigit():
                ids.add(int(val))
    return list(ids)

async def add_admin_id(user_id: int):
    current = await get_admin_ids()
    if user_id not in current:
        current.append(user_id)
        await set_setting("admin_ids", ",".join(str(x) for x in current))

async def remove_admin_id(user_id: int):
    current = await get_admin_ids()
    if user_id in current:
        current.remove(user_id)
        await set_setting("admin_ids", ",".join(str(x) for x in current))

async def is_admin_user(user_id: int, bot=None) -> bool:
    admin_list = await get_admin_ids()
    if user_id in admin_list:
        return True

    # If bot instance provided, dynamically check membership in official admin group
    if bot and ADMIN_CHAT_ID:
        try:
            member = await bot.get_chat_member(chat_id=ADMIN_CHAT_ID, user_id=user_id)
            if member.status in ("creator", "administrator"):
                await add_admin_id(user_id)
                return True
        except Exception:
            pass

    return False

# ==================== Kassa ====================

async def get_kassa() -> float:
    val = await get_setting("total_kassa")
    try:
        return float(val) if val else 0.0
    except ValueError:
        return 0.0

async def add_to_kassa(amount: float) -> float:
    current = await get_kassa()
    new_kassa = round(current + amount, 2)
    await set_setting("total_kassa", str(new_kassa))
    return new_kassa

async def set_kassa(amount: float) -> float:
    new_kassa = round(max(0.0, amount), 2)
    await set_setting("total_kassa", str(new_kassa))
    return new_kassa

# ==================== Statistics ====================

async def get_stats_summary() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        # Total users
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'approved' AND is_banned = 0") as cur:
            approved_workers = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'") as cur:
            pending_users = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1 OR status = 'banned'") as cur:
            banned_users = (await cur.fetchone())[0]

        async with db.execute("SELECT SUM(profits_count), SUM(total_earned), SUM(total_payouts) FROM users") as cur:
            row = await cur.fetchone()
            total_profits_count = row[0] or 0
            total_earned_sum = round(row[1] or 0.0, 2)
            total_payouts_sum = round(row[2] or 0.0, 2)

        async with db.execute("SELECT COUNT(*) FROM applications WHERE status = 'pending'") as cur:
            pending_apps_count = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM profit_reports WHERE status = 'pending'") as cur:
            pending_profits_count = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM payout_requests WHERE status = 'pending'") as cur:
            pending_payouts_count = (await cur.fetchone())[0]

    kassa = await get_kassa()
    total_balance_unpaid = max(0.0, round(total_earned_sum - total_payouts_sum, 2))

    return {
        "kassa": kassa,
        "total_users": total_users,
        "approved_workers": approved_workers,
        "pending_users": pending_users,
        "banned_users": banned_users,
        "total_profits_count": total_profits_count,
        "total_earned_sum": total_earned_sum,
        "total_payouts_sum": total_payouts_sum,
        "total_balance_unpaid": total_balance_unpaid,
        "pending_apps_count": pending_apps_count,
        "pending_profits_count": pending_profits_count,
        "pending_payouts_count": pending_payouts_count
    }

# ==================== Users ====================

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def is_user_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user:
        return False
    return bool(user["is_banned"] or user["status"] == "banned")

async def register_initial_user(user_id: int, username: str | None, full_name: str):
    user = await get_user(user_id)
    if not user:
        now_str = datetime.now().strftime("%d.%m.%Y")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, full_name, status, is_banned, profits_count, total_earned, total_payouts, created_at)
                VALUES (?, ?, ?, 'new', 0, 0, 0.0, 0.0, ?)
                """,
                (user_id, username or "", full_name, now_str)
            )
            await db.commit()
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username or "", full_name, user_id)
            )
            await db.commit()

async def set_user_status(user_id: int, status: str, reg_date: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if reg_date:
            await db.execute(
                "UPDATE users SET status = ?, reg_date = ? WHERE user_id = ?",
                (status, reg_date, user_id)
            )
        else:
            await db.execute(
                "UPDATE users SET status = ? WHERE user_id = ?",
                (status, user_id)
            )
        await db.commit()

async def set_user_ban_status(user_id: int, is_banned: bool):
    flag = 1 if is_banned else 0
    new_status = "banned" if is_banned else "approved"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_banned = ?, status = CASE WHEN ? = 1 THEN 'banned' ELSE 'approved' END WHERE user_id = ?",
            (flag, flag, user_id)
        )
        await db.commit()

async def set_user_subscription(user_id: int, is_subscribed: bool):
    flag = 1 if is_subscribed else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_subscribed = ? WHERE user_id = ?",
            (flag, user_id)
        )
        await db.commit()

async def set_user_balance(user_id: int, new_balance: float):
    new_balance = round(max(0.0, new_balance), 2)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()
        if not user:
            return None
        total_payouts = user["total_payouts"] or 0.0
        # total_earned = total_payouts + new_balance
        new_total_earned = round(total_payouts + new_balance, 2)
        await db.execute(
            "UPDATE users SET total_earned = ? WHERE user_id = ?",
            (new_total_earned, user_id)
        )
        await db.commit()
        return {
            "user_id": user_id,
            "balance": new_balance,
            "total_earned": new_total_earned,
            "total_payouts": total_payouts
        }

async def set_user_stats(user_id: int, earned: float | None = None, profits_count: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if earned is not None and profits_count is not None:
            await db.execute(
                "UPDATE users SET total_earned = ?, profits_count = ? WHERE user_id = ?",
                (round(max(0.0, earned), 2), max(0, profits_count), user_id)
            )
        elif earned is not None:
            await db.execute(
                "UPDATE users SET total_earned = ? WHERE user_id = ?",
                (round(max(0.0, earned), 2), user_id)
            )
        elif profits_count is not None:
            await db.execute(
                "UPDATE users SET profits_count = ? WHERE user_id = ?",
                (max(0, profits_count), user_id)
            )
        await db.commit()

async def search_users(query: str, limit: int = 15) -> list:
    query = query.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if query.isdigit() or (query.startswith("-") and query[1:].isdigit()):
            uid = int(query)
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ? OR user_id LIKE ? LIMIT ?",
                (uid, f"%{query}%", limit)
            ) as cur:
                return await cur.fetchall()
        else:
            clean_q = query.lstrip("@")
            async with db.execute(
                """
                SELECT * FROM users 
                WHERE LOWER(username) LIKE LOWER(?) OR LOWER(full_name) LIKE LOWER(?)
                ORDER BY profits_count DESC
                LIMIT ?
                """,
                (f"%{clean_q}%", f"%{clean_q}%", limit)
            ) as cur:
                return await cur.fetchall()

async def get_top_workers(limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM users 
            WHERE status = 'approved' AND is_banned = 0
            ORDER BY total_earned DESC, profits_count DESC
            LIMIT ?
            """,
            (limit,)
        ) as cur:
            return await cur.fetchall()

async def get_all_broadcast_users() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned = 0") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

# ==================== Applications ====================

async def save_application(user_id: int, q1: str, q2: str, q3: str):
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO applications (user_id, q1_source, q2_time, q3_experience, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, q1, q2, q3, now_str)
        )
        await db.commit()

async def update_application_status(user_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE applications SET status = ? 
            WHERE id = (SELECT id FROM applications WHERE user_id = ? ORDER BY id DESC LIMIT 1)
            """,
            (status, user_id)
        )
        await db.commit()

async def update_application_by_id_status(app_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
        await db.commit()

async def get_pending_applications_list(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT a.id, a.user_id, a.q1_source, a.q2_time, a.q3_experience, a.status, a.created_at,
                   u.username, u.full_name
            FROM applications a
            LEFT JOIN users u ON a.user_id = u.user_id
            WHERE a.status = 'pending'
            ORDER BY a.id ASC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cur:
            return await cur.fetchall()

async def get_application_by_id(app_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT a.*, u.username, u.full_name
            FROM applications a
            LEFT JOIN users u ON a.user_id = u.user_id
            WHERE a.id = ?
        """
        async with db.execute(query, (app_id,)) as cur:
            return await cur.fetchone()

# ==================== Profits ====================

async def add_user_profit(identifier: str | int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        user = None
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.lstrip("-").isdigit()):
            uid = int(identifier)
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)) as cur:
                user = await cur.fetchone()
        else:
            uname = str(identifier).lstrip("@")
            async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (uname,)) as cur:
                user = await cur.fetchone()
        
        if not user:
            return None

        new_count = (user["profits_count"] or 0) + 1
        new_earned = round((user["total_earned"] or 0.0) + amount, 2)
        total_payouts = user["total_payouts"] or 0.0
        balance = max(0.0, round(new_earned - total_payouts, 2))

        await db.execute(
            "UPDATE users SET profits_count = ?, total_earned = ? WHERE user_id = ?",
            (new_count, new_earned, user["user_id"])
        )
        await db.commit()

        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "profits_count": new_count,
            "total_earned": new_earned,
            "total_payouts": total_payouts,
            "balance": balance,
            "amount": amount
        }

async def create_profit_report(
    user_id: int, 
    work_type: str = "Оффер", 
    deal_code: str = "", 
    nft_links: str = "", 
    photo_id: str = "",
    amount: float = 0.0
) -> int:
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO profit_reports (user_id, amount, work_type, deal_code, nft_links, photo_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, amount, work_type, deal_code, nft_links, photo_id, now_str)
        )
        await db.commit()
        return cur.lastrowid

async def approve_profit_report(report_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM profit_reports WHERE id = ?", (report_id,)) as cur:
            report = await cur.fetchone()
        
        if not report or report["status"] != "pending":
            return None

        user_id = report["user_id"]

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()

        if not user:
            return None

        new_profits_count = (user["profits_count"] or 0) + 1
        new_earned = round((user["total_earned"] or 0.0) + amount, 2)
        total_payouts = user["total_payouts"] or 0.0
        balance = max(0.0, round(new_earned - total_payouts, 2))

        await db.execute(
            "UPDATE users SET profits_count = ?, total_earned = ? WHERE user_id = ?",
            (new_profits_count, new_earned, user_id)
        )
        await db.execute(
            "UPDATE profit_reports SET status = 'approved', amount = ? WHERE id = ?",
            (amount, report_id)
        )
        await db.commit()

        return {
            "user_id": user_id,
            "username": user["username"],
            "full_name": user["full_name"],
            "amount": amount,
            "work_type": report["work_type"],
            "profits_count": new_profits_count,
            "total_earned": new_earned,
            "total_payouts": total_payouts,
            "balance": balance
        }

async def get_profit_report(report_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM profit_reports WHERE id = ?", (report_id,)) as cur:
            return await cur.fetchone()

async def update_profit_report_status(report_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE profit_reports SET status = ? WHERE id = ?", (status, report_id))
        await db.commit()

async def get_pending_profit_reports_list(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT p.*, u.username, u.full_name
            FROM profit_reports p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.status = 'pending'
            ORDER BY p.id ASC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cur:
            return await cur.fetchall()

# ==================== Payouts ====================

async def add_user_payout(identifier: str | int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        user = None
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.lstrip("-").isdigit()):
            uid = int(identifier)
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (uid,)) as cur:
                user = await cur.fetchone()
        else:
            uname = str(identifier).lstrip("@")
            async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (uname,)) as cur:
                user = await cur.fetchone()
        
        if not user:
            return None

        new_payouts = round((user["total_payouts"] or 0.0) + amount, 2)
        total_earned = user["total_earned"] or 0.0
        balance = max(0.0, round(total_earned - new_payouts, 2))

        await db.execute(
            "UPDATE users SET total_payouts = ? WHERE user_id = ?",
            (new_payouts, user["user_id"])
        )
        await db.commit()

        # Автоматическое пополнение кассы команды при выплате
        new_kassa = await add_to_kassa(amount)

        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "total_payouts": new_payouts,
            "total_earned": total_earned,
            "balance": balance,
            "total_kassa": new_kassa,
            "amount": amount
        }

async def has_pending_payout(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM payout_requests WHERE user_id = ? AND status = 'pending'",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return bool(row and row[0] > 0)

async def create_payout_request(user_id: int, amount: float, wallet: str) -> int:
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO payout_requests (user_id, amount, wallet, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (user_id, amount, wallet, now_str)
        )
        await db.commit()
        return cur.lastrowid

async def get_payout_request(request_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payout_requests WHERE id = ?", (request_id,)) as cur:
            return await cur.fetchone()

async def update_payout_request_status(request_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payout_requests SET status = ? WHERE id = ?", (status, request_id))
        await db.commit()

async def approve_payout_and_add_to_kassa(request_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM payout_requests WHERE id = ?", (request_id,)) as cur:
            req = await cur.fetchone()

        if not req or req["status"] != "pending":
            return None

        amount = float(req["amount"])
        user_id = req["user_id"]

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()

        if not user:
            return None

        new_payouts = round((user["total_payouts"] or 0.0) + amount, 2)
        total_earned = user["total_earned"] or 0.0
        balance = max(0.0, round(total_earned - new_payouts, 2))

        await db.execute(
            "UPDATE users SET total_payouts = ? WHERE user_id = ?",
            (new_payouts, user_id)
        )
        await db.execute("UPDATE payout_requests SET status = 'approved' WHERE id = ?", (request_id,))
        await db.commit()

        # Автоматически отправляем сумму профита в кассу команды
        new_kassa = await add_to_kassa(amount)

        return {
            "user_id": user_id,
            "username": user["username"],
            "full_name": user["full_name"],
            "amount": amount,
            "wallet": req["wallet"],
            "total_payouts": new_payouts,
            "total_earned": total_earned,
            "balance": balance,
            "total_kassa": new_kassa
        }

async def get_pending_payout_requests_list(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT p.*, u.username, u.full_name, u.total_earned, u.total_payouts
            FROM payout_requests p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.status = 'pending'
            ORDER BY p.id ASC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cur:
            return await cur.fetchall()

async def get_user_recent_activity(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM profit_reports WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (user_id,)
        ) as cur:
            profits = await cur.fetchall()
        async with db.execute(
            "SELECT * FROM payout_requests WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (user_id,)
        ) as cur:
            payouts = await cur.fetchall()
        return profits, payouts

# ==================== Web & Audit Logs ====================

async def log_activity(action_type: str, actor: str, details: str):
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO activity_logs (timestamp, action_type, actor, details) VALUES (?, ?, ?, ?)",
            (now_str, action_type, actor, details)
        )
        await db.commit()

async def get_activity_logs(limit: int = 100) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        ) as cur:
            return await cur.fetchall()

async def get_all_applications_list(limit: int = 100) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT a.*, u.username, u.full_name
            FROM applications a
            LEFT JOIN users u ON a.user_id = u.user_id
            ORDER BY a.id DESC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cur:
            return await cur.fetchall()

async def get_all_profit_reports_list(limit: int = 100) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT p.*, u.username, u.full_name, u.total_earned, u.total_payouts
            FROM profit_reports p
            LEFT JOIN users u ON p.user_id = u.user_id
            ORDER BY p.id DESC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cur:
            return await cur.fetchall()

async def get_all_payout_requests_list(limit: int = 100) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT p.*, u.username, u.full_name, u.total_earned, u.total_payouts
            FROM payout_requests p
            LEFT JOIN users u ON p.user_id = u.user_id
            ORDER BY p.id DESC
            LIMIT ?
        """
        async with db.execute(query, (limit,)) as cur:
            return await cur.fetchall()

