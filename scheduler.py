import logging
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from helpers import render_template

logger = logging.getLogger(__name__)


def create_scheduler():
    return AsyncIOScheduler()


async def send_reminder(bot, db, task_id):
    task = await db.get_task(task_id)
    if not task or not task["is_active"]:
        return

    if task["mode"] == "count_down":
        today = date.today()
        start = datetime.strptime(task["start_date"], "%Y-%m-%d").date()
        days_elapsed = (today - start).days + 1
        days_left = task["total_days"] - days_elapsed + 1
        if days_left < 0:
            await db.pause_task(task_id)
            logger.info(f"Task {task_id} completed, paused automatically.")
            return

    message = render_template(task["message_template"], task)

    try:
        chat_id = task["target_chat_id"]
        if chat_id.startswith("@"):
            await bot.send_message(chat_id=chat_id, text=message)
        else:
            await bot.send_message(chat_id=int(chat_id), text=message)
        logger.info(f"Sent reminder for task {task_id} to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send reminder for task {task_id}: {e}")


async def schedule_task_jobs(scheduler, bot, db, task_id):
    remove_task_jobs_sync(scheduler, task_id)

    schedules = await db.get_schedules(task_id)
    for s in schedules:
        h, m = map(int, s["time_str"].split(":"))
        scheduler.add_job(
            send_reminder,
            CronTrigger(hour=h, minute=m),
            args=[bot, db, task_id],
            id=f"task_{task_id}_{s['time_str']}",
            replace_existing=True,
        )
    logger.info(f"Scheduled {len(schedules)} jobs for task {task_id}")


def remove_task_jobs_sync(scheduler, task_id):
    job_ids = [job.id for job in scheduler.get_jobs() if job.id.startswith(f"task_{task_id}_")]
    for job_id in job_ids:
        scheduler.remove_job(job_id)


async def remove_task_jobs(scheduler, task_id):
    remove_task_jobs_sync(scheduler, task_id)


async def reschedule_all(scheduler, bot, db, admin_id):
    tasks = await db.get_all_active_tasks(admin_id)
    for t in tasks:
        await schedule_task_jobs(scheduler, bot, db, t["id"])
