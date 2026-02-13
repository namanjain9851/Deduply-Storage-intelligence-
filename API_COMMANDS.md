# 🔧 API Commands Reference

Quick reference for all API endpoints with curl commands.

---

## Base Configuration

```bash
BASE_URL="http://localhost:8000/api/files"
USER_ID="user123"
```

---

## 📤 Upload File

### Basic Upload
```bash
curl -X POST $BASE_URL/ \
  -H "UserId: $USER_ID" \
  -F "file=@document.pdf"
```

### Upload with Response
```bash
curl -X POST http://localhost:8000/api/files/ \
  -H "UserId: user123" \
  -F "file=@test.txt" | python3 -m json.tool
```

---

## 📋 List Files

### List All Files
```bash
curl -X GET $BASE_URL/ \
  -H "UserId: $USER_ID"
```

### Pretty Print
```bash
curl -X GET http://localhost:8000/api/files/ \
  -H "UserId: user123" | python3 -m json.tool
```

---

## 🔍 Search & Filter

### Search by Filename
```bash
curl -X GET "$BASE_URL/?search=report" \
  -H "UserId: $USER_ID"
```

### Filter by File Type
```bash
curl -X GET "$BASE_URL/?file_type=application/pdf" \
  -H "UserId: $USER_ID"
```

### Filter by Size Range
```bash
# Files between 1KB and 5MB
curl -X GET "$BASE_URL/?min_size=1024&max_size=5242880" \
  -H "UserId: $USER_ID"
```

### Filter by Date Range
```bash
curl -X GET "$BASE_URL/?start_date=2024-01-01T00:00:00Z&end_date=2024-12-31T23:59:59Z" \
  -H "UserId: $USER_ID"
```

### Combine Multiple Filters
```bash
curl -X GET "$BASE_URL/?search=report&file_type=application/pdf&min_size=1024&start_date=2024-01-01T00:00:00Z" \
  -H "UserId: $USER_ID"
```

---

## 📊 Storage Statistics

### Get Storage Stats
```bash
curl -X GET $BASE_URL/storage_stats/ \
  -H "UserId: $USER_ID"
```

### Pretty Print
```bash
curl -X GET http://localhost:8000/api/files/storage_stats/ \
  -H "UserId: user123" | python3 -m json.tool
```

---

## 📁 File Types

### Get Available File Types
```bash
curl -X GET $BASE_URL/file_types/ \
  -H "UserId: $USER_ID"
```

### Pretty Print
```bash
curl -X GET http://localhost:8000/api/files/file_types/ \
  -H "UserId: user123" | python3 -m json.tool
```

---

## 🔎 Get File Details

### Get Specific File
```bash
FILE_ID="550e8400-e29b-41d4-a716-446655440000"
curl -X GET $BASE_URL/$FILE_ID/ \
  -H "UserId: $USER_ID"
```

### Pretty Print
```bash
curl -X GET http://localhost:8000/api/files/<file-id>/ \
  -H "UserId: user123" | python3 -m json.tool
```

---

## 🗑️ Delete File

### Delete Specific File
```bash
FILE_ID="550e8400-e29b-41d4-a716-446655440000"
curl -X DELETE $BASE_URL/$FILE_ID/ \
  -H "UserId: $USER_ID"
```

### With Status Code
```bash
curl -X DELETE http://localhost:8000/api/files/<file-id>/ \
  -H "UserId: user123" \
  -w "\nHTTP Status: %{http_code}\n"
```

---

## 🧪 Test Deduplication

### Upload Same File Twice
```bash
# First upload (creates original)
curl -X POST $BASE_URL/ \
  -H "UserId: $USER_ID" \
  -F "file=@test.txt"

# Second upload (creates reference)
curl -X POST $BASE_URL/ \
  -H "UserId: $USER_ID" \
  -F "file=@test.txt"
```

Check the response - `is_reference` should be `true` for the second upload.

---

## ⏱️ Test Rate Limiting

### Rapid Requests (3rd should fail)
```bash
curl -X GET $BASE_URL/ -H "UserId: $USER_ID" &
curl -X GET $BASE_URL/ -H "UserId: $USER_ID" &
curl -X GET $BASE_URL/ -H "UserId: $USER_ID"
```

Expected: 3rd request returns HTTP 429 with `"error": "Call Limit Reached"`

### Wait and Retry
```bash
curl -X GET $BASE_URL/ -H "UserId: $USER_ID"
sleep 2
curl -X GET $BASE_URL/ -H "UserId: $USER_ID"  # Should work
```

---

## 💾 Test Storage Quota

### Create Large File
```bash
# Create 2MB file
dd if=/dev/zero of=large.bin bs=1M count=2

# Upload multiple times to exceed 10MB quota
for i in {1..6}; do
  curl -X POST $BASE_URL/ \
    -H "UserId: test_quota_$i" \
    -F "file=@large.bin"
  echo ""
done
```

Expected: Should fail after ~5 uploads with HTTP 429 `"error": "Storage Quota Exceeded"`

---

## ❌ Error Cases

### Missing UserId Header
```bash
curl -X GET $BASE_URL/
```
Expected: HTTP 400 `"error": "UserId header is required"`

### Missing File in Upload
```bash
curl -X POST $BASE_URL/ \
  -H "UserId: $USER_ID"
```
Expected: HTTP 400 `"error": "No file provided"`

### Invalid File ID
```bash
curl -X GET $BASE_URL/invalid-id/ \
  -H "UserId: $USER_ID"
```
Expected: HTTP 404

---

## 🔄 Complete Workflow Example

### 1. Create Test File
```bash
echo "This is a test file" > test.txt
```

