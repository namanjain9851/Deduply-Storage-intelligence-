# 🏗️ Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENT                               │
│              (curl, Postman, Browser)                        │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP Request
                     │ Header: UserId: user123
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    DJANGO SERVER                             │
│                  (Port 8000)                                 │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │          MIDDLEWARE LAYER                          │    │
│  │                                                     │    │
│  │  1. Security Middleware                            │    │
│  │  2. Session Middleware                             │    │
│  │  3. CSRF Middleware                                │    │
│  │  4. ⭐ Rate Limit Middleware (Custom)              │    │
│  │     - Checks call limit (2/second)                 │    │
│  │     - Returns 429 if exceeded                      │    │
│  │     - Attaches user_id to request                  │    │
│  └────────────────────────────────────────────────────┘    │
│                     │                                        │
│                     ▼                                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │            URL ROUTING                             │    │
│  │                                                     │    │
│  │  /api/files/                    → FileViewSet      │    │
│  │  /api/files/<id>/               → FileViewSet      │    │
│  │  /api/files/storage_stats/      → storage_stats    │    │
│  │  /api/files/file_types/         → file_types       │    │
│  └────────────────────────────────────────────────────┘    │
│                     │                                        │
│                     ▼                                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │            FILE VIEWSET                            │    │
│  │                                                     │    │
│  │  • create()      → Upload & Deduplicate            │    │
│  │  • list()        → Filter & Search                 │    │
│  │  • retrieve()    → Get details                     │    │
│  │  • destroy()     → Delete with ref counting        │    │
│  │  • storage_stats() → Get storage info              │    │
│  │  • file_types()    → Get file types                │    │
│  └────────────────────────────────────────────────────┘    │
│                     │                                        │
│                     ▼                                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │            DATABASE LAYER                          │    │
│  │              (SQLite)                              │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────┐         │    │
│  │  │  File Model                          │         │    │
│  │  │  - id (UUID)                         │         │    │
│  │  │  - file (FileField)                  │         │    │
│  │  │  - user_id (indexed)                 │         │    │
│  │  │  - file_hash (SHA-256, indexed)      │         │    │
│  │  │  - is_reference (Boolean)            │         │    │
│  │  │  - original_file (ForeignKey)        │         │    │
│  │  └──────────────────────────────────────┘         │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────┐         │    │
│  │  │  UserStorageStats Model              │         │    │
│  │  │  - user_id (unique, indexed)         │         │    │
│  │  │  - total_storage_used                │         │    │
│  │  │  - original_storage_used             │         │    │
│  │  └──────────────────────────────────────┘         │    │
│  └────────────────────────────────────────────────────┘    │
│                     │                                        │
│                     ▼                                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │          FILE STORAGE                              │    │
│  │        (media/uploads/)                            │    │
│  │                                                     │    │
│  │  Files stored as: <SHA256_HASH>.<ext>             │    │
│  │                                                     │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    CACHE LAYER                               │
│                  (Local Memory)                              │
│                                                              │
│  Used for Rate Limiting:                                    │
│  Key: rate_limit:<user_id>                                  │
│  Value: [timestamp1, timestamp2, ...]                       │
└─────────────────────────────────────────────────────────────┘
```

---

## File Upload Flow (with Deduplication)

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ POST /api/files/
     │ file: document.pdf
     │ UserId: user123
     ▼
┌─────────────────┐
│ Rate Limiter    │ ◄── Check: user123 call count
│ Middleware      │     ✓ Allow (within limit)
└────┬────────────┘
     ▼
┌─────────────────┐
│  FileViewSet    │
│   .create()     │
└────┬────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│  Calculate SHA-256 Hash                 │
│  Hash: a665a45920422f9d417e...          │
└────┬────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│  Check: Does file with this hash exist  │
│         for user123?                    │
└────┬────────────────────────────────────┘
     │
     ├─── YES (Duplicate Found) ───┐
     │                              │
     │                              ▼
     │                    ┌──────────────────────┐
     │                    │ Create Reference     │
     │                    │ - is_reference: true │
     │                    │ - original_file: id  │
     │                    │ - same file path     │
     │                    └──────────────────────┘
     │                              │
     │                              ▼
     │                    ┌──────────────────────┐
     │                    │ Update Stats:        │
     │                    │ original_used += size│
     │                    │ (total_used unchanged)│
     │                    └──────────────────────┘
     │                              │
     │                              └──────┐
     │                                     │
     └─── NO (New File) ──────┐           │
                              │           │
                              ▼           │
                    ┌──────────────────┐  │
                    │ Check Quota      │  │
                    │ user123:         │  │
                    │ used + size ≤ 10MB│ │
                    └────┬─────────────┘  │
                         │                │
         ┌───────────────┴─────────┐     │
         │                         │     │
    OVER QUOTA                 OK   │     │
         │                         │     │
         ▼                         ▼     │
    ┌─────────┐         ┌────────────────┐│
    │ Return  │         │ Save File      ││
    │ HTTP 429│         │ Create Record  ││
    └─────────┘         └────┬───────────┘│
                             │            │
                             ▼            │
                    ┌──────────────────┐  │
                    │ Update Stats:    │  │
                    │ total_used += size│ │
                    │ original_used += │  │
                    └────┬─────────────┘  │
                         │                │
                         └────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Return File Info │
                    │ HTTP 201         │
                    └──────────────────┘
```

