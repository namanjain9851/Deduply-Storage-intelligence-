from django.db import models
import uuid
import os

def file_upload_path(instance, filename):
    """Generate file path for new file upload using file hash"""
    # Use the file hash as the filename to enable deduplication
    ext = filename.split('.')[-1] if '.' in filename else 'bin'
    filename = f"{instance.file_hash}.{ext}" if hasattr(instance, 'file_hash') and instance.file_hash else f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)

class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=file_upload_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100)
    size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user_id = models.CharField(max_length=255, db_index=True)  # User identifier from header
    file_hash = models.CharField(max_length=64, db_index=True)  # SHA-256 hash for deduplication
    is_reference = models.BooleanField(default=False)  # True if this is a reference to another file
    original_file = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='references')  # Reference to original file
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user_id', 'uploaded_at']),
            models.Index(fields=['user_id', 'file_type']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['user_id', 'size']),
        ]
    
    def __str__(self):
        return self.original_filename
    
    @property
    def reference_count(self):
        """Count how many files reference this one (if original) or the original's reference count"""
        if self.is_reference and self.original_file:
            return self.original_file.references.count()
        return self.references.count()


class UserStorageStats(models.Model):
    """Track storage usage per user"""
    user_id = models.CharField(max_length=255, unique=True, db_index=True)
    total_storage_used = models.BigIntegerField(default=0)  # Actual storage after deduplication
    original_storage_used = models.BigIntegerField(default=0)  # Storage without deduplication
    
    class Meta:
        verbose_name_plural = "User Storage Stats"
    
    def __str__(self):
        return f"Storage for {self.user_id}"
    
    @property
    def storage_savings(self):
        return self.original_storage_used - self.total_storage_used
    
    @property
    def savings_percentage(self):
        if self.original_storage_used == 0:
            return 0.0
        return (self.storage_savings / self.original_storage_used) * 100