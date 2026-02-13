# Implementation Summary - Abnormal File Vault

## Overview
This document provides a comprehensive overview of the implemented features for the Abnormal File Vault project.

## Features Implemented

### ✅ 1. File Deduplication System

**Implementation Details:**
- **Hash Algorithm**: SHA-256 for reliable file content identification
- **Storage Strategy**: Files with identical content share the same physical file on disk
- **Reference System**: Duplicate uploads create lightweight reference entries instead of storing multiple copies

**How It Works:**
1. When a file is uploaded, its SHA-256 hash is calculated
2. The system checks if a file with the same hash already exists for that user
3. If exists: Creates a reference entry pointing to the original file
4. If new: Stores the physical file and creates the original entry

**Database Schema:**
```python
class File(models.Model):
    file_hash = models.CharField(max_length=64)  # SHA-256 hash
    is_reference = models.BooleanField(default=False)
    original_file = models.ForeignKey('self', ...)  # Points to original if reference
```

**Benefits:**
- Saves storage space automatically
- Transparent to the end user
- Tracks storage savings via statistics endpoint

---

### ✅ 2. Search & Filtering System

**Implemented Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `search` | string | Case-insensitive filename search | `?search=report` |
| `file_type` | string | Filter by MIME type | `?file_type=application/pdf` |
| `min_size` | integer | Minimum file size in bytes | `?min_size=1024` |
| `max_size` | integer | Maximum file size in bytes | `?max_size=5242880` |
| `start_date` | ISO 8601 | Filter files uploaded after date | `?start_date=2024-01-01T00:00:00Z` |
| `end_date` | ISO 8601 | Filter files uploaded before date | `?end_date=2024-12-31T23:59:59Z` |

**Features:**
- Multiple filters can be combined simultaneously
- Efficient database queries with proper indexing
- Optimized for large datasets

**Example Query:**
```bash
GET /api/files/?search=report&file_type=application/pdf&min_size=1000&start_date=2024-01-01T00:00:00Z
```

**Performance Optimization:**
- Database indexes on frequently filtered fields:
  - `user_id` + `uploaded_at`
  - `user_id` + `file_type`
  - `user_id` + `size`
  - `file_hash`

---

### ✅ 3. Rate Limiting System

**Configuration:**
```python
RATE_LIMIT_CALLS = 2  # Calls allowed
RATE_LIMIT_WINDOW = 1  # Time window in seconds
```

**Implementation:**
- **Middleware-based**: Applied to all `/api/` endpoints
- **Per-user tracking**: Uses `UserId` header for identification
- **Cache-based**: Uses Django's cache framework (easily switchable to Redis)
- **Sliding window**: Tracks request timestamps and removes old ones

**How It Works:**
1. Each request is logged with timestamp
2. Old requests outside the time window are removed
3. If request count exceeds limit, returns HTTP 429
4. Automatically resets after time window passes

**Response on Limit Exceeded:**
```json
{
  "error": "Call Limit Reached"
}
```
HTTP Status: 429 (Too Many Requests)

---

### ✅ 4. Storage Quota System

**Configuration:**
```python
USER_STORAGE_LIMIT_MB = 10  # Limit per user in MB
```

**Implementation:**
- **Per-user tracking**: Each user has a separate storage quota
- **Real-time checking**: Validates before accepting uploads
- **Deduplication-aware**: Only counts actual storage used, not references

**Storage Tracking Model:**
```python
class UserStorageStats(models.Model):
    user_id = models.CharField(max_length=255)
    total_storage_used = models.BigIntegerField()  # Actual storage
    original_storage_used = models.BigIntegerField()  # Without dedup
```

**How It Works:**
1. Before upload, checks if adding file would exceed quota
2. If within limit: Upload proceeds and stats are updated
3. If exceeds: Returns HTTP 429 with "Storage Quota Exceeded"
4. On file deletion: Storage stats are decremented

**Response on Quota Exceeded:**
```json
{
  "error": "Storage Quota Exceeded"
}
```
HTTP Status: 429 (Too Many Requests)

---

## API Endpoints

### Core Endpoints

#### 1. Upload File
```
POST /api/files/
Header: UserId: <user_id>
Body: multipart/form-data with 'file' field
```

#### 2. List Files (with filtering)
```
GET /api/files/?<filters>
Header: UserId: <user_id>
```

#### 3. Get File Details
```
GET /api/files/{id}/
Header: UserId: <user_id>
```

#### 4. Delete File
```
DELETE /api/files/{id}/
Header: UserId: <user_id>
```

#### 5. Storage Statistics ⭐ NEW
```
GET /api/files/storage_stats/
Header: UserId: <user_id>
```

Returns:
```json
{
  "user_id": "user123",
  "total_storage_used": 5242880,
  "original_storage_used": 10485760,
  "storage_savings": 5242880,
  "savings_percentage": 50.0
}
```

#### 6. Available File Types ⭐ NEW
```
GET /api/files/file_types/
Header: UserId: <user_id>
```

Returns:
```json
[
  "application/json",
  "application/pdf",
  "image/jpeg",
  "text/plain"
]
```

---

## Database Schema

### File Model
```python
class File(models.Model):
    id = UUIDField (primary key)
    file = FileField
    original_filename = CharField
    file_type = CharField (MIME type)
    size = BigIntegerField (bytes)
    uploaded_at = DateTimeField
    user_id = CharField (from header)
    file_hash = CharField (SHA-256)
    is_reference = BooleanField
    original_file = ForeignKey (self-reference)
```

**Indexes:**
- `(user_id, uploaded_at)` - For date-based queries
- `(user_id, file_type)` - For file type filtering
- `(file_hash)` - For deduplication lookups
- `(user_id, size)` - For size-based filtering

