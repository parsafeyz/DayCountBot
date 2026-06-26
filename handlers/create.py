import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import (
    ASK_NAME, ASK_MODE, ASK_START_DATE, ASK_END_DATE,
    ASK_TARGET_CHAT, ASK_FREQUENCY, ASK_TIMES, ASK_TEMPLATE, ASK_TEMPLATE_TEXT, CONFIRM,
    DEFAULT_TEMPLATE_UP, DEFAULT_TEMPLATE_DOWN,
)
from scheduler import schedule_task_jobs
from .start import MAIN_MENU


async def create_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("Task name?")
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("Count Up", callback_data="count_up")],
        [InlineKeyboardButton("Count Down", callback_data="count_down")],
    ]
    await update.message.reply_text(
        f"Name: {context.user_data['name']}\nMode?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_MODE


async def ask_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = query.data
    await query.edit_message_text(
        f"Name: {context.user_data['name']}\n"
        f"Mode: {context.user_data['mode']}\n"
        "Start date (YYYY-MM-DD)?"
    )
    return ASK_START_DATE


async def ask_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Invalid date. Use YYYY-MM-DD.")
        return ASK_START_DATE
    context.user_data["start_date"] = text

    if context.user_data["mode"] == "count_down":
        await update.message.reply_text("End date (YYYY-MM-DD)?")
        return ASK_END_DATE

    return await go_to_target_chat(update, context)


async def ask_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        end = datetime.strptime(text, "%Y-%m-%d").date()
        start = datetime.strptime(context.user_data["start_date"], "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text("Invalid date. Use YYYY-MM-DD.")
        return ASK_END_DATE
    if end <= start:
        await update.message.reply_text("End date must be after start date.")
        return ASK_END_DATE
    context.user_data["end_date"] = text
    return await go_to_target_chat(update, context)


async def go_to_target_chat(update, context):
    await update.message.reply_text(
        "Target chat for reminders?\n\n"
        "- Type 'me' for your private chat\n"
        "- Type a numeric chat ID (e.g. -1001234567890)\n"
        "- Type a @username for channels/groups"
    )
    return ASK_TARGET_CHAT


async def ask_target_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
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
            await update.message.reply_text("Invalid. Use 'me', a numeric ID, or @username.")
            return ASK_TARGET_CHAT
    context.user_data["target_chat_id"] = chat_id
    context.user_data["chat_type"] = chat_type
    await update.message.reply_text("How many reminders per day? (1-10)")
    return ASK_FREQUENCY


async def ask_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        freq = int(update.message.text.strip())
        if freq < 1 or freq > 10:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Enter a number between 1 and 10.")
        return ASK_FREQUENCY
    context.user_data["frequency"] = freq
    await update.message.reply_text(
        f"Enter {freq} reminder time(s) separated by commas (HH:MM, 24h format).\n"
        f"Example: 09:00, 14:30, 21:00"
    )
    return ASK_TIMES


async def ask_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    freq = context.user_data["frequency"]
    parts = [t.strip() for t in update.message.text.split(",")]
    if len(parts) != freq:
        await update.message.reply_text(f"You entered {len(parts)} time(s), but need exactly {freq}. Try again.")
        return ASK_TIMES
    for t in parts:
        if not re.match(r"^\d{2}:\d{2}$", t):
            await update.message.reply_text(f"Invalid time format: {t}. Use HH:MM.")
            return ASK_TIMES
        h, m = map(int, t.split(":"))
        if h > 23 or m > 59:
            await update.message.reply_text(f"Invalid time: {t}.")
            return ASK_TIMES
    context.user_data["times"] = parts
    mode = context.user_data["mode"]
    default_tpl = DEFAULT_TEMPLATE_UP if mode == "count_up" else DEFAULT_TEMPLATE_DOWN
    keyboard = [
        [InlineKeyboardButton("Use Default", callback_data="tpl_default")],
        [InlineKeyboardButton("Custom Template", callback_data="tpl_custom")],
    ]
    await update.message.reply_text(
        f"Default template: {default_tpl}\n\n"
        f"Placeholders: {{current_day}}, {{total_days}}, {{days_left}}, {{date}}\n\n"
        f"Use default or custom?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_TEMPLATE


async def ask_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "tpl_default":
        mode = context.user_data["mode"]
        template = DEFAULT_TEMPLATE_UP if mode == "count_up" else DEFAULT_TEMPLATE_DOWN
        context.user_data["template"] = template
        return await show_confirm(update, context)
    else:
        await query.edit_message_text("Enter your custom template:")
        return ASK_TEMPLATE_TEXT


async def ask_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["template"] = update.message.text.strip()
    return await show_confirm(update, context)


async def show_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    d = context.user_data
    times_str = ", ".join(d["times"])
    if d["mode"] == "count_down":
        total = (datetime.strptime(d["end_date"], "%Y-%m-%d").date() - datetime.strptime(d["start_date"], "%Y-%m-%d").date()).days
        duration = f"Start: {d['start_date']}\nEnd: {d['end_date']}\nTotal days: {total}"
    else:
        duration = f"Start: {d['start_date']}"

    summary = (
        f"Confirm task creation:\n\n"
        f"Name: {d['name']}\n"
        f"Mode: {d['mode']}\n"
        f"{duration}\n"
        f"Target: {d['target_chat_id']} ({d['chat_type']})\n"
        f"Times: {times_str}\n"
        f"Template: {d['template']}"
    )
    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data="confirm_yes")],
        [InlineKeyboardButton("Cancel", callback_data="confirm_no")],
    ]
    if update.callback_query:
        await query.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_no":
        await query.edit_message_text("Cancelled.", reply_markup=MAIN_MENU)
        context.user_data.clear()
        return ConversationHandler.END
    db = context.bot_data["db"]
    admin_id = context.bot_data["admin_id"]
    d = context.user_data

    if d["mode"] == "count_down":
        total_days = (datetime.strptime(d["end_date"], "%Y-%m-%d").date() - datetime.strptime(d["start_date"], "%Y-%m-%d").date()).days
    else:
        total_days = 0

    task_id = await db.create_task(
        admin_id=admin_id, name=d["name"], mode=d["mode"],
        start_date=d["start_date"], total_days=total_days,
        target_chat_id=d["target_chat_id"], chat_type=d["chat_type"],
        message_template=d["template"],
    )
    for t in d["times"]:
        await db.add_schedule(task_id, t)
    await schedule_task_jobs(context.bot_data["scheduler"], context.application.bot, db, task_id)
    keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
    await query.edit_message_text(f"Task #{task_id} created!", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.", reply_markup=MAIN_MENU)
    elif update.message:
        await update.message.reply_text("Cancelled.", reply_markup=MAIN_MENU)
    context.user_data.clear()
    return ConversationHandler.END


create_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_entry, pattern=r"^menu_create$")],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_MODE: [CallbackQueryHandler(ask_mode, pattern=r"^(count_up|count_down)$")],
        ASK_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_start_date)],
        ASK_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_end_date)],
        ASK_TARGET_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_target_chat)],
        ASK_FREQUENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_frequency)],
        ASK_TIMES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_times)],
        ASK_TEMPLATE: [CallbackQueryHandler(ask_template, pattern=r"^tpl_")],
        ASK_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_template_text)],
        CONFIRM: [CallbackQueryHandler(confirm, pattern=r"^confirm_")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CallbackQueryHandler(cancel, pattern=r"^menu_back$"),
    ],
)
