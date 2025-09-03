import logging
import time

from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time
            logger.info(f"{request.method} {request.path} - {duration:.3f}s")
        return response

    def process_exception(self, request, exception):
        logger.error(f"Exception: {request.method} {request.path} {exception}")
        return None


class SSRPerformanceMiddleware:
    """Middleware to monitor SSR performance"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        # Log SSR performance for analytics pages
        if "analytics" in request.path or request.path == "/":
            duration = time.time() - start_time

            # Cache performance metrics (with error handling)
            try:
                cache_key = f'ssr_performance_{request.path}_{request.user.id if request.user.is_authenticated else "anonymous"}'
                cache.set(cache_key, duration, 3600)  # Cache for 1 hour
            except Exception as e:
                logger.warning(f"Failed to cache performance metrics: {e}")

            # Log performance data
            logger.info(
                f"SSR Performance: {request.path} - {duration:.3f}s - User: {request.user.id if request.user.is_authenticated else 'anonymous'}"
            )

            # Add performance header for monitoring
            response["X-SSR-Duration"] = f"{duration:.3f}"

        return response

    def process_exception(self, request, exception):
        if "analytics" in request.path:
            logger.error(f"SSR Error: {request.path} - {exception}")
        return None
