from aiogram.fsm.state import State, StatesGroup

class ApplicationState(StatesGroup):
    q1_source = State()
    q2_time = State()
    q3_experience = State()
    confirm = State()

class ProfitOTCState(StatesGroup):
    deal_code = State()
    nft_links = State()
    screenshot = State()
    confirm = State()

class ProfitOfferState(StatesGroup):
    nft_links = State()
    screenshot = State()
    confirm = State()

class ProfitGuarantorState(StatesGroup):
    nft_links = State()
    screenshot = State()
    confirm = State()

class RequestPayoutState(StatesGroup):
    amount = State()
    wallet = State()

class AdminApproveProfitState(StatesGroup):
    waiting_amount = State()

# In-bot Admin Panel FSM States
class AdminSearchUserState(StatesGroup):
    waiting_query = State()

class AdminUserActionState(StatesGroup):
    waiting_profit_amount = State()
    waiting_payout_amount = State()
    waiting_balance = State()
    waiting_direct_message = State()

class AdminKassaActionState(StatesGroup):
    waiting_set = State()
    waiting_add = State()
    waiting_sub = State()

class AdminBroadcastState(StatesGroup):
    waiting_content = State()
    confirm_send = State()

class AdminSettingsActionState(StatesGroup):
    waiting_link = State()
    waiting_add_admin = State()
