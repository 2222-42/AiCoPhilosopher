import json
import uuid
from datetime import datetime, timedelta

import aiosqlite


class MessageQueueAdapter:
    def __init__(self, db_path: str = "") -> None:
        self.db_path = db_path
        self._archive_days: dict[str, int] = {
            "status_update": 30,
            "user_notification": 30,
            "error_notification": 90,
            "delegation_request": 365,
            "delegation_response": 365,
            "steering_command": 365,
            "steering_ack": 365,
            "help_request": 365,
            "help_response": 365,
            "review_request": 365,
            "review_response": 365,
            "result_delivery": 365,
        }

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        return conn

    async def initialize(self) -> None:
        conn = await self._connect()
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    recipient_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    payload_json TEXT DEFAULT '{}',
                    epistemic_status_json TEXT DEFAULT '{}',
                    correlation_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered INTEGER DEFAULT 0,
                    archived INTEGER DEFAULT 0
                )""")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_mq_recipient ON messages(recipient_id, delivered, archived)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_mq_project ON messages(project_id)")
            await conn.commit()
        finally:
            await conn.close()

    async def send(self, message: dict[str, object]) -> str:
        mid = str(message.get("message_id", uuid.uuid4().hex))
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT INTO messages
                   (message_id, project_id, sender_id, recipient_id, message_type,
                    payload_json, epistemic_status_json, correlation_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (mid,
                 str(message.get("project_id", "")),
                 str(message.get("sender_id", "")),
                 str(message.get("recipient_id", "")),
                 str(message.get("message_type", "")),
                 json.dumps(message.get("payload", {})),
                 json.dumps(message.get("epistemic_status", {})),
                 str(message.get("correlation_id")) if message.get("correlation_id") else None),
            )
            await conn.commit()
            return mid
        finally:
            await conn.close()

    async def receive(self, recipient_id: str, timeout: float = 5.0) -> list[dict[str, object]]:
        conn = await self._connect()
        try:
            cursor = await conn.execute(
                """SELECT * FROM messages
                   WHERE recipient_id = ? AND delivered = 0 AND archived = 0
                   ORDER BY timestamp ASC LIMIT 100""",
                (recipient_id,),
            )
            rows = await cursor.fetchall()
            messages = [dict(row) for row in rows]
            if messages:
                mids = [m["message_id"] for m in messages]
                placeholders = ",".join("?" for _ in mids)
                await conn.execute(
                    f"UPDATE messages SET delivered = 1 WHERE message_id IN ({placeholders})",
                    mids,
                )
                await conn.commit()
            return messages
        finally:
            await conn.close()

    async def broadcast(self, message: dict[str, object], agent_ids: list[str]) -> list[str]:
        ids = []
        for agent_id in agent_ids:
            msg = dict(message)
            msg["recipient_id"] = agent_id
            msg["message_id"] = uuid.uuid4().hex
            mid = await self.send(msg)
            ids.append(mid)
        return ids

    async def poll_inbox(self, agent_id: str, timeout: float = 5.0) -> list[dict[str, object]]:
        return await self.receive(agent_id, timeout)

    async def message_count(self, project_id: str) -> int:
        conn = await self._connect()
        try:
            cursor = await conn.execute(
                "SELECT COUNT(*) as cnt FROM messages WHERE project_id = ? AND archived = 0",
                (project_id,),
            )
            row = await cursor.fetchone()
            return row["cnt"] if row else 0
        finally:
            await conn.close()

    async def archive_old_messages(self) -> int:
        conn = await self._connect()
        try:
            total = 0
            for msg_type, days in self._archive_days.items():
                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                cursor = await conn.execute(
                    "UPDATE messages SET archived = 1 WHERE message_type = ? AND timestamp < ?",
                    (msg_type, cutoff),
                )
                total += cursor.rowcount
            await conn.commit()
            return total
        finally:
            await conn.close()
