from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Create Task", callback_data="menu_create")],
    [InlineKeyboardButton("List Tasks", callback_data="menu_list"),
     InlineKeyboardButton("Status", callback_data="menu_status")],
    [InlineKeyboardButton("Edit Task", callback_data="menu_edit"),
     InlineKeyboardButton("Delete Task", callback_data="menu_delete")],
    [InlineKeyboardButton("Pause Task", callback_data="menu_pause"),
     InlineKeyboardButton("Resume Task", callback_data="menu_resume")],
])


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_id = context.bot_data["admin_id"]
    if user_id != admin_id:
        await update.message.reply_text("Unauthorized.")
        return

    await update.message.reply_text("Welcome! Choose an action:", reply_markup=MAIN_MENU)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_list":
        db = context.bot_data["db"]
        admin_id = context.bot_data["admin_id"]
        from helpers import build_task_summary
        tasks = await db.get_all_tasks(admin_id)
        if not tasks:
            keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
            await query.edit_message_text("No tasks found.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        lines = []
        task_buttons = []
        for t in tasks:
            schedules = await db.get_schedules(t["id"])
            lines.append(build_task_summary(t, schedules))
            lines.append("---")
            task_buttons.append([
                InlineKeyboardButton(f"Edit #{t['id']}", callback_data=f"do_edit_{t['id']}"),
                InlineKeyboardButton(f"Delete #{t['id']}", callback_data=f"do_delete_{t['id']}"),
            ])
        task_buttons.append([InlineKeyboardButton("Back", callback_data="menu_back")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(task_buttons))
    elif query.data == "menu_status":
        db = context.bot_data["db"]
        admin_id = context.bot_data["admin_id"]
        from helpers import build_status_message
        tasks = await db.get_all_tasks(admin_id)
        if not tasks:
            keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
            await query.edit_message_text("No tasks found.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        lines = [build_status_message(t) for t in tasks]
        keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data in ("menu_edit", "menu_delete", "menu_pause", "menu_resume"):
        db = context.bot_data["db"]
        admin_id = context.bot_data["admin_id"]
        tasks = await db.get_all_tasks(admin_id)
        if not tasks:
            keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
            await query.edit_message_text("No tasks found.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        action = query.data.replace("menu_", "")
        buttons = []
        for t in tasks:
            buttons.append([InlineKeyboardButton(f"#{t['id']} - {t['name']}", callback_data=f"do_{action}_{t['id']}")])
        buttons.append([InlineKeyboardButton("Back", callback_data="menu_back")])
        await query.edit_message_text(f"Select a task to {action}:", reply_markup=InlineKeyboardMarkup(buttons))
    elif query.data == "menu_back":
        await query.edit_message_text("Choose an action:", reply_markup=MAIN_MENU)


async def handle_do_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[-1])
    db = context.bot_data["db"]
    from scheduler import remove_task_jobs
    await remove_task_jobs(context.bot_data["scheduler"], task_id)
    await db.delete_task(task_id)
    keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
    await query.edit_message_text(f"Task #{task_id} deleted.", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_do_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[-1])
    db = context.bot_data["db"]
    from scheduler import remove_task_jobs
    await db.pause_task(task_id)
    await remove_task_jobs(context.bot_data["scheduler"], task_id)
    keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
    await query.edit_message_text(f"Task #{task_id} paused.", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_do_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[-1])
    db = context.bot_data["db"]
    from scheduler import schedule_task_jobs
    await db.resume_task(task_id)
    await schedule_task_jobs(context.bot_data["scheduler"], context.application.bot, db, task_id)
    keyboard = [[InlineKeyboardButton("Back", callback_data="menu_back")]]
    await query.edit_message_text(f"Task #{task_id} resumed.", reply_markup=InlineKeyboardMarkup(keyboard))
