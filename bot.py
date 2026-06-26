import logging
import threading
import warnings
from telegram.ext import Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler
from telegram import Bot
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID, TELEGRAM_DB_PATH,
    BALE_BOT_TOKEN, BALE_ADMIN_ID, BALE_DB_PATH, BALE_API_BASE_URL,
)
from database import Database
from scheduler import create_scheduler, reschedule_all
from handlers.start import (
    start_handler, menu_callback,
    handle_do_delete, handle_do_pause, handle_do_resume,
)
from handlers.create import create_conversation
from handlers.tasks import edit_conversation

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
warnings.filterwarnings("ignore", message=".*per_message.*")
logger = logging.getLogger(__name__)


def create_bot_app(token, admin_id, db_path, platform_name, base_url=None):
    db = Database(db_path)
    scheduler = create_scheduler()

    if base_url:
        bot = Bot(token=token, base_url=base_url)
        application = ApplicationBuilder().bot(bot).build()
    else:
        application = Application.builder().token(token).build()

    application.bot_data["admin_id"] = admin_id
    application.bot_data["db"] = db
    application.bot_data["scheduler"] = scheduler
    application.bot_data["platform"] = platform_name

    application.add_handler(CommandHandler("start", start_handler), group=0)
    application.add_handler(create_conversation, group=1)
    application.add_handler(edit_conversation, group=2)

    application.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu_(list|status|edit|delete|pause|resume|back)$"), group=0)
    application.add_handler(CallbackQueryHandler(handle_do_delete, pattern=r"^do_delete_\d+$"), group=0)
    application.add_handler(CallbackQueryHandler(handle_do_pause, pattern=r"^do_pause_\d+$"), group=0)
    application.add_handler(CallbackQueryHandler(handle_do_resume, pattern=r"^do_resume_\d+$"), group=0)

    return application


async def post_init(application: Application):
    await application.bot_data["db"].init_db()
    scheduler = application.bot_data["scheduler"]
    if not scheduler.running:
        scheduler.start()
    application.bot_data["scheduler_started"] = True
    await reschedule_all(
        scheduler,
        application.bot,
        application.bot_data["db"],
        application.bot_data["admin_id"],
    )
    logger.info(f"{application.bot_data['platform']} bot initialized, database ready, scheduler started.")


async def post_shutdown(application: Application):
    scheduler = application.bot_data.get("scheduler")
    if scheduler and application.bot_data.get("scheduler_started"):
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass
    logger.info(f"{application.bot_data.get('platform', 'Unknown')} scheduler shut down.")


def run_bot(app):
    app.post_init = post_init
    app.post_shutdown = post_shutdown
    app.run_polling(allowed_updates=["message", "callback_query"])


def main():
    threads = []

    if TELEGRAM_BOT_TOKEN:
        telegram_app = create_bot_app(
            TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID, TELEGRAM_DB_PATH, "Telegram"
        )
        t = threading.Thread(target=run_bot, args=(telegram_app,), daemon=True)
        threads.append(t)
        logger.info("Telegram bot starting...")

    if BALE_BOT_TOKEN:
        bale_app = create_bot_app(
            BALE_BOT_TOKEN, BALE_ADMIN_ID, BALE_DB_PATH, "Bale",
            base_url=BALE_API_BASE_URL
        )
        t = threading.Thread(target=run_bot, args=(bale_app,), daemon=True)
        threads.append(t)
        logger.info("Bale bot starting...")

    if not threads:
        logger.error("No bot tokens configured!")
        return

    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
