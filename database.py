import aiosqlite


class Database:
    def __init__(self, db_path):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    mode TEXT NOT NULL CHECK(mode IN ('count_up', 'count_down')),
                    start_date TEXT NOT NULL,
                    total_days INTEGER NOT NULL,
                    target_chat_id TEXT NOT NULL,
                    chat_type TEXT NOT NULL CHECK(chat_type IN ('private', 'group', 'channel')),
                    message_template TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    time_str TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            await db.commit()

    async def create_task(self, admin_id, name, mode, start_date, total_days, target_chat_id, chat_type, message_template):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO tasks (admin_id, name, mode, start_date, total_days, target_chat_id, chat_type, message_template)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (admin_id, name, mode, start_date, total_days, target_chat_id, chat_type, message_template))
            await db.commit()
            return cursor.lastrowid

    async def add_schedule(self, task_id, time_str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO schedules (task_id, time_str) VALUES (?, ?)",
                (task_id, time_str)
            )
            await db.commit()

    async def get_task(self, task_id):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            return await cursor.fetchone()

    async def get_all_active_tasks(self, admin_id):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE admin_id = ? AND is_active = 1",
                (admin_id,)
            )
            return await cursor.fetchall()

    async def get_all_tasks(self, admin_id):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE admin_id = ?",
                (admin_id,)
            )
            return await cursor.fetchall()

    async def get_schedules(self, task_id):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM schedules WHERE task_id = ?",
                (task_id,)
            )
            return await cursor.fetchall()

    async def delete_task(self, task_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()

    async def delete_schedules(self, task_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM schedules WHERE task_id = ?", (task_id,))
            await db.commit()

    async def update_task(self, task_id, **kwargs):
        async with aiosqlite.connect(self.db_path) as db:
            set_clause = ", ".join(f"{k} = ?" for k in kwargs)
            values = list(kwargs.values()) + [task_id]
            await db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
            await db.commit()

    async def pause_task(self, task_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tasks SET is_active = 0 WHERE id = ?", (task_id,))
            await db.commit()

    async def resume_task(self, task_id):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tasks SET is_active = 1 WHERE id = ?", (task_id,))
            await db.commit()
