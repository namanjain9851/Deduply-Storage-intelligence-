# Production Readiness Guide - Scaling to Millions of Users

## Executive Summary

Your file vault application is a solid MVP with good architecture. To handle **millions of users** in production, you need to address 15 critical areas across infrastructure, security, performance, reliability, and operations.

**Priority Levels:**
- 🔴 **CRITICAL** - Must have before production launch
- 🟠 **HIGH** - Required for scale and reliability
- 🟡 **MEDIUM** - Important for operational excellence
- 🟢 **LOW** - Nice to have, optimize later

---

## 1. Authentication & Authorization 🔴 CRITICAL

### Current State
- Uses simple `UserId` header (insecure, easily spoofed)
- No authentication mechanism
- No authorization checks beyond user isolation

### Production Requirements

#### 1.1 Implement Proper Authentication
```python
# Add to requirements.txt
djangorestframework-simplejwt>=5.3.0
django-cors-headers>=4.3.0
```

**Options:**
- **JWT Tokens** (recommended for API-first)
- **OAuth 2.0** (for third-party integrations)
- **Django Session Auth** (for web apps)

**Implementation:**
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

#### 1.2 User Management
- [ ] User registration endpoint
- [ ] Email verification
- [ ] Password reset flow
- [ ] Multi-factor authentication (MFA)
- [ ] Account lockout after failed attempts
- [ ] Session management

#### 1.3 Role-Based Access Control (RBAC)
```python
class User(AbstractUser):
    role = models.CharField(choices=[
        ('user', 'User'),
        ('premium', 'Premium'),
        ('admin', 'Admin'),
    ])
    storage_quota_mb = models.IntegerField(default=10)
    api_rate_limit = models.IntegerField(default=100)
```

---

## 2. Database Optimization 🔴 CRITICAL

### Current State
- SQLite (single-file, not designed for concurrent writes)
- Limited concurrency support
- No replication or backup

### Production Requirements

#### 2.1 Switch to Production Database
**PostgreSQL** (recommended) or **MySQL**

```python
# requirements.txt
psycopg2-binary>=2.9.9  # PostgreSQL
# OR
mysqlclient>=2.2.0  # MySQL

# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'filevault'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}
```

#### 2.2 Database Optimizations
```python
# Add to models.py
class File(models.Model):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            # Existing indexes
            models.Index(fields=['user_id', 'uploaded_at']),
            models.Index(fields=['user_id', 'file_type']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['user_id', 'size']),
            
            # Additional for scale
            models.Index(fields=['uploaded_at']),  # For admin queries
            models.Index(fields=['is_reference', 'file_hash']),  # Dedup lookups
            models.Index(fields=['user_id', 'is_reference']),  # User file counts
        ]
        # Partition by upload date for millions of records
        db_table_comment = 'Consider partitioning by uploaded_at for 100M+ rows'
```

#### 2.3 Connection Pooling
```python
# requirements.txt
django-db-connection-pool>=1.2.4

# Use PgBouncer for PostgreSQL
# Or ProxySQL for MySQL
```

#### 2.4 Read Replicas
```python
# settings.py
DATABASES = {
    'default': {
        # Primary (writes)
    },
    'replica': {
        # Read replica (reads)
    }
}

DATABASE_ROUTERS = ['core.db_router.ReplicaRouter']
```

#### 2.5 Query Optimization
```python
# Add to views.py
from django.db.models import Count, Sum, Prefetch

def get_queryset(self):
    return File.objects.filter(user_id=user_id) \
        .select_related('original_file') \
        .prefetch_related(
            Prefetch('references', 
                queryset=File.objects.only('id', 'size'))
        ) \
        .only(  # Don't fetch file content in listings
            'id', 'original_filename', 'file_type', 
            'size', 'uploaded_at', 'is_reference'
        )
```

---

## 3. Cloud Storage 🔴 CRITICAL

### Current State
- Local file storage (not scalable, single server dependency)
- No redundancy or backup
- No CDN support

### Production Requirements

#### 3.1 Migrate to Cloud Object Storage
**AWS S3** (recommended), **Google Cloud Storage**, or **Azure Blob Storage**

