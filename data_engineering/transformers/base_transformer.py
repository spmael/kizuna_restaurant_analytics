import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class BaseTransformer(ABC):
    """Base class for data transformers"""

    def __init__(self, **kwargs):
        self.options = kwargs
        self.errors = []
        self.warnings = []

    @abstractmethod
    def transform(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transform the data and return cleaned DataFrames"""
        pass

    def log_error(self, message: str, row_number: Optional[int] = None):
        """Log Transformer errors"""
        error_msg = f"Row {row_number}: {message}" if row_number else message
        self.errors.append(error_msg)
        logger.error(error_msg)

    def log_warning(self, message: str, row_number: Optional[int] = None):
        warning_msg = f"Row {row_number}: {message}" if row_number else message
        self.warnings.append(warning_msg)
        logger.warning(warning_msg)
