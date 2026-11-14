import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "9173223180:AAG-EyCuLRcabnJvC5sV8SBBXf14WLr44Uw")

# Official admin group ID for Haster TEAM
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "-1003594237696"))

# Predefined Admin IDs (comma separated in .env, e.g. ADMIN_IDS=1234567,9876543)
ADMIN_IDS = [
    int(x.strip()) 
    for x in os.getenv("ADMIN_IDS", "").split(",") 
    if x.strip().isdigit()
]

BANNER_PATH = BASE_DIR / "photo_2026-11-13_17-19-03.jpg"
DB_PATH = BASE_DIR / "bot.db"

DEFAULT_CHAT_URL = "https://t.me/+C_PtTHkOsDExMGJi"
DEFAULT_RESERV_URL = "https://t.me/rezerv_haster_team"
DEFAULT_PEREHODNIK_URL = "https://t.me/haster_tt"

CHAT_URL = DEFAULT_CHAT_URL
RESERV_URL = DEFAULT_RESERV_URL
PEREHODNIK_URL = DEFAULT_PEREHODNIK_URL
