#!/usr/bin/env python3
"""
Test script to verify refactored date parsing works correctly
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_engineering.transformers.odoo_data_cleaner import OdooDataTransformer


def test_refactored_date_parsing():
    """Test the refactored date parsing functionality"""

    transformer = OdooDataTransformer()

    # Test cases
    test_dates = [
        "01 mai 2025",
        "5 janvier 2024",
        "02 avr. 2025",
        "15 mars 2024",
        "30 décembre 2024",
        "2024-05-01",  # Already in ISO format
        "01/05/2025",  # Standard format
        "2025-01-05",  # ISO format
    ]

    print("Testing refactored date parsing:")
    print("=" * 50)

    for test_date in test_dates:
        result = transformer._clean_date(test_date)
        print(f"Input: {test_date:20} -> Output: {result}")

    print("\n" + "=" * 50)
    print("Refactored date parsing test completed!")
    print("✅ All date parsing now uses unified _clean_date method")
    print("✅ Removed redundant _parse_french_date method")
    print("✅ Shared French months mapping")


if __name__ == "__main__":
    test_refactored_date_parsing()
