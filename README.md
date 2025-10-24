# 🚀 Kommo CRM Integration

Production-ready integration for syncing orders from Google Sheets to Kommo CRM with automated contact management and lead generation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 📋 Overview

This integration bridges your sales automation workflow by:
- 🔄 **Automatically syncing orders** from Google Sheets to Kommo CRM
- 👥 **Creating contacts** with Telegram metadata (ID, username, chat link)
- 💰 **Generating leads (deals)** for each order in the CRM
- 📝 **Adding timeline notes** with order details
- 🏷️ **Tagging contacts** (Support, Docs, Refund, Billing)
- ✅ **Deduplicating orders** to prevent duplicate entries
- 🔁 **Running continuously** with scheduled synchronization

Perfect for businesses using Telegram bots for sales and support, wanting to centralize data in Kommo CRM.

---

## ✨ Features

### Core Functionality
- ✅ **Google Sheets Integration** - Reads orders from specified sheet/tab
- ✅ **Kommo CRM API** - Full API integration with retry logic
- ✅ **Automatic Contact Creation** - Creates contacts if not found by Telegram ID
- ✅ **Lead Generation** - Creates deals/leads for each order
- ✅ **Timeline Notes** - Adds formatted notes to contact timeline
- ✅ **Smart Tagging** - Automatically tags contacts based on activity
- ✅ **Deduplication** - Prevents duplicate orders using fingerprinting
- ✅ **Error Handling** - Comprehensive error handling with retries
- ✅ **Logging** - Detailed logs with rotation

### Demo & Testing
- 🎭 **Unified Demo Runner** - Run all modules in one process
- 🤖 **Contact Generator** - Simulates Telegram support bot interactions
- 🛍️ **Order Generator** - Simulates sales bot creating orders
- 📊 **Live Dashboard** - Real-time sync statistics

---

## 🛠️ Requirements

- **Python 3.10+**
- **Google Service Account** with Sheets API access
- **Kommo CRM Account** with API access token
- **Google Sheet** with orders data

---

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/automatesh/kommo-crm-integration.git
cd kommo-crm-integration
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# Add your Google service account JSON to credentials/
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Kommo CRM
KOMMO_SUBDOMAIN=your_subdomain
KOMMO_ACCESS_TOKEN=your_long_lived_token

# Google Sheets
GOOGLE_CREDENTIALS_PATH=credentials/google_service_account.json
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_SHEET_NAME=Orders

# Sync Settings
SYNC_INTERVAL=10
LOG_LEVEL=INFO
```

### Google Service Account Setup

1. Create service account in Google Cloud Console
2. Enable Google Sheets API
3. Download JSON credentials
4. Place in `credentials/google_service_account.json`
5. Share your Google Sheet with service account email

### Kommo CRM Setup

1. Get your subdomain from Kommo URL
2. Create integration in Kommo settings
3. Generate long-lived access token
4. Add required custom fields:
   - Telegram ID (text)
   - Telegram Username (text)
   - Telegram Chat Link (text)

---

## 🚀 Usage

### Run Synchronization

#### One-time Sync
```bash
python main.py --mode once
```

#### Scheduled Sync (every 10 seconds)
```bash
python main.py --mode schedule
```

#### Test Connection
```bash
python main.py --test
```

### Generate Demo Data

#### Create Test Contacts (Telegram Bot Simulator)
```bash
python demo/telegram_bot_simulator.py --contacts 10
```

#### Create Test Orders (Sales Bot Simulator)
```bash
python demo/sales_bot_simulator.py --generate 20
```

#### Create Custom Fields in Kommo
```bash
python demo/create_custom_fields.py
```

### Run Full Demo

**All 3 modules simultaneously:**
```bash
python demo_runner.py
```

This runs:
- 👤 Contact Generator (every 15s)
- 🛍️ Order Generator (every 12s)
- 🔄 Order Sync (every 20s)

---

## 📊 Google Sheets Structure

Your Google Sheet should have these columns:

| Column | Type | Description |
|--------|------|-------------|
| `telegram_username` | string | @username of customer |
| `telegram_id` | string | Telegram ID (used for matching) |
| `date` | date | Order date (YYYY-MM-DD) |
| `product` | string | Product name |
| `amount` | number | Order amount |
| `currency` | string | Currency (USD, EUR, RUB) |
| `payment_status` | string | paid, pending, cancelled |

**Example:**
```
@ivan_petrov, 100001, 2025-10-24, Premium Subscription, 99.99, USD, paid
@maria_k, 100002, 2025-10-24, Pro Account, 149.50, EUR, pending
```

---

## 🏗️ Architecture

```
┌─────────────────┐
│ Google Sheets   │
│  (Orders Data)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  SheetsClient   │      │   KommoClient    │
│  (read orders)  │      │  (CRM API)       │
└────────┬────────┘      └────────┬─────────┘
         │                        │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────┐
         │ OrderSyncService│
         │  - Deduplicate  │
         │  - Create leads │
         │  - Add notes    │
         │  - Tag contacts │
         └────────┬────────┘
                  │
                  ▼
         ┌────────────────┐
         │   Kommo CRM    │
         │ - Contacts     │
         │ - Leads        │
         │ - Timeline     │
         │ - Tags         │
         └────────────────┘
