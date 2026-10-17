"""Модуль хранения данных парсера."""

import csv
import sqlite3
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "parser_data.sqlite"
REPORTS_DIR = Path(__file__).parent / "reports"


def init_db(db_path=None):
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER NOT NULL,
            title TEXT NOT NULL,
            state TEXT NOT NULL,
            user TEXT NOT NULL,
            labels TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            url TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            UNIQUE(number, url)
        )
    """)
    conn.commit()
    logger.info("Database initialized: %s", db_path.name)
    return conn


def _normalize_labels(raw_labels):
    if not raw_labels:
        return ""
    first = raw_labels[0]
    if isinstance(first, dict):
        return ",".join(
            str(label.get("name", ""))
            for label in raw_labels
            if isinstance(label, dict) and label.get("name")
        )
    else:
        return ",".join(str(label) for label in raw_labels if label)


def _normalize_user(user_val):
    """Извлечь login из user dict или вернуть строку."""
    if isinstance(user_val, dict):
        return user_val.get("login", "")
    return str(user_val) if user_val else ""


def save_issues(issues, conn=None):
    own_conn = False
    if conn is None:
        conn = init_db()
        own_conn = True
    saved = 0
    skipped = 0
    try:
        for issue in issues:
            try:
                labels_str = _normalize_labels(issue.get("labels", []))
                user_str = _normalize_user(issue.get("user", ""))
                conn.execute("""
                    INSERT OR IGNORE INTO issues
                    (number, title, state, user, labels, created_at, updated_at, url, first_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    issue["number"],
                    issue["title"],
                    issue["state"],
                    user_str,
                    labels_str,
                    issue["created_at"],
                    issue["updated_at"],
                    issue["url"],
                ))
                saved += 1
            except Exception as e:
                logger.error("Error saving issue #%s: %s", issue.get("number"), e)
                skipped += 1
        conn.commit()
        logger.info("Saved: %d, Skipped: %d, Total: %d", saved, skipped, len(issues))
    finally:
        if own_conn:
            conn.close()
    return {"saved": saved, "skipped": skipped, "total": len(issues)}


def get_all_issues(conn=None):
    own_conn = False
    if conn is None:
        conn = init_db()
        own_conn = True
    try:
        cursor = conn.execute("""
            SELECT number, title, state, user, labels,
                   created_at, updated_at, url, first_seen_at
            FROM issues
            ORDER BY number DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if own_conn:
            conn.close()


def get_new_issues(issues, conn=None):
    own_conn = False
    if conn is None:
        conn = init_db()
        own_conn = True
    try:
        cursor = conn.execute("SELECT number FROM issues")
        existing_numbers = {row["number"] for row in cursor.fetchall()}
        new_issues = [
            issue for issue in issues
            if issue["number"] not in existing_numbers
        ]
        logger.info("New issues: %d из %d", len(new_issues), len(issues))
        return new_issues
    finally:
        if own_conn:
            conn.close()


def _filter_issue_for_csv(issue):
    return {
        "number": issue.get("number", ""),
        "title": issue.get("title", ""),
        "state": issue.get("state", ""),
        "user": _normalize_user(issue.get("user", "")),
        "labels": _normalize_labels(issue.get("labels", [])),
        "created_at": issue.get("created_at", ""),
        "updated_at": issue.get("updated_at", ""),
        "url": issue.get("html_url", issue.get("url", "")),
    }


def export_to_csv(issues, filename=None):
    REPORTS_DIR.mkdir(exist_ok=True)
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = "issues_" + timestamp + ".csv"
    csv_path = REPORTS_DIR / filename
    fieldnames = ["number", "title", "state", "user", "labels", "created_at", "updated_at", "url"]
    filtered_issues = [_filter_issue_for_csv(issue) for issue in issues]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_issues)
    logger.info("CSV exported: %s (%d rows)", csv_path.name, len(filtered_issues))
    return csv_path


def get_stats(conn=None):
    own_conn = False
    if conn is None:
        conn = init_db()
        own_conn = True
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM issues").fetchone()["cnt"]
        open_count = conn.execute("SELECT COUNT(*) as cnt FROM issues WHERE state='open'").fetchone()["cnt"]
        closed_count = conn.execute("SELECT COUNT(*) as cnt FROM issues WHERE state='closed'").fetchone()["cnt"]
        users_cursor = conn.execute("SELECT DISTINCT user FROM issues ORDER BY user")
        users = [row["user"] for row in users_cursor.fetchall()]
        return {"total": total, "open": open_count, "closed": closed_count, "users": users}
    finally:
        if own_conn:
            conn.close()