### 2. Upload File
```bash
RESPONSE=$(curl -s -X POST $BASE_URL/ \
  -H "UserId: $USER_ID" \
  -F "file=@test.txt")
echo $RESPONSE | python3 -m json.tool

# Extract file ID
FILE_ID=$(echo $RESPONSE | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
echo "File ID: $FILE_ID"
```

### 3. List Files
```bash
curl -X GET $BASE_URL/ \
  -H "UserId: $USER_ID" | python3 -m json.tool
```

### 4. Search for File
```bash
curl -X GET "$BASE_URL/?search=test" \
  -H "UserId: $USER_ID" | python3 -m json.tool
```

### 5. Get File Details
```bash
curl -X GET $BASE_URL/$FILE_ID/ \
  -H "UserId: $USER_ID" | python3 -m json.tool
```

### 6. Check Storage Stats
```bash
curl -X GET $BASE_URL/storage_stats/ \
  -H "UserId: $USER_ID" | python3 -m json.tool
```

### 7. Upload Duplicate
```bash
curl -X POST $BASE_URL/ \
  -H "UserId: $USER_ID" \
  -F "file=@test.txt" | python3 -m json.tool
```

### 8. Check Storage Stats Again
```bash
curl -X GET $BASE_URL/storage_stats/ \
  -H "UserId: $USER_ID" | python3 -m json.tool
```
Note: `storage_savings` should show savings from deduplication

### 9. Delete File
```bash
curl -X DELETE $BASE_URL/$FILE_ID/ \
  -H "UserId: $USER_ID" \
  -w "\nHTTP Status: %{http_code}\n"
```

### 10. Verify Deletion
```bash
curl -X GET $BASE_URL/ \
  -H "UserId: $USER_ID" | python3 -m json.tool
```

---

## 📝 Useful curl Options

### Show HTTP Status Code
```bash
curl -w "\nHTTP Status: %{http_code}\n" [other options]
```

### Show Response Headers
```bash
curl -i [other options]
```

### Verbose Output
```bash
curl -v [other options]
```

### Save Response to File
```bash
curl -o response.json [other options]
```

### Silent Mode (no progress bar)
```bash
curl -s [other options]
```

### Follow Redirects
```bash
curl -L [other options]
```

---

## 🧪 Quick Test Script

Save as `quick_test.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/files"
USER_ID="quicktest_$(date +%s)"

echo "Testing with UserId: $USER_ID"

# Create test file
echo "Test content" > /tmp/test.txt

echo "1. Uploading file..."
RESPONSE=$(curl -s -X POST $BASE_URL/ -H "UserId: $USER_ID" -F "file=@/tmp/test.txt")
echo $RESPONSE | python3 -m json.tool

echo -e "\n2. Listing files..."
curl -s -X GET $BASE_URL/ -H "UserId: $USER_ID" | python3 -m json.tool

echo -e "\n3. Checking storage stats..."
curl -s -X GET $BASE_URL/storage_stats/ -H "UserId: $USER_ID" | python3 -m json.tool

echo -e "\n4. Getting file types..."
curl -s -X GET $BASE_URL/file_types/ -H "UserId: $USER_ID" | python3 -m json.tool

echo -e "\n5. Uploading duplicate..."
curl -s -X POST $BASE_URL/ -H "UserId: $USER_ID" -F "file=@/tmp/test.txt" | python3 -m json.tool

echo -e "\n6. Checking storage stats again..."
curl -s -X GET $BASE_URL/storage_stats/ -H "UserId: $USER_ID" | python3 -m json.tool

# Cleanup
rm /tmp/test.txt

echo -e "\nTest complete!"
```

Run with:
```bash
chmod +x quick_test.sh
./quick_test.sh
```

---

## 🎯 Common Query Parameter Combinations

### Find Large PDFs
```bash
curl -X GET "$BASE_URL/?file_type=application/pdf&min_size=1048576" \
  -H "UserId: $USER_ID"
```

### Recent Text Files
```bash
curl -X GET "$BASE_URL/?file_type=text/plain&start_date=2024-01-01T00:00:00Z" \
  -H "UserId: $USER_ID"
```

### Small Images
```bash
curl -X GET "$BASE_URL/?file_type=image/jpeg&max_size=102400" \
  -H "UserId: $USER_ID"
```

### Search in Date Range
```bash
curl -X GET "$BASE_URL/?search=report&start_date=2024-01-01T00:00:00Z&end_date=2024-03-31T23:59:59Z" \
  -H "UserId: $USER_ID"
```

---

## 📱 Using with HTTPie (Alternative to curl)

If you prefer HTTPie:

### Upload
```bash
http -f POST $BASE_URL/ UserId:$USER_ID file@document.pdf
```

### List
```bash
http GET $BASE_URL/ UserId:$USER_ID
```

### Search
```bash
http GET "$BASE_URL/?search=test" UserId:$USER_ID
```

### Delete
```bash
http DELETE $BASE_URL/$FILE_ID/ UserId:$USER_ID
```

---

## 🐛 Debugging Tips

### Check Server is Running
```bash
curl -I http://localhost:8000/api/files/ -H "UserId: test"
```

### Test Network Connectivity
```bash
curl -v http://localhost:8000/
```

### Validate JSON Response
```bash
curl -s http://localhost:8000/api/files/ -H "UserId: test" | python3 -c "import sys,json; json.load(sys.stdin)"
```

### Check Response Time
```bash
curl -w "\nTime: %{time_total}s\n" -o /dev/null -s http://localhost:8000/api/files/ -H "UserId: test"
```

---

**Happy Testing! 🚀**

For automated testing, use:
- `./test_api.sh` (Bash)
- `python test_api.py` (Python)

For comprehensive testing guide, see: [TESTING_GUIDE.md](TESTING_GUIDE.md)