---

## Search & Filter Flow

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ GET /api/files/?search=report&file_type=application/pdf&min_size=1024
     │ UserId: user123
     ▼
┌─────────────────┐
│ Rate Limiter    │
│ Middleware      │
└────┬────────────┘
     ▼
┌─────────────────┐
│  FileViewSet    │
│   .list()       │
└────┬────────────┘
     │
     ▼
┌──────────────────────────────────────┐
│  Build Query                         │
│                                      │
│  1. Base: File.objects.filter(       │
│           user_id='user123')         │
│                                      │
│  2. Add search:                      │
│     .filter(original_filename        │
│            __icontains='report')     │
│                                      │
│  3. Add file_type:                   │
│     .filter(file_type=               │
│            'application/pdf')        │
│                                      │
│  4. Add size filter:                 │
│     .filter(size__gte=1024)          │
│                                      │
│  5. Optimize with indexes:           │
│     - Uses index on (user_id,        │
│       file_type)                     │
│     - Uses index on (user_id, size)  │
│                                      │
│  6. Prefetch references:             │
│     .select_related('original_file') │
│     .prefetch_related('references')  │
└────┬─────────────────────────────────┘
     │
     ▼
┌──────────────────┐
│  Return Results  │
│  HTTP 200        │
│  Paginated List  │
└──────────────────┘
```

---

## Rate Limiting Flow

```
Request comes in
     │
     ▼
┌────────────────────────────────────┐
│ Rate Limit Middleware              │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│ Extract UserId from header         │
│ user_id = "user123"                │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│ Get request timestamps from cache  │
│ Key: "rate_limit:user123"          │
│ Value: [ts1, ts2, ...]             │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│ Filter old timestamps              │
│ Keep only: now - timestamp < 1s    │
│ Example: [1642012345.67, ...]      │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│ Check count                        │
│ len(timestamps) < 2?               │
└────┬───────────────────────────────┘
     │
     ├─── YES (OK) ────┐
     │                 │
     │                 ▼
     │      ┌──────────────────────┐
     │      │ Add current timestamp│
     │      │ Update cache         │
     │      └──────────┬───────────┘
     │                 │
     │                 ▼
     │      ┌──────────────────────┐
     │      │ Continue to view     │
     │      └──────────────────────┘
     │
     └─── NO (LIMIT EXCEEDED) ──┐
                                │
                                ▼
                    ┌──────────────────────┐
                    │ Return HTTP 429      │
                    │ "Call Limit Reached" │
                    └──────────────────────┘
```

---

## Storage Quota Check

```
File upload attempt
     │
     ▼
┌────────────────────────────────────┐
│ Get/Create UserStorageStats        │
│ for user_id                        │
└────┬───────────────────────────────┘
     │
     ▼
┌────────────────────────────────────┐
│ Check if deduplication applies     │
└────┬───────────────────────────────┘
     │
     ├─── File exists (Duplicate) ──┐
     │                               │
     │                               ▼
     │                     ┌──────────────────┐
     │                     │ No quota check   │
     │                     │ (no new storage) │
     │                     │ Update only:     │
     │                     │ original_used += │
     │                     └──────────────────┘
     │
     └─── New File ─────┐
                        │
                        ▼
            ┌───────────────────────┐
            │ Calculate:            │
            │ total_used + new_size │
            │ ≤ 10MB?               │
            └────┬──────────────────┘
                 │
     ┌───────────┴──────────┐
     │                      │
   NO (Over)             YES (OK)
     │                      │
     ▼                      ▼