```python
# requirements.txt
boto3>=1.34.0  # AWS
django-storages>=1.14.2

# settings.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = 'private'
AWS_S3_ENCRYPTION = True  # Server-side encryption

# For millions of users
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 3600  # Signed URLs expire in 1 hour
```

#### 3.2 CDN Configuration
```python
# Use CloudFront (AWS) or CloudFlare
AWS_CLOUDFRONT_DOMAIN = os.environ.get('AWS_CLOUDFRONT_DOMAIN')
if AWS_CLOUDFRONT_DOMAIN:
    AWS_S3_CUSTOM_DOMAIN = AWS_CLOUDFRONT_DOMAIN
```

#### 3.3 Multi-Region Replication
- Configure S3 cross-region replication
- Reduce latency for global users
- Disaster recovery

#### 3.4 Storage Classes
```python
# Implement intelligent tiering
AWS_S3_OBJECT_PARAMETERS = {
    'StorageClass': 'INTELLIGENT_TIERING',  # Auto cost optimization
}

# Move old files to cheaper storage
# After 90 days: STANDARD_IA
# After 180 days: GLACIER
```

---

## 4. Caching Layer 🔴 CRITICAL

### Current State
- Local memory cache (lost on restart, not shared across servers)
- Only used for rate limiting

### Production Requirements

#### 4.1 Redis Implementation
```python
# requirements.txt
redis>=5.0.1
django-redis>=5.4.0

# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'filevault',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session storage in Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

#### 4.2 Caching Strategy
```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

class FileViewSet(viewsets.ModelViewSet):
    
    @cache_page(60 * 5)  # Cache for 5 minutes
    @action(detail=False, methods=['get'])
    def storage_stats(self, request):
        cache_key = f'storage_stats:{user_id}'
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = self._get_or_create_storage_stats(user_id)
            cache.set(cache_key, stats, timeout=300)
        
        return Response(StorageStatsSerializer(stats).data)
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Invalidate cache on upload
        cache.delete(f'storage_stats:{request.user_id}')
        cache.delete(f'file_types:{request.user_id}')
        return response
```

#### 4.3 What to Cache
- [ ] User storage statistics
- [ ] File type lists
- [ ] User metadata
- [ ] File hash lookups (deduplication checks)
- [ ] Search results (with TTL)
- [ ] API responses (conditional)

#### 4.4 Redis Cluster
For millions of users:
```yaml
# docker-compose.yml
redis-cluster:
  image: redis:7-alpine
  command: redis-server --cluster-enabled yes
  deploy:
    replicas: 6  # 3 masters + 3 replicas
```

---

## 5. Security Hardening 🔴 CRITICAL

### Current State
- DEBUG = True
- Weak SECRET_KEY
- ALLOWED_HOSTS = ['*']
- No HTTPS enforcement
- No input sanitization
- No virus scanning

### Production Requirements

#### 5.1 Django Security Settings
```python
# settings.py - PRODUCTION SETTINGS

# Secret Management
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('DJANGO_SECRET_KEY environment variable must be set')

# Debug
DEBUG = False

# Hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CORS (if needed for frontend)
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
CORS_ALLOW_CREDENTIALS = True
```

#### 5.2 File Upload Security
```python
# settings.py
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880

# Allowed file types (whitelist)
ALLOWED_UPLOAD_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'txt', 'csv', 'json', 'xml',
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
    'mp4', 'mov', 'avi', 'mkv',
    'mp3', 'wav', 'ogg',
    'zip', 'tar', 'gz', '7z',
]

MAX_FILE_SIZE_MB = 100  # Per file
```

```python
# views.py
import magic

