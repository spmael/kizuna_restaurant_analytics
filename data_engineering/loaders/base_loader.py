import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)

class BaseLoader(ABC):
    """Base class for data loaders"""

    def __init__(self, user: None, **kwargs):
        self.user = user
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
