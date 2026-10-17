"""Главный модуль парсера GitHub Issues.

Объединяет все модули:
- parser: получение данных с GitHub API
- storage: сохранение в SQLite и CSV
- reporter: формирование отчёта об изменениях
- notifier: отправка отчёта в Telegram

Запуск: python main.py
"""

import logging
import sys
from pathlib import Path

import config
import parser
import storage
import reporter
import notifier

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция парсера."""
    logger.info("=" * 60)
    logger.info("Запуск парсера GitHub Issues")
    logger.info("=" * 60)

    # 1. Проверяем настройки
    logger.info("Проверка настроек...")
    missing = config.check_required_env()
    if missing:
        logger.error("Отсутствуют обязательные переменные в .env: %s", missing)
        logger.error("Заполните .env и запустите снова")
        return False

    # Получаем настройки репозитория
    owner = config.get_github_owner()
    repo = config.get_github_repo()
    repo_name = f"{owner}/{repo}"
    logger.info("Репозиторий: %s", repo_name)

    # 2. Парсим issues с GitHub
    logger.info("Получение issues с GitHub API...")
    try:
        issues = parser.get_issues()
        logger.info("Получено issues: %d", len(issues))
    except Exception as e:
        logger.error("Ошибка при получении issues: %s", e)
        return False

    if not issues:
        logger.warning("Issues не получены. Проверьте токен и настройки репозитория")
        return False

    # 3. Сохраняем в БД и CSV
    logger.info("Сохранение данных...")
    save_result = storage.save_issues(issues)
    logger.info("Сохранено: %d, Пропущено: %d", save_result["saved"], save_result["skipped"])

    # Экспорт в CSV
    csv_path = storage.export_to_csv(issues)
    logger.info("CSV экспортирован: %s", csv_path.name)

    # 4. Формируем отчёт
    logger.info("Формирование отчёта...")
    report_result = reporter.generate_full_report(issues, repo_name=repo_name)
    logger.info("Отчёт создан: %s", report_result["report_path"].name)

    # Выводим отчёт в консоль
    print("\n" + report_result["report_text"] + "\n")

    # 5. Отправляем в Telegram
    logger.info("Отправка отчёта в Telegram...")
    sent = notifier.send_report(report_result["report_text"])
    if sent:
        logger.info("Отчёт успешно отправлен в Telegram")
    else:
        logger.warning("Не удалось отправить отчёт в Telegram (проверьте токен и chat_id)")

    # 6. Статистика
    stats = storage.get_stats()
    logger.info("Статистика БД: всего=%d, open=%d, closed=%d", stats["total"], stats["open"], stats["closed"])

    logger.info("=" * 60)
    logger.info("Парсер завершил работу")
    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