┌─────────────┐   ┌─────────────────┐
│ Return      │   │ Allow upload    │
│ HTTP 429    │   │ Update:         │
│ "Storage    │   │ total_used +=   │
│  Quota      │   │ original_used +=│
│  Exceeded"  │   └─────────────────┘
└─────────────┘
```

---

## Database Schema Relationships

```
┌────────────────────────────────────┐
│            File                    │
├────────────────────────────────────┤
│ id (PK, UUID)                      │
│ file (FileField)                   │
│ original_filename                  │
│ file_type                          │
│ size                               │
│ uploaded_at                        │
│ user_id (indexed)                  │
│ file_hash (indexed)                │
│ is_reference (Boolean)             │
│ original_file_id (FK) ─────────┐   │
└────────────────────────────────│───┘
                                 │
                                 │ ForeignKey
                                 │ (self-reference)
                                 │
                                 └──────┐
                                        │
                                        ▼
┌─────────────────────────────────────────┐
│  Original File                          │
│  (same File model)                      │
│                                         │
│  Can have multiple references pointing  │
│  to it via original_file_id             │
└─────────────────────────────────────────┘

Example:
┌──────────────┐         ┌──────────────┐
│ File 1       │         │ File 2       │
│ is_reference:│◄────────│ is_reference:│
│   false      │   FK    │   true       │
│ (Original)   │         │ (Reference)  │
└──────────────┘         └──────────────┘
       ▲
       │ FK
       │
┌──────────────┐
│ File 3       │
│ is_reference:│
│   true       │
│ (Reference)  │
└──────────────┘


┌────────────────────────────────────┐
│      UserStorageStats              │
├────────────────────────────────────┤
│ id (PK)                            │
│ user_id (unique, indexed)          │
│ total_storage_used                 │
│ original_storage_used              │
│                                    │
│ Calculated properties:             │
│ • storage_savings                  │
│ • savings_percentage               │
└────────────────────────────────────┘
```

---

## Configuration & Settings Flow

```
backend/core/settings.py
          │
          ├─── RATE_LIMIT_CALLS = 2
          │    RATE_LIMIT_WINDOW = 1
          │           │
          │           └──► Used by: files/middleware.py
          │                         (RateLimitMiddleware)
          │
          ├─── USER_STORAGE_LIMIT_MB = 10
          │           │
          │           └──► Used by: files/views.py
          │                         (FileViewSet.STORAGE_LIMIT_BYTES)
          │
          ├─── CACHES = {...}
          │           │
          │           └──► Used by: Rate limiting cache
          │                         (stores timestamps)
          │
          └─── MIDDLEWARE = [...]
                      │
                      └──► Includes: RateLimitMiddleware
```

---

## File Naming Convention

```
Original Filename: "my_document.pdf"
                          │
                          ▼
                  Calculate SHA-256
                          │
                          ▼
File Hash: "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
                          │
                          ▼
Physical Filename: "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3.pdf"
                          │
                          ▼
Storage Path: "media/uploads/a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3.pdf"

Benefits:
✓ Same content = Same filename
✓ Enables deduplication
✓ No filename conflicts
✓ Content addressable storage
```

---

## API Request/Response Flow

```
Request:
    POST /api/files/
    Headers:
        UserId: user123
        Content-Type: multipart/form-data
    Body:
        file: <binary data>

    │
    ▼
    
Middleware Processing:
    1. Security checks
    2. Rate limit check
    3. CSRF validation
    4. Attach user_id to request
    
    │
    ▼
    
View Processing:
    1. Validate file present
    2. Calculate hash
    3. Check for duplicate
    4. Check quota (if new)
    5. Save file/reference
    6. Update stats
    
    │
    ▼
    
Response:
    HTTP 201 Created
    {
        "id": "550e8400-e29b...",
        "file": "/media/uploads/...",
        "original_filename": "document.pdf",
        "file_type": "application/pdf",
        "size": 1024,
        "uploaded_at": "2024-01-15T10:30:00Z",
        "user_id": "user123",
        "file_hash": "a665a459...",
        "reference_count": 1,
        "is_reference": false,
        "original_file": null
    }
```

---

## Key Design Decisions

```
1. Middleware for Rate Limiting
   Why? Centralized, reusable, no code duplication
   
2. SHA-256 for Hashing
   Why? Industry standard, fast, negligible collision risk
   
3. Reference System for Deduplication
   Why? Maintains user file lists while saving storage
   
4. Database Indexes
   Why? Fast queries even with millions of files
   
5. Configurable Limits
   Why? Easy to adjust without code changes
   
6. Cache-based Rate Limiting
   Why? Fast, in-memory, easily upgradable to Redis
```

---

This architecture provides:
- ✅ Scalability
- ✅ Performance
- ✅ Maintainability
- ✅ Security
- ✅ Reliability
