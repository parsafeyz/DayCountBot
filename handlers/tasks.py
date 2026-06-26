import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
from config import (
    EDIT_CHOOSE_FIELD, EDIT_NAME, EDIT_MODE, EDIT_START_DATE,
    EDIT_END_DATE, EDIT_TARGET_CHAT, EDIT_TEMPLATE, EDIT_SCHEDULES, EDIT_CONFIRM,
    DEFAULT_TEMPLATE_UP, DEFAULT_TEMPLATE_DOWN,
)
from scheduler import schedule_task_jobs, remove_task_jobs
from helpers import build_task_summary, build_status_message
from .start import MAIN_MENU


async def handle_do_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[-1])
    db = context.bot_data["db"]
    admin_id = context.bot_data["admin_id"]
    task = await db.get_task(task_id)
    if not task or task["admin_id"] != admin_id:
        await query.edit_message_text("Task not found.", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    context.user_data["edit_task_id"] = task_id
    keyboard = [
        [InlineKeyboardButton("Name", callback_data="edit_name"),
         InlineKeyboardButton("Mode", callback_data="edit_mode")],
        [InlineKeyboardButton("Start Date", callback_data="edit_start_date"),
         InlineKeyboardButton("End Date", callback_data="edit_end_date")],
        [InlineKeyboardButton("Target Chat", callback_data="edit_target_chat"),
         InlineKeyboardButton("Template", callback_data="edit_template")],
        [InlineKeyboardButton("Schedule", callback_data="edit_schedule")],
        [InlineKeyboardButton("Back", callback_data="menu_back")],
    ]
    await query.edit_message_text(
        f"Editing task #{task_id}:\n{build_task_summary(task, await db.get_schedules(task_id))}\n\nWhat to edit?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return EDIT_CHOOSE_FIELD


async def edit_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "menu_back":
        await query.edit_message_text("Choose an action:", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    field = query.data.replace("edit_", "")
    context.user_data["edit_field"] = field
    prompts = {
        "name": "New name?",
        "mode": "New mode? (count_up / count_down)",
        "start_date": "New start date (YYYY-MM-DD)?",
        "end_date": "New end date (YYYY-MM-DD)?",
        "target_chat": "New target chat? (me, numeric ID, or @username)",
        "template": "New template? (or 'default')",
        "schedule": "New schedule? (comma-separated HH:MM times)",
    }
    await query.edit_message_text(prompts[field])
    state_map = {
        "name": EDIT_NAME, "mode": EDIT_MODE, "start_date": EDIT_START_DATE,
        "end_date": EDIT_END_DATE, "target_chat": EDIT_TARGET_CHAT,
        "template": EDIT_TEMPLATE, "schedule": EDIT_SCHEDULES,
    }
    return state_map[field]


async def edit_receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = context.bot_data["db"]
    field = context.user_data.get("edit_field")
    task_id = context.user_data["edit_task_id"]
    text = update.message.text.strip()

    if field == "name":
        await db.update_task(task_id, name=text)
    elif field == "mode":
        if text not in ("count_up", "count_down"):
            await update.message.reply_text("Invalid mode. Use count_up or count_down.")
            return EDIT_MODE
        await db.update_task(task_id, mode=text)
    elif field == "start_date":
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Invalid date format. Use YYYY-MM-DD.")
            return EDIT_START_DATE
        await db.update_task(task_id, start_date=text)
    elif field == "end_date":
        task = await db.get_task(task_id)
        try:
            end = datetime.strptime(text, "%Y-%m-%d").date()
            start = datetime.strptime(task["start_date"], "%Y-%m-%d").date()
        except ValueError:
            await update.message.reply_text("Invalid date format. Use YYYY-MM-DD.")
            return EDIT_END_DATE
        if end <= start:
            await update.message.reply_text("End date must be after start date.")
            return EDIT_END_DATE
        total_days = (end - start).days
        await db.update_task(task_id, total_days=total_days)
    elif field == "target_chat":
        if text.lower() == "me":
            chat_id = str(update.effective_chat.id)
            chat_type = "private"
        elif text.startswith("@"):
            chat_id = text
            chat_type = "channel"
        else:
            try:
                chat_id = str(int(text))
                chat_type = "group" if chat_id.startswith("-") else "private"
            except ValueError:
                await update.message.reply_text("Invalid. Use 'me', numeric ID, or @username.")
                return EDIT_TARGET_CHAT
        await db.update_task(task_id, target_chat_id=chat_id, chat_type=chat_type)
    elif field == "template":
        if text.lower() == "default":
            task = await db.get_task(task_id)
            text = DEFAULT_TEMPLATE_UP if task["mode"] == "count_up" else DEFAULT_TEMPLATE_DOWN
        await db.update_task(task_id, message_template=text)
    elif field == "schedule":
        parts = [t.strip() for t in text.split(",")]
        for t in parts:
            if not re.match(r"^\d{2}:\d{2}$", t):
                await update.message.reply_text(f"Invalid time: {t}. Use HH:MM.")
                return EDIT_SCHEDULES
        await db.delete_schedules(task_id)
        for t in parts:
            await db.add_schedule(task_id, t)

    await remove_task_jobs(context.bot_data["scheduler"], task_id)
    await schedule_task_jobs(context.bot_data["scheduler"], context.application.bot, db, task_id)

    task = await db.get_task(task_id)
    schedules = await db.get_schedules(task_id)
    keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
    await update.message.reply_text(
        f"Updated!\n\n{build_task_summary(task, schedules)}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.", reply_markup=MAIN_MENU)
    elif update.message:
        await update.message.reply_text("Cancelled.", reply_markup=MAIN_MENU)
    context.user_data.clear()
    return ConversationHandler.END


edit_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_do_edit, pattern=r"^do_edit_\d+$")],
    states={
        EDIT_CHOOSE_FIELD: [
            CallbackQueryHandler(edit_choose_field, pattern=r"^(edit_|menu_back)"),
        ],
        EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_value)],
        EDIT_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_value)],
        EDIT_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_value)],
        EDIT_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_value)],
        EDIT_TARGET_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_value)],
        EDIT_TEMPLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_value)],
        EDIT_SCHEDULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_value)],
    },
    fallbacks=[
        CommandHandler("cancel", edit_cancel),
        CallbackQueryHandler(edit_cancel, pattern=r"^menu_back$"),
    ],
)

tasks_handlers = [
    edit_conversation,
]
