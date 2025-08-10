import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Base class for data loaders"""

    def __init__(self, user: None, upload_instance=None, **kwargs):
        self.user = user
        self.upload_instance = upload_instance
        self.upload_filename = (
            upload_instance.original_file_name if upload_instance else ""
        )
        self.options = kwargs
        self.created_count = 0
        self.updated_count = 0
        self.error_count = 0
        self.errors = []

    @abstractmethod
    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load data into database and return statistics"""
        pass

    def log_loader_stats(self):
        """Log loading statistics"""
        logger.info(
            f"Loading completed - Created: {self.created_count}, "
            f"Updated: {self.updated_count}, Errors: {self.error_count}"
        )

    def log_error(self, message: str, row_number: int = None):
        """Log error message"""
        if row_number:
            error_msg = f"Row {row_number}: {message}"
        else:
            error_msg = message

        self.errors.append(error_msg)
        self.error_count += 1
        logger.error(error_msg)

    def log_info(self, message: str):
        """Log info message"""
        logger.info(message)
