"""Lightweight SQLite checkpointer fallback for LangGraph.

Provides a minimal persistent checkpointer when the optional
langgraph sqlite saver is unavailable. This stores full checkpoints
and pending writes in SQLite for durability across restarts.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    RunnableConfig,
    WRITES_IDX_MAP,
    get_checkpoint_id,
    get_checkpoint_metadata,
)


class LocalSqliteSaver(BaseCheckpointSaver[str]):
    """SQLite-backed checkpoint saver for local persistence."""

    def __init__(self, db_path: Path, *, serde: Any | None = None) -> None:
        super().__init__(serde=serde)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    checkpoint_type TEXT NOT NULL,
                    checkpoint_blob BLOB NOT NULL,
                    metadata_type TEXT NOT NULL,
                    metadata_blob BLOB NOT NULL,
                    parent_checkpoint_id TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS writes (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    write_idx INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    value_blob BLOB NOT NULL,
                    task_path TEXT,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_latest "
                "ON checkpoints(thread_id, checkpoint_ns, created_at)"
            )
            conn.commit()

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        with self._get_conn() as conn:
            if checkpoint_id:
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                    """,
                    (thread_id, checkpoint_ns, checkpoint_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE thread_id = ? AND checkpoint_ns = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (thread_id, checkpoint_ns),
                ).fetchone()

            if row is None:
                return None

            checkpoint = self.serde.loads_typed(
                (row["checkpoint_type"], row["checkpoint_blob"])
            )
            metadata = self.serde.loads_typed(
                (row["metadata_type"], row["metadata_blob"])
            )
            parent_checkpoint_id = row["parent_checkpoint_id"]

            writes_rows = conn.execute(
                """
                SELECT * FROM writes
                WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                ORDER BY write_idx ASC
                """,
                (thread_id, checkpoint_ns, row["checkpoint_id"]),
            ).fetchall()

            pending_writes = [
                (
                    write_row["task_id"],
                    write_row["channel"],
                    self.serde.loads_typed(
                        (write_row["value_type"], write_row["value_blob"])
                    ),
                )
                for write_row in writes_rows
            ]

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": row["checkpoint_id"],
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                pending_writes=pending_writes,
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    }
                    if parent_checkpoint_id
                    else None
                ),
            )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"] if config else None
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "") if config else None
        checkpoint_id = get_checkpoint_id(config) if config else None
        before_id = get_checkpoint_id(before) if before else None

        query = "SELECT * FROM checkpoints"
        params: list[Any] = []
        clauses: list[str] = []

        if thread_id:
            clauses.append("thread_id = ?")
            params.append(thread_id)
        if checkpoint_ns is not None:
            clauses.append("checkpoint_ns = ?")
            params.append(checkpoint_ns)
        if checkpoint_id:
            clauses.append("checkpoint_id = ?")
            params.append(checkpoint_id)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY created_at DESC"

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()

            for row in rows:
                if before_id and row["checkpoint_id"] >= before_id:
                    continue

                metadata = self.serde.loads_typed(
                    (row["metadata_type"], row["metadata_blob"])
                )
                if filter and not all(
                    metadata.get(key) == value for key, value in filter.items()
                ):
                    continue

                checkpoint = self.serde.loads_typed(
                    (row["checkpoint_type"], row["checkpoint_blob"])
                )
                parent_checkpoint_id = row["parent_checkpoint_id"]

                writes_rows = conn.execute(
                    """
                    SELECT * FROM writes
                    WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                    ORDER BY write_idx ASC
                    """,
                    (row["thread_id"], row["checkpoint_ns"], row["checkpoint_id"]),
                ).fetchall()

                pending_writes = [
                    (
                        write_row["task_id"],
                        write_row["channel"],
                        self.serde.loads_typed(
                            (write_row["value_type"], write_row["value_blob"])
                        ),
                    )
                    for write_row in writes_rows
                ]

                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": row["thread_id"],
                            "checkpoint_ns": row["checkpoint_ns"],
                            "checkpoint_id": row["checkpoint_id"],
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    pending_writes=pending_writes,
                    parent_config=(
                        {
                            "configurable": {
                                "thread_id": row["thread_id"],
                                "checkpoint_ns": row["checkpoint_ns"],
                                "checkpoint_id": parent_checkpoint_id,
                            }
                        }
                        if parent_checkpoint_id
                        else None
                    ),
                )

                if limit is not None:
                    limit -= 1
                    if limit <= 0:
                        break

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        checkpoint_type, checkpoint_blob = self.serde.dumps_typed(checkpoint)
        metadata_type, metadata_blob = self.serde.dumps_typed(
            get_checkpoint_metadata(config, metadata)
        )

        created_at = datetime.now().isoformat()

        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO checkpoints
                    (thread_id, checkpoint_ns, checkpoint_id, checkpoint_type, checkpoint_blob,
                     metadata_type, metadata_blob, parent_checkpoint_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint["id"],
                        checkpoint_type,
                        sqlite3.Binary(checkpoint_blob),
                        metadata_type,
                        sqlite3.Binary(metadata_blob),
                        parent_checkpoint_id,
                        created_at,
                    ),
                )
                conn.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        with self._lock:
            with self._get_conn() as conn:
                for idx, (channel, value) in enumerate(writes):
                    write_idx = WRITES_IDX_MAP.get(channel, idx)
                    if write_idx >= 0:
                        existing = conn.execute(
                            """
                            SELECT 1 FROM writes
                            WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?
                              AND task_id = ? AND write_idx = ?
                            """,
                            (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx),
                        ).fetchone()
                        if existing:
                            continue

                    value_type, value_blob = self.serde.dumps_typed(value)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO writes
                        (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx,
                         channel, value_type, value_blob, task_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            thread_id,
                            checkpoint_ns,
                            checkpoint_id,
                            task_id,
                            write_idx,
                            channel,
                            value_type,
                            sqlite3.Binary(value_blob),
                            task_path,
                        ),
                    )
                conn.commit()

    def delete_thread(self, thread_id: str) -> None:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
                conn.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
                conn.commit()
