from datetime import datetime
from typing import Any, Optional

import aiosqlite

from .models import Request


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.create_tables()

    async def close(self) -> None:
        await self.conn.close()

    async def create_tables(self) -> None:
        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_user_id TEXT NOT NULL,
                discord_username TEXT NOT NULL,
                search_term TEXT NOT NULL,
                refined_search_term TEXT,
                artist TEXT,
                song TEXT,
                album TEXT,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'downloading', 'complete', 'failed')),
                message_id TEXT,
                youtube_url TEXT,
                youtube_title TEXT,
                file_path TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        # Add columns if they don't exist (for existing databases)
        try:
            await self.conn.execute(
                "ALTER TABLE requests ADD COLUMN refined_search_term TEXT"
            )
        except aiosqlite.OperationalError:
            pass  # Column already exists
        try:
            await self.conn.execute("ALTER TABLE requests ADD COLUMN artist TEXT")
        except aiosqlite.OperationalError:
            pass  # Column already exists
        try:
            await self.conn.execute("ALTER TABLE requests ADD COLUMN song TEXT")
        except aiosqlite.OperationalError:
            pass  # Column already exists
        try:
            await self.conn.execute("ALTER TABLE requests ADD COLUMN album TEXT")
        except aiosqlite.OperationalError:
            pass  # Column already exists
        try:
            await self.conn.execute(
                "ALTER TABLE requests ADD COLUMN original_message_id TEXT"
            )
        except aiosqlite.OperationalError:
            pass  # Column already exists
        try:
            await self.conn.execute(
                "ALTER TABLE requests ADD COLUMN original_channel_id TEXT"
            )
        except aiosqlite.OperationalError:
            pass  # Column already exists
        await self.conn.commit()

    async def create_request(self, request: Request) -> int:
        now = datetime.now().isoformat()
        cursor = await self.conn.execute(
            """
            INSERT INTO requests (discord_user_id, discord_username, search_term, refined_search_term, artist, song, album, status, original_message_id, original_channel_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                request.discord_user_id,
                request.discord_username,
                request.search_term,
                request.refined_search_term,
                request.artist,
                request.song,
                request.album,
                request.status,
                request.original_message_id,
                request.original_channel_id,
                now,
                now,
            ),
        )
        await self.conn.commit()
        result = cursor.lastrowid
        if result is None:
            raise RuntimeError("Failed to get last row ID")
        return int(result)

    async def update_request(self, request_id: int, **kwargs: Any) -> None:
        if not kwargs:
            return
        now = datetime.now().isoformat()
        kwargs["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [request_id]
        await self.conn.execute(
            f"UPDATE requests SET {set_clause} WHERE id = ?", values
        )
        await self.conn.commit()

    async def get_request_by_message_id(self, message_id: str) -> Optional[Request]:
        cursor = await self.conn.execute(
            "SELECT * FROM requests WHERE message_id = ?", (message_id,)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_request(row)
        return None

    async def get_request_by_id(self, request_id: int) -> Optional[Request]:
        cursor = await self.conn.execute(
            "SELECT * FROM requests WHERE id = ?", (request_id,)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_request(row)
        return None

    async def get_requests_by_file_path(self, file_path: str) -> list[Request]:
        """Get requests by file path."""
        cursor = await self.conn.execute(
            "SELECT * FROM requests WHERE file_path = ?", (file_path,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_request(row) for row in rows]

    def _row_to_request(self, row: Any) -> Request:
        return Request(
            id=row[0],
            discord_user_id=row[1],
            discord_username=row[2],
            search_term=row[3],
            refined_search_term=row[4] if len(row) > 4 else None,
            artist=row[5] if len(row) > 5 else None,
            song=row[6] if len(row) > 6 else None,
            album=row[7] if len(row) > 7 else None,
            status=row[8] if len(row) > 8 else "pending",
            message_id=row[9] if len(row) > 9 else None,
            youtube_url=row[10] if len(row) > 10 else None,
            youtube_title=row[11] if len(row) > 11 else None,
            file_path=row[12] if len(row) > 12 else None,
            error_message=row[13] if len(row) > 13 else None,
            created_at=datetime.fromisoformat(row[14])
            if len(row) > 14 and row[14]
            else None,
            updated_at=datetime.fromisoformat(row[15])
            if len(row) > 15 and row[15]
            else None,
            original_message_id=row[16] if len(row) > 16 else None,
            original_channel_id=row[17] if len(row) > 17 else None,
        )
