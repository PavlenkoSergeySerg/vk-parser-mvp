"""Модуль отправки отчёта в Telegram.

Использует Telegram Bot API для отправки текстовых сообщений.
Если бот не настроен (нет токена или chat_id) — возвращает False без падения.
"""

import logging
import sys
from typing import Optional

import requests

import config

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

# Telegram Bot API
TELEGRAM_API_BASE = "https://api.telegram.org"

# Максимальная длина сообщения в Telegram
MAX_MESSAGE_LENGTH = 4096


def send_message(
    text: str,
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
    parse_mode: str = "HTML",
) -> bool:
    """Отправить текстовое сообщение в Telegram.

    Args:
        text: Текст сообщения (поддерживает HTML-разметку)
        chat_id: ID чата (по умолчанию из .env)
        bot_token: Токен бота (по умолчанию из .env)
        parse_mode: Формат разметки — "HTML" или "Markdown"

    Returns:
        True если сообщение отправлено, False иначе.
    """
    # Берём настройки из config
    token = bot_token or config.get_telegram_bot_token()
    chat = chat_id or config.get_telegram_chat_id()

    # Проверяем, что настройки есть
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN не настроен в .env")
        return False
    if not chat:
        logger.warning("TELEGRAM_CHAT_ID не настроен в .env")
        return False

    # Формируем URL
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"

    # Данные запроса
    payload = {
        "chat_id": chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        proxies = config.get_proxies()
        response = requests.post(url, json=payload, timeout=10, proxies=proxies)
        response.raise_for_status()

        result = response.json()
        if result.get("ok"):
            logger.info("Message sent to Telegram chat %s", chat)
            return True
        else:
            logger.error("Telegram API error: %s", result.get("description"))
            return False

    except requests.exceptions.RequestException as e:
        logger.error("Telegram request failed: %s", e)
        return False


def send_long_message(
    text: str,
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> bool:
    """Отправить длинное сообщение, разбивая на части.

    Telegram ограничивает сообщения 4096 символами.
    Эта функция разбивает текст на части по переносам строк.

    Args:
        text: Длинный текст сообщения
        chat_id: ID чата (по умолчанию из .env)
        bot_token: Токен бота (по умолчанию из .env)

    Returns:
        True если все части отправлены, False если хотя бы одна не отправлена.
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        return send_message(text, chat_id, bot_token)

    # Разбиваем текст на части
    parts = _split_text(text, MAX_MESSAGE_LENGTH)
    logger.info("Splitting message into %d parts", len(parts))

    all_sent = True
    for i, part in enumerate(parts, 1):
        header = f"({i}/{len(parts)})\n"
        success = send_message(header + part, chat_id, bot_token)
        if not success:
            all_sent = False
            logger.error("Failed to send part %d/%d", i, len(parts))

    return all_sent


def _split_text(text: str, max_length: int) -> list[str]:
    """Разбить текст на части по переносам строк.

    Args:
        text: Исходный текст
        max_length: Максимальная длина части

    Returns:
        Список частей текста.
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    for line in text.split("\n"):
        # Если строка сама длиннее лимита — разбиваем по символам
        if len(line) > max_length:
            if current_part:
                parts.append(current_part)
                current_part = ""
            for i in range(0, len(line), max_length):
                parts.append(line[i:i + max_length])
            continue

        # Проверяем, поместится ли строка в текущую часть
        if len(current_part) + len(line) + 1 <= max_length:
            current_part = current_part + "\n" + line if current_part else line
        else:
            # Текущая часть заполнена — сохраняем и начинаем новую
            if current_part:
                parts.append(current_part)
            current_part = line

    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part)

    return parts


def send_report(
    report_text: str,
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> bool:
    """Отправить отчёт в Telegram (с автоматической разбивкой).

    Это основная функция для использования в main.py.

    Args:
        report_text: Текст отчёта из reporter.py
        chat_id: ID чата (по умолчанию из .env)
        bot_token: Токен бота (по умолчанию из .env)

    Returns:
        True если отчёт отправлен, False иначе.
    """
    logger.info("Sending report to Telegram (length: %d)", len(report_text))
    return send_long_message(report_text, chat_id, bot_token)


def test_connection(
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> bool:
    """Проверить подключение к Telegram Bot API.

    Отправляет тестовое сообщение "✅ Парсер подключён к Telegram".

    Args:
        chat_id: ID чата (по умолчанию из .env)
        bot_token: Токен бота (по умолчанию из .env)

    Returns:
        True если подключение работает, False иначе.
    """
    test_message = "✅ <b>Парсер подключён к Telegram</b>\n\nЕсли вы видите это сообщение — бот работает корректно."
    return send_message(test_message, chat_id, bot_token)


def get_me(bot_token: Optional[str] = None) -> Optional[dict]:
    """Получить информацию о боте (для проверки токена).

    Args:
        bot_token: Токен бота (по умолчанию из .env)

    Returns:
        Словарь с информацией о боте или None при ошибке.
    """
    token = bot_token or config.get_telegram_bot_token()
    if not token:
        return None

    url = f"{TELEGRAM_API_BASE}/bot{token}/getMe"

    try:
        proxies = config.get_proxies()
        response = requests.get(url, timeout=10, proxies=proxies)
        response.raise_for_status()
        result = response.json()
        if result.get("ok"):
            return result.get("result")
        return None
    except requests.exceptions.RequestException:
        return None
# test save
   # ПРОВЕРКА СОХРАНЕНИЯ ПРЯМО СЕЙЧАС
