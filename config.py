"""Модуль загрузки настроек из переменных окружения.

Все секреты (токены, ключи) читаются только из .env через os.getenv().

"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
# Path(__file__).parent — это папка, где лежит config.py
# .parent ещё раз — поднимаемся на уровень вверх (корень проекта)
project_root = Path(__file__).parent
env_path = project_root / ".env"

# load_dotenv() читает .env и добавляет переменные в os.environ
# override=False — не перезаписывает переменные, если они уже есть в системе
load_dotenv(dotenv_path=env_path, override=False)


def get_github_token() -> str:
    """Возвращает GitHub токен.
    
    Raises:
        ValueError: если токен не настроен в .env
    """
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "GITHUB_TOKEN не найден в .env. "
            "Скопируй .env.example в .env и заполни токен."
        )
    return token


def get_github_owner() -> str:
    """Возвращает имя владельца репозитория (username)."""
    owner = os.getenv("GITHUB_OWNER", "").strip()
    if not owner:
        raise ValueError(
            "GITHUB_OWNER не найден в .env. "
            "Укажи свой GitHub username."
        )
    return owner


def get_github_repo() -> str:
    """Возвращает имя репозитория."""
    repo = os.getenv("GITHUB_REPO", "").strip()
    if not repo:
        raise ValueError(
            "GITHUB_REPO не найден в .env. "
            "Укажи имя репозитория для парсинга issues."
        )
    return repo


def get_telegram_bot_token() -> str | None:
    """Возвращает токен Telegram бота (может быть None, если не настроен)."""
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None


def get_telegram_chat_id() -> str | None:
    """Возвращает chat_id для уведомлений (может быть None)."""
    return os.getenv("TELEGRAM_CHAT_ID", "").strip() or None


def get_parser_interval_hours() -> int:
    """Возвращает интервал парсинга в часах (по умолчанию 24)."""
    try:
        return int(os.getenv("PARSER_INTERVAL_HOURS", "24"))
    except ValueError:
        return 24


def check_required_env() -> list[str]:
    """Проверяет, что все обязательные переменные окружения заполнены.
    
    Returns:
        Список недостающих переменных. Пустой список = всё ок.
    """
    missing = []
    required = ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO"]
    
    for var in required:
        if not os.getenv(var, "").strip():
            missing.append(var)
    
    return missing

def get_http_proxy() -> str | None:
    """Возвращает HTTP прокси (может быть None)."""
    return os.getenv("HTTP_PROXY", "").strip() or None


def get_https_proxy() -> str | None:
    """Возвращает HTTPS прокси (может быть None)."""
    return os.getenv("HTTPS_PROXY", "").strip() or None


def get_proxies() -> dict | None:
    """Возвращает словарь прокси для requests (может быть None)."""
    http = get_http_proxy()
    https = get_https_proxy()
    if http or https:
        return {"http": http, "https": https}
    return None
