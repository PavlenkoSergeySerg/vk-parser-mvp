"""Модуль сбора данных с GitHub API.

Парсит открытые issues из указанного репозитория.
Все настройки берутся из config.py (через .env).
"""

import time
import logging
import requests
import sys
from typing import Optional

import config

# Для Windows: переключаем stdout/stderr на UTF-8, чтобы кириллица в логах не падала
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Настраиваем логирование (правило: логи без секретов)
logger = logging.getLogger(__name__)

# GitHub API требует User-Agent — иначе вернёт 403
# Формат: имя-проекта/версия (правило хорошего тона)
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "vk-parser-mvp/1.0 (VK Education student project)"
}

# Базовый URL GitHub REST API
GITHUB_API_BASE = "https://api.github.com"


def get_issues(
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    state: str = "open",
    per_page: int = 30,
    page: int = 1,
) -> list[dict]:
    """Получить список issues из GitHub репозитория.
    
    Args:
        owner: Владелец репо (по умолчанию из .env)
        repo: Имя репо (по умолчанию из .env)
        state: Состояние issues — 'open', 'closed', 'all'
        per_page: Сколько issues за один запрос (max 100)
        page: Номер страницы для пагинации
    
    Returns:
        Список словарей с данными issues.
        Каждый dict содержит: number, title, user, labels, created_at, updated_at
    
    Raises:
        requests.HTTPError: при ошибке API (401, 404, 403)
        ValueError: если не настроены GITHUB_TOKEN/OWNER/REPO
    """
    # Берём значения из config (он читает .env)
    token = config.get_github_token()
    owner = owner or config.get_github_owner()
    repo = repo or config.get_github_repo()
    
    # Добавляем токен в заголовки
    headers = {**HEADERS, "Authorization": f"token {token}"}
    
    # Формируем URL endpoint
    # Документация: https://docs.github.com/en/rest/issues/issues#list-repository-issues
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues"
    
    # Параметры запроса
    params = {
        "state": state,
        "per_page": per_page,
        "page": page,
    }
    
    logger.info(f"Запрос issues: {owner}/{repo}, state={state}, page={page}")
    
    # Делаем запрос с таймаутом 10 секунд
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10,
    )
    
    # Проверяем статус ответа
    # 200 — ок, 401 — неверный токен, 404 — репо не найден, 403 — rate limit
    response.raise_for_status()
    
    # Парсим JSON
    issues = response.json()
    
    # GitHub API возвращает и pull requests вместе с issues
    # Фильтруем: оставляем только issues (у них нет ключа 'pull_request')
    issues_only = [
        issue for issue in issues if "pull_request" not in issue
    ]
    
    logger.info(f"Получено issues: {len(issues_only)} из {len(issues)} записей")
    
    return issues_only


def format_issue(issue: dict) -> dict:
    """Преобразует сырой ответ GitHub в удобную структуру.
    
    GitHub возвращает много полей — оставляем только нужные.
    """
    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "user": issue["user"]["login"],
        "labels": [label["name"] for label in issue.get("labels", [])],
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "url": issue["html_url"],
    }


def get_all_issues(
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    state: str = "open",
    max_pages: int = 5,
) -> list[dict]:
    """Получить все issues с пагинацией.
    
    GitHub возвращает максимум 100 issues за запрос.
    Если их больше — делаем несколько запросов с задержкой (rate limiting).
    
    Args:
        max_pages: Максимальное количество страниц (защита от бесконечного цикла)
    
    Returns:
        Список всех issues (до max_pages * 100 штук)
    """
    all_issues = []
    
    for page in range(1, max_pages + 1):
        logger.info(f"Загружаю страницу {page}/{max_pages}")
        
        issues = get_issues(owner=owner, repo=repo, state=state, page=page, per_page=100)
        
        if not issues:
            # Пустая страница — значит дальше ничего нет
            break
        
        all_issues.extend(issues)
        
        # Rate limiting: задержка 2 секунды между запросами
        # (правило из AGENTS.md — не чаще 1 запроса в 2–3 секунды)
        if page < max_pages:
            time.sleep(2)
    
    # Преобразуем в удобный формат
    return [format_issue(issue) for issue in all_issues]


def test_connection() -> bool:
    """Проверить подключение к GitHub API.
    
    Returns:
        True если подключение работает, False иначе.
    """
    try:
        token = config.get_github_token()
        owner = config.get_github_owner()
        repo = config.get_github_repo()
        
        headers = {**HEADERS, "Authorization": f"token {token}"}
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        logger.info(f"Подключение к GitHub OK: {owner}/{repo}")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка подключения к GitHub: {e}")
        return False
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return False