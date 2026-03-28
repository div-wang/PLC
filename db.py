#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import app_storage


def db_path() -> str:
    return app_storage.user_file_path("plc_monitor.db")


def _connect() -> sqlite3.Connection:
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ring_detail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                ring_no INTEGER NOT NULL,
                weight REAL NOT NULL,
                travel REAL NOT NULL,
                time TEXT NOT NULL,
                total_weight REAL NOT NULL,
                total_travel REAL NOT NULL,
                UNIQUE(project_id, ring_no)
            )
            """
        )


def _next_backup_no_for_file(path: str) -> int:
    d = os.path.dirname(path)
    base = os.path.basename(path)
    prefix = base + ".backup"
    max_n = 0
    try:
        names = os.listdir(d) if d else []
    except Exception:
        names = []
    for name in names:
        if not isinstance(name, str):
            continue
        if not name.startswith(prefix):
            continue
        tail = name[len(prefix) :]
        try:
            n = int(tail)
        except Exception:
            continue
        max_n = max(max_n, n)
    return max_n + 1


def backup_and_recreate_db() -> int:
    path = db_path()
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    n = _next_backup_no_for_file(path)
    suffix = f".backup{n}"

    # 确保关闭所有连接并写入数据
    if os.path.exists(path):
        try:
            import gc
            gc.collect()
        except Exception:
            pass

    for p in (path + "-shm", path + "-wal", path):
        if os.path.exists(p):
            try:
                os.replace(p, p + suffix)
            except Exception:
                pass

    init_db()
    return n


def _meta_get(conn: sqlite3.Connection, key: str) -> Optional[str]:
    cur = conn.execute("SELECT value FROM app_meta WHERE key = ?", (key,))
    row = cur.fetchone()
    if not row:
        return None
    return str(row["value"]) if row["value"] is not None else None


def _meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def upsert_ring_detail(
    project_id: str,
    ring_no: int,
    weight: float,
    time_str: str,
    total_weight: float,
    travel: float = 0.0,
    total_travel: float = 0.0,
) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ring_detail(project_id, ring_no, weight, travel, time, total_weight, total_travel)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, ring_no) DO UPDATE SET
                weight=excluded.weight,
                travel=excluded.travel,
                time=excluded.time,
                total_weight=excluded.total_weight,
                total_travel=excluded.total_travel
            """,
            (str(project_id), int(ring_no), float(weight), float(travel), str(time_str), float(total_weight), float(total_travel)),
        )


def recent_rings(project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    init_db()
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT project_id, ring_no, weight, travel, time, total_weight, total_travel
            FROM ring_detail
            WHERE project_id = ?
            ORDER BY ring_no DESC
            LIMIT ?
            """,
            (str(project_id), int(limit)),
        )
        rows = cur.fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows[::-1]:
        out.append(
            {
                "project_id": r["project_id"],
                "ring_no": int(r["ring_no"]),
                "weight": float(r["weight"]),
                "travel": float(r["travel"]),
                "time": str(r["time"]),
                "total_weight": float(r["total_weight"]),
                "total_travel": float(r["total_travel"]),
            }
        )
    return out


def sum_ring_weight_before(project_id: str, ring_no_exclusive: int) -> float:
    init_db()
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(SUM(weight), 0) AS s
            FROM ring_detail
            WHERE project_id = ? AND ring_no < ?
            """,
            (str(project_id), int(ring_no_exclusive)),
        )
        row = cur.fetchone()
    if not row:
        return 0.0
    try:
        return float(row["s"] or 0.0)
    except Exception:
        return 0.0


def max_ring_no(project_id: str) -> Optional[int]:
    init_db()
    with _connect() as conn:
        cur = conn.execute(
            "SELECT MAX(ring_no) AS mx FROM ring_detail WHERE project_id = ?",
            (str(project_id),),
        )
        row = cur.fetchone()
    if not row:
        return None
    v = row["mx"]
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def get_ring_detail(project_id: str, ring_no: int) -> Optional[Dict[str, Any]]:
    init_db()
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT project_id, ring_no, weight, travel, time, total_weight, total_travel
            FROM ring_detail
            WHERE project_id = ? AND ring_no = ?
            """,
            (str(project_id), int(ring_no)),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "project_id": str(row["project_id"]),
        "ring_no": int(row["ring_no"]),
        "weight": float(row["weight"]),
        "travel": float(row["travel"]),
        "time": str(row["time"]),
        "total_weight": float(row["total_weight"]),
        "total_travel": float(row["total_travel"]),
    }


def delete_ring_detail(project_id: str, ring_no: int) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            "DELETE FROM ring_detail WHERE project_id = ? AND ring_no = ?",
            (str(project_id), int(ring_no)),
        )


def meta_get(key: str) -> Optional[str]:
    init_db()
    with _connect() as conn:
        return _meta_get(conn, str(key))


def get_last_ring_detail(project_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT project_id, ring_no, weight, travel, time, total_weight, total_travel
            FROM ring_detail
            WHERE project_id = ?
            ORDER BY ring_no DESC
            LIMIT 1
            """,
            (str(project_id),),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "project_id": str(row["project_id"]),
        "ring_no": int(row["ring_no"]),
        "weight": float(row["weight"]),
        "travel": float(row["travel"]),
        "time": str(row["time"]),
        "total_weight": float(row["total_weight"]),
        "total_travel": float(row["total_travel"]),
    }


def meta_set(key: str, value: str) -> None:
    init_db()
    with _connect() as conn:
        _meta_set(conn, str(key), str(value))



def migrate_ring_records_json_if_needed(json_filename: str = "ring_records.json") -> None:
    init_db()
    with _connect() as conn:
        if _meta_get(conn, "ring_detail_migrated") == "1":
            return
        src_path = app_storage.user_file_path(json_filename)
        if not os.path.exists(src_path):
            _meta_set(conn, "ring_detail_migrated", "1")
            conn.commit()
            return
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            _meta_set(conn, "ring_detail_migrated", "1")
            conn.commit()
            return
        records = raw.get("records") if isinstance(raw, dict) else None
        if not isinstance(records, list):
            _meta_set(conn, "ring_detail_migrated", "1")
            conn.commit()
            return
        for rec in records:
            if not isinstance(rec, dict):
                continue
            try:
                pid = str(rec.get("project_id") or "")
                ring_no = int(rec.get("ring_no") or 0)
                weight = float(rec.get("weight") or 0.0)
                travel = float(rec.get("travel") or 0.0)
                ts = str(rec.get("time") or "")
                total_weight = float(rec.get("total_weight") or 0.0)
                total_travel = float(rec.get("total_travel") or 0.0)
                if not pid or ring_no < 0:
                    continue
                conn.execute(
                    """
                    INSERT INTO ring_detail(project_id, ring_no, weight, travel, time, total_weight, total_travel)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, ring_no) DO NOTHING
                    """,
                    (pid, ring_no, weight, travel, ts, total_weight, total_travel),
                )
            except Exception:
                continue
        _meta_set(conn, "ring_detail_migrated", "1")
        conn.commit()