```

---

## 📁 Project Structure

```
kommo-crm-integration/
├── src/
│   ├── __init__.py
│   ├── kommo_client.py          # Kommo CRM API client
│   ├── sheets_client.py         # Google Sheets client
│   ├── order_sync_service.py    # Sync orchestration logic
│   ├── message_simulator.py     # Telegram conversation generator
│   └── logger.py                # Logging configuration
│
├── demo/
│   ├── telegram_bot_simulator.py  # Contact generator
│   ├── sales_bot_simulator.py     # Order generator
│   └── create_custom_fields.py    # Setup Kommo fields
│
├── credentials/
│   └── google_service_account.json  # Google credentials (not in git)
│
├── logs/
│   └── kommo-sync.log             # Application logs
│
├── config.py                      # Configuration loader
├── main.py                        # Entry point
├── demo_runner.py                 # Unified demo runner
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

---

## 🔧 API Reference

### Order Object

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

### Timeline Note Format

```
🛍️ Товар: Premium Subscription
💰 Сумма: 99.99 USD
✅ Статус: paid
👤 Telegram: @ivan_petrov (ID: 100001)
📅 Дата: 24.10.2025
```

### Lead (Deal) Format

- **Name:** `{product} - {date}`
- **Budget:** `{amount}`
- **Contact:** Linked to contact by Telegram ID
- **Status:** Initial pipeline stage

---

## 🏷️ Tags

Contacts are automatically tagged based on activity:

| Tag | Description | Added When |
|-----|-------------|------------|
| `Support` | Support conversations | Has support messages |
| `Docs` | Documentation requests | Asks about docs |
| `Refund` | Refund requests | Mentions refund |
| `Billing` | Has orders | Any order synced |

---

## 📝 Logging

Logs are written to:
- **Console** (colored output)
- **File** `logs/kommo-sync.log` (with rotation)

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

Example output:
```
[2025-10-24 17:12:01] [INFO] Starting order synchronization
[2025-10-24 17:12:01] [INFO] Found 5 orders in Google Sheets
[2025-10-24 17:12:01] [INFO] Grouped orders into 4 unique contacts
[2025-10-24 17:12:02] [INFO]   💰 Created lead ID: 2013280
[2025-10-24 17:12:02] [INFO]   🏷️  Added 'Billing' tag to contact
[2025-10-24 17:12:02] [INFO]   ✓ Training Course - 4407.03 USD (paid)
```

---

## 🧪 Testing

Run tests:
```bash
pytest tests/
```

---

## 🚨 Troubleshooting

### Common Issues

**1. Authentication Failed (401)**
- Check `KOMMO_ACCESS_TOKEN` is valid
- Ensure token hasn't expired
- Verify subdomain is correct

**2. Google Sheets Permission Denied**
- Share sheet with service account email
- Check service account has read access
- Verify Sheet ID is correct

**3. Contact Not Found**
- Ensure "Telegram ID" custom field exists in Kommo
- Check field name matches exactly (case-sensitive)
- Verify Telegram IDs match between sheet and CRM

**4. Duplicates Still Created**
- Check deduplication logic in logs
- Verify order fingerprinting (date + amount + product)
- Ensure timeline notes format is consistent

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit pull request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Repository:** https://github.com/automatesh/kommo-crm-integration
- **Kommo CRM API:** https://www.kommo.com/developers/
- **Google Sheets API:** https://developers.google.com/sheets/api

---

## 👨‍💻 Author

**automatesh**  
📧 alex@automatesh.it.com

---

## 🙏 Acknowledgments

- Kommo CRM for excellent API documentation
- Google Sheets API for easy integration
- Python community for amazing libraries

---

**Built with ❤️ for seamless CRM automation**
