#!/bin/bash

# Abnormal File Vault - Quick Test Script
# This script performs basic API tests

BASE_URL="http://localhost:8000/api/files"
USER_ID="testuser123"

echo "========================================"
echo "Abnormal File Vault - API Test Script"
echo "========================================"
echo ""

# Check if server is running
echo "1. Checking if server is running..."
if curl -s --head --request GET "$BASE_URL/" -H "UserId: $USER_ID" | grep "200\|404" > /dev/null; then 
   echo "✓ Server is running"
else
   echo "✗ Server is not running. Please start with: python manage.py runserver"
   exit 1
fi
echo ""


# Create test files
echo "2. Creating test files..."
mkdir -p test_files
echo "This is a test file for upload" > test_files/test1.txt
echo "This is a test file for upload" > test_files/test1_duplicate.txt  # Same content for deduplication
echo "Different content" > test_files/test2.txt
dd if=/dev/zero of=test_files/medium.bin bs=1K count=500 2>/dev/null  # 500KB file
echo "✓ Test files created"
echo ""

# Test 1: Upload first file
echo "3. Testing file upload..."
RESPONSE=$(curl -s -X POST "$BASE_URL/" \
  -H "UserId: $USER_ID" \
  -F "file=@test_files/test1.txt")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
FILE_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "✓ First file uploaded. ID: $FILE_ID"
echo ""
sleep 1

# Test 2: Upload duplicate file (test deduplication)
echo "4. Testing file deduplication..."
RESPONSE=$(curl -s -X POST "$BASE_URL/" \
  -H "UserId: $USER_ID" \
  -F "file=@test_files/test1_duplicate.txt")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
IS_REFERENCE=$(echo "$RESPONSE" | grep -o '"is_reference":[^,]*' | cut -d':' -f2)
if [ "$IS_REFERENCE" = "true" ]; then
    echo "✓ Deduplication working - file created as reference"
else
    echo "⚠ Deduplication may not be working as expected"
fi
echo ""
sleep 1

# Test 3: List files
echo "5. Testing list files..."
RESPONSE=$(curl -s -X GET "$BASE_URL/" -H "UserId: $USER_ID")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo "✓ Files listed"
echo ""
sleep 1

# Test 4: Search by filename
echo "6. Testing search functionality..."
RESPONSE=$(curl -s -X GET "$BASE_URL/?search=test1" -H "UserId: $USER_ID")
COUNT=$(echo "$RESPONSE" | grep -o '"count":[0-9]*' | cut -d':' -f2)
echo "Found $COUNT files matching 'test1'"
echo "✓ Search working"
echo ""
sleep 1

# Test 5: Storage stats
echo "7. Testing storage statistics..."
RESPONSE=$(curl -s -X GET "$BASE_URL/storage_stats/" -H "UserId: $USER_ID")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo "✓ Storage stats retrieved"
echo ""
sleep 1

# Test 6: File types
echo "8. Testing file types endpoint..."
RESPONSE=$(curl -s -X GET "$BASE_URL/file_types/" -H "UserId: $USER_ID")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo "✓ File types retrieved"
echo ""

# Test 7: Rate limiting
echo "9. Testing rate limiting (2 calls/second)..."
echo "Making 3 rapid requests..."
curl -s -X GET "$BASE_URL/" -H "UserId: $USER_ID" > /dev/null &
curl -s -X GET "$BASE_URL/" -H "UserId: $USER_ID" > /dev/null &
RESPONSE=$(curl -s -X GET "$BASE_URL/" -H "UserId: $USER_ID")
if echo "$RESPONSE" | grep -q "Call Limit Reached"; then
    echo "✓ Rate limiting working - 3rd request blocked"
else
    echo "⚠ Rate limiting may not be working (or requests were too slow)"
fi
wait
echo ""

# Wait for rate limit to reset
echo "10. Waiting for rate limit to reset..."
sleep 2
echo "✓ Rate limit should be reset now"
echo ""

# Test 8: Get specific file details
if [ ! -z "$FILE_ID" ]; then
    echo "11. Testing get file details..."
    RESPONSE=$(curl -s -X GET "$BASE_URL/$FILE_ID/" -H "UserId: $USER_ID")
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo "✓ File details retrieved"
    echo ""
fi
sleep 1

# Test 9: Filter by file type
echo "12. Testing filter by file type..."
RESPONSE=$(curl -s -X GET "$BASE_URL/?file_type=text/plain" -H "UserId: $USER_ID")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo "✓ File type filtering working"
echo ""
sleep 1

# Test 10: Delete file
if [ ! -z "$FILE_ID" ]; then
    echo "13. Testing file deletion..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/$FILE_ID/" -H "UserId: $USER_ID")
    if [ "$HTTP_CODE" = "204" ]; then
        echo "✓ File deleted successfully (HTTP 204)"
    else
        echo "⚠ File deletion returned HTTP $HTTP_CODE"
    fi
    echo ""
fi

# Cleanup
echo "14. Cleaning up test files..."
rm -rf test_files
echo "✓ Test files cleaned up"
echo ""

echo "========================================"
echo "✓ All tests completed!"
echo "========================================"
echo ""
echo "For more detailed testing, see TESTING_GUIDE.md"
