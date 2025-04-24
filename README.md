# 🔌 Energy Manager

An intelligent energy‐saving app that schedules your Tapo smart plugs based on electricity prices 📈.  
Includes a FastAPI backend and a Vite+React frontend with live plug control and usage charts.

---

## 🚀 Features

- ✅ Auto‐fetch and parse daily electricity prices
- ⏱️ Schedule N configurable periods per plug for cheapest runtime
- 📧 Daily email report with price chart (PNG)
- 🌐 REST API to list plugs, toggle on/off, view active countdown
- 📊 React UI with interactive plug details and hourly energy usage chart

---

## 📂 Project Structure

```
.
├── api.py
├── energy_manager.py
├── config.properties
├── requirements.txt
└── client
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.js
    └── src
        ├── App.tsx
        ├── main.tsx
        ├── App.css
        └── index.css
```

---

## 🛠️ Prerequisites

- Python 3.9+
- Node.js 16+ & npm
- Tapo account credentials & local SMTP server (or adjust `send_email`)

---

## ⚙️ Configuration

Create `config.properties` in the project root:

```properties
[email]
from_email = your_from_email@example.com
to_email   = your_to_email@example.com

[credentials]
tapo_email    = your_tapo_account@example.com
tapo_password = your_tapo_password

[plug1]
enabled                   = true
name                      = Kitchen Plug
address                   = 192.168.1.10
period1_start_hour        = 0
period1_end_hour          = 6
period1_runtime_human     = 2h
period2_start_hour        = 18
period2_end_hour          = 23
period2_runtime_human     = 1h

[plug2]
enabled                   = true
name                      = Washing Machine
address                   = 192.168.1.11
period1_start_hour        = 8
period1_end_hour          = 12
period1_runtime_human     = 1h30m
period2_start_hour        = 20
period2_end_hour          = 22
period2_runtime_human     = 45m
period3_start_hour        = 0
period3_end_hour          = 3
period3_runtime_human     = 15m
```

---

## 🏗️ Development

1. Clone & enter project dir
   ```bash
   git clone https://github.com/yourusername/energy-manager.git
   cd energy-manager
   ```

2. Python backend
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn api:app --reload
   ```
    - API runs on http://localhost:8000
    - Static chart served at `/api/static/prices_chart.png`

3. React frontend
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
    - Frontend runs on http://localhost:5173
    - Proxies `/api` → http://localhost:8000

---

## 🚀 Production

1. Build frontend
   ```bash
   cd frontend
   npm run build
   ```
    - Output in `frontend/dist`

2. Serve static assets and API under one domain
    - Copy `frontend/dist` into a static directory
    - Mount via FastAPI or use Nginx to serve `/` from `dist` and `/api` to Uvicorn

3. Run Uvicorn
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000
   ```

---

## 🔧 Troubleshooting

- Ensure Tapo IPs are reachable on your LAN
- Check SMTP logs for email delivery
- Increase logging level in `energy_manager.py` if needed

---

Feel free to ⭐ the repo!
