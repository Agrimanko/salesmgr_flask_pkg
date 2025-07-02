
# SalesMgr Flask

## Requirements
- Python 3.10+
- pip

## Quickstart

```bash
# 1. Extract this folder
cd salesmgr_flask_pkg

# 2. (Optional) virtualenv
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py

# Open http://127.0.0.1:5000
```

First run seeds SQLite DB (`sales.db`) from `orders_seed.csv`. Delete that DB to reseed.

## Features
* Dashboard with start/end filter, metrics & Chart.js bar chart (Top 10 kode).
* Orders list (pagination), add, delete.
* Export to Excel (`/orders/export`).
