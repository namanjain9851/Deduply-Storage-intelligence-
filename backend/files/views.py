import hashlib
import os
from django.shortcuts import render
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from .models import File, UserStorageStats
from .serializers import FileSerializer, StorageStatsSerializer


class FileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer
    
    # Configuration for storage limits (easily adjustable)
    STORAGE_LIMIT_MB = getattr(settings, 'USER_STORAGE_LIMIT_MB', 10)
    STORAGE_LIMIT_BYTES = STORAGE_LIMIT_MB * 1024 * 1024
    
    def get_queryset(self):
        """Get files for the current user with filtering"""
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            return File.objects.none()
        
        queryset = File.objects.filter(user_id=user_id)
        
        # Search by filename (case-insensitive)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(original_filename__icontains=search)
        
        # Filter by file type (MIME type)
        file_type = self.request.query_params.get('file_type', None)
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        # Filter by file size range
        min_size = self.request.query_params.get('min_size', None)
        if min_size:
            try:
                queryset = queryset.filter(size__gte=int(min_size))
            except ValueError:
                pass
        
        max_size = self.request.query_params.get('max_size', None)
        if max_size:
            try:
                queryset = queryset.filter(size__lte=int(max_size))
            except ValueError:
                pass
        
        # Filter by upload date range (ISO 8601 format)
        start_date = self.request.query_params.get('start_date', None)
        if start_date:
            queryset = queryset.filter(uploaded_at__gte=start_date)
        
        end_date = self.request.query_params.get('end_date', None)
        if end_date:
            queryset = queryset.filter(uploaded_at__lte=end_date)
        
        return queryset.select_related('original_file').prefetch_related('references')
    
    def _calculate_file_hash(self, file_obj):
        """Calculate SHA-256 hash of file content"""
        hash_sha256 = hashlib.sha256()
        
        # Reset file pointer to beginning
        file_obj.seek(0)
        
        # Read file in chunks to handle large files
        for chunk in iter(lambda: file_obj.read(4096), b''):
            hash_sha256.update(chunk)
        
        # Reset file pointer again for later use
        file_obj.seek(0)
        
        return hash_sha256.hexdigest()
    
    def _get_or_create_storage_stats(self, user_id):
        """Get or create storage stats for user"""
        stats, created = UserStorageStats.objects.get_or_create(
            user_id=user_id,
            defaults={
                'total_storage_used': 0,
                'original_storage_used': 0
            }
        )
        return stats
    
    def _check_storage_limit(self, user_id, file_size):
        """Check if uploading file would exceed storage limit"""
        stats = self._get_or_create_storage_stats(user_id)
        
        # Check if adding this file would exceed limit
        if stats.total_storage_used + file_size > self.STORAGE_LIMIT_BYTES:
            return False, stats
        
        return True, stats
    
    def create(self, request, *args, **kwargs):
        """Upload file with deduplication support"""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response({'error': 'UserId header is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate file hash for deduplication
        file_hash = self._calculate_file_hash(file_obj)
        file_size = file_obj.size
        
        # Check for existing file with same hash for this user
        existing_file = File.objects.filter(
            user_id=user_id, 
            file_hash=file_hash,
            is_reference=False
        ).first()
        
        # If file already exists, create a reference instead
        if existing_file:
            # Create reference entry
            file_instance = File(
                original_filename=file_obj.name,
                file_type=file_obj.content_type or 'application/octet-stream',
                size=file_size,
                user_id=user_id,
                file_hash=file_hash,
                is_reference=True,
                original_file=existing_file,
                file=existing_file.file  # Point to the same file
            )
            file_instance.save()
            
            # Update storage stats (only original storage, not actual)
            stats = self._get_or_create_storage_stats(user_id)
            stats.original_storage_used += file_size
            stats.save()
            
            serializer = self.get_serializer(file_instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Check storage limit before saving new file
        can_upload, stats = self._check_storage_limit(user_id, file_size)
        if not can_upload:
            return Response(
                {'error': 'Storage Quota Exceeded'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Create new file entry
        file_instance = File(
            original_filename=file_obj.name,
            file_type=file_obj.content_type or 'application/octet-stream',
            size=file_size,
            user_id=user_id,
            file_hash=file_hash,
            is_reference=False
        )
        
        # Save the file
        file_instance.file = file_obj
        file_instance.save()
        
        # Update storage stats
        stats.total_storage_used += file_size
        stats.original_storage_used += file_size
        stats.save()
        
        serializer = self.get_serializer(file_instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Delete file and update storage stats"""
        instance = self.get_object()
        user_id = getattr(request, 'user_id', None)
        
        # Verify ownership
        if instance.user_id != user_id:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        file_size = instance.size
        is_reference = instance.is_reference
        original_file = instance.original_file
        
        # Get storage stats
        stats = self._get_or_create_storage_stats(user_id)
        
        if is_reference:
            # Just remove the reference, don't delete actual file
            stats.original_storage_used -= file_size
        else:
            # Check if there are other references
            reference_count = instance.references.count()
            
            if reference_count > 0:
                # Don't delete physical file, just mark this entry as deleted
                # and update the references to point to another copy
                first_reference = instance.references.first()
                if first_reference:
                    # Promote first reference to be the original
                    first_reference.is_reference = False
                    first_reference.original_file = None
                    first_reference.save()
                    
                    # Update other references to point to the new original
                    instance.references.exclude(id=first_reference.id).update(
                        original_file=first_reference
                    )
            else:
                # No references, safe to delete physical file
                if instance.file and os.path.isfile(instance.file.path):
                    os.remove(instance.file.path)
                
                stats.total_storage_used -= file_size
            
            stats.original_storage_used -= file_size
        
        stats.save()
        instance.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def storage_stats(self, request):
        """Get storage statistics for the user"""
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'error': 'UserId header is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stats = self._get_or_create_storage_stats(user_id)
        serializer = StorageStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def file_types(self, request):
        """Get list of unique file types for the user"""
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'error': 'UserId header is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_types = File.objects.filter(user_id=user_id).values_list(
            'file_type', flat=True
        ).distinct().order_by('file_type')
        
        return Response(list(file_types))
