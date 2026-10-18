# VK Parser MVP — Парсер GitHub Issues с уведомлениями в Telegram

Учебный проект для VK Обучение. Парсер собирает issues из GitHub-репозиториев, сохраняет историю изменений и отправляет отчёты в Telegram.

## Цель проекта

Автоматизировать мониторинг GitHub-репозиториев с уведомлениями об изменениях (новые issues, закрытые, обновлённые).

## Возможности

- Парсинг GitHub API с rate limiting (2 сек между запросами)
- Хранение данных в SQLite (история изменений)
- Экспорт в CSV для анализа в Excel
- Сравнение с предыдущим запуском (новые/закрытые/обновлённые issues)
- Отправка отчётов в Telegram через бота
- Поддержка HTTP-прокси (для работы в регионах с блокировками)
- Безопасное хранение секретов в `.env`

## Быстрый старт

### 1. Установка

```bash
git clone <url-репозитория>
cd vk-parser-mvp

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. Настройка

Скопируй шаблон и заполни своими данными:

```bash
cp .env.example .env
```

Открой `.env` и заполни:
- `GITHUB_TOKEN` — токен GitHub (https://github.com/settings/tokens)
- `GITHUB_OWNER` — владелец репозитория (например, `microsoft`)
- `GITHUB_REPO` — название репозитория (например, `vscode`)
- `TELEGRAM_BOT_TOKEN` — токен бота от @BotFather (опционально)
- `TELEGRAM_CHAT_ID` — твой chat_id от @userinfobot (опционально)
- `HTTP_PROXY` / `HTTPS_PROXY` — прокси для Telegram (опционально, для РФ)

### 3. Запуск

```bash
python main.py
```

### 4. Результат

В консоли — логи работы парсера. В Telegram — отчёт:

```
 Отчёт по репозиторию: microsoft/vscode
🕐 Время: 2026-10-17 21:23

🔄 Обновлённые issues (1):
  #342303 Excessive memory usage when using agent coding on win11

 Всего issues: 20
   Новых: 0
   Закрытых: 0
   Обновлённых: 1
   Без изменений: 19
```

## Архитектура

Модульная архитектура с разделением ответственности:

| Модуль | Ответственность |
|--------|----------------|
| `config.py` | Загрузка настроек из `.env` |
| `parser.py` | Парсинг GitHub Issues API |
| `storage.py` | Хранение в SQLite + экспорт в CSV |
| `reporter.py` | Формирование отчёта об изменениях |
| `notifier.py` | Отправка уведомлений в Telegram |
| `main.py` | Точка входа, оркестрация модулей |

## Технические детали

### Rate Limiting
GitHub API ограничивает запросы: 60/час для анонимных, 5000 для авторизованных. Парсер делает паузу 2 секунды между запросами.

### Нормализация данных
GitHub API возвращает сложные структуры (dict, list). Модуль `storage.py` нормализует их:
- `user: {"login": "octocat", ...}` → `"octocat"`
- `labels: [{"name": "bug"}, ...]` → `"bug,enhancement"`

### Прокси для Telegram
В регионах с блокировками Telegram API недоступен напрямую. Модуль `notifier.py` поддерживает HTTP/HTTPS прокси через переменные `HTTP_PROXY` и `HTTPS_PROXY`.

### Идемпотентность
Повторный запуск не создаёт дубликаты в БД благодаря `UNIQUE(number, url)` constraint и `INSERT OR IGNORE`.

## Структура проекта


vk-parser-mvp/
── main.py              # Точка входа
├── config.py            # Загрузка настроек
├── parser.py            # Парсинг GitHub API
├── storage.py           # SQLite + CSV
├── reporter.py          # Формирование отчёта
├── notifier.py          # Telegram-уведомления
├── .env.example         # Шаблон переменных окружения
├── .gitignore           # Исключения для Git
├── AGENTS.md            # Инструкции для AI-агентов
├── README.md            # Документация
└── requirements.txt     # Зависимости


## Чему я научился

1. Работа с REST API (GitHub, Telegram)
2. Модульная архитектура Python-приложений
3. Обработка ошибок и graceful degradation
4. Безопасное хранение секретов (.env)
5. Нормализация сложных данных (dict → str)
6. Настройка прокси для обхода блокировок
7. Git workflow с атомарными коммитами

## Использованные технологии

- Python 3.13
- GitHub REST API
- Telegram Bot API
- SQLite3
- HTTP-прокси
- Git + GitHub
- VS Code

## Автор

Сергей Павленко  
Учебный проект для VK Обучение  
Октябрь 2026
