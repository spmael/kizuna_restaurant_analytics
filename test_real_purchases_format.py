import os

# Import the ConversionFixer directly (without Django models)
import sys

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "data_engineering", "utils"))


# Create a mock ConversionFixer that doesn't depend on Django models
class MockConversionFixer:
    def __init__(self):
        self.fixes_applied = 0
        self.fixes_log = []
        self.patterns_found = {}

    def fix_purchases_data(self, df):
        """Fix conversion errors in purchases data"""
        fixed_df = df.copy()

        for idx, row in fixed_df.iterrows():
            try:
                quantity = row.get("quantity_purchased", 0)
                product_name = row.get("product", "Unknown")

                # Check for conversion errors
                fix_result = self._check_and_fix_conversion_large_quantities(
                    quantity, product_name, idx + 1
                )

                if fix_result:
                    corrected_qty, corrected_unit, pattern_name = fix_result

                    # Apply the fix to the DataFrame
                    fixed_df.at[idx, "quantity_purchased"] = corrected_qty

                    self.fixes_applied += 1
                    self.fixes_log.append(
                        {
                            "row": idx + 1,
                            "product": product_name,
                            "original_quantity": quantity,
                            "corrected_quantity": corrected_qty,
                            "corrected_unit": corrected_unit,
                            "pattern": pattern_name,
                        }
                    )

                    # Track patterns
                    if pattern_name not in self.patterns_found:
                        self.patterns_found[pattern_name] = 0
                    self.patterns_found[pattern_name] += 1

            except Exception as e:
                print(f"Error fixing row {idx + 1}: {str(e)}")

        return fixed_df

    def _check_and_fix_conversion_large_quantities(self, quantity, product, row_num):
        """Check if a large quantity needs fixing and return the correction"""
        if quantity > 1000000:
            corrected_qty = quantity / 1000000
            corrected_unit = "kg"
            pattern_name = "kg_to_unit_error"
            print(
                f"Row {row_num}: Detected kg_to_unit_error for {product} - {quantity} → {corrected_qty} {corrected_unit}"
            )
            return corrected_qty, corrected_unit, pattern_name

        elif quantity > 100000:
            corrected_qty = quantity / 1000
            corrected_unit = "g"
            pattern_name = "g_to_unit_error"
            print(
                f"Row {row_num}: Detected g_to_unit_error for {product} - {quantity} → {corrected_qty} {corrected_unit}"
            )
            return corrected_qty, corrected_unit, pattern_name

        elif quantity > 10000:
            corrected_qty = quantity / 1000
            corrected_unit = "kg"
            pattern_name = "kg_to_g_error"
            print(
                f"Row {row_num}: Detected kg_to_g_error for {product} - {quantity} → {corrected_qty} {corrected_unit}"
            )
            return corrected_qty, corrected_unit, pattern_name

        return None

    def get_fixes_summary(self):
        return {
            "total_fixes": self.fixes_applied,
            "patterns_found": self.patterns_found,
            "fixes_log": self.fixes_log,
        }


