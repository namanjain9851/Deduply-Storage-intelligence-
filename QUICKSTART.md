# 🚀 Quick Start Guide - Abnormal File Vault

This guide will help you get the project running and tested in under 5 minutes!

## Step 1: Initial Setup (First Time Only)

Run the setup script:

```bash
./setup.sh
```

This will:
- Create necessary directories
- Activate virtual environment
- Install dependencies
- Create and apply database migrations

**⏱️ Time: ~2-3 minutes**

---

## Step 2: Start the Server

Run the start server script:

```bash
./start_server.sh
```

Or manually:

```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

**The server will be available at: http://localhost:8000**

**⏱️ Time: ~10 seconds**

---

## Step 3: Test the API

### Option A: Automated Tests (Recommended)

In a **new terminal window**, run:

```bash
./test_api.sh
```

Or use the Python version:

```bash
python test_api.py
```

**⏱️ Time: ~30 seconds**

### Option B: Manual Quick Test

In a **new terminal window**, try these commands:

#### 1. Create a test file
```bash
echo "Hello, File Vault!" > test.txt
```

#### 2. Upload it
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@test.txt"
```

#### 3. List your files
```bash
curl -X GET http://localhost:8000/api/files/ \
  -H "UserId: user123"
```

#### 4. Get storage stats
```bash
curl -X GET http://localhost:8000/api/files/storage_stats/ \
  -H "UserId: user123"
```

**⏱️ Time: ~1 minute**

---

## Step 4: Verify Features

### ✅ Test File Deduplication

Upload the same file twice:

```bash
# First upload
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@test.txt"

# Second upload (should create reference, not duplicate)
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@test.txt"
```

Check the response: `is_reference` should be `true` for the second upload.

### ✅ Test Search & Filtering

```bash
# Search by filename
curl -X GET "http://localhost:8000/api/files/?search=test" \
  -H "UserId: user123"

# Filter by file type
curl -X GET "http://localhost:8000/api/files/?file_type=text/plain" \
  -H "UserId: user123"
```

### ✅ Test Rate Limiting

Make 3 rapid requests (3rd should fail):

```bash
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123" & \
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123" & \
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123"
```

The 3rd request should return: `{"error": "Call Limit Reached"}`

### ✅ Test Storage Quota

Try uploading files larger than 10MB total per user - should get quota error.

---

## Common Commands Cheat Sheet

### Server Management
```bash
# Start server
./start_server.sh

# Stop server
# Press Ctrl+C in the server terminal
```

### Testing
```bash
# Run automated tests
./test_api.sh
# OR
python test_api.py

# Run specific curl test
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123"
```

### Database Management
```bash
cd backend
source venv/bin/activate

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser (for admin access)
python manage.py createsuperuser

# Reset database
rm data/db.sqlite3
python manage.py migrate
```

### Admin Interface
```bash
# Create superuser first (if not done)
cd backend
source venv/bin/activate
python manage.py createsuperuser

# Then access at:
# http://localhost:8000/admin/
```

---

## API Endpoints Quick Reference

**Base URL:** `http://localhost:8000/api/files/`

**Required Header:** `UserId: <user_id>`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files/` | POST | Upload file |
| `/api/files/` | GET | List files (with filters) |
| `/api/files/{id}/` | GET | Get file details |
| `/api/files/{id}/` | DELETE | Delete file |
| `/api/files/storage_stats/` | GET | Storage statistics |
| `/api/files/file_types/` | GET | Available file types |

### Query Parameters for List/Filter

| Parameter | Example | Description |
|-----------|---------|-------------|
| `search` | `?search=report` | Search filename |
| `file_type` | `?file_type=application/pdf` | Filter by MIME type |
| `min_size` | `?min_size=1024` | Min file size (bytes) |
| `max_size` | `?max_size=5242880` | Max file size (bytes) |
| `start_date` | `?start_date=2024-01-01T00:00:00Z` | Files after date |
| `end_date` | `?end_date=2024-12-31T23:59:59Z` | Files before date |

---

## Troubleshooting

### Port Already in Use
```bash
# Use a different port
cd backend
source venv/bin/activate
python manage.py runserver 8001
```

### Virtual Environment Issues
```bash
# Recreate virtual environment
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database Issues
```bash
cd backend
rm data/db.sqlite3
source venv/bin/activate
python manage.py migrate
```

### Permission Issues
```bash
chmod +x setup.sh start_server.sh test_api.sh test_api.py
chmod -R 755 backend/media/
```

---

## Configuration

Edit `backend/core/settings.py` to adjust:

```python
# Rate Limiting
RATE_LIMIT_CALLS = 2      # Calls per window
RATE_LIMIT_WINDOW = 1     # Time window in seconds

# Storage Quota
USER_STORAGE_LIMIT_MB = 10  # MB per user
```

---

## What's Next?

- ✅ **Testing**: See [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive test cases
- ✅ **Documentation**: See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
- ✅ **Admin**: Access admin interface at http://localhost:8000/admin/
- ✅ **Production**: Review production deployment checklist in README.md

---

## Summary

**You now have a fully functional file vault with:**
- ✅ File deduplication (saves storage)
- ✅ Advanced search and filtering
- ✅ Rate limiting (2 calls/second)
- ✅ Storage quotas (10MB per user)
- ✅ Storage statistics
- ✅ File type listing

**Happy Testing! 🎉**
