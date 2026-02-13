import time
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
#search by content 
#single word 
#file name and its content as output
class RateLimitMiddleware:
    """
    Middleware to implement rate limiting per user.
    Limits API calls to X calls per N seconds (configurable).
    Default: 2 calls per second
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Configuration - easily adjustable
        self.max_calls = getattr(settings, 'RATE_LIMIT_CALLS', 2)
        self.time_window = getattr(settings, 'RATE_LIMIT_WINDOW', 1)  # seconds
    
    def __call__(self, request):
        # Only apply rate limiting to API endpoints
        if not request.path.startswith('/api/'):
            return self.get_response(request)
        
        # Get user ID from header
        user_id = request.META.get('HTTP_USERID')
        
        if not user_id:
            return JsonResponse(
                {'error': 'UserId header is required'},
                status=400
            )
        
        # Create cache key for this user
        cache_key = f'rate_limit:{user_id}'
        
        # Get current request timestamps from cache
        request_times = cache.get(cache_key, [])
        current_time = time.time()
        
        # Remove old timestamps outside the time window
        request_times = [t for t in request_times if current_time - t < self.time_window]
        
        # Check if rate limit exceeded
        if len(request_times) >= self.max_calls:
            return JsonResponse(
                {'error': 'Call Limit Reached'},
                status=429
            )
        
        # Add current request timestamp
        request_times.append(current_time)
        
        # Store updated timestamps in cache
        cache.set(cache_key, request_times, self.time_window + 1)
        
        # Attach user_id to request for use in views
        request.user_id = user_id
        
        response = self.get_response(request)
        return response
