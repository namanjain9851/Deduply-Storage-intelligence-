# Abnormal File Vault - Testing Guide

## Setup Instructions

### Prerequisites
- Python 3.9+
- pip
- Docker (optional, for containerized setup)

### Installation Steps

#### 1. Navigate to the backend directory
```bash
cd backend
```

#### 2. Activate virtual environment (if exists) or create new one
```bash
# If venv already exists
source venv/bin/activate  # On Windows: venv\Scripts\activate

# If you need to create a new venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Create necessary directories
```bash
mkdir -p media/uploads data staticfiles
```

#### 5. Run migrations to set up the database
```bash
python manage.py makemigrations
python manage.py migrate
```

#### 6. (Optional) Create superuser for admin access
```bash
python manage.py createsuperuser
```

#### 7. Start the development server
```bash
python manage.py runserver
```

The server will be available at: http://localhost:8000

---

## Testing the API

### Important: All API requests require the `UserId` header
```bash
-H "UserId: user123"
```

### Base URL
```
http://localhost:8000/api/files/
```

---

## Test Cases

### 1. Upload a File (POST /api/files/)

**Test Case 1.1: Upload a new file**
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@/path/to/test.txt"
```

Expected Response (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "file": "/media/uploads/a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3.txt",
  "original_filename": "test.txt",
  "file_type": "text/plain",
  "size": 1024,
  "uploaded_at": "2024-01-15T10:30:00.123456Z",
  "user_id": "user123",
  "file_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
  "reference_count": 0,
  "is_reference": false,
  "original_file": null
}
```

**Test Case 1.2: Upload duplicate file (tests deduplication)**
```bash
# Upload the same file again
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@/path/to/test.txt"
```

Expected: File should be created as a reference (is_reference: true) pointing to the original file.

**Test Case 1.3: Test storage quota exceeded**
```bash
# Upload files totaling more than 10MB
# Should get 429 error after exceeding quota
```

Expected Response (429):
```json
{
  "error": "Storage Quota Exceeded"
}
```

---

### 2. List Files (GET /api/files/)

**Test Case 2.1: List all files for a user**
```bash
curl -X GET http://localhost:8000/api/files/ \
  -H "UserId: user123"
```

**Test Case 2.2: Search by filename**
```bash
curl -X GET "http://localhost:8000/api/files/?search=test" \
  -H "UserId: user123"
```

**Test Case 2.3: Filter by file type**
```bash
curl -X GET "http://localhost:8000/api/files/?file_type=text/plain" \
  -H "UserId: user123"
```

**Test Case 2.4: Filter by file size range**
```bash
curl -X GET "http://localhost:8000/api/files/?min_size=1000&max_size=5000" \
  -H "UserId: user123"
```

**Test Case 2.5: Filter by date range**
```bash
curl -X GET "http://localhost:8000/api/files/?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z" \
  -H "UserId: user123"
```

**Test Case 2.6: Combine multiple filters**
```bash
curl -X GET "http://localhost:8000/api/files/?search=test&file_type=text/plain&min_size=100" \
  -H "UserId: user123"
```

---

### 3. Get File Details (GET /api/files/{id}/)

```bash
curl -X GET http://localhost:8000/api/files/{file-id}/ \
  -H "UserId: user123"
```

---

### 4. Delete File (DELETE /api/files/{id}/)

**Test Case 4.1: Delete a file**
```bash
curl -X DELETE http://localhost:8000/api/files/{file-id}/ \
  -H "UserId: user123"
```

Expected Response: 204 No Content

**Test Case 4.2: Delete original file with references**
- When you delete the original file that has references, the system should:
  - Promote the first reference to be the original
  - Update other references to point to the new original
  - Not delete the physical file

---

### 5. Get Storage Statistics (GET /api/files/storage_stats/)

```bash
curl -X GET http://localhost:8000/api/files/storage_stats/ \
  -H "UserId: user123"
```

Expected Response (200):
```json
{
  "user_id": "user123",
  "total_storage_used": 5120,
  "original_storage_used": 10240,
  "storage_savings": 5120,
  "savings_percentage": 50.0
}
```

This shows:
- `total_storage_used`: Actual storage used after deduplication (bytes)
- `original_storage_used`: Storage that would be used without deduplication (bytes)
- `storage_savings`: Bytes saved through deduplication
- `savings_percentage`: Percentage of storage saved

---

### 6. Get Available File Types (GET /api/files/file_types/)

```bash
curl -X GET http://localhost:8000/api/files/file_types/ \
  -H "UserId: user123"
```

Expected Response (200):
```json
[
  "application/json",
  "application/pdf",
  "image/jpeg",
  "image/png",
  "text/plain"
]
```

---

### 7. Test Rate Limiting

**Test Case 7.1: Rate limit (2 calls per second)**

```bash
# Make 3 rapid requests - the 3rd should fail
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123" &
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123" &
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123"
```

Expected: The 3rd request should return 429 error:
```json
{
  "error": "Call Limit Reached"
}
```

**Test Case 7.2: Rate limit resets after time window**
```bash
# Make 2 requests, wait 1+ second, make another - should succeed
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123"
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123"
sleep 2
curl -X GET http://localhost:8000/api/files/ -H "UserId: user123"
```

---

### 8. Test Error Cases

**Test Case 8.1: Missing UserId header**
```bash
curl -X GET http://localhost:8000/api/files/
```

Expected Response (400):
```json
{
  "error": "UserId header is required"
}
```

**Test Case 8.2: Upload without file**
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123"
```