### UserStorageStats Model
```python
class UserStorageStats(models.Model):
    user_id = CharField (unique)
    total_storage_used = BigIntegerField
    original_storage_used = BigIntegerField
```

---

## Architecture & Design Decisions

### 1. Middleware for Rate Limiting
**Why:** 
- Centralized enforcement across all endpoints
- Easy to configure and maintain
- No code duplication

### 2. SHA-256 for File Hashing
**Why:**
- Industry standard for file integrity
- Very low collision probability
- Fast computation even for large files

### 3. Reference-based Deduplication
**Why:**
- Maintains user file listings independently
- Allows different users to "own" the same file
- Proper reference counting prevents premature deletion

### 4. Database Indexes
**Why:**
- Efficient filtering even with millions of files
- Optimized for common query patterns
- Production-ready performance

### 5. Configurable Limits
**Why:**
- Easy to adjust without code changes
- Environment-specific configurations
- Business requirements can change

---

## Configuration Options

All limits are easily configurable in `backend/core/settings.py`:

```python
# Rate Limiting
RATE_LIMIT_CALLS = 2  # Calls per window
RATE_LIMIT_WINDOW = 1  # Seconds

# Storage Quota
USER_STORAGE_LIMIT_MB = 10  # MB per user

# Cache (for rate limiting)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        # In production, use Redis:
        # 'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        # 'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

---

## File Structure

```
backend/
├── core/
│   ├── settings.py          # Configuration (rate limits, storage quota)
│   └── urls.py              # URL routing
├── files/
│   ├── models.py            # File and UserStorageStats models
│   ├── views.py             # ViewSet with all endpoints
│   ├── serializers.py       # API serializers
│   ├── middleware.py        # Rate limiting middleware
│   ├── admin.py             # Admin interface configuration
│   └── urls.py              # App-level URL routing
├── media/
│   └── uploads/             # Physical file storage
└── data/
    └── db.sqlite3           # SQLite database
```

---

## Testing

### Automated Test Scripts

1. **Bash Script**: `test_api.sh`
   ```bash
   chmod +x test_api.sh
   ./test_api.sh
   ```

2. **Python Script**: `test_api.py`
   ```bash
   python test_api.py
   ```

### Manual Testing Guide
See `TESTING_GUIDE.md` for comprehensive manual testing instructions.

---

## Production Considerations

### Security
- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Set `DEBUG = False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Implement authentication/authorization (JWT, OAuth, etc.)
- [ ] Enable HTTPS
- [ ] Add CORS configuration for frontend

### Performance
- [ ] Use PostgreSQL/MySQL instead of SQLite
- [ ] Use Redis for cache backend
- [ ] Configure CDN for file delivery
- [ ] Add database query optimization
- [ ] Implement connection pooling

### Storage
- [ ] Use cloud storage (S3, GCS, Azure Blob)
- [ ] Implement backup strategy
- [ ] Configure file retention policies
- [ ] Add virus scanning for uploads

### Monitoring
- [ ] Set up logging (Sentry, CloudWatch, etc.)
- [ ] Add performance monitoring
- [ ] Configure alerts for quota limits
- [ ] Track API usage metrics

---

## Best Practices Followed

1. **SOLID Principles**
   - Single Responsibility: Each class has one clear purpose
   - Open/Closed: Configuration-based extensibility
   - Dependency Inversion: Django's built-in abstractions

2. **DRY (Don't Repeat Yourself)**
   - Reusable middleware for rate limiting
   - Shared serializers for consistent API responses

3. **Performance Optimization**
   - Database indexing for common queries
   - Efficient file hash calculation with streaming
   - Prefetch related objects to avoid N+1 queries

4. **Security**
   - User isolation (users can only access their files)
   - Input validation on all endpoints
   - SQL injection prevention (Django ORM)

5. **Maintainability**
   - Clear code organization
   - Comprehensive documentation
   - Configurable settings
   - Type hints where applicable

6. **Testing**
   - Automated test scripts provided
   - Manual testing guide included
   - Edge cases documented

---

## Key Achievements

✅ **File Deduplication**: Automatic storage optimization with SHA-256 hashing
✅ **Search & Filter**: Multi-parameter filtering with efficient database queries
✅ **Rate Limiting**: Configurable per-user call limits (2 calls/second)
✅ **Storage Quota**: Enforced 10MB limit per user
✅ **Storage Statistics**: Real-time tracking of storage savings
✅ **File Types**: Dynamic list of uploaded file types
✅ **Performance**: Database indexes for production-scale queries
✅ **User Isolation**: Complete separation between users
✅ **Error Handling**: Proper HTTP status codes and error messages
✅ **Documentation**: Comprehensive testing and deployment guides

---

## API Contract Compliance

All endpoints match the specified API contract:

✅ `GET /api/files/` - List with filtering
✅ `POST /api/files/` - Upload with deduplication
✅ `GET /api/files/{id}/` - Get file details
✅ `DELETE /api/files/{id}/` - Delete file
✅ `GET /api/files/storage_stats/` - Storage statistics
✅ `GET /api/files/file_types/` - Available file types

All response formats match the specification exactly.

---

## How to Run

### Quick Start
```bash
cd backend
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

### Run Tests
```bash
# Bash tests
./test_api.sh

# Python tests
python test_api.py
```

### Create Submission Zip
```bash
python create_submission_zip.py
```

---

## Conclusion

This implementation provides a production-ready file vault with all requested features:
- **Efficient storage** through deduplication
- **Fast retrieval** through optimized search and filtering
- **Protected resources** through rate limiting and storage quotas
- **Scalable architecture** ready for production deployment

All features are fully functional, well-documented, and tested.
