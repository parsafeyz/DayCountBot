from datetime import datetime, date


def calculate_day_info(task):
    today = date.today()
    start = datetime.strptime(task["start_date"], "%Y-%m-%d").date()
    days_elapsed = (today - start).days + 1

    if task["mode"] == "count_up":
        total = days_elapsed
        days_left = 0
    else:
        total = task["total_days"]
        days_left = max(total - days_elapsed + 1, 0)

    return {
        "current_day": days_elapsed,
        "total_days": total,
        "days_left": days_left,
        "date": today.strftime("%Y-%m-%d"),
        "name": task["name"],
    }


def render_template(template, task):
    info = calculate_day_info(task)
    return template.format(**info)


def build_task_summary(task, schedules):
    mode_label = "Count Up" if task["mode"] == "count_up" else "Count Down"
    status = "Active" if task["is_active"] else "Paused"
    times = ", ".join(s["time_str"] for s in schedules) if schedules else "None"

    if task["mode"] == "count_up":
        info = calculate_day_info(task)
        duration = f"Day {info['current_day']}"
    else:
        duration = f"Total days: {task['total_days']}"

    return (
        f"ID: {task['id']}\n"
        f"Name: {task['name']}\n"
        f"Mode: {mode_label}\n"
        f"Start: {task['start_date']}\n"
        f"{duration}\n"
        f"Target: {task['target_chat_id']} ({task['chat_type']})\n"
        f"Schedule: {times}\n"
        f"Status: {status}\n"
        f"Template: {task['message_template']}"
    )


def build_status_message(task):
    info = calculate_day_info(task)
    if task["mode"] == "count_up":
        return f"{task['name']}: Day {info['current_day']}"
    else:
        return f"{task['name']}: {info['days_left']} days left (Day {info['current_day']} of {info['total_days']})"
