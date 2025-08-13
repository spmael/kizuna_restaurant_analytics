import logging
from typing import Dict

import pandas as pd

from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class OdooExtractor(BaseExtractor):
    """Extract data from Odoo Excel export with multiple sheets including recipes"""

    # Expected sheet names
    EXPECTED_SHEETS = {
        "products": ["products", "produits", "produit", "product"],
        "purchases": ["purchases", "achats", "achat", "purchase"],
        "sales": ["sales", "ventes", "vente", "sale", "commandes_detaillees"],
        "recipes": ["recipes", "recettes", "recette", "recipe"],
    }

    def extract(self) -> Dict[str, pd.DataFrame]:
        """Extract data from Odoo Excel export with multiple sheets including recipes"""

        if not self.validate_file():
            return {}

        # Load the Excel file
        try:
            # Read all sheets from the Excel file
            excel_data = pd.read_excel(
                self.file_path,
                sheet_name=None,
                na_values=["", "None", "NULL", "null", "#N/A"],
            )

            # Map sheet names to standardized names
            mapped_data = self._map_sheet_names(excel_data)

            # Clean and validate each sheet
            cleaned_data = {}

            for sheet_type, df in mapped_data.items():
                if df is not None and not df.empty:
                    cleaned_data[sheet_type] = self._clean_dataframe(df, sheet_type)

            self.log_extractor_stats(cleaned_data)
            return cleaned_data
        except Exception as e:
            error_msg = f"Error extracting data from Odoo Excel file: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return {}

    def _map_sheet_names(
        self, excel_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """Map sheet names to expected sheet types"""
        mapped_data = {}
        sheet_names = list(excel_data.keys())

        logger.info(f"Found {len(sheet_names)} sheets in the file")

        for sheet_type, possible_names in self.EXPECTED_SHEETS.items():
            found_sheet = None

            # Look for exact matches (case-insensitive)
            for sheet_name in sheet_names:
                if sheet_name.lower().strip() in [
                    name.lower().strip() for name in possible_names
                ]:
                    found_sheet = sheet_name
                    break

            # if no exact match, look for partial matches
            if not found_sheet:
                for sheet_name in sheet_names:
                    for possible_name in possible_names:
                        if possible_name.lower().strip() in sheet_name.lower().strip():
                            found_sheet = sheet_name
                            break
                    if found_sheet:
                        break

            if found_sheet:
                mapped_data[sheet_type] = excel_data[found_sheet]
                logger.info(f"Mapped {found_sheet} to {sheet_type} sheet")
            else:
                logger.warning(
                    f"No matching sheet found for '{sheet_type}', Expected: {possible_names}"
                )
                mapped_data[sheet_type] = None

        return mapped_data

    def _clean_dataframe(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Clean DataFrame based on sheet type"""

        # Remove completely empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all")

        # Keep original column names for proper mapping

        # Remove leading and trailing whitespace from string columns
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip()
            # Replace 'nan' with NaN
            df[col] = df[col].replace("nan", pd.NA)

        logger.info(
            f"Cleaned {sheet_type} sheet with {df.shape[0]} rows and {df.shape[1]} columns"
        )
        logger.info(f"Columns: {list(df.columns)}")

        return df
