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
                if not pid or ring_no <= 0:
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