def create(self, request, *args, **kwargs):
    file_obj = request.FILES.get('file')
    
    # 1. Size check
    if file_obj.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        return Response({'error': 'File too large'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # 2. Extension check
    ext = file_obj.name.split('.')[-1].lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        return Response({'error': 'File type not allowed'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # 3. MIME type validation (using python-magic)
    mime = magic.from_buffer(file_obj.read(2048), mime=True)
    file_obj.seek(0)
    
    # 4. Content inspection
    if self._is_malicious(file_obj):
        return Response({'error': 'Malicious file detected'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Continue with upload...
```

#### 5.3 Virus Scanning
```python
# requirements.txt
clamd>=1.0.2  # ClamAV interface

# views.py
import clamd

def _scan_file(self, file_obj):
    """Scan file for viruses using ClamAV"""
    cd = clamd.ClamdUnixSocket()
    
    file_obj.seek(0)
    scan_result = cd.instream(file_obj)
    file_obj.seek(0)
    
    status = scan_result.get('stream')
    if status[0] == 'FOUND':
        logger.warning(f'Virus detected: {status[1]}')
        return False
    
    return True
```

#### 5.4 Rate Limiting Enhancements
```python
# More sophisticated rate limiting
RATE_LIMITS = {
    'anonymous': {'calls': 10, 'window': 60},      # 10/minute
    'authenticated': {'calls': 100, 'window': 60},  # 100/minute
    'premium': {'calls': 1000, 'window': 60},       # 1000/minute
    'upload': {'calls': 10, 'window': 3600},        # 10 uploads/hour
    'download': {'calls': 100, 'window': 3600},     # 100 downloads/hour
}
```

#### 5.5 DDoS Protection
- [ ] Use CloudFlare or AWS WAF
- [ ] Implement request throttling at load balancer
- [ ] Geographic rate limiting
- [ ] IP blacklisting/whitelisting
- [ ] Challenge pages (CAPTCHA)

#### 5.6 Data Encryption
```python
# Encrypt file names and metadata
from cryptography.fernet import Fernet

class File(models.Model):
    # Store encrypted filename
    encrypted_filename = models.BinaryField()
    encryption_key_id = models.CharField(max_length=50)
    
    def set_filename(self, filename, key):
        f = Fernet(key)
        self.encrypted_filename = f.encrypt(filename.encode())
    
    def get_filename(self, key):
        f = Fernet(key)
        return f.decrypt(self.encrypted_filename).decode()

# Enable encryption at rest in S3
AWS_S3_ENCRYPTION = True
AWS_S3_OBJECT_PARAMETERS = {
    'ServerSideEncryption': 'AES256',
    # Or use KMS
    # 'ServerSideEncryption': 'aws:kms',
    # 'SSEKMSKeyId': os.environ.get('KMS_KEY_ID'),
}
```

---

## 6. API Rate Limiting & Throttling 🟠 HIGH

### Current State
- Simple cache-based rate limiting
- Fixed 2 calls/second (100 in debug)
- No differentiation by endpoint or user type

### Production Requirements

#### 6.1 Advanced Throttling
```python
# requirements.txt
django-ratelimit>=4.1.0

# throttling.py
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'
    rate = '60/min'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'
    rate = '1000/hour'

class UploadRateThrottle(UserRateThrottle):
    scope = 'upload'
    rate = '10/hour'

class PremiumRateThrottle(UserRateThrottle):
    scope = 'premium'
    rate = '10000/hour'

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'core.throttling.BurstRateThrottle',
        'core.throttling.SustainedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'burst': '60/min',
        'sustained': '1000/hour',
        'upload': '10/hour',
        'premium': '10000/hour',
    }
}
```

#### 6.2 Per-Endpoint Throttling
```python
class FileViewSet(viewsets.ModelViewSet):
    
    def get_throttles(self):
        if self.action == 'create':
            return [UploadRateThrottle()]
        return super().get_throttles()
```

#### 6.3 API Gateway
Consider using:
- **Kong Gateway**
- **AWS API Gateway**
- **Google Cloud API Gateway**

Benefits:
- Advanced rate limiting
- Request routing
- API versioning
- Analytics
- Authentication

---

## 7. Application Scaling 🟠 HIGH

### Current State
- Single server deployment
- No horizontal scaling
- No load balancing

### Production Requirements

#### 7.1 Containerization
```dockerfile
# backend/Dockerfile (production-ready)
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "core.wsgi:application"]
```

#### 7.2 Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: filevault-api
spec:
  replicas: 3  # Start with 3, scale based on load
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: filevault-api
  template:
    metadata:
      labels:
        app: filevault-api
    spec:
      containers:
      - name: api
        image: filevault-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DJANGO_SETTINGS_MODULE
          value: core.settings
        - name: DB_HOST
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: host
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: filevault-api
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: filevault-api
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: filevault-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: filevault-api
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 7.3 Gunicorn Configuration
```python
# gunicorn.conf.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000
timeout = 60
keepalive = 5
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
```

#### 7.4 Load Balancer Configuration
```nginx
# nginx.conf
upstream filevault_backend {
    least_conn;
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.filevault.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.filevault.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Upload limits
    client_max_body_size 100M;
    client_body_timeout 300s;
    
    location / {
        proxy_pass http://filevault_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /media/ {
        # Serve from CDN instead
        return 302 https://cdn.filevault.com$request_uri;
    }
    
    location /health/ {
        access_log off;
        proxy_pass http://filevault_backend;
    }
}
```

---

## 8. Monitoring & Observability 🟠 HIGH

### Current State
- No monitoring
- No logging infrastructure
- No error tracking
- No performance metrics

### Production Requirements

#### 8.1 Application Performance Monitoring (APM)
```python
# requirements.txt
sentry-sdk>=1.40.0
django-prometheus>=2.3.1
newrelic>=9.5.0  # Alternative to Sentry

# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,
    environment=os.environ.get('ENVIRONMENT', 'production'),
    send_default_pii=False,
    before_send=before_send_filter,  # Filter sensitive data
)
```

#### 8.2 Structured Logging
```python
# requirements.txt
python-json-logger>=2.0.7

# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/filevault/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'files': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}
```

#### 8.3 Metrics Collection
```python
# Prometheus metrics
# views.py
from prometheus_client import Counter, Histogram, Gauge

file_uploads_total = Counter(
    'file_uploads_total',
    'Total number of file uploads',
    ['user_type', 'file_type']
)

file_upload_size = Histogram(
    'file_upload_size_bytes',
    'Size of uploaded files',
    buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600]
)

storage_used = Gauge(
    'storage_used_bytes',
    'Total storage used',
    ['user_id']
)

def create(self, request, *args, **kwargs):
    file_obj = request.FILES.get('file')
    
    # Record metrics
    file_uploads_total.labels(
        user_type=request.user.role,
        file_type=file_obj.content_type
    ).inc()
    
    file_upload_size.observe(file_obj.size)
    
    # ... rest of upload logic
```

#### 8.4 Health Check Endpoints
```python
# views.py
from django.db import connection
from django.core.cache import cache
from rest_framework.decorators import api_view

@api_view(['GET'])
def health_check(request):
    """Simple health check"""
    return Response({'status': 'healthy'})

@api_view(['GET'])
def readiness_check(request):
    """Detailed readiness check"""
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        'storage': check_storage(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return Response({
        'ready': all_healthy,
        'checks': checks
    }, status=status_code)

def check_database():
    try:
        connection.ensure_connection()
        return True
    except Exception:
        return False

def check_cache():
    try:
        cache.set('health_check', 'ok', 10)
        return cache.get('health_check') == 'ok'
    except Exception:
        return False

def check_storage():
    try:
        # Check S3 connectivity
        from django.core.files.storage import default_storage
        default_storage.exists('health_check.txt')
        return True
    except Exception:
        return False
```

#### 8.5 Dashboards
**Grafana + Prometheus Stack**
```yaml
# docker-compose.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=changeme
  
  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"
```

**Key Metrics to Monitor:**
- Request rate, latency, error rate
- File upload success/failure rates
- Storage usage per user
- Database connection pool usage
- Cache hit/miss rates
- API rate limit violations
- Queue depths (for async tasks)
- Server CPU, memory, disk usage

---

## 9. Asynchronous Processing 🟠 HIGH

### Current State
- All operations are synchronous
- File hashing blocks the request
- No background job processing

### Production Requirements

#### 9.1 Celery for Background Tasks
```python
# requirements.txt
celery>=5.3.4
redis>=5.0.1  # Celery broker

# celery.py
from celery import Celery

app = Celery('filevault')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# settings.py
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

#### 9.2 Background Tasks
```python
# tasks.py
from celery import shared_task
import hashlib

@shared_task(bind=True, max_retries=3)
def process_file_upload(self, file_id):
    """Process file upload asynchronously"""
    try:
        file_obj = File.objects.get(id=file_id)
        
        # 1. Calculate hash (if not already done)
        if not file_obj.file_hash:
            file_obj.file_hash = calculate_file_hash(file_obj.file)
            file_obj.save()
        
        # 2. Virus scan
        scan_file_for_viruses.delay(file_id)
        
        # 3. Generate thumbnail (for images)
        if file_obj.file_type.startswith('image/'):
            generate_thumbnail.delay(file_id)
        
        # 4. Extract metadata
        extract_metadata.delay(file_id)
        
        return {'status': 'success', 'file_id': str(file_id)}
    
    except Exception as exc:
        self.retry(exc=exc, countdown=60)

@shared_task
def scan_file_for_viruses(file_id):
    """Scan file for viruses"""
    file_obj = File.objects.get(id=file_id)
    # Implement virus scanning
    pass

@shared_task
def generate_thumbnail(file_id):
    """Generate thumbnail for image files"""
    file_obj = File.objects.get(id=file_id)
    # Implement thumbnail generation
    pass

@shared_task
def cleanup_old_files():
    """Periodic task to clean up deleted files"""
    # Implement cleanup logic
    pass

@shared_task
def generate_storage_reports():
    """Generate storage usage reports"""
    # Implement report generation
    pass
```

#### 9.3 Async Upload Flow
```python
# views.py
def create(self, request, *args, **kwargs):
    file_obj = request.FILES.get('file')
    
    # Quick validation
    if not file_obj or file_obj.size > MAX_SIZE:
        return Response({'error': 'Invalid file'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Create file record (minimal processing)
    file_instance = File(
        original_filename=file_obj.name,
        file_type=file_obj.content_type,
        size=file_obj.size,
        user_id=request.user_id,
        status='processing',  # Add status field
    )
    file_instance.file = file_obj
    file_instance.save()
    
    # Process asynchronously
    process_file_upload.delay(str(file_instance.id))
    
    return Response({
        'id': file_instance.id,
        'status': 'processing',
        'message': 'File is being processed'
    }, status=status.HTTP_202_ACCEPTED)
```

#### 9.4 Celery Beat for Scheduled Tasks
```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-old-files': {
        'task': 'files.tasks.cleanup_old_files',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'generate-storage-reports': {
        'task': 'files.tasks.generate_storage_reports',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    'check-storage-quotas': {
        'task': 'files.tasks.check_storage_quotas',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}
```

---

## 10. Data Backup & Disaster Recovery 🟠 HIGH

### Current State
- No backup strategy
- No disaster recovery plan
- Single point of failure

### Production Requirements

#### 10.1 Database Backups
```bash
# Automated PostgreSQL backups
#!/bin/bash
# backup.sh

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups/postgres"
DB_NAME="filevault"

# Create backup
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | \
    gzip > $BACKUP_DIR/backup_$TIMESTAMP.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/backup_$TIMESTAMP.sql.gz \
    s3://filevault-backups/postgres/

# Keep only last 30 days locally
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

# Verify backup
gunzip -t $BACKUP_DIR/backup_$TIMESTAMP.sql.gz
```

**Backup Strategy:**
- Full backup: Daily at 2 AM
- Incremental backup: Every 6 hours
- Point-in-time recovery (PITR) enabled
- Retention: 30 days hot, 1 year cold storage
- Test recovery: Monthly

#### 10.2 File Storage Backups
```python
# S3 versioning and lifecycle
{
    "Rules": [
        {
            "Id": "backup-lifecycle",
            "Status": "Enabled",
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "STANDARD_IA"
                },
                {
                    "Days": 90,
                    "StorageClass": "GLACIER"
                }
            ],
            "NoncurrentVersionTransitions": [
                {
                    "NoncurrentDays": 30,
                    "StorageClass": "GLACIER"
                }
            ],
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 365
            }
        }
    ]
}
```

#### 10.3 Disaster Recovery Plan
```markdown
## RTO/RPO Targets
- Recovery Time Objective (RTO): 4 hours
- Recovery Point Objective (RPO): 1 hour

## Multi-Region Setup
- Primary: us-east-1
- Secondary: us-west-2
- Tertiary: eu-west-1

## Failover Procedure
1. Health check detects primary region failure
2. Route 53 automatically fails over to secondary
3. Database replica promoted to primary
4. Application servers scaled up in secondary region
5. Notify operations team

## Recovery Testing
- Monthly: Backup restoration test
- Quarterly: Full DR drill
- Annually: Regional failover test
```

---

## 11. Search Optimization 🟡 MEDIUM

### Current State
- Basic database queries with LIKE
- No full-text search
- Limited scalability

### Production Requirements

#### 11.1 Elasticsearch Integration
```python
# requirements.txt
elasticsearch>=8.11.0
django-elasticsearch-dsl>=8.0

# settings.py
ELASTICSEARCH_DSL = {
    'default': {
        'hosts': os.environ.get('ELASTICSEARCH_URL', 'localhost:9200'),
        'http_auth': (
            os.environ.get('ES_USER', 'elastic'),
            os.environ.get('ES_PASSWORD', 'changeme')
        ),
    },
}

# documents.py
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

@registry.register_document
class FileDocument(Document):
    user_id = fields.KeywordField()
    original_filename = fields.TextField(
        analyzer='standard',
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        }
    )
    file_type = fields.KeywordField()
    size = fields.LongField()
    uploaded_at = fields.DateField()
    file_hash = fields.KeywordField()
    
    # Full-text search on content (for text files)
    content = fields.TextField()
    
    class Index:
        name = 'files'
        settings = {
            'number_of_shards': 3,
            'number_of_replicas': 2,
        }
    
    class Django:
        model = File
        fields = []

# views.py
from elasticsearch_dsl import Search

@action(detail=False, methods=['get'])
def search(self, request):
    query = request.query_params.get('q', '')
    user_id = request.user_id
    
    s = Search(index='files') \
        .filter('term', user_id=user_id) \
        .query('multi_match', 
               query=query, 
               fields=['original_filename^3', 'content'])
    
    # Autocomplete
    if request.query_params.get('suggest'):
        s = s.suggest('filename_suggest', 
                     query, 
                     completion={'field': 'original_filename.suggest'})
    
    response = s.execute()
    # Process and return results
```

#### 11.2 Search Features
- [ ] Full-text search
- [ ] Autocomplete/suggestions
- [ ] Fuzzy matching
- [ ] File content search (PDF, DOCX, etc.)
- [ ] Faceted search (by file type, size, date)
- [ ] Search analytics

---

## 12. API Versioning & Documentation 🟡 MEDIUM

### Current State
- No API versioning
- No interactive documentation

### Production Requirements

#### 12.1 API Versioning
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2'],
}

# urls.py
urlpatterns = [
    path('api/v1/', include('files.urls_v1')),
    path('api/v2/', include('files.urls_v2')),
]
```

#### 12.2 OpenAPI/Swagger Documentation
```python
# requirements.txt
drf-spectacular>=0.27.0

# settings.py
INSTALLED_APPS += ['drf_spectacular']

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'File Vault API',
    'DESCRIPTION': 'Secure file storage with deduplication',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]
