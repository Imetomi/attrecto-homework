#!/bin/bash
# Portfolio Health Dashboard Launcher

echo "🚀 Starting Portfolio Health Dashboard..."
echo ""
echo "Dashboard will be available at:"
echo "  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uv run uvicorn dashboard.app:app --host 127.0.0.1 --port 8000 --reload
