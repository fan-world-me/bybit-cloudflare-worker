# Bybit Trades Sync — Cloudflare Workers

Автоматическая синхронизация исполненных сделок с [Bybit API v5](https://bybit-exchange.github.io/docs/v5/intro) в базу данных [Cloudflare D1](https://developers.cloudflare.com/d1/). Запускается как Cloudflare Worker каждые 6 часов через cron-триггер.

## Возможности

- Получает историю исполнений по всем категориям: `spot`, `linear`, `inverse`
- Асинхронно записывает новые сделки в Cloudflare D1 (дублей не создаёт)
- Автоматически запускается раз в 6 часов (cron trigger)
- REST API на FastAPI для ручного запуска и просмотра данных
- Написан на Python (Cloudflare Workers Python runtime / Pyodide)

## Технологии

| Компонент       | Технология                          |
|-----------------|-------------------------------------|
| Runtime         | Cloudflare Workers (Python/Pyodide) |
| HTTP-фреймворк  | FastAPI (ASGI)                      |
| База данных     | Cloudflare D1 (SQLite)              |
| Источник данных | Bybit REST API v5                   |
| Расписание      | Cloudflare Cron Triggers            |

## Структура проекта
bybit-cloudflare-worker/

├── src/

│   ├── index.py          # FastAPI приложение + on_scheduled handler

│   ├── bybit_client.py   # Клиент Bybit API v5 (async, HMAC-SHA256)

│   ├── database.py       # Операции с Cloudflare D1

│   └── models.py         # Pydantic модели данных

├── schema.sql            # SQL схема для D1

├── wrangler.toml         # Конфиг Cloudflare Workers

├── .env                  # Секреты (не попадает в Git)

├── .env.example          # Шаблон переменных окружения

├── requirements.txt      # Зависимости

└── README.md

## Быстрый старт

### 1. Клонируй репозиторий

```bash
git clone https://github.com/fan-world-me/bybit-cloudflare-worker.git
cd bybit-cloudflare-worker
```

### 2. Заполни `.env`

```bash
cp .env.example .env
```

Открой `.env` и заполни своими данными:

```env
BYBIT_API_KEY=твой_api_key
BYBIT_API_SECRET=твой_api_secret
CLOUDFLARE_ACCOUNT_ID=твой_account_id
CLOUDFLARE_API_TOKEN=твой_api_token
```

> `.env` прописан в `.gitignore` — никогда не попадёт в Git.

### 3. Установи Wrangler

```bash
npm install -g wrangler
wrangler login
```

### 4. Создай D1 базу данных

```bash
wrangler d1 create bybit-trades
```

Скопируй `database_id` из вывода и вставь в `wrangler.toml`:

```toml
[[d1_databases]]
binding = "DB"
database_name = "bybit-trades"
database_id = "ВАШ_DATABASE_ID"
```

### 5. Накати схему

```bash
wrangler d1 execute bybit-trades --remote --file=schema.sql
```

### 6. Добавь секреты в Cloudflare

```bash
wrangler secret put BYBIT_API_KEY
wrangler secret put BYBIT_API_SECRET
```

### 7. Деплой

```bash
wrangler deploy
```

## API эндпоинты

| Метод | Путь     | Описание                              |
|-------|----------|---------------------------------------|
| GET   | /health  | Проверка состояния сервиса            |
| GET   | /trades  | Список последних сделок (`?limit=20`) |
| POST  | /sync    | Ручной запуск синхронизации с Bybit   |

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

```toml
[triggers]
crons = ["0 */6 * * *"]  # каждые 6 часов (00:00, 06:00, 12:00, 18:00 UTC)
```

## Получение API ключей Bybit

1. Войди в [Bybit](https://www.bybit.com)
2. Перейди в **Account** → **API Management**
3. Создай ключ с разрешениями: **Read** → **Unified Trading / Spot / Derivatives**
4. Скопируй API Key и API Secret в `.env`

## Безопасность

- Секреты хранятся в Cloudflare Secrets — не в коде и не в репозитории
- `.env` защищён `.gitignore`
- Подпись запросов к Bybit: HMAC-SHA256

## Лицензия

[GNU General Public License v3.0](LICENSE)