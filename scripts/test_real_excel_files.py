#!/usr/bin/env python3
"""
Test script for loading real Excel files with Odoo Extractor
This script allows you to test the extractor with your actual Excel files.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_engineering.extractors.odoo_extractor import OdooExtractor
from data_engineering.extractors.recipe_extractor import RecipeExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def analyze_excel_file(file_path: str):
    """
    Analyze the structure of an Excel file before extraction
    """
    print(f"\n{'='*80}")
    print("ANALYZING EXCEL FILE")
    print(f"File: {file_path}")
    print(f"{'='*80}")

    try:
        # Read all sheets without processing
        excel_data = pd.read_excel(file_path, sheet_name=None)

        print(f"📊 Found {len(excel_data)} sheets:")
        for sheet_name, df in excel_data.items():
            print(f"  📋 '{sheet_name}': {df.shape[0]} rows × {df.shape[1]} columns")

            # Show column names
            print(f"     Columns: {list(df.columns)}")

            # Show first few rows
            if not df.empty:
                print(f"     First row sample: {df.iloc[0].to_dict()}")
            print()

        return excel_data

    except Exception as e:
        print(f"❌ Error analyzing file: {str(e)}")
        return None


def display_dataframe_info(df: pd.DataFrame, sheet_name: str):
    """
    Display comprehensive information about a dataframe
    """
    print(f"\n{'='*60}")
    print(f"SHEET: {sheet_name.upper()}")
    print(f"{'='*60}")

    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")

    print(f"\nColumns ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")

    print("\nData Types:")
    for col, dtype in df.dtypes.items():
        print(f"  {col}: {dtype}")

    print("\nMissing Values:")
    missing_counts = df.isnull().sum()
    if missing_counts.sum() > 0:
        for col, count in missing_counts[missing_counts > 0].items():
            print(f"  {col}: {count} ({count/len(df)*100:.1f}%)")
    else:
        print("  No missing values found")

    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))

    if len(df) > 5:
        print("\nLast 5 rows:")
        print(df.tail().to_string(index=False))

    # Show summary statistics for numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        print("\nNumeric Summary Statistics:")
        print(df[numeric_cols].describe().to_string())

    # Show value counts for categorical columns (first 10 unique values)
    categorical_cols = df.select_dtypes(include=["object"]).columns
    if len(categorical_cols) > 0:
        print("\nCategorical Value Counts (top 10):")
        for col in categorical_cols[:3]:  # Limit to first 3 categorical columns
            if (
                df[col].nunique() <= 20
            ):  # Only show if reasonable number of unique values
                print(f"\n{col}:")
                value_counts = df[col].value_counts().head(10)
                for value, count in value_counts.items():
                    print(f"  {value}: {count}")


def test_odoo_extractor(file_path: str):
    """
    Test the OdooExtractor with the given file
    """
    print(f"\n{'='*80}")
    print("TESTING ODOO EXTRACTOR")
    print(f"File: {file_path}")
    print(f"{'='*80}")

    try:
        # Initialize the extractor
        extractor = OdooExtractor(file_path)

        # Extract data
        print("\nExtracting data...")
        extracted_data = extractor.extract()

        if not extracted_data:
            print("❌ No data extracted!")
            if extractor.errors:
                print("Errors encountered:")
                for error in extractor.errors:
                    print(f"  - {error}")
            return

        print(f"✅ Successfully extracted {len(extracted_data)} sheets")

        # Display each dataframe
        for sheet_name, df in extracted_data.items():
            if df is not None and not df.empty:
                display_dataframe_info(df, sheet_name)
            else:
                print(f"\nSheet '{sheet_name}': Empty or None")

        # Display extractor statistics
        print(f"\n{'='*60}")
        print("EXTRACTOR STATISTICS")
        print(f"{'='*60}")
        total_rows = sum(len(df) for df in extracted_data.values() if df is not None)
        print(f"Total rows extracted: {total_rows}")
        print(f"Total sheets: {len(extracted_data)}")

        if extractor.errors:
            print(f"\nErrors: {len(extractor.errors)}")
            for error in extractor.errors:
                print(f"  - {error}")

        return extracted_data

    except Exception as e:
        print(f"❌ Error testing Odoo extractor: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def test_recipe_extractor(file_path: str):
    """
    Test the RecipeExtractor with the given file
    """
    print(f"\n{'='*80}")
    print("TESTING RECIPE EXTRACTOR")
    print(f"File: {file_path}")
    print(f"{'='*80}")

    try:
        # Initialize the extractor
        extractor = RecipeExtractor(file_path)

        # Extract data
        print("\nExtracting recipe data...")
        extracted_data = extractor.extract()

        if not extracted_data:
            print("❌ No data extracted!")
            if extractor.errors:
                print("Errors encountered:")
                for error in extractor.errors:
                    print(f"  - {error}")
            return

        print(f"✅ Successfully extracted {len(extracted_data)} recipe sheets")

        # Display each dataframe
        for sheet_name, df in extracted_data.items():
            if df is not None and not df.empty:
                display_dataframe_info(df, sheet_name)
            else:
                print(f"\nSheet '{sheet_name}': Empty or None")

        # Display extractor statistics
        print(f"\n{'='*60}")
        print("RECIPE EXTRACTOR STATISTICS")
        print(f"{'='*60}")
        total_rows = sum(len(df) for df in extracted_data.values() if df is not None)
        print(f"Total rows extracted: {total_rows}")
        print(f"Total sheets: {len(extracted_data)}")

        if extractor.errors:
            print(f"\nErrors: {len(extractor.errors)}")
            for error in extractor.errors:
                print(f"  - {error}")

        return extracted_data

    except Exception as e:
        print(f"❌ Error testing Recipe extractor: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def save_extracted_data(extracted_data: dict, output_dir: str, file_prefix: str):
    """
    Save extracted dataframes to CSV files for further analysis
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Saving extracted data to: {output_path}")

    for sheet_name, df in extracted_data.items():
        if df is not None and not df.empty:
            csv_file = output_path / f"{file_prefix}_{sheet_name}.csv"
            df.to_csv(csv_file, index=False)
            print(f"  ✅ Saved {sheet_name}: {csv_file}")


