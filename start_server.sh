#!/bin/bash

# Abnormal File Vault - Start Server Script

echo "========================================"
echo "Starting Abnormal File Vault Server"
echo "========================================"
echo ""

cd backend

if [ ! -d "venv" ]; then
    echo "✗ Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting Django development server..."
echo "Server will be available at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

./venv/bin/python manage.py runserver
