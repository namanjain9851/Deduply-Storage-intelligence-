#!/bin/bash

# Abnormal File Vault - Setup Script
# This script sets up the project for the first time

echo "========================================"
echo "Abnormal File Vault - Setup Script"
echo "========================================"
echo ""

# Navigate to backend directory
cd backend

echo "1. Creating necessary directories..."
mkdir -p media/uploads data staticfiles
echo "✓ Directories created"
echo ""

echo "2. Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠ Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✓ Virtual environment created and activated"
fi
echo ""

echo "3. Installing/upgrading dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

echo "4. Creating database migrations..."
python manage.py makemigrations
echo "✓ Migrations created"
echo ""

echo "5. Applying database migrations..."
python manage.py migrate
echo "✓ Migrations applied"
echo ""

echo "========================================"
echo "✓ Setup complete!"
echo "========================================"
echo ""
echo "To start the server, run:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "Or simply run:"
echo "  ./start_server.sh"
echo ""
echo "To run tests, use:"
echo "  ./test_api.sh"
echo "  OR"
echo "  python test_api.py"