```

---

## 13. Compliance & Legal 🟡 MEDIUM

### Production Requirements

#### 13.1 GDPR Compliance
- [ ] User consent management
- [ ] Data export functionality
- [ ] Right to be forgotten (data deletion)
- [ ] Data retention policies
- [ ] Privacy policy
- [ ] Cookie consent

```python
@action(detail=False, methods=['get'])
def export_data(self, request):
    """Export all user data (GDPR compliance)"""
    user_id = request.user_id
    
    files = File.objects.filter(user_id=user_id)
    stats = UserStorageStats.objects.get(user_id=user_id)
    
    data = {
        'user_id': user_id,
        'files': FileSerializer(files, many=True).data,
        'storage_stats': StorageStatsSerializer(stats).data,
        'export_date': timezone.now().isoformat(),
    }
    
    return Response(data)

@action(detail=False, methods=['delete'])
def delete_account(self, request):
    """Delete all user data (GDPR right to be forgotten)"""
    user_id = request.user_id
    
    # Delete files
    File.objects.filter(user_id=user_id).delete()
    
    # Delete stats
    UserStorageStats.objects.filter(user_id=user_id).delete()
    
    # Delete from S3
    # ... implement S3 deletion
    
    return Response({'message': 'All data deleted'})
```

#### 13.2 Audit Logging
```python
class AuditLog(models.Model):
    user_id = models.CharField(max_length=255)
    action = models.CharField(max_length=50)  # upload, delete, download, etc.
    resource_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField()
    
    class Meta:
        indexes = [
            models.Index(fields=['user_id', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

# Log all actions
def create(self, request, *args, **kwargs):
    response = super().create(request, *args, **kwargs)
    
    AuditLog.objects.create(
        user_id=request.user_id,
        action='file_upload',
        resource_id=response.data['id'],
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={'filename': response.data['original_filename']}
    )
    
    return response
```

#### 13.3 Terms of Service
- [ ] Upload size limits
- [ ] Acceptable use policy
- [ ] Prohibited content
- [ ] Data retention
- [ ] Service availability SLA

---

## 14. Testing & CI/CD 🟡 MEDIUM

### Current State
- Manual test scripts
- No automated testing
- No CI/CD pipeline

### Production Requirements

#### 14.1 Comprehensive Test Suite
```python
# requirements.txt
pytest>=7.4.3
pytest-django>=4.7.0
pytest-cov>=4.1.0
factory-boy>=3.3.0
faker>=21.0.0

# tests/test_views.py
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from files.models import File

@pytest.mark.django_db
class TestFileUpload:
    
    def test_upload_new_file(self, api_client, user):
        file_content = b'test content'
        file = SimpleUploadedFile("test.txt", file_content)
        
        response = api_client.post(
            '/api/v1/files/',
            {'file': file},
            headers={'UserId': user.id}
        )
        
        assert response.status_code == 201
        assert File.objects.count() == 1
    
    def test_deduplication(self, api_client, user):
        # Upload same file twice
        file_content = b'duplicate content'
        
        file1 = SimpleUploadedFile("test1.txt", file_content)
        response1 = api_client.post('/api/v1/files/', {'file': file1})
        
        file2 = SimpleUploadedFile("test2.txt", file_content)
        response2 = api_client.post('/api/v1/files/', {'file': file2})
        
        # Second upload should be a reference
        assert response2.data['is_reference'] is True
    
    def test_storage_quota_exceeded(self, api_client, user):
        # Upload file exceeding quota
        large_file = SimpleUploadedFile("large.bin", b'x' * 11 * 1024 * 1024)
        
        response = api_client.post('/api/v1/files/', {'file': large_file})
        
        assert response.status_code == 429
        assert 'Storage Quota Exceeded' in response.data['error']

# Load testing
# tests/load_test.py
from locust import HttpUser, task, between

class FileVaultUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def upload_file(self):
        files = {'file': ('test.txt', b'test content')}
        self.client.post(
            '/api/v1/files/',
            files=files,
            headers={'UserId': 'user123'}
        )
    
    @task(5)
    def list_files(self):
        self.client.get(
            '/api/v1/files/',
            headers={'UserId': 'user123'}
        )
    
    @task(1)
    def storage_stats(self):
        self.client.get(
            '/api/v1/files/storage_stats/',
            headers={'UserId': 'user123'}
        )

# Run: locust -f tests/load_test.py --host=http://localhost:8000
```

#### 14.2 CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
        pip install pytest pytest-django pytest-cov
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
      run: |
        cd backend
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
    
    - name: Security scan
      run: |
        pip install bandit safety
        bandit -r backend/
        safety check --file backend/requirements.txt

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Build Docker image
      run: |
        docker build -t filevault-api:${{ github.sha }} backend/
    
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker tag filevault-api:${{ github.sha }} filevault-api:latest
        docker push filevault-api:${{ github.sha }}
        docker push filevault-api:latest
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v4
      with:
        manifests: |
          k8s/deployment.yaml
          k8s/service.yaml
        images: |
          filevault-api:${{ github.sha }}
```

---

## 15. Performance Optimization 🟢 LOW (initially)

### Production Requirements

#### 15.1 Database Query Optimization
```python
# Use select_related and prefetch_related
queryset = File.objects.filter(user_id=user_id) \
    .select_related('original_file') \
    .prefetch_related('references') \
    .only('id', 'original_filename', 'size', 'uploaded_at')

# Database connection pooling
# requirements.txt
psycopg2-pool>=1.1

# Use database indexes
# Add GIN index for full-text search in PostgreSQL
class Migration:
    operations = [
        migrations.RunSQL(
            "CREATE INDEX file_filename_gin ON files_file USING gin(to_tsvector('english', original_filename));"
        )
    ]
```

#### 15.2 Caching Strategy
```python
# Cache expensive queries
from django.core.cache import cache

def get_user_files_count(user_id):
    cache_key = f'user_files_count:{user_id}'
    count = cache.get(cache_key)
    
    if count is None:
        count = File.objects.filter(user_id=user_id).count()
        cache.set(cache_key, count, timeout=3600)
    
    return count
```

#### 15.3 CDN for Static Assets
- Use CloudFlare, CloudFront, or Fastly
- Cache API responses where appropriate
- Edge caching for frequently accessed files

#### 15.4 Database Partitioning
For 100M+ files:
```sql
-- Partition by upload date
CREATE TABLE files_2024_01 PARTITION OF files
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE files_2024_02 PARTITION OF files
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

---

## 16. Cost Optimization 🟢 LOW (initially)

### Production Requirements

#### 16.1 Storage Cost Optimization
```python
# Implement intelligent tiering
- Hot storage (frequently accessed): Standard S3
- Warm storage (occasionally accessed): S3-IA
- Cold storage (rarely accessed): Glacier

# Delete duplicate file metadata after X days
# Keep only one reference
```

#### 16.2 Compute Cost Optimization
- Right-size instances based on metrics
- Use spot instances for non-critical workers
- Auto-scaling based on load
- Schedule scale-down during off-peak hours

#### 16.3 Monitoring Costs
```python
# Track costs by user
class UserCostTracking(models.Model):
    user_id = models.CharField(max_length=255)
    storage_cost = models.DecimalField(max_digits=10, decimal_places=2)
    bandwidth_cost = models.DecimalField(max_digits=10, decimal_places=2)
    compute_cost = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.DateField()
```

---

## Implementation Roadmap

### Phase 1: Critical (Weeks 1-4)
1. ✅ Authentication & Authorization
2. ✅ Database migration to PostgreSQL
3. ✅ Cloud storage (S3) integration
4. ✅ Redis caching
5. ✅ Security hardening
6. ✅ HTTPS setup

### Phase 2: High Priority (Weeks 5-8)
7. ✅ Application scaling (Kubernetes)
8. ✅ Monitoring & logging
9. ✅ Async processing (Celery)
10. ✅ Backup & DR setup
11. ✅ Advanced rate limiting

### Phase 3: Medium Priority (Weeks 9-12)
12. ✅ Elasticsearch integration
13. ✅ API versioning & docs
14. ✅ Compliance features
15. ✅ CI/CD pipeline
16. ✅ Load testing

### Phase 4: Optimization (Ongoing)
17. ✅ Performance tuning
18. ✅ Cost optimization
19. ✅ Advanced features
20. ✅ Continuous improvement

---

## Cost Estimates (for 1M users)

### Infrastructure Costs (Monthly)
- **Compute** (Kubernetes): $2,000 - $5,000
- **Database** (PostgreSQL RDS): $1,000 - $3,000
- **Cache** (Redis): $500 - $1,500
- **Storage** (S3): $500 - $2,000 per TB
- **CDN**: $100 - $500 per TB transferred
- **Monitoring** (Sentry, Datadog): $500 - $2,000
- **Total**: ~$5,000 - $15,000/month

### Scaling Estimates
- 1M users, 10GB average: ~10PB storage = $200,000/month
- With 50% deduplication: ~5PB = $100,000/month
- Additional bandwidth, compute: $20,000 - $50,000/month

**Total for 1M users**: $125,000 - $165,000/month

---

## Success Metrics

### Performance
- API latency: p95 < 200ms, p99 < 500ms
- Upload success rate: > 99.9%
- Downtime: < 0.1% (99.9% uptime)

### Scale
- Support 1M concurrent users
- Handle 10,000 uploads/second
- Store 100M+ files

### Reliability
- RTO: < 4 hours
- RPO: < 1 hour
- Data durability: 99.999999999% (11 nines)

---

## Conclusion

Your current implementation is a solid MVP, but **production readiness for millions of users requires significant infrastructure and operational enhancements**. Focus on:

1. **Security First**: Authentication, HTTPS, encryption
2. **Scalability**: Cloud storage, horizontal scaling, caching
3. **Reliability**: Monitoring, backups, disaster recovery
4. **Performance**: Async processing, query optimization, CDN

The roadmap above provides a clear path from MVP to production-grade system. Prioritize the critical items first, then iterate based on real-world usage and metrics.
