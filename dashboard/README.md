# Portfolio Health Dashboard

A simple, real-time web dashboard to visualize portfolio health metrics from the AI analysis.

## Features

- **Real-time Metrics**: Live summary cards showing key statistics
- **Interactive Charts**: Severity and type breakdown visualizations
- **Issues Table**: Priority-sorted open issues with contact information
- **Resolved Issues**: Recently resolved issues with resolution evidence
- **Auto-refresh**: Updates every 30 seconds

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Tailwind CSS + Vanilla JavaScript
- **Charts**: Chart.js
- **Data**: TinyDB (reads from `portfolio_data.json`)

## Quick Start

### 1. Run the Dashboard

```bash
# From project root
uv run python dashboard/app.py
```

Or use uvicorn directly:

```bash
uv run uvicorn dashboard.app:app --reload --host 0.0.0.0 --port 8000
```

### 2. Open in Browser

Navigate to: http://localhost:8000

## API Endpoints

The dashboard provides these REST API endpoints:

- `GET /` - Dashboard HTML page
- `GET /api/summary` - Portfolio summary statistics
- `GET /api/issues/open` - Open issues (sorted by priority)
- `GET /api/issues/resolved` - Resolved issues
- `GET /api/projects` - Project-level statistics
- `GET /health` - Health check

## API Examples

### Get Summary
```bash
curl http://localhost:8000/api/summary | jq
```

### Get Open Issues
```bash
curl http://localhost:8000/api/issues/open | jq
```

## Dashboard Sections

### 1. Summary Cards
- Total Issues
- Open Issues (with average priority)
- Resolved Issues (with resolution rate)
- Threads Analyzed

### 2. Charts
- **Severity Breakdown**: Doughnut chart showing high/medium/low severity issues
- **Type Breakdown**: Bar chart showing unresolved actions vs emerging risks

### 3. Open Issues Table
Priority-sorted table showing:
- Priority score
- Issue title and evidence
- Type (Action/Risk)
- Project name
- Contact person and email
- Days outstanding

### 4. Resolved Issues Table
Shows recently resolved issues with:
- Issue title
- Project
- Duration (days)
- Resolution evidence

## Auto-Refresh

The dashboard automatically refreshes data every 30 seconds to stay in sync with the database.

## Customization

### Change Port

```bash
uv run python dashboard/app.py --port 3000
```

Or edit `dashboard/app.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=3000)
```

### Modify Colors

Edit the Tailwind config in `dashboard/templates/dashboard.html`:

```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                primary: '#3b82f6',
                // Add your colors
            }
        }
    }
}
```

## Production Deployment

For production, use a proper ASGI server:

```bash
uv add gunicorn

# Run with gunicorn
gunicorn dashboard.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Or use Docker:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uvicorn", "dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### "Database not found"
Make sure you've run the analysis first:
```bash
uv run python main.py
```

### Port already in use
Change the port or kill the existing process:
```bash
lsof -ti:8000 | xargs kill
```

### Charts not loading
Check browser console for errors. Ensure Chart.js CDN is accessible.
