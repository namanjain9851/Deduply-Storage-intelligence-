#!/usr/bin/env python3
"""
Abnormal File Vault - API Test Script (Python)
This script performs comprehensive API tests
"""

import requests
import json
import time
import tempfile
import os
from pathlib import Path

BASE_URL = "http://localhost:8000/api/files"
USER_ID = "testuser_python"

def print_section(title):
    print("\n" + "="*50)
    print(f"  {title}")
    print("="*50)

def print_response(response):
    """Pretty print JSON response"""
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print(f"Status Code: {response.status_code}")

def test_server_running():
    """Test if server is running"""
    print_section("1. Checking Server")
    try:
        response = requests.get(f"{BASE_URL}/", headers={"UserId": USER_ID}, timeout=5)
        print("✓ Server is running")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running. Please start with: python manage.py runserver")
        return False

def test_file_upload():
    """Test file upload"""
    print_section("2. Testing File Upload")
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file for upload")
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            files = {'file': ('test_upload.txt', f, 'text/plain')}
            response = requests.post(
                f"{BASE_URL}/",
                headers={"UserId": USER_ID},
                files=files
            )
        
        print_response(response)
        
        if response.status_code == 201:
            print("✓ File uploaded successfully")
            return response.json()
        else:
            print("✗ File upload failed")
            return None
    finally:
        os.unlink(temp_file)

def test_deduplication(file_content="This is a test file for deduplication"):
    """Test file deduplication"""
    print_section("3. Testing File Deduplication")
    
    # Upload same file twice
    uploaded_files = []
    
    for i in range(2):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(file_content)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {'file': (f'test_dedup_{i}.txt', f, 'text/plain')}
                response = requests.post(
                    f"{BASE_URL}/",
                    headers={"UserId": USER_ID},
                    files=files
                )
            
            if response.status_code == 201:
                data = response.json()
                uploaded_files.append(data)
                print(f"\nUpload {i+1}:")
                print(f"  - ID: {data['id']}")
                print(f"  - Is Reference: {data['is_reference']}")
                print(f"  - File Hash: {data['file_hash']}")
        finally:
            os.unlink(temp_file)
    
    if len(uploaded_files) == 2:
        if not uploaded_files[0]['is_reference'] and uploaded_files[1]['is_reference']:
            print("\n✓ Deduplication working correctly")
            print(f"  - First upload is original")
            print(f"  - Second upload is reference")
            return True
        else:
            print("\n⚠ Deduplication may not be working as expected")
            return False
    
    return False