def main():
    """
    Main function to run the tests with real Excel files
    """
    parser = argparse.ArgumentParser(
        description="Test Odoo Extractor with real Excel files"
    )
    parser.add_argument("--odoo-file", help="Path to Odoo Excel file")
    parser.add_argument("--recipe-file", help="Path to Recipe Excel file")
    parser.add_argument(
        "--output-dir",
        default="data/extracted",
        help="Output directory for extracted data",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze file structure without extraction",
    )
    parser.add_argument(
        "--save-csv", action="store_true", help="Save extracted data to CSV files"
    )

    args = parser.parse_args()

    print("🧪 REAL EXCEL FILES TEST SCRIPT")
    print("=" * 50)

    # Test Odoo file if provided
    if args.odoo_file:
        if os.path.exists(args.odoo_file):
            print(f"\n📁 Testing Odoo file: {args.odoo_file}")

            # Analyze file structure
            analyze_excel_file(args.odoo_file)

            if not args.analyze_only:
                # Test extraction
                extracted_data = test_odoo_extractor(args.odoo_file)

                # Save to CSV if requested
                if args.save_csv and extracted_data:
                    save_extracted_data(extracted_data, args.output_dir, "odoo")
        else:
            print(f"❌ Odoo file not found: {args.odoo_file}")

    # Test Recipe file if provided
    if args.recipe_file:
        if os.path.exists(args.recipe_file):
            print(f"\n📁 Testing Recipe file: {args.recipe_file}")

            # Analyze file structure
            analyze_excel_file(args.recipe_file)

            if not args.analyze_only:
                # Test extraction
                extracted_data = test_recipe_extractor(args.recipe_file)

                # Save to CSV if requested
                if args.save_csv and extracted_data:
                    save_extracted_data(extracted_data, args.output_dir, "recipe")
        else:
            print(f"❌ Recipe file not found: {args.recipe_file}")

    # If no files provided, show usage
    if not args.odoo_file and not args.recipe_file:
        print("\n📋 Usage Examples:")
        print(
            "  python scripts/test_real_excel_files.py --odoo-file /path/to/odoo.xlsx"
        )
        print(
            "  python scripts/test_real_excel_files.py --recipe-file /path/to/recipes.xlsx"
        )
        print(
            "  python scripts/test_real_excel_files.py --odoo-file /path/to/odoo.xlsx --recipe-file /path/to/recipes.xlsx"
        )
        print(
            "  python scripts/test_real_excel_files.py --odoo-file /path/to/odoo.xlsx --analyze-only"
        )
        print(
            "  python scripts/test_real_excel_files.py --odoo-file /path/to/odoo.xlsx --save-csv"
        )
        print("\n📋 Options:")
        print("  --odoo-file: Path to Odoo Excel file")
        print("  --recipe-file: Path to Recipe Excel file")
        print(
            "  --output-dir: Output directory for extracted data (default: data/extracted)"
        )
        print("  --analyze-only: Only analyze file structure without extraction")
        print("  --save-csv: Save extracted data to CSV files")

    print(f"\n{'='*80}")
    print("TEST COMPLETED")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
