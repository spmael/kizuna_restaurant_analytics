import logging
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from apps.restaurant_data.models import Product, UnitOfMeasure

logger = logging.getLogger(__name__)


class ConversionFixer:
    """Utility to detect and fix large quantity conversion errors during transformation"""

    def __init__(self):
        # Threshold for detecting conversion errors
        self.large_quantity_threshold = (
            50000  # Quantities above this are suspicious for "unit"
        )

        # Known conversion patterns (based on analysis)
        self.conversion_patterns = {
            # Pattern: large quantity in "unit" → likely kg conversion error
            "kg_to_unit_error": {
                "detection": lambda qty, unit: qty > self.large_quantity_threshold
                and unit == "unit",
                "correction_factor": 1000000,  # Divide by 1M to get back to kg
                "correct_unit": "kg",
                "description": "kg amount converted to grams then multiplied again",
            },
            # Pattern: medium quantity in "unit" → likely g conversion error
            "g_to_unit_error": {
                "detection": lambda qty, unit: 1000
                < qty
                < self.large_quantity_threshold
                and unit == "unit",
                "correction_factor": 1000,  # Divide by 1K to get back to g
                "correct_unit": "g",
                "description": "gram amount mistakenly treated as unit",
            },
            # Pattern: very large quantity in "unit" → likely ml conversion error
            "ml_to_unit_error": {
                "detection": lambda qty, unit: qty > 1000000 and unit == "unit",
                "correction_factor": 1000000,  # Divide by 1M to get back to ml
                "correct_unit": "ml",
                "description": "ml amount mistakenly treated as unit",
            },
            # Pattern: large quantity in "g" → likely kg conversion error
            "kg_to_g_error": {
                "detection": lambda qty, unit: qty > 10000 and unit == "g",
                "correction_factor": 1000,  # Divide by 1K to get back to kg
                "correct_unit": "kg",
                "description": "kg amount mistakenly treated as grams",
            },
        }

        self.fixes_applied = 0
        self.fixes_log = []

    def fix_purchases_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix conversion errors in purchases data"""

        if df is None or df.empty:
            return df

        logger.info(
            f"Starting conversion fixing for purchases data with {len(df)} records"
        )

        # Reset counters
        self.fixes_applied = 0
        self.fixes_log = []

        # Create a copy to avoid modifying original
        fixed_df = df.copy()

        # Apply fixes to each row
        for idx, row in fixed_df.iterrows():
            try:
                quantity = row.get("quantity_purchased", 0)
                product = row.get("product", "Unknown")

                # Check for conversion errors (without relying on unit_of_measure)
                fix_result = self._check_and_fix_conversion_large_quantities(
                    quantity, product, idx + 1
                )

                if fix_result:
                    corrected_qty, corrected_unit, pattern_name = fix_result

                    # Apply the fix to the DataFrame
                    fixed_df.at[idx, "quantity_purchased"] = corrected_qty

                    # Update the product's unit of measure in the database
                    self._update_product_unit_of_measure(product, corrected_unit)

                    self.fixes_applied += 1
                    self.fixes_log.append(
                        {
                            "row": idx + 1,
                            "product": product,
                            "original_quantity": quantity,
                            "corrected_quantity": corrected_qty,
                            "corrected_unit": corrected_unit,
                            "pattern": pattern_name,
                        }
                    )

            except Exception as e:
                logger.warning(f"Error fixing conversion for row {idx + 1}: {str(e)}")

        logger.info(f"Conversion fixing completed. Applied {self.fixes_applied} fixes.")

        if self.fixes_applied > 0:
            logger.info("Fixes applied:")
            for fix in self.fixes_log[:10]:  # Log first 10 fixes
                logger.info(
                    f"  Row {fix['row']}: {fix['product']} - "
                    f"{fix['original_quantity']} → {fix['corrected_quantity']} {fix['corrected_unit']} "
                    f"({fix['pattern']})"
                )
            if len(self.fixes_log) > 10:
                logger.info(f"  ... and {len(self.fixes_log) - 10} more fixes")

        return fixed_df

    def _check_and_fix_conversion_large_quantities(
        self, quantity: float, product: str, row_num: int
    ) -> Optional[Tuple[float, str, str]]:
        """Check if a large quantity needs fixing and return the correction"""

        # Skip if quantity is not numeric or is zero/negative
        if pd.isna(quantity) or quantity <= 0:
            return None

        # Define large quantity thresholds for different types of errors
        if quantity > 1000000:  # Very large quantities (like 4,000,000)
            # Likely kg → unit conversion error (divide by 1M)
            corrected_qty = quantity / 1000000
            corrected_unit = "kg"
            pattern_name = "kg_to_unit_error"
            logger.info(
                f"Row {row_num}: Detected kg_to_unit_error for {product} - "
                f"{quantity} → {corrected_qty} {corrected_unit}"
            )
            return corrected_qty, corrected_unit, pattern_name

        elif quantity > 100000:  # Large quantities (like 274,000)
            # Likely g → unit conversion error (divide by 1K)
            corrected_qty = quantity / 1000
            corrected_unit = "g"
            pattern_name = "g_to_unit_error"
            logger.info(
                f"Row {row_num}: Detected g_to_unit_error for {product} - "
                f"{quantity} → {corrected_qty} {corrected_unit}"
            )
            return corrected_qty, corrected_unit, pattern_name

        elif quantity > 10000:  # Medium-large quantities
            # Likely kg → g conversion error (divide by 1K)
            corrected_qty = quantity / 1000
            corrected_unit = "kg"
            pattern_name = "kg_to_g_error"
            logger.info(
                f"Row {row_num}: Detected kg_to_g_error for {product} - "
                f"{quantity} → {corrected_qty} {corrected_unit}"
            )
            return corrected_qty, corrected_unit, pattern_name

        return None

    def _update_product_unit_of_measure(self, product_name: str, correct_unit: str):
        """Update the product's unit of measure in the database"""
        try:
            # Find the product by name (case-insensitive)
            product = Product.objects.filter(name__iexact=product_name).first()
            if product:
                # Get or create the correct unit of measure
                unit_of_measure, created = UnitOfMeasure.objects.get_or_create(
                    name=correct_unit,
                    defaults={"description": f"Unit: {correct_unit}"}
                )
                
                # Update the product's unit of measure
                old_unit = product.unit_of_measure.name if product.unit_of_measure else "None"
                product.unit_of_measure = unit_of_measure
                product.save()
                
                logger.info(
                    f"Updated product '{product_name}' unit of measure: "
                    f"{old_unit} → {correct_unit}"
                )
            else:
                logger.warning(f"Product '{product_name}' not found in database")
                
        except Exception as e:
            logger.error(f"Error updating unit of measure for product '{product_name}': {str(e)}")

    def get_fixes_summary(self) -> Dict[str, Any]:
        """Get a summary of all fixes applied"""
        return {
            "total_fixes": self.fixes_applied,
            "fixes_log": self.fixes_log,
            "patterns_found": self._get_pattern_summary(),
        }

    def _get_pattern_summary(self) -> Dict[str, int]:
        """Get summary of which patterns were found"""
        pattern_counts = {}
        for fix in self.fixes_log:
            pattern = fix["pattern"]
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        return pattern_counts

    def reset_counters(self):
        """Reset fix counters and logs"""
        self.fixes_applied = 0
        self.fixes_log = []
