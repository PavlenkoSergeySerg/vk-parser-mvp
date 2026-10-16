"""Модуль формирования отчёта об изменениях.

Сравнивает текущие issues с предыдущим запуском (из БД)
и формирует текстовый отчёт для Telegram.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import storage

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent / "reports"


def _normalize_user(user_val) -> str:
    """Извлечь login из user dict или вернуть строку."""
    if isinstance(user_val, dict):
        return user_val.get("login", "")
    return str(user_val) if user_val else ""


def _normalize_labels(raw_labels) -> str:
    """Преобразовать labels в строку через запятую."""
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


def compare_issues(
    current_issues: list[dict],
    conn=None,
) -> dict:
    """Сравнить текущие issues с данными в БД.

    Args:
        current_issues: Свежие issues с GitHub (сырой формат)
        conn: Соединение с БД (если None — создаётся новое)

    Returns:
        Словарь: {
            'new': [...],           # Новые issues (не были в БД)
            'closed': [...],        # Закрытые issues (были open, стали closed)
            'updated': [...],       # Обновлённые issues (изменился updated_at)
            'unchanged': [...],     # Без изменений
        }
    """
    # Получаем issues из БД
    db_issues = storage.get_all_issues(conn)
    db_issues_by_number = {issue["number"]: issue for issue in db_issues}

    new_issues = []
    closed_issues = []
    updated_issues = []
    unchanged_issues = []

    for issue in current_issues:
        number = issue["number"]
        current_state = issue.get("state", "open")
        current_updated = issue.get("updated_at", "")

        if number not in db_issues_by_number:
            # Новый issue — не был в БД
            new_issues.append(issue)
        else:
            db_issue = db_issues_by_number[number]
            db_state = db_issue.get("state", "open")
            db_updated = db_issue.get("updated_at", "")

            if db_state == "open" and current_state == "closed":
                # Был открыт, стал закрыт
                closed_issues.append(issue)
            elif current_updated != db_updated:
                # Изменился updated_at — значит обновлён
                updated_issues.append(issue)
            else:
                # Без изменений
                unchanged_issues.append(issue)

    logger.info(
        "Compare: new=%d, closed=%d, updated=%d, unchanged=%d",
        len(new_issues), len(closed_issues), len(updated_issues), len(unchanged_issues)
    )

    return {
        "new": new_issues,
        "closed": closed_issues,
        "updated": updated_issues,
        "unchanged": unchanged_issues,
    }


def format_report(comparison: dict, repo_name: str = "") -> str:
    """Сформировать текстовый отчёт из результатов сравнения.

    Args:
        comparison: Словарь из compare_issues()
        repo_name: Имя репозитория для заголовка

    Returns:
        Текстовый отчёт (строка).
    """
    lines = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"📊 Отчёт по репозиторию: {repo_name}")
    lines.append(f" Время: {timestamp}")
    lines.append("")

    # Новые issues
    new_issues = comparison.get("new", [])
    if new_issues:
        lines.append(f"🆕 Новые issues ({len(new_issues)}):")
        for issue in new_issues:
            number = issue.get("number", "")
            title = issue.get("title", "")
            user = _normalize_user(issue.get("user", ""))
            labels = _normalize_labels(issue.get("labels", []))
            labels_str = f" [{labels}]" if labels else ""
            lines.append(f"  #{number} {title}{labels_str} — @{user}")
        lines.append("")

    # Закрытые issues
    closed_issues = comparison.get("closed", [])
    if closed_issues:
        lines.append(f"✅ Закрытые issues ({len(closed_issues)}):")
        for issue in closed_issues:
            number = issue.get("number", "")
            title = issue.get("title", "")
            lines.append(f"  #{number} {title}")
        lines.append("")

    # Обновлённые issues
    updated_issues = comparison.get("updated", [])
    if updated_issues:
        lines.append(f"🔄 Обновлённые issues ({len(updated_issues)}):")
        for issue in updated_issues:
            number = issue.get("number", "")
            title = issue.get("title", "")
            lines.append(f"  #{number} {title}")
        lines.append("")

    # Сводка
    total = len(new_issues) + len(closed_issues) + len(updated_issues) + len(comparison.get("unchanged", []))
    lines.append(f" Всего issues: {total}")
    lines.append(f"   Новых: {len(new_issues)}")
    lines.append(f"   Закрытых: {len(closed_issues)}")
    lines.append(f"   Обновлённых: {len(updated_issues)}")
    lines.append(f"   Без изменений: {len(comparison.get('unchanged', []))}")

    return "\n".join(lines)


def save_report(
    report_text: str,
    filename: Optional[str] = None,
) -> Path:
    """Сохранить отчёт в файл.

    Args:
        report_text: Текст отчёта
        filename: Имя файла (по умолчанию report_YYYYMMDD_HHMMSS.txt)

    Returns:
        Путь к созданному файлу.
    """
    REPORTS_DIR.mkdir(exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.txt"

    report_path = REPORTS_DIR / filename

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info("Report saved: %s", report_path.name)
    return report_path


def generate_full_report(
    current_issues: list[dict],
    repo_name: str = "",
    conn=None,
) -> dict:
    """Полный цикл: сравнить, сформировать отчёт, сохранить.

    Args:
        current_issues: Свежие issues с GitHub
        repo_name: Имя репозитория
        conn: Соединение с БД

    Returns:
        Словарь: {
            'comparison': {...},
            'report_text': '...',
            'report_path': Path(...),
        }
    """
    # 1. Сравниваем
    comparison = compare_issues(current_issues, conn)

    # 2. Формируем отчёт
    report_text = format_report(comparison, repo_name)

    # 3. Сохраняем
    report_path = save_report(report_text)

    return {
        "comparison": comparison,
        "report_text": report_text,
        "report_path": report_path,
    }
