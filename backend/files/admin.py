from django.contrib import admin
from .models import File, UserStorageStats


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_filename', 'user_id', 'file_type', 'size', 'uploaded_at', 'is_reference', 'file_hash']
    list_filter = ['user_id', 'file_type', 'is_reference', 'uploaded_at']
    search_fields = ['original_filename', 'user_id', 'file_hash']
    readonly_fields = ['id', 'uploaded_at', 'file_hash']
    ordering = ['-uploaded_at']


@admin.register(UserStorageStats)
class UserStorageStatsAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'total_storage_used', 'original_storage_used', 'storage_savings', 'savings_percentage']
    search_fields = ['user_id']
    readonly_fields = ['storage_savings', 'savings_percentage']
