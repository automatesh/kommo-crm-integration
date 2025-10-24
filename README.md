# 🚀 Kommo CRM Интеграция

Production-ready интеграция для синхронизации заказов из Google Sheets в Kommo CRM с автоматическим управлением контактами и созданием сделок.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 📋 Обзор

Эта интеграция объединяет ваш процесс автоматизации продаж:
- 🔄 **Автоматическая синхронизация заказов** из Google Sheets в Kommo CRM
- 👥 **Создание контактов** с метаданными Telegram (ID, username, ссылка на чат)
- 💰 **Генерация сделок** для каждого заказа в CRM
- 📝 **Добавление заметок в timeline** с деталями заказа
- 🏷️ **Тегирование контактов** (Support, Docs, Refund, Billing)
- ✅ **Дедупликация заказов** для предотвращения дубликатов
- 🔁 **Непрерывная работа** по расписанию

Идеально для бизнеса, использующего Telegram ботов для продаж и поддержки, желающего централизовать данные в Kommo CRM.

---

## ✨ Возможности

### Основной функционал
- ✅ **Интеграция с Google Sheets** - Чтение заказов из указанной таблицы
- ✅ **Kommo CRM API** - Полная интеграция с логикой повторных попыток
- ✅ **Автоматическое создание контактов** - Создаёт контакты если не найдены по Telegram ID
- ✅ **Генерация сделок** - Создаёт сделки/лиды для каждого заказа
- ✅ **Timeline заметки** - Добавляет форматированные заметки в timeline контакта
- ✅ **Умное тегирование** - Автоматически проставляет теги в зависимости от активности
- ✅ **Дедупликация** - Предотвращает дублирование заказов через fingerprinting
- ✅ **Обработка ошибок** - Комплексная обработка ошибок с повторными попытками
- ✅ **Логирование** - Подробные логи с ротацией

### Демо и тестирование
- 🎭 **Объединённый демо-раннер** - Запуск всех модулей в одном процессе
- 🤖 **Генератор контактов** - Симулирует взаимодействия бота поддержки Telegram
- 🛍️ **Генератор заказов** - Симулирует создание заказов ботом продаж
- 📊 **Живая статистика** - Статистика синхронизации в реальном времени

---

## 🛠️ Требования

- **Python 3.10+**
- **Google Service Account** с доступом к Sheets API
- **Kommo CRM аккаунт** с API токеном доступа
- **Google Таблица** с данными заказов

---

## 📦 Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/automatesh/kommo-crm-integration.git
cd kommo-crm-integration
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить конфигурацию

```bash
# Скопировать пример файла окружения
cp .env.example .env

# Отредактировать .env с вашими credentials
# Добавить ваш Google service account JSON в credentials/
```

---

## ⚙️ Конфигурация

### Переменные окружения (.env)

```env
# Kommo CRM
KOMMO_SUBDOMAIN=ваш_субдомен
KOMMO_ACCESS_TOKEN=ваш_долгосрочный_токен

# Google Sheets
GOOGLE_CREDENTIALS_PATH=credentials/google_service_account.json
GOOGLE_SHEET_ID=id_вашей_таблицы
GOOGLE_SHEET_NAME=Orders

# Настройки синхронизации
SYNC_INTERVAL=10
LOG_LEVEL=INFO
```

### Настройка Google Service Account

1. Создать service account в Google Cloud Console
2. Включить Google Sheets API
3. Скачать JSON credentials
4. Поместить в `credentials/google_service_account.json`
5. Расшарить вашу Google таблицу на email service account

### Настройка Kommo CRM

1. Получить ваш субдомен из URL Kommo
2. Создать интеграцию в настройках Kommo
3. Сгенерировать долгосрочный токен доступа
4. Добавить необходимые пользовательские поля:
   - Telegram ID (текст)
   - Telegram Username (текст)
   - Telegram Chat Link (текст)

---

## 🚀 Использование

### Запуск синхронизации

#### Разовая синхронизация
```bash
python main.py --mode once
```

#### Синхронизация по расписанию (каждые 10 секунд)
```bash
python main.py --mode schedule
```

#### Тест подключения
```bash
python main.py --test
```

### Генерация демо-данных

#### Создать тестовые контакты (Симулятор Telegram бота)
```bash
python demo/telegram_bot_simulator.py --contacts 10
```

#### Создать тестовые заказы (Симулятор бота продаж)
```bash
python demo/sales_bot_simulator.py --generate 20
```

#### Создать пользовательские поля в Kommo
```bash
python demo/create_custom_fields.py
```

### Запуск полного демо

**Все 3 модуля одновременно:**
```bash
python demo_runner.py
```

Это запускает:
- 👤 Генератор контактов (каждые 15с)
- 🛍️ Генератор заказов (каждые 12с)
- 🔄 Синхронизация заказов (каждые 20с)

---

## 📊 Структура Google Sheets

Ваша Google таблица должна содержать эти колонки:

| Колонка | Тип | Описание |
|--------|------|----------|
| `telegram_username` | string | @username клиента |
| `telegram_id` | string | Telegram ID (используется для поиска) |
| `date` | date | Дата заказа (YYYY-MM-DD) |
| `product` | string | Название товара |
| `amount` | number | Сумма заказа |
| `currency` | string | Валюта (USD, EUR, RUB) |
| `payment_status` | string | paid, pending, cancelled |

**Пример:**
```
@ivan_petrov, 100001, 2025-10-24, Premium Subscription, 99.99, USD, paid
@maria_k, 100002, 2025-10-24, Pro Account, 149.50, EUR, pending
```

---

## 🏗️ Архитектура

