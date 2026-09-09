"""
History manager using SQLite database.
Stores generated audio metadata, audio paths, and performance stats.
Supports full pagination, search, and filtering.
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import threading

from ..config import DB_PATH


@dataclass
class HistoryRecord:
    id: int
    timestamp: str
    text: str
    voice_name: str
    profile_name: str
    audio_path: str
    duration: float
    process_time: float
    rtf: float


class HistoryManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            text TEXT NOT NULL,
                            voice_name TEXT NOT NULL,
                            profile_name TEXT NOT NULL,
                            audio_path TEXT NOT NULL,
                            duration REAL NOT NULL,
                            process_time REAL NOT NULL,
                            rtf REAL NOT NULL
                        )
                        """
                    )
            finally:
                conn.close()

    def add_record(
        self,
        text: str,
        voice_name: str,
        profile_name: str,
        audio_path: str,
        duration: float,
        process_time: float,
        rtf: float,
    ) -> HistoryRecord:
        timestamp_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO history (timestamp, text, voice_name, profile_name, audio_path, duration, process_time, rtf)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (timestamp_str, text, voice_name, profile_name, audio_path, duration, process_time, rtf),
                    )
                    record_id = cursor.lastrowid
            finally:
                conn.close()

        return HistoryRecord(
            id=record_id,
            timestamp=timestamp_str,
            text=text,
            voice_name=voice_name,
            profile_name=profile_name,
            audio_path=audio_path,
            duration=duration,
            process_time=process_time,
            rtf=rtf,
        )

    def get_records(self, limit: int = 50) -> List[HistoryRecord]:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT id, timestamp, text, voice_name, profile_name, audio_path, duration, process_time, rtf
                    FROM history
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
            finally:
                conn.close()

        return [
            HistoryRecord(
                id=row["id"],
                timestamp=row["timestamp"],
                text=row["text"],
                voice_name=row["voice_name"],
                profile_name=row["profile_name"],
                audio_path=row["audio_path"],
                duration=row["duration"],
                process_time=row["process_time"],
                rtf=row["rtf"],
            )
            for row in rows
        ]

    def get_records_paginated(
        self,
        page: int = 1,
        page_size: int = 6,
        search_query: str = "",
        voice_filter: str = "all"
    ) -> Tuple[List[HistoryRecord], int]:
        """
        Lấy danh sách bản ghi có phân trang, hỗ trợ tìm kiếm và lọc giọng.
        Trả về (records, total_count).
        """
        page = max(1, page)
        offset = (page - 1) * page_size

        where_clauses = []
        params = []

        if search_query:
            where_clauses.append("(text LIKE ? OR voice_name LIKE ?)")
            pattern = f"%{search_query}%"
            params.extend([pattern, pattern])

        if voice_filter and voice_filter != "all":
            where_clauses.append("voice_name = ?")
            params.append(voice_filter)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self._lock:
            conn = self._get_connection()
            try:
                # 1. Đếm tổng số bản ghi thỏa điều kiện
                count_query = f"SELECT COUNT(*) FROM history {where_sql}"
                cursor = conn.execute(count_query, params)
                total_count = cursor.fetchone()[0]

                # 2. Lấy dữ liệu của trang hiện tại
                data_query = f"""
                    SELECT id, timestamp, text, voice_name, profile_name, audio_path, duration, process_time, rtf
                    FROM history
                    {where_sql}
                    ORDER BY id DESC
                    LIMIT ? OFFSET ?
                """
                cursor = conn.execute(data_query, params + [page_size, offset])
                rows = cursor.fetchall()
            finally:
                conn.close()

        records = [
            HistoryRecord(
                id=row["id"],
                timestamp=row["timestamp"],
                text=row["text"],
                voice_name=row["voice_name"],
                profile_name=row["profile_name"],
                audio_path=row["audio_path"],
                duration=row["duration"],
                process_time=row["process_time"],
                rtf=row["rtf"],
            )
            for row in rows
        ]
        return records, total_count

    def get_distinct_voices(self) -> List[str]:
        """Lấy danh sách các giọng đã từng được tạo để phục vụ bộ lọc."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute("SELECT DISTINCT voice_name FROM history ORDER BY voice_name ASC")
                rows = cursor.fetchall()
            finally:
                conn.close()
        return [row[0] for row in rows if row[0]]

    def delete_record(self, record_id: int) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    cursor = conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
                    return cursor.rowcount > 0
            finally:
                conn.close()

    def clear_all(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM history")
            finally:
                conn.close()
