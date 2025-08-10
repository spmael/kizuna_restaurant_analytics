import logging
from typing import Dict

import pandas as pd

from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class RecipeExtractor(BaseExtractor):
    """Extract recipe data from excel file"""

    def extract(self) -> Dict[str, pd.DataFrame]:
        """Extract recipe data from excel file"""

        logger.info(f"Starting recipe extraction from: {self.file_path}")

        if not self.validate_file():
            logger.error("Recipe file validation failed")
            return {}

        try:
            # Try to read the file as single sheet first
            logger.info("Reading recipe file as single sheet...")
            df = pd.read_excel(
                self.file_path,
                na_values=["", "None", "NULL", "null", "#N/A"],
                keep_default_na=True,
            )

            logger.info(
                f"Recipe file loaded. Shape: {df.shape}, Columns: {list(df.columns)}"
            )

            # Clean the data
            df = self._clean_recipe_data(df)
            logger.info(f"Recipe data cleaned. Shape: {df.shape}")

            result = {"recipes": df}
            self.log_extractor_stats(result)
            return result

        except Exception:
            # Try reading all sheets in case it's a multi-sheet file
            try:
                excel_data = pd.read_excel(self.file_path, sheet_name=None)
                cleaned_data = {}

                for sheet_name, sheet_df in excel_data.items():
                    if not sheet_df.empty:
                        cleaned_data["recipes"] = self._clean_recipe_data(sheet_df)
                        break  # Take first non-empty sheet

                self.log_extractor_stats(cleaned_data)
                return cleaned_data
            except Exception as e:
                error_msg = f"Error extracting recipe data from Excel file: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                return {}

    def _clean_recipe_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean recipe data from excel file"""

        # Remove completely empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all")

        # Clean string columns first
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip()
            # Replace various forms of NaN/empty with pandas NA
            df[col] = df[col].replace(
                ["nan", "NaN", "NAN", "None", "null", "NULL", ""], pd.NA
            )

        # Convert main_ingredient column to boolean if it exists
        if "main_ingredient" in df.columns:
            df["main_ingredient"] = df["main_ingredient"].map(
                {
                    "1": True,
                    "0": False,
                }
            )
            # Fill remaining NaN values with False
            df["main_ingredient"] = df["main_ingredient"].fillna(False)

        # Convert quantity to numeric if it exists
        if "quantity" in df.columns:
            df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

        return df