Expected Response (400):
```json
{
  "error": "No file provided"
}
```

---

## Testing with Different Users

Test isolation between users by using different UserId values:

```bash
# User 1
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user1" \
  -F "file=@test1.txt"

# User 2
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user2" \
  -F "file=@test2.txt"

# Verify User 1 can't see User 2's files
curl -X GET http://localhost:8000/api/files/ -H "UserId: user1"
```

---

## Testing File Deduplication

### Complete Deduplication Test Scenario

1. **Create a test file:**
```bash
echo "This is a test file for deduplication" > test_dedup.txt
```

2. **Upload the file first time (User 1):**
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: testuser1" \
  -F "file=@test_dedup.txt"
```
Note the `file_hash` value in the response.

3. **Upload the same file again (User 1):**
```bash
curl -X POST http://localhost:8000/api/files/ \
  -F "file=@test_dedup.txt" \
  -H "UserId: testuser1"
```

4. **Check the response:**
- `is_reference` should be `true`
- `original_file` should reference the first upload's ID
- The physical file should not be duplicated on disk

5. **Check storage stats:**
```bash
curl -X GET http://localhost:8000/api/files/storage_stats/ \
  -H "UserId: testuser1"
```

You should see:
- `original_storage_used` = 2 × file size (as if both were stored)
- `total_storage_used` = 1 × file size (actual storage used)
- `storage_savings` shows the savings from deduplication

---

## Performance Testing

### Test Search Performance with Indexes

1. Upload multiple files (50+)
2. Run search queries and note response times:

```bash
# Search by filename
time curl -X GET "http://localhost:8000/api/files/?search=test" -H "UserId: user123"

# Filter by file type
time curl -X GET "http://localhost:8000/api/files/?file_type=text/plain" -H "UserId: user123"

# Filter by size range
time curl -X GET "http://localhost:8000/api/files/?min_size=1000&max_size=5000" -H "UserId: user123"
```

Database indexes on `user_id`, `file_type`, `size`, and `uploaded_at` should make these queries fast.

---

## Admin Interface Testing

1. Navigate to http://localhost:8000/admin/
2. Login with superuser credentials
3. Check the following:
   - Files are listed with all relevant information
   - UserStorageStats shows storage metrics
   - Can filter and search files by various attributes

---

## Configuration Options

The following settings can be easily adjusted in `backend/core/settings.py`:

### Rate Limiting
```python
RATE_LIMIT_CALLS = 2  # Number of calls allowed
RATE_LIMIT_WINDOW = 1  # Time window in seconds
```

### Storage Quota
```python
USER_STORAGE_LIMIT_MB = 10  # Storage limit per user in MB
```

---

## Troubleshooting

### Issue: Migrations not applied
```bash
python manage.py migrate
```

### Issue: Database locked
```bash
# Stop the server, then:
rm data/db.sqlite3
python manage.py migrate
```

### Issue: File upload permissions
```bash
chmod -R 755 media/
```

### Issue: Port already in use
```bash
# Use a different port
python manage.py runserver 8001
```

---

## Sample Test Files

Create test files for testing:

```bash
# Create various test files
echo "Small text file" > small.txt
dd if=/dev/zero of=medium.bin bs=1M count=2  # 2MB file
dd if=/dev/zero of=large.bin bs=1M count=8   # 8MB file
dd if=/dev/zero of=toolarge.bin bs=1M count=12  # 12MB file (exceeds quota)
```

---

## Expected Behavior Summary

| Feature | Expected Behavior |
|---------|-------------------|
| File Upload | Files are stored with SHA-256 hash-based naming |
| Deduplication | Duplicate files create references, not physical copies |
| Search | Case-insensitive filename search works |
| Filtering | Multiple filters can be combined |
| Rate Limiting | Max 2 calls per second per user |
| Storage Quota | Max 10MB per user (configurable) |
| Storage Stats | Accurate tracking of actual vs. deduplicated storage |
| File Types | Returns unique MIME types for user's files |
| User Isolation | Users only see their own files |

---

## Testing Checklist

- [ ] File upload works
- [ ] Duplicate file creates reference (not new physical file)
- [ ] Search by filename works (case-insensitive)
- [ ] Filter by file type works
- [ ] Filter by size range works
- [ ] Filter by date range works
- [ ] Multiple filters work together
- [ ] Rate limiting enforced (3rd request in 1 second fails)
- [ ] Storage quota enforced (>10MB rejected)
- [ ] Storage stats are accurate
- [ ] File types endpoint returns correct list
- [ ] File deletion works
- [ ] Original file deletion with references handled correctly
- [ ] Missing UserId header returns 400
- [ ] User isolation works (users can't see each other's files)
- [ ] Admin interface shows all data correctly

---

## Production Deployment Notes

Before deploying to production:

1. Change `SECRET_KEY` in settings.py
2. Set `DEBUG = False`
3. Configure `ALLOWED_HOSTS` properly
4. Use PostgreSQL or MySQL instead of SQLite
5. Use Redis for cache backend (for rate limiting)
6. Configure proper file storage (S3, etc.)
7. Set up proper authentication/authorization
8. Configure HTTPS
9. Set up monitoring and logging

---

## Additional Notes

- The file hash is calculated using SHA-256 for reliable deduplication
- Database indexes ensure efficient querying even with large datasets
- The reference counting system ensures files aren't deleted while references exist
- Rate limiting uses local memory cache (use Redis in production)
- Storage stats are updated in real-time on upload/delete
