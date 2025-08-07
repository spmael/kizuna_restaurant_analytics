import logging
from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for data extractors"""

    def __init__(self, file_path: str, **kwargs):
        self.file_path = file_path
        self.options = kwargs
        self.errors = []

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Extract data from source and return dictionary of DataFrames"""
        pass

    def validate_file(self) -> bool:
        import os

        if not os.path.exists(self.file_path):
            self.errors.append(_("File does not exist: {}").format(self.file_path))
            return False

        if not os.path.isfile(self.file_path):
            self.errors.append(_("Path is not a file: {}").format(self.file_path))
            return False

        return True

    def log_extractor_stats(self, data: Dict[str, pd.DataFrame]):
        """Log extractor statistics"""
        total_rows = sum(len(df) for df in data.values())
        logger.info(f"Extracted {len(data)} sheets with {total_rows} total rows")

        for sheet_name, df in data.items():
            logger.info(
                f"Sheet '{sheet_name}': {df.shape[0]} rows, {df.shape[1]} columns"
            )