def test_list_files():
    """Test listing files"""
    print_section("4. Testing List Files")
    
    response = requests.get(
        f"{BASE_URL}/",
        headers={"UserId": USER_ID}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', 0)
        print(f"\n✓ Listed {count} files")
        return data
    else:
        print("\n✗ Failed to list files")
        return None

def test_search():
    """Test search functionality"""
    print_section("5. Testing Search Functionality")
    
    response = requests.get(
        f"{BASE_URL}/?search=test",
        headers={"UserId": USER_ID}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', 0)
        print(f"\n✓ Search found {count} files")
        return True
    else:
        print("\n✗ Search failed")
        return False

def test_filter_by_type():
    """Test filtering by file type"""
    print_section("6. Testing Filter by File Type")
    
    response = requests.get(
        f"{BASE_URL}/?file_type=text/plain",
        headers={"UserId": USER_ID}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        count = data.get('count', 0)
        print(f"\n✓ Filter found {count} text/plain files")
        return True
    else:
        print("\n✗ Filtering failed")
        return False

def test_storage_stats():
    """Test storage statistics endpoint"""
    print_section("7. Testing Storage Statistics")
    
    response = requests.get(
        f"{BASE_URL}/storage_stats/",
        headers={"UserId": USER_ID}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Storage Stats:")
        print(f"  - Total Storage Used: {data['total_storage_used']} bytes")
        print(f"  - Original Storage Used: {data['original_storage_used']} bytes")
        print(f"  - Storage Savings: {data['storage_savings']} bytes")
        print(f"  - Savings Percentage: {data['savings_percentage']:.2f}%")
        return True
    else:
        print("\n✗ Failed to get storage stats")
        return False

def test_file_types():
    """Test file types endpoint"""
    print_section("8. Testing File Types Endpoint")
    
    response = requests.get(
        f"{BASE_URL}/file_types/",
        headers={"UserId": USER_ID}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        file_types = response.json()
        print(f"\n✓ Found {len(file_types)} unique file types")
        return True
    else:
        print("\n✗ Failed to get file types")
        return False

def test_rate_limiting():
    """Test rate limiting (2 calls/second)"""
    print_section("9. Testing Rate Limiting")
    
    print("Making 3 rapid requests...")
    responses = []
    
    for i in range(3):
        response = requests.get(
            f"{BASE_URL}/",
            headers={"UserId": f"{USER_ID}_rate_test"}
        )
        responses.append(response)
        print(f"  Request {i+1}: Status {response.status_code}")
    
    # Check if any request was rate limited
    rate_limited = any(r.status_code == 429 for r in responses)
    
    if rate_limited:
        print("\n✓ Rate limiting is working")
        print("  At least one request was blocked (HTTP 429)")
        return True
    else:
        print("\n⚠ Rate limiting may not be working")
        print("  (or requests were too slow)")
        return False

def test_storage_quota():
    """Test storage quota (10MB limit)"""
    print_section("10. Testing Storage Quota")
    
    # Create a large file (2MB)
    large_content = "x" * (2 * 1024 * 1024)
    
    print("Uploading files to test quota...")
    user_id_quota = f"{USER_ID}_quota_test"
    upload_count = 0
    
    for i in range(6):  # Try to upload 12MB total
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_content)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {'file': (f'large_file_{i}.txt', f, 'text/plain')}
                response = requests.post(
                    f"{BASE_URL}/",
                    headers={"UserId": user_id_quota},
                    files=files
                )
            
            print(f"  Upload {i+1}: Status {response.status_code}")
            
            if response.status_code == 429:
                print("\n✓ Storage quota is enforced")
                print(f"  Upload blocked after {upload_count} files")
                return True
            elif response.status_code == 201:
                upload_count += 1
        finally:
            os.unlink(temp_file)
    
    print("\n⚠ Storage quota may not be enforced")
    print(f"  Uploaded {upload_count} files without hitting limit")
    return False

def test_get_file_details(file_id):
    """Test getting file details"""
    print_section("11. Testing Get File Details")
    
    response = requests.get(
        f"{BASE_URL}/{file_id}/",
        headers={"UserId": USER_ID}
    )
    
    print_response(response)
    
    if response.status_code == 200:
        print("\n✓ File details retrieved")
        return True
    else:
        print("\n✗ Failed to get file details")
        return False

def test_delete_file(file_id):
    """Test file deletion"""
    print_section("12. Testing File Deletion")
    
    response = requests.delete(
        f"{BASE_URL}/{file_id}/",
        headers={"UserId": USER_ID}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 204:
        print("✓ File deleted successfully")
        return True
    else:
        print("✗ File deletion failed")
        return False

def test_missing_userid():
    """Test error handling for missing UserId header"""
    print_section("13. Testing Missing UserId Header")
    
    response = requests.get(f"{BASE_URL}/")
    
    print_response(response)
    
    if response.status_code == 400:
        print("\n✓ Missing UserId header properly rejected")
        return True
    else:
        print("\n⚠ Missing UserId header not properly handled")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*50)
    print("  Abnormal File Vault - API Test Suite")
    print("="*50)
    
    # Test server
    if not test_server_running():
        return
    
    # Basic tests
    uploaded_file = test_file_upload()
    test_deduplication()
    files_data = test_list_files()
    test_search()
    test_filter_by_type()
    test_storage_stats()
    test_file_types()
    test_rate_limiting()
    test_storage_quota()
    test_missing_userid()
    
    # Test with specific file if we have one
    if uploaded_file and 'id' in uploaded_file:
        file_id = uploaded_file['id']
        test_get_file_details(file_id)
        
        # Wait for rate limit to reset
        print("\n⏳ Waiting 2 seconds for rate limit to reset...")
        time.sleep(2)
        
        test_delete_file(file_id)
    
    # Summary
    print_section("Test Summary")
    print("✓ All tests completed!")
    print("\nFor more detailed testing instructions, see TESTING_GUIDE.md")
    print("\nNote: Some tests may show warnings if timing is sensitive")
    print("      or if data from previous runs exists.")

if __name__ == "__main__":
    main()
