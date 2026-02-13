A Django-based file management application designed for efficient file handling, storage optimization through deduplication, and intelligent search capabilities.

## 🎯 Features Implemented

### ✅ File Deduplication System
- Automatic detection of duplicate files using SHA-256 hashing
- Storage optimization by creating references instead of duplicate copies
- Real-time tracking of storage savings

### ✅ Advanced Search & Filtering
- Search by filename (case-insensitive)
- Filter by file type (MIME type)
- Filter by file size range (min/max)
- Filter by upload date range (ISO 8601 format)
- Combine multiple filters simultaneously

### ✅ Rate Limiting
- Configurable per-user API rate limiting (default: 2 calls/second)
- Automatic reset after time window
- Proper HTTP 429 responses

### ✅ Storage Quota Management
- Per-user storage limits (default: 10MB)
- Real-time quota checking before uploads
- Deduplication-aware storage tracking

### ✅ Additional Endpoints
- **Storage Statistics**: View storage usage and savings from deduplication
- **File Types**: List unique file types uploaded by user

## 🚀 Technology Stack

### Backend
- Django 4.x (Python web framework)
- Django REST Framework (API development)
- SQLite (Development database)
- Gunicorn (WSGI HTTP Server)
- WhiteNoise (Static file serving)

### Infrastructure
- Docker and Docker Compose
- Local file storage with volume mounting

## 📋 Prerequisites

Before you begin, ensure you have installed:
- Python (3.9 or higher) - for local development
- Docker (20.10.x or higher) and Docker Compose (2.x or higher) - optional

## 🛠️ Quick Start

### Option 1: Local Development (Recommended for Testing)

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Activate virtual environment**
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies** (if needed)
   ```bash
   pip install -r requirements.txt
   ```

4. **Create necessary directories**
   ```bash
   mkdir -p media/uploads data staticfiles
   ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser (optional, for admin access)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

The server will be available at: **http://localhost:8000**

### Option 2: Using Docker

```bash
docker-compose up --build
```

## 🧪 Testing the Application

### Automated Testing

We provide two automated test scripts:

#### Option A: Bash Script
```bash
./test_api.sh
```

#### Option B: Python Script
```bash
python test_api.py
```

Both scripts will:
- ✅ Verify server is running
- ✅ Test file uploads
- ✅ Test deduplication
- ✅ Test search and filtering
- ✅ Test rate limiting
- ✅ Test storage quota
- ✅ Test all API endpoints

### Manual Testing

For detailed manual testing instructions, see **[TESTING_GUIDE.md](TESTING_GUIDE.md)**

The testing guide includes:
- Complete setup instructions
- All API endpoint examples with curl commands
- Expected responses for each test case
- Error case testing
- Performance testing guidelines

## 📝 API Documentation

### Important: All requests require `UserId` header
```bash
-H "UserId: user123"
```

### Core Endpoints

#### 1. Upload File
```bash
POST /api/files/
Header: UserId: <user_id>
Body: multipart/form-data with 'file' field
```

#### 2. List Files (with optional filters)
```bash
GET /api/files/?search=<query>&file_type=<mime>&min_size=<bytes>&max_size=<bytes>&start_date=<iso>&end_date=<iso>
Header: UserId: <user_id>
```

#### 3. Get File Details
```bash
GET /api/files/{id}/
Header: UserId: <user_id>
```

#### 4. Delete File
```bash
DELETE /api/files/{id}/
Header: UserId: <user_id>
```

#### 5. Storage Statistics
```bash
GET /api/files/storage_stats/
Header: UserId: <user_id>
```

#### 6. Available File Types
```bash
GET /api/files/file_types/
Header: UserId: <user_id>
```

### Example Usage

**Upload a file:**
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@document.pdf"
```

**Search files:**
```bash
curl -X GET "http://localhost:8000/api/files/?search=report&file_type=application/pdf" \
  -H "UserId: user123"
```

**Get storage stats:**
```bash
curl -X GET http://localhost:8000/api/files/storage_stats/ \
  -H "UserId: user123"
```

## 🗄️ Project Structure