def test_real_purchases_format():
    """Test the ConversionFixer with real purchases data format"""

    # Create sample data that matches your real format
    # This simulates the pivot table format from your Excel file
    test_data = {
        "Unnamed: 0": [
            "Ailes de Poulet au paprika",  # Product name
            "4 avril 2025",  # Date
            "Ailes de Poulet au paprika",  # Product name
            "27 avril 2025",  # Date
            "Saucisses de Bœuf",  # Product name
            "11 avril 2025",  # Date
            "Ailes de Poulet au paprika",  # Product name
            "25 avril 2025",  # Date
            "Ailes de Poulet au paprika",  # Product name
            "18 avril 2025",  # Date
        ],
        "Qté commandée": [
            None,  # No quantity for product name row
            4000000.0,  # Large quantity that should be fixed
            None,  # No quantity for product name row
            2740000.0,  # Large quantity that should be fixed
            None,  # No quantity for product name row
            2220000.0,  # Large quantity that should be fixed
            None,  # No quantity for product name row
            2120000.0,  # Large quantity that should be fixed
            None,  # No quantity for product name row
            2010000.0,  # Large quantity that should be fixed
        ],
        "Total": [
            None,  # No total for product name row
            11400.0,  # Total cost
            None,  # No total for product name row
            7809.0,  # Total cost
            None,  # No total for product name row
            10767.0,  # Total cost
            None,  # No total for product name row
            6042.0,  # Total cost
            None,  # No total for product name row
            5729.0,  # Total cost
        ],
    }

    # Create DataFrame
    df = pd.DataFrame(test_data)

    print("=== ORIGINAL PIVOT TABLE FORMAT ===")
    print(df)
    print()

    # Simulate the pivot-to-tabular conversion logic
    print("=== SIMULATING PIVOT TO TABULAR CONVERSION ===")

    # French month mapping
    french_months = {
        "janvier": "01",
        "janv.": "01",
        "février": "02",
        "févr.": "02",
        "fevrier": "02",
        "fevr.": "02",
        "mars": "03",
        "avril": "04",
        "avr.": "04",
        "mai": "05",
        "juin": "06",
        "juillet": "07",
        "juil.": "07",
        "août": "08",
        "aout": "08",
        "septembre": "09",
        "sept.": "09",
        "octobre": "10",
        "oct.": "10",
        "novembre": "11",
        "nov.": "11",
        "décembre": "12",
        "dec.": "12",
        "déc.": "12",
    }

    def is_date_string(text, french_months):
        """Check if a string represents a French date"""
        if pd.isna(text):
            return False

        text = str(text).strip()

        for month_abbr in french_months.keys():
            if month_abbr in text and any(char.isdigit() for char in text):
                parts = text.split()
                if len(parts) == 3:
                    if (
                        parts[0].isdigit()
                        and parts[1] == month_abbr
                        and len(parts[2]) == 4
                        and parts[2].isdigit()
                    ):
                        return True
        return False

    def clean_date(value):
        """Clean and convert value to date"""
        if pd.isna(value):
            return None

        try:
            date_str = str(value).strip()

            for month_name, month_num in french_months.items():
                if month_name in date_str.lower():
                    parts = date_str.split()
                    if len(parts) >= 3:
                        day = parts[0]
                        year = parts[-1]

                        if len(year) == 4 and 2020 <= int(year) <= 2030:
                            return f"{year}-{month_num}-{day.zfill(2)}"

            return None
        except:
            return None

    # Convert pivot to tabular
    result_rows = []
    current_product = None

    for idx, row in df.iterrows():
        unnamed_col = row["Unnamed: 0"]
        qte = row["Qté commandée"]
        total = row["Total"]

        if pd.isna(unnamed_col) or str(unnamed_col).strip() == "":
            continue

        if not is_date_string(unnamed_col, french_months):
            # This is a product name
            current_product = str(unnamed_col).strip()
        else:
            # This is a date row, create a purchase record
            if current_product is not None and current_product != "":
                purchase_date = clean_date(unnamed_col)

                if purchase_date is not None:
                    if not pd.isna(qte) and not pd.isna(total):
                        result_rows.append(
                            {
                                "purchase_date": purchase_date,
                                "product": current_product,
                                "quantity_purchased": qte,
                                "total_cost": total,
                            }
                        )

    # Create the result DataFrame
    if result_rows:
        result_df = pd.DataFrame(result_rows)

        print("=== CONVERTED TABULAR FORMAT ===")
        print(result_df)
        print()

        # Apply conversion fixes
        print("=== APPLYING CONVERSION FIXES ===")
        conversion_fixer = MockConversionFixer()
        fixed_df = conversion_fixer.fix_purchases_data(result_df)

        print("=== CONVERSION FIXER SUMMARY ===")
        fix_summary = conversion_fixer.get_fixes_summary()
        print(f"Total fixes applied: {fix_summary['total_fixes']}")
        for pattern, count in fix_summary["patterns_found"].items():
            print(f"  {pattern}: {count} fixes")
        print()

        print("=== SAMPLE FIXED QUANTITIES ===")
        for idx, row in fixed_df.head().iterrows():
            original_qty = result_df.iloc[idx]["quantity_purchased"]
            fixed_qty = row["quantity_purchased"]
            print(
                f"Row {idx + 1}: {row['product']} - {fixed_qty} (was {original_qty:,.0f})"
            )

        return fixed_df
    else:
        print("❌ No data was converted - check the pivot conversion logic")
        return pd.DataFrame()


if __name__ == "__main__":
    test_real_purchases_format()
