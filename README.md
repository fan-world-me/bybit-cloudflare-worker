# Bybit Trades Sync — Cloudflare Workers

Автоматическая синхронизация исполненных сделок с [Bybit API v5](https://bybit-exchange.github.io/docs/v5/intro) в базу данных [Cloudflare D1](https://developers.cloudflare.com/d1/). Запускается как Cloudflare Worker каждые 6 часов через cron-триггер.

## Возможности

- Получает историю исполнений по всем категориям: `spot`, `linear`, `inverse`
- Асинхронно записывает новые сделки в Cloudflare D1 (дублей не создаёт)
- Автоматически запускается раз в 6 часов (cron trigger)
- REST API на FastAPI для ручного запуска и просмотра данных
- Написан на Python (Cloudflare Workers Python runtime / Pyodide)

## Технологии

| Компонент        | Технология                          |
|-----------------|-------------------------------------|
| Runtime          | Cloudflare Workers (Python/Pyodide) |
| HTTP-фреймворк  | FastAPI (ASGI)                      |
| База данных      | Cloudflare D1 (SQLite)              |
| Источник данных  | Bybit REST API v5                   |
| Расписание       | Cloudflare Cron Triggers            |

## Структура проекта

```
bybit-cloudflare-worker/
├── src/
│   ├── index.py          # FastAPI приложение + on_scheduled handler
│   ├── bybit_client.py   # Клиент Bybit API v5 (async, HMAC-SHA256)
│   ├── database.py       # Операции с Cloudflare D1
│   └── models.py         # Pydantic модели данных
├── schema.sql            # SQL схема для D1 (применить вручную)
├── wrangler.toml         # Конфиг Cloudflare Workers
├── requirements.txt      # Зависимости для локальной разработки
└── README.md
```

## Быстрый старт

### 1. Установка Wrangler

```bash
npm install -g wrangler
wrangler login
```

### 2. Создание D1 базы данных

```bash
wrangler d1 create bybit-trades
```

Скопируй `database_id` из вывода и вставь в `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "bybit-trades"
database_id = "ТВОЙ_DATABASE_ID_СЮДА"
```

### 3. Применение схемы

```bash
wrangler d1 execute bybit-trades --file=schema.sql
```

### 4. Добавление секретов

```bash
wrangler secret put BYBIT_API_KEY
wrangler secret put BYBIT_API_SECRET
```

### 5. Деплой

```bash
wrangler deploy
```

## API эндпоинты

| Метод  | Путь      | Описание                                |
|--------|----------|-----------------------------------------|
| GET    | /health  | Проверка состояния сервиса              |
| GET    | /trades  | Список последних сделок из D1 (`?limit=20`) |
| POST   | /sync    | Ручной запуск синхронизации с Bybit     |

### Примеры запросов

```bash
# Проверить статус
curl https://bybit-trades-sync.YOUR_SUBDOMAIN.workers.dev/health

# Последние 50 сделок
curl https://bybit-trades-sync.YOUR_SUBDOMAIN.workers.dev/trades?limit=50

# Ручная синхронизация
curl -X POST https://bybit-trades-sync.YOUR_SUBDOMAIN.workers.dev/sync
```

### Пример ответа `/sync`

```json
{
  "success": true,
  "new_trades": 12,
  "total_fetched": 150,
  "message": "Synced 12 new trades out of 150 fetched."
}
```

## Cron расписание

Воркер запускается автоматически по расписанию, заданному в `wrangler.toml`:

```toml
[triggers]
crons = ["0 */6 * * *"]   # каждые 6 часов (00:00, 06:00, 12:00, 18:00 UTC)
```

Изменить расписание можно в `wrangler.toml` — [формат cron стандартный](https://developers.cloudflare.com/workers/configuration/cron-triggers/).

## Схема базы данных D1

```sql
CREATE TABLE trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exec_id         TEXT    NOT NULL UNIQUE,   -- уникальный ID исполнения
    order_id        TEXT    NOT NULL,
    symbol          TEXT    NOT NULL,           -- BTCUSDT, ETHUSDT, ...
    category        TEXT    NOT NULL,           -- spot / linear / inverse
    side            TEXT    NOT NULL,           -- Buy / Sell
    order_type      TEXT    NOT NULL,           -- Market / Limit
    exec_price      TEXT    NOT NULL,
    exec_qty        TEXT    NOT NULL,
    exec_value      TEXT    NOT NULL,
    exec_fee        TEXT    NOT NULL,
    fee_currency    TEXT    NOT NULL,
    exec_time       TEXT    NOT NULL,           -- timestamp в мс
    order_link_id   TEXT,
    stop_order_type TEXT,
    created_at      INTEGER NOT NULL DEFAULT (unixepoch())
);
```

## Локальная разработка

```bash
pip install -r requirements.txt
```

> **Примечание:** для локального тестирования используй `uvicorn src.index:app --reload`. Привязки D1 и секреты доступны только в среде Cloudflare Workers — локально их нужно мокировать.

## Получение API ключей Bybit

1. Войди в [Bybit](https://www.bybit.com)
2. Перейди в **Account** → **API Management**
3. Создай ключ с разрешениями: **Read** → **Unified Trading** / **Spot** / **Derivatives**
4. Сохрани API Key и API Secret

## Безопасность

- Секреты хранятся в Cloudflare Secrets (не в коде)
- Подпись запросов к Bybit: HMAC-SHA256
- Все данные остаются в твоей инфраструктуре Cloudflare

## Лицензия

Этот проект распространяется под лицензией [GNU General Public License v3.0](LICENSE).
