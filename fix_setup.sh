#!/bin/bash

# Fix Setup Script - Ensures packages are installed in venv

echo "========================================"
echo "Abnormal File Vault - Fixed Setup"
echo "========================================"
echo ""

# Navigate to backend directory
cd backend

echo "1. Removing old virtual environment..."
rm -rf venv
echo "✓ Old venv removed"
echo ""

echo "2. Creating fresh virtual environment..."
python3 -m venv venv
echo "✓ New venv created"
echo ""

echo "3. Creating necessary directories..."
mkdir -p media/uploads data staticfiles
echo "✓ Directories created"
echo ""

echo "4. Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

echo "5. Upgrading pip in venv..."
pip install --upgrade pip
echo "✓ Pip upgraded"
echo ""

echo "6. Installing dependencies in venv..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

echo "7. Verifying Django installation..."
python -c "import django; print(f'Django {django.get_version()} installed successfully!')"
echo ""

echo "8. Creating database migrations..."
python manage.py makemigrations
echo "✓ Migrations created"
echo ""

echo "9. Applying database migrations..."
python manage.py migrate
echo "✓ Migrations applied"
echo ""

echo "========================================"
echo "✓ Setup complete!"
echo "========================================"
echo ""
echo "Virtual environment is at: backend/venv"
echo ""
echo "To start the server, run:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "Or from project root:"
echo "  ./start_server.sh"
echo ""
echo "To run tests:"
echo "  ./test_api.sh"
echo "  OR"
echo "  python test_api.py"