```
dplat-file-vault-coding-challenge/
├── backend/                    # Django backend
│   ├── core/                   # Project settings
│   │   ├── settings.py         # Configuration (rate limits, storage quota)
│   │   └── urls.py             # Main URL routing
│   ├── files/                  # Main application
│   │   ├── models.py           # File and UserStorageStats models
│   │   ├── views.py            # API ViewSet with all endpoints
│   │   ├── serializers.py      # API serializers
│   │   ├── middleware.py       # Rate limiting middleware
│   │   ├── admin.py            # Admin interface
│   │   └── urls.py             # App URL routing
│   ├── media/uploads/          # Uploaded files storage
│   ├── data/                   # SQLite database
│   └── requirements.txt        # Python dependencies
├── TESTING_GUIDE.md            # Comprehensive testing instructions
├── IMPLEMENTATION_SUMMARY.md   # Detailed implementation documentation
├── test_api.sh                 # Bash test script
├── test_api.py                 # Python test script
├── create_submission_zip.py    # Submission zip creator
└── docker-compose.yml          # Docker composition
```

## ⚙️ Configuration

All limits are easily configurable in `backend/core/settings.py`:

```python
# Rate Limiting (X calls per N seconds)
RATE_LIMIT_CALLS = 2
RATE_LIMIT_WINDOW = 1  # seconds

# Storage Quota (MB per user)
USER_STORAGE_LIMIT_MB = 10
```

## 🔧 Key Implementation Features

### File Deduplication
- Uses SHA-256 hashing for file content identification
- Stores one physical copy, creates references for duplicates
- Tracks both actual and original storage usage
- Automatic storage savings calculation

### Search & Filtering
- Multiple simultaneous filters supported
- Database indexes for optimal performance
- Case-insensitive search
- Date range filtering with ISO 8601 format

### Rate Limiting
- Middleware-based implementation
- Per-user tracking via UserId header
- Configurable limits (calls per time window)
- Sliding window algorithm

### Storage Quota
- Per-user storage tracking
- Pre-upload validation
- Deduplication-aware (only counts actual storage)
- Real-time statistics endpoint

## 🔒 Security Features

- User isolation (users only see their own files)
- UUID-based file identification
- Input validation on all endpoints
- Django's built-in security features:
  - CSRF protection
  - XSS prevention
  - SQL injection protection

## 📊 Admin Interface

Access the admin interface at: **http://localhost:8000/admin/**

Features:
- View all files and metadata
- Monitor storage statistics per user
- Filter and search capabilities
- User-friendly interface for debugging

## 🐛 Troubleshooting

### Port Conflicts
```bash
# Use a different port
python manage.py runserver 8001
```

### Database Issues
```bash
# Reset database
rm backend/data/db.sqlite3
cd backend
python manage.py migrate
```

### File Upload Issues
- Maximum file size: 10MB per user quota
- Ensure proper permissions on media directory
- Check storage quota hasn't been exceeded

### Rate Limiting
- Default: 2 calls per second
- Wait 1+ second between bursts of requests
- Each user has independent rate limits

## 📚 Additional Documentation

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing instructions with examples
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Detailed technical documentation
- **Backend README** - See `backend/README.md` for more backend details

## 🚀 Production Deployment Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Set `DEBUG = False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use PostgreSQL or MySQL instead of SQLite
- [ ] Use Redis for cache backend (rate limiting)
- [ ] Configure cloud storage (S3, GCS, Azure Blob)
- [ ] Implement proper authentication/authorization
- [ ] Enable HTTPS
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Add virus scanning for uploads


## ✅ Features Checklist

- [x] File deduplication with SHA-256 hashing
- [x] Search by filename (case-insensitive)
- [x] Filter by file type (MIME type)
- [x] Filter by file size range
- [x] Filter by upload date range
- [x] Multiple simultaneous filters
- [x] Rate limiting (2 calls/second, configurable)
- [x] Storage quota (10MB per user, configurable)
- [x] Storage statistics endpoint
- [x] File types endpoint
- [x] Database indexing for performance
- [x] User isolation
- [x] Reference counting for deduplication
- [x] Proper error handling
- [x] Admin interface
- [x] Comprehensive documentation
- [x] Automated test scripts

