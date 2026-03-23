# RFID Access Control System

## Project Structure

```
rfid-system/
├── main.py               ← FastAPI app (all backend logic)
├── requirements.txt
├── rfid.db               ← SQLite database (auto-created on first run)
└── templates/
    ├── dashboard.html    ← Main UI
    └── partials/
        ├── card_row.html ← HTMX card table row
        └── log_rows.html ← HTMX log table rows
```

## Setup

```bash
# Create venv (recomended)
python -m venv .venv
# Activate venv
.venv\Scripts\activate

# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at: http://localhost:8000

## ESP32 Configuration

In your ESP32 sketch, change the `apiUrl` to point to your server:

```cpp
// If running locally (ESP32 and PC on same WiFi):
const char* apiUrl = "http://192.168.1.XXX:8000/functions/v1/rfid-api/check";
//                             ↑ replace with your PC's local IP

// If deployed to a server:
const char* apiUrl = "http://your-domain.com/functions/v1/rfid-api/check";
```

Find your PC's local IP:
- Windows: run `ipconfig` in cmd → look for IPv4 Address
- Linux/Mac: run `ip a` or `ifconfig`

> ⚠️  The ESP32 uses HTTP (not HTTPS) when talking to a local server.
>     Make sure both devices are on the same WiFi network.

## API Response Format

The `/functions/v1/rfid-api/check` endpoint matches exactly what your
existing ESP32 code expects:

**Access granted:**
```json
{ "access_granted": true, "user": { "name": "John Doe" } }
```

**Access denied:**
```json
{ "access_granted": false }
```

## Features

- ✅ Add / remove RFID cards via web UI
- ✅ Enable / disable cards without deleting them
- ✅ Real-time scan log (last 50 scans)
- ✅ Stats: total cards, active, granted, denied
- ✅ HTMX – no page reloads needed
- ✅ SQLite – no external database required
