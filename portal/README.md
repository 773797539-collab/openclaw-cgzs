# OpenClaw Agent Portal

Real-time dashboard for monitoring OpenClaw agents, tasks, and portfolio.

## Quick Start

```bash
cd /home/admin/openclaw/workspace/portal
python3 server.py
```

Portal runs at: **http://localhost:18792**

> Note: Port 18791 is reserved for the OpenClaw gateway. The portal runs on 18792.

## Features

- **Agent Activity Feed** - See what each agent is working on in real-time
- **Task Board** - Kanban-style task view (Todo / In Progress / Done / Blocked)
- **Portfolio Holdings** - Live stock positions with P&L
- **Price Charts** - Sparkline charts for each holding
- **Auto-refresh** - Updates every 10 seconds automatically

## Status Files

The portal reads from JSON files in `status/`:

| File | Description |
|------|-------------|
| `system.json` | Agent statuses and gateway info |
| `tasks.json` | Task board with status, workers, results |
| `portfolio.json` | Holdings with current prices |
| `portfolio_history.json` | Price history for sparkline charts |

Update these files to change what's displayed. The server will automatically pick up changes on the next refresh cycle.

## Architecture

- **FastAPI** server serves JSON API endpoints and the HTML page
- **Vanilla JavaScript** polls `/api/status/all` every 10 seconds
- **Vanilla CSS** - Dark theme matching OpenClaw aesthetic
- **No external dependencies** beyond FastAPI and uvicorn

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Main portal HTML page |
| `GET /api/status/all` | Combined status (system + tasks + portfolio) |
| `GET /api/status/system` | Agent and gateway status |
| `GET /api/status/tasks` | Task board data |
| `GET /api/status/portfolio` | Portfolio holdings |
| `GET /api/status/portfolio/history` | Price history for charts |
| `GET /static/portal.js` | Static JavaScript |

## Customization

### Adding a new task

Edit `status/tasks.json`:

```json
{
  "id": "task-006",
  "title": "Your task title",
  "description": "Task description",
  "status": "todo",
  "priority": "high",
  "workers": ["agent-name"],
  "created_at": "2026-03-26T10:00:00+08:00",
  "updated_at": "2026-03-26T10:00:00+08:00",
  "result": null,
  "labels": ["frontend", "backend"]
}
```

### Adding a portfolio holding

Edit `status/portfolio.json`:

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "shares": 10,
  "cost": 1500.00,
  "current_price": 172.50,
  "currency": "USD"
}
```

## Troubleshooting

**Portal won't start?**
```bash
# Check FastAPI is installed
pip install fastapi uvicorn

# Check port is free
lsof -i :18791
```

**Status not updating?**
- Verify JSON files are valid (no syntax errors)
- Check server logs for any errors
- Try clicking "Refresh Now" in the header

## Auto-start

The server attempts to auto-start `portal_inbox_server` if not running. For production use, consider setting up a systemd service or supervisor.
