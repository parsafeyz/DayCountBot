import os
from dotenv import load_dotenv

load_dotenv()

# Telegram config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BOT_TOKEN", ""))
TELEGRAM_ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", os.getenv("ADMIN_ID", "0")))
TELEGRAM_DB_PATH = os.getenv("TELEGRAM_DB_PATH", "telegram_daycount.db")

# Bale config
BALE_BOT_TOKEN = os.getenv("BALE_BOT_TOKEN", "")
BALE_ADMIN_ID = int(os.getenv("BALE_ADMIN_ID", "0"))
BALE_DB_PATH = os.getenv("BALE_DB_PATH", "bale_daycount.db")

# Bale API base URL (include /bot suffix)
BALE_API_BASE_URL = "https://tapi.bale.ai/bot"

DEFAULT_TEMPLATE_UP = "Day {current_day} | {name}"
DEFAULT_TEMPLATE_DOWN = "{days_left} days left to {name} | {current_day} of {total_days}"

# Create wizard states
(
    ASK_NAME,
    ASK_MODE,
    ASK_START_DATE,
    ASK_END_DATE,
    ASK_TARGET_CHAT,
    ASK_FREQUENCY,
    ASK_TIMES,
    ASK_TEMPLATE,
    ASK_TEMPLATE_TEXT,
    CONFIRM,
) = range(10)

# Edit wizard states
(
    EDIT_CHOOSE_FIELD,
    EDIT_NAME,
    EDIT_MODE,
    EDIT_START_DATE,
    EDIT_END_DATE,
    EDIT_TARGET_CHAT,
    EDIT_TEMPLATE,
    EDIT_SCHEDULES,
    EDIT_CONFIRM,
) = range(9, 18)
