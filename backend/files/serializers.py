from rest_framework import serializers
from .models import File, UserStorageStats

class FileSerializer(serializers.ModelSerializer):
    reference_count = serializers.ReadOnlyField()
    original_file = serializers.UUIDField(source='original_file.id', read_only=True, allow_null=True)
    
    class Meta:
        model = File
        fields = [
            'id', 'file', 'original_filename', 'file_type', 'size', 
            'uploaded_at', 'user_id', 'file_hash', 'reference_count',
            'is_reference', 'original_file'
        ]
        read_only_fields = ['id', 'uploaded_at', 'file_hash', 'is_reference', 'original_file']


class StorageStatsSerializer(serializers.ModelSerializer):
    storage_savings = serializers.ReadOnlyField()
    savings_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = UserStorageStats
        fields = ['user_id', 'total_storage_used', 'original_storage_used', 'storage_savings', 'savings_percentage']
