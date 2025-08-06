import logging
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log incoming requests and their processing time.
    """

    def process_request(self, request):
        request.start_time = time.time()
        logger.info(f"Request: {request.method} {request.path}")

    def process_response(self, request, response):
        response_time = time.time() - request.start_time
        logger.info(
            f"Request completed: {request.method} {request.path}"
            f"Status: {response.status_code} - Duration: {response_time:.2f}s"
        )
        return response

    def process_exception(self, request, exception):
        logger.error(f"Exception: {request.method} {request.path} {exception}")
        return None