```
┌─────────────────┐
│ Google Sheets   │
│  (Данные        │
│   заказов)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  SheetsClient   │      │   KommoClient    │
│  (чтение        │      │  (CRM API)       │
│   заказов)      │      │                  │
└────────┬────────┘      └────────┬─────────┘
         │                        │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ OrderSyncService│
         │  - Дедупликация │
         │  - Создание     │
         │    сделок       │
         │  - Добавление   │
         │    заметок      │
         │  - Тегирование  │
         └────────┬────────┘
                  │
                  ▼
         ┌────────────────┐
         │   Kommo CRM    │
         │ - Контакты     │
         │ - Сделки       │
         │ - Timeline     │
         │ - Теги         │
         └────────────────┘
```

---

## 📁 Структура проекта

```
kommo-crm-integration/
├── src/
│   ├── __init__.py
│   ├── kommo_client.py          # Kommo CRM API клиент
│   ├── sheets_client.py         # Google Sheets клиент
│   ├── order_sync_service.py    # Логика синхронизации
│   ├── message_simulator.py     # Генератор Telegram диалогов
│   └── logger.py                # Настройка логирования
│
├── demo/
│   ├── telegram_bot_simulator.py  # Генератор контактов
│   ├── sales_bot_simulator.py     # Генератор заказов
│   └── create_custom_fields.py    # Настройка полей Kommo
│
├── credentials/
│   └── google_service_account.json  # Google credentials (не в git)
│
├── logs/
│   └── kommo-sync.log             # Логи приложения
│
├── config.py                      # Загрузчик конфигурации
├── main.py                        # Точка входа
├── demo_runner.py                 # Объединённый демо-раннер
├── requirements.txt               # Python зависимости
├── .env.example                   # Шаблон окружения
├── .gitignore                     # Правила игнорирования Git
└── README.md                      # Этот файл
```

---

## 🔧 Справочник API

### Объект Order

```python
Order(
    telegram_username: str,    # @username
    telegram_id: str,          # "100001"
    date: datetime,            # 2025-10-24
    product: str,              # "Premium Subscription"
    amount: float,             # 99.99
    currency: str,             # "USD"
    payment_status: str        # "paid"
)
```

### Формат заметки Timeline

```
🛍️ Товар: Premium Subscription
💰 Сумма: 99.99 USD
✅ Статус: paid
👤 Telegram: @ivan_petrov (ID: 100001)
📅 Дата: 24.10.2025
```

### Формат сделки (Lead)

- **Название:** `{product} - {date}`
- **Бюджет:** `{amount}`
- **Контакт:** Привязан к контакту по Telegram ID
- **Статус:** Начальный этап воронки

---

## 🏷️ Теги

Контакты автоматически тегируются в зависимости от активности:

| Тег | Описание | Добавляется когда |
|-----|----------|-------------------|
| `Support` | Обращения в поддержку | Есть сообщения в поддержку |
| `Docs` | Запросы документации | Спрашивает о документации |
| `Refund` | Запросы возврата | Упоминает возврат |
| `Billing` | Есть заказы | Любой заказ синхронизирован |

---

## 📝 Логирование

Логи записываются в:
- **Консоль** (цветной вывод)
- **Файл** `logs/kommo-sync.log` (с ротацией)

Уровни логов: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

Пример вывода:
```
[2025-10-24 17:12:01] [INFO] Начало синхронизации заказов
[2025-10-24 17:12:01] [INFO] Найдено 5 заказов в Google Sheets
[2025-10-24 17:12:01] [INFO] Заказы сгруппированы по 4 уникальным контактам
[2025-10-24 17:12:02] [INFO]   💰 Создана сделка ID: 2013280
[2025-10-24 17:12:02] [INFO]   🏷️  Добавлен тег 'Billing' контакту
[2025-10-24 17:12:02] [INFO]   ✓ Training Course - 4407.03 USD (paid)
```

---

## 🧪 Тестирование

Запуск тестов:
```bash
pytest tests/
```

---

## 🚨 Решение проблем

### Частые проблемы

**1. Ошибка аутентификации (401)**
- Проверьте что `KOMMO_ACCESS_TOKEN` валидный
- Убедитесь что токен не истёк
- Проверьте правильность субдомена

**2. Google Sheets доступ запрещён**
- Расшарьте таблицу на email service account
- Проверьте что service account имеет доступ на чтение
- Проверьте правильность Sheet ID

**3. Контакт не найден**
- Убедитесь что пользовательское поле "Telegram ID" существует в Kommo
- Проверьте что название поля совпадает точно (учитывая регистр)
- Проверьте что Telegram ID совпадают между таблицей и CRM

**4. Всё равно создаются дубликаты**
- Проверьте логику дедупликации в логах
- Проверьте fingerprinting заказов (дата + сумма + товар)
- Убедитесь что формат заметок timeline консистентный

---

## 🤝 Вклад в проект

Вклад приветствуется! Пожалуйста:
1. Сделайте fork репозитория
2. Создайте feature ветку
3. Внесите изменения
4. Добавьте тесты
5. Отправьте pull request

---

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE) для деталей.

---

## 🔗 Ссылки

- **Репозиторий:** https://github.com/automatesh/kommo-crm-integration
- **Kommo CRM API:** https://www.kommo.com/developers/
- **Google Sheets API:** https://developers.google.com/sheets/api

---

## 👨‍💻 Автор

**automatesh**  
📧 alex@automatesh.it.com

---

## 🙏 Благодарности

- Kommo CRM за отличную документацию API
- Google Sheets API за простую интеграцию
- Python сообществу за потрясающие библиотеки

---

**Создано с ❤️ для бесшовной автоматизации CRM**
