import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict

import pandas as pd

# from ..utils.conversion_fixer import ConversionFixer
from .base_transformer import BaseTransformer


class OdooDataTransformer(BaseTransformer):
    """Transform and clean Odoo data for restaurant analytics including recipes"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize conversion fixer
        # self.conversion_fixer = ConversionFixer()

        # Column mappings for different language and format
        self.column_mappings = {
            "products": {
                "name": ["Nom"],
                "purchase_category": ["Catégorie de produits"],
                "sales_category": ["Catégorie du point de vente"],
                "unit_of_measure": ["Unité"],
                "current_selling_price": ["Prix de vente"],
                "current_cost_per_unit": ["Coût"],
                "current_stock": ["Quantité en stock"],
                "favorite": ["Favori"],
                "variant_values": ["Valeurs de la variante"],
            },
            "purchases": {
                "purchase_date": ["purchase_date"],
                "product": ["product"],
                "quantity_purchased": ["quantité_commandée"],
                "total_cost": ["total"],
            },
            "sales": {
                "sale_date": ["Date de la commande"],
                "order_number": ["Commander"],
                "product": ["Variante de produit"],
                "quantity_sold": ["Qté commandée"],
                "unit_sale_price": ["Prix unitaire"],
                "total_sale_price": ["Total"],
                "customer": ["Client"],
                "cashier": ["Vendeur"],
            },
            "recipes": {
                "dish_name": ["Plat", "Dish"],
                "ingredient": ["Ingrédient", "Ingredient"],
                "quantity": ["Quantité", "Quantity"],
                "main_ingredient": ["Principal", "Main"],
                "unit_of_recipe": ["Unité", "Unit"],
            },
        }

    def transform(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transform and clean all sheets"""

        # Initialize empty dictionaries for transformed data
        transformed_data = {}

        # Process each sheet type
        for sheet_type, df in data.items():
            if df is not None and not df.empty:
                try:
                    transformed_df = self._transform_sheet(df, sheet_type)
                    if transformed_df is not None and not transformed_df.empty:
                        transformed_data[sheet_type] = transformed_df
                except Exception as e:
                    error_msg = f"Error transforming {sheet_type} sheet: {str(e)}"
                    self.errors.append(error_msg)

        return transformed_data

    def _transform_sheet(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Transform individual sheet"""

        if sheet_type == "products":
            return self._transform_products(df)
        elif sheet_type == "purchases":
            return self._transform_purchases(df)
        elif sheet_type == "sales":
            return self._transform_sales(df)
        elif sheet_type == "recipes":
            return self._transform_recipes(df)
        else:
            self.log_warning(f"Unknown sheet type: {sheet_type}")
            return df

    def _transform_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform products sheet"""

        # Log initial state
        self.log_info(
            f"Products transformation started. Initial DataFrame shape: {df.shape}"
        )
        self.log_info(f"Initial columns: {list(df.columns)}")

        # Rename columns
        df = self._map_columns(df, "products")
        self.log_info(f"After column mapping: {list(df.columns)}")

        # Ensure all required columns are present with defaults
        required_columns = [
            "name",
            "purchase_category",
            "sales_category",
            "unit_of_measure",
            "current_selling_price",
            "current_cost_per_unit",
            "current_stock",
        ]

        # Add missing columns with defaults
        for col in required_columns:
            if col not in df.columns:
                if col == "purchase_category" or col == "sales_category":
                    df[col] = "Unknown"
                elif col == "unit_of_measure":
                    df[col] = "unit"
                elif col == "current_selling_price" or col == "current_cost_per_unit":
                    df[col] = 0.0
                elif col == "current_stock":
                    df[col] = 0
                elif col == "name":
                    # Generate names for rows without names
                    df[col] = df.apply(
                        lambda row, idx=df.index: (
                            f"Product {idx + 1}"
                            if pd.isna(row.get("name", ""))
                            or str(row.get("name", "")).strip() == ""
                            else str(row.get("name", "")).strip()
                        ),
                        axis=1,
                    )
                self.log_info(f"Added missing column '{col}' with default values")

        # Combine name (formerly nom) with variant_values to create a formatted product name
        if "variant_values" in df.columns:
            df["name"] = df.apply(
                lambda row: self._combine_nom_with_variant(
                    row["name"], row["variant_values"]
                ),
                axis=1,
            )
            self.log_info("Applied name and variant combination")

        self.log_info(
            f"All required columns present. DataFrame shape before cleaning: {df.shape}"
        )

        self.log_info(
            f"All required columns present. DataFrame shape before cleaning: {df.shape}"
        )

        transformed_df = df.copy()

        # Clean and validate data
        for idx, row in transformed_df.iterrows():
            try:
                # Clean product name
                if pd.isna(row["name"]) or str(row["name"]).strip() == "":
                    self.log_warning(
                        f"Empty product name at row {idx + 1}, setting to 'Unknown Product'"
                    )
                    transformed_df.at[idx, "name"] = f"Unknown Product {idx + 1}"
                else:
                    transformed_df.at[idx, "name"] = str(row["name"]).strip()

                # Clean cost per unit
                cost_per_unit = self._clean_decimal(row["current_cost_per_unit"])
                if cost_per_unit is None:
                    cost_per_unit = 0
                elif cost_per_unit < 0:
                    self.log_warning(
                        f"Negative cost for product {row['name']}: {row['current_cost_per_unit']}, setting to 0",
                        idx + 1,
                    )
                    cost_per_unit = 0

                transformed_df.at[idx, "current_cost_per_unit"] = float(cost_per_unit)

                # Clean selling price
                selling_price = self._clean_decimal(row["current_selling_price"])
                if selling_price is None:
                    selling_price = 0
                elif selling_price < 0:
                    self.log_warning(
                        f"Negative selling price for product {row['name']}: {row['current_selling_price']}, setting to 0",
                        idx + 1,
                    )
                    selling_price = 0

                transformed_df.at[idx, "current_selling_price"] = float(selling_price)

                # Set default purchase category if missing
                if (
                    pd.isna(row["purchase_category"])
                    or str(row["purchase_category"]).strip() == ""
                ):
                    transformed_df.at[idx, "purchase_category"] = "Unknown"

                # Set default sales category if missing
                if (
                    pd.isna(row["sales_category"])
                    or str(row["sales_category"]).strip() == ""
                ):
                    transformed_df.at[idx, "sales_category"] = "Unknown"

                # Clean unit of measure
                unit_of_measure = self._standardize_unit_of_measure(
                    row["unit_of_measure"]
                )
                if unit_of_measure is None:
                    unit_of_measure = "unit"

                transformed_df.at[idx, "unit_of_measure"] = unit_of_measure

                # Clean current stock
                current_stock = self._clean_decimal(row["current_stock"])
                if current_stock is None:
                    current_stock = 0

                transformed_df.at[idx, "current_stock"] = int(current_stock)

            except Exception as e:
                self.log_warning(
                    f"Error processing product row {idx + 1}: {str(e)}, continuing with defaults"
                )
                # Set defaults for this row instead of skipping
                transformed_df.at[idx, "current_cost_per_unit"] = 0.0
                transformed_df.at[idx, "current_selling_price"] = 0.0
                transformed_df.at[idx, "current_stock"] = 0
                transformed_df.at[idx, "unit_of_measure"] = "unit"

        # Final DataFrame with only required columns
        transformed_df = transformed_df[required_columns]

        self.log_info(
            f"Products transformation completed. Final DataFrame shape: {transformed_df.shape}"
        )
        self.log_info(f"Final columns: {list(transformed_df.columns)}")

        return transformed_df

    def _transform_purchases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform purchases sheet from pivot table format to tabular format"""

        self.log_info(f"Starting purchases transformation. DataFrame shape: {df.shape}")
        self.log_info(f"Purchases columns: {list(df.columns)}")
        self.log_info(f"Number of columns: {len(df.columns)}")
        self.log_info(f"Has 'Unnamed: 0' column: {'Unnamed: 0' in df.columns}")

        # Check if this is a pivot table format (first column contains product names and dates)
        if len(df.columns) == 3 and "Unnamed: 0" in df.columns:
            self.log_info("Detected pivot table format, converting to tabular...")
            return self._convert_pivot_to_tabular(df)
        else:
            self.log_info("Detected tabular format, cleaning data directly...")
            self.log_info(
                f"Pivot detection failed: expected 3 columns, got {len(df.columns)}"
            )
            self.log_info(
                f"Expected 'Unnamed: 0' column, found columns: {list(df.columns)}"
            )

        # If it's already in tabular format, just clean the data
        df = self._map_columns(df, "purchases")

        required_columns = [
            "purchase_date",
            "product",
            "quantity_purchased",
            "total_cost",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.log_warning(
                f"Missing required columns for purchases: {missing_columns}"
            )
            return pd.DataFrame()

        transformed_df = df.copy()

        # Clean and validate data
        for idx, row in df.iterrows():
            try:
                # Clean purchase date
                purchase_date = self._clean_date(row["purchase_date"])
                if purchase_date is None:
                    self.log_error(
                        f"Invalid purchase date: {row['purchase_date']}", idx + 1
                    )
                    continue

                transformed_df.at[idx, "purchase_date"] = purchase_date

                # Clean product
                product = self._clean_product_name(str(row["product"]).strip())
                if product == "":
                    self.log_error(f"Empty product at row {idx + 1}", idx + 1)
                    continue

                transformed_df.at[idx, "product"] = product

                # Clean quantity
                quantity = self._clean_decimal(row["quantity_purchased"])
                if quantity is None:
                    self.log_error(
                        f"Invalid quantity: {row['quantity_purchased']}", idx + 1
                    )
                    continue

                transformed_df.at[idx, "quantity_purchased"] = int(quantity)

                # Clean total
                total = self._clean_decimal(row["total_cost"])
                if total is None:
                    self.log_error(f"Invalid total cost: {row['total_cost']}", idx + 1)
                    continue

                transformed_df.at[idx, "total_cost"] = int(total)

            except Exception as e:
                self.log_error(
                    f"Error processing purchases row {idx + 1}: {str(e)}", idx + 1
                )
                continue

        # Apply conversion fixer if needed (disabled)
        # transformed_df = self.conversion_fixer.fix_purchases_data(transformed_df)
        # fix_summary = self.conversion_fixer.get_fixes_summary()

        return transformed_df

    def _convert_pivot_to_tabular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert pivot format purchases to tabular with columns purchase_date, product, quantity_purchased, total_cost"""

        # French month abbreviations mapping (shared with _clean_date)
        french_months = self._get_french_months_mapping()

        result_rows = []
        current_product = None

        for idx, row in df.iterrows():
            unnamed_col = row["Unnamed: 0"]
            qte = row["Qté commandée"]
            total = row["Total"]

            # Skip rows with empty or invalid data
            if pd.isna(unnamed_col) or str(unnamed_col).strip() == "":
                continue

            # Check if this row contains a product name (not a date)
            if not self._is_date_string(unnamed_col, french_months):
                # This is a product name - update current product
                current_product = self._clean_product_name(str(unnamed_col).strip())
                # Don't create a record yet - wait for the date row
            else:
                # This is a date row, create a purchase record
                if current_product is not None and current_product != "":
                    # Parse the French date using the unified _clean_date method
                    purchase_date = self._clean_date(unnamed_col)

                    if purchase_date is not None:
                        # Only create record if we have valid quantity and total
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
            return self._clean_purchases_data(result_df)
        else:
            return pd.DataFrame()

    def _clean_purchases_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean the converted purchases data"""

        required_columns = [
            "purchase_date",
            "product",
            "quantity_purchased",
            "total_cost",
        ]

        # Ensure all required columns exist
        for col in required_columns:
            if col not in df.columns:
                df[col] = None

        # Clean and validate data
        cleaned_rows = []
        for idx, row in df.iterrows():
            try:
                # Clean purchase date
                purchase_date = self._clean_date(row["purchase_date"])
                if purchase_date is None:
                    self.log_error(
                        f"Invalid purchase date: {row['purchase_date']}", idx + 1
                    )
                    continue

                # Clean product
                product = self._clean_product_name(str(row["product"]).strip())
                if product == "":
                    self.log_error(f"Empty product at row {idx + 1}", idx + 1)
                    continue

                # Clean quantity
                quantity = self._clean_decimal(row["quantity_purchased"])
                if quantity is None:
                    self.log_error(
                        f"Invalid quantity: {row['quantity_purchased']}", idx + 1
                    )
                    continue

                # Clean total
                total = self._clean_decimal(row["total_cost"])
                if total is None:
                    self.log_error(f"Invalid total: {row['total_cost']}", idx + 1)
                    continue

                cleaned_rows.append(
                    {
                        "purchase_date": purchase_date,
                        "product": product,
                        "quantity_purchased": quantity,
                        "total_cost": total,
                    }
                )

            except Exception as e:
                self.log_error(
                    f"Error processing purchase row {idx + 1}: {str(e)}", idx + 1
                )

        result_df = pd.DataFrame(cleaned_rows)

        # Apply conversion fixes for large quantity issues
        if not result_df.empty:
            self.log_info(
                "Applying conversion fixes to purchases data (pivot conversion path)..."
            )
            self.log_info(
                f"Before conversion fix - Sample quantities: {result_df['quantity_purchased'].head().tolist()}"
            )

            # result_df = self.conversion_fixer.fix_purchases_data(result_df)

            # Log conversion fix summary
            # fix_summary = self.conversion_fixer.get_fixes_summary()
            # if fix_summary["total_fixes"] > 0:
            #     self.log_info(f"Applied {fix_summary['total_fixes']} conversion fixes")
            #     for pattern, count in fix_summary["patterns_found"].items():
            #         self.log_info(f"  {pattern}: {count} fixes")
            #     self.log_info(
            #         f"After conversion fix - Sample quantities: {result_df['quantity_purchased'].head().tolist()}"
            #     )
            # else:
            self.log_info("No conversion fixes were applied")
        else:
            self.log_info(
                "No purchases data to apply conversion fixes to (pivot conversion path)"
            )

        return result_df

    def _get_french_months_mapping(self) -> dict:
        """Get French month abbreviations mapping (shared across methods)"""
        return {
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

    def _is_date_string(self, text: str, french_months: dict) -> bool:
        """Check if a string represents a French date"""
        if pd.isna(text):
            return False

        text = str(text).strip()

        # Check for French date pattern: "30 avr. 2025" or "01 mai 2025"
        for month_abbr in french_months.keys():
            if month_abbr in text and any(char.isdigit() for char in text):
                # Additional validation: should have exactly 3 parts (day, month, year)
                parts = text.split()
                if len(parts) == 3:
                    # First part should be a number (day)
                    # Second part should be the month abbreviation
                    # Third part should be a 4-digit year
                    if (
                        parts[0].isdigit()
                        and parts[1] == month_abbr
                        and len(parts[2]) == 4
                        and parts[2].isdigit()
                    ):
                        return True

        return False

    def _transform_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform sales sheet"""

        # Rename columns
        df = self._map_columns(df, "sales")

        # Required columns check
        required_columns = [
            "sale_date",
            "order_number",
            "product",
            "quantity_sold",
            "unit_sale_price",
            "total_sale_price",
            "customer",
            "cashier",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.log_warning(f"Missing required columns for sales: {missing_columns}")
            return pd.DataFrame()

        transformed_df = df.copy()

        # Clean and validate data
        for idx, row in transformed_df.iterrows():
            try:
                # Clean sale date
                sale_date = self._clean_date(row["sale_date"])
                if sale_date is None:
                    self.log_error(f"Invalid date: {row['date']}", idx + 1)
                    continue

                transformed_df.at[idx, "sale_date"] = sale_date

                # Clean numeric fields
                quantity_sold = self._clean_decimal(row["quantity_sold"])
                if quantity_sold is None:
                    self.log_error(
                        f"Invalid quantity sold: {row['quantity_sold']}", idx + 1
                    )
                    continue

                transformed_df.at[idx, "quantity_sold"] = float(quantity_sold)

                unit_sale_price = self._clean_decimal(row["unit_sale_price"])
                if unit_sale_price is None or unit_sale_price <= 0:
                    self.log_error(
                        f"Invalid unit sale price: {row['unit_sale_price']}", idx + 1
                    )
                    continue

                transformed_df.at[idx, "unit_sale_price"] = float(unit_sale_price)

                # Calculate total sale price
                if "total_sale_price" not in df.columns or pd.isna(
                    row["total_sale_price"]
                ):
                    transformed_df.at[idx, "total_sale_price"] = float(
                        quantity_sold * unit_sale_price
                    )
                else:
                    total_sale_price = self._clean_decimal(row["total_sale_price"])
                    transformed_df.at[idx, "total_sale_price"] = float(
                        total_sale_price or quantity_sold * unit_sale_price
                    )

                # Clean order number
                order_number = str(row["order_number"]).strip()
                if order_number == "":
                    self.log_error(f"Empty order number at row {idx + 1}", idx + 1)

                transformed_df.at[idx, "order_number"] = order_number

                # Clean product
                product = str(row["product"]).strip()
                if product == "":
                    self.log_error(f"Empty product at row {idx + 1}", idx + 1)
                else:
                    # Clean product name by removing bracketed prefixes
                    product = self._clean_product_name(product)

                transformed_df.at[idx, "product"] = product

                # Clean customer
                customer = str(row["customer"]).strip()
                if (
                    customer == ""
                    or customer is None
                    or customer == "None"
                    or customer == "no name"
                ):
                    customer = "Walk-in Customer"

                transformed_df.at[idx, "customer"] = customer

                # Clean cashier
                cashier = str(row["cashier"]).strip()
                if cashier == "":
                    self.log_error(f"Empty cashier at row {idx + 1}", idx + 1)
                transformed_df.at[idx, "cashier"] = cashier

            except Exception as e:
                self.log_error(
                    f"Error processing sales row {idx + 1}: {str(e)}", idx + 1
                )

        # Final DataFrame with only required columns
        transformed_df = transformed_df[required_columns]

        return transformed_df

    def _map_columns(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Map DataFrames to standard column names"""

        if sheet_type not in self.column_mappings:
            return df

        # Get column mappings for this sheet
        mappings = self.column_mappings.get(sheet_type, {})

        # Create column mapping dictionary
        column_map = {}
        for standard_name, possible_names in mappings.items():
            for col in possible_names:
                if col in df.columns:
                    column_map[col] = standard_name
                    break

        # Rename columns
        if column_map:
            df = df.rename(columns=column_map)

        return df

    def _clean_decimal(self, value):
        """Clean and convert value to decimal"""

        if pd.isna(value):
            return None
        try:
            # Convert to string
            str_value = str(value).strip()

            # Remove non-numeric characters
            str_value = re.sub(r"[^0-9.]", "", str_value)

            # Handle different decimal separators
            str_value = str_value.replace(",", ".")

            # Remove extra dots (keep only the last one)
            parts = str_value.split(".")
            if len(parts) > 2:
                str_value = ".".join(parts[:-1]) + "." + parts[-1]

            return Decimal(str_value)

        except (InvalidOperation, ValueError):
            return None

    def _clean_date(self, value):
        """Clean and convert value to date"""

        if pd.isna(value):
            return None

        try:
            if isinstance(value, datetime):
                return value

            # Convert to string for processing
            date_str = str(value).strip()

            # Check if it's a French date format (e.g., "5 janvier 2024" or "01 mai 2025")
            french_months = self._get_french_months_mapping()

            # Try to parse French date format
            for month_name, month_num in french_months.items():
                if month_name in date_str.lower():
                    # Extract day, month, and year
                    parts = date_str.split()
                    if len(parts) >= 3:
                        day = parts[0]
                        year = parts[-1]  # Last part should be year

                        # Ensure year is 4 digits and reasonable
                        if len(year) == 4 and 2020 <= int(year) <= 2030:
                            # Format as ISO date
                            return f"{year}-{month_num}-{day.zfill(2)}"

            # If not French format, try standard pandas datetime parsing (without dayfirst=True)
            try:
                parsed_date = pd.to_datetime(value)
                return parsed_date.strftime("%Y-%m-%d")
            except Exception:
                pass

            # If all parsing attempts fail, log warning and return None
            self.log_warning(f"Could not parse date value: {value}")
            return None

        except (ValueError, TypeError) as e:
            self.log_warning(f"Invalid date value: {value} - Error: {str(e)}")
            return None

    def _standardize_unit_of_measure(self, value):
        """Standardize unit of measure"""

        if pd.isna(value):
            return None

        value_lower = value.lower().strip()

        # Unit mappings
        unit_mappings = {
            "unit": ["unit", "unité", "unité(s)", "unités"],
            "kg": ["kg", "kilo", "kilogram", "kilogramme"],
            "g": ["g", "gram", "gramme", "gr"],
            "l": ["l", "litre", "liter", "lt"],
            "ml": ["ml", "millilitre", "milliliter"],
            "pcs": ["pcs", "pieces", "pièces", "piece", "pièce"],
            "dozen": ["dozen", "douzaine", "dz"],
            "bottle": ["bottle", "bouteille", "btl"],
            "can": ["can", "boîte", "boite", "canette"],
            "pack": ["pack", "paquet", "packet"],
            "box": ["box", "caisse", "carton"],
            "botte": ["botte"],
            "lot": [
                "lot",
                "lot de 2",
                "lot de 3",
                "lot de 4",
                "lot de 5",
                "lot de 6",
                "lot de 7",
                "lot de 8",
                "lot de 9",
                "lot de 10",
            ],
        }

        for standard_unit, variations in unit_mappings.items():
            if value_lower in variations:
                return standard_unit

        return value_lower

    def _combine_nom_with_variant(self, nom: str, valeurs_de_la_variante: str) -> str:
        """
        Combine nom and valeurs_de_la_variante to create a formatted product name.

        Args:
            nom: The product name
            valeurs_de_la_variante: The variant values (e.g., "Morceaux: Entier")

        Returns:
            Combined name (e.g., "Dinde (Entier)" from nom="Dinde" and valeurs_de_la_variante="Morceaux: Entier")
        """
        if pd.isna(nom) or pd.isna(valeurs_de_la_variante):
            return nom if not pd.isna(nom) else ""

        nom = str(nom).strip()
        valeurs_de_la_variante = str(valeurs_de_la_variante).strip()

        if not valeurs_de_la_variante:
            return nom

        # Extract the part after ":" if it exists
        if ":" in valeurs_de_la_variante:
            variant_part = valeurs_de_la_variante.split(":", 1)[1].strip()
        else:
            variant_part = valeurs_de_la_variante

        if variant_part:
            return f"{nom} ({variant_part})"
        else:
            return nom

    def _clean_product_name(self, product_name: str) -> str:
        """Clean product name by removing bracketed prefixes like [TIPS], [SALARY], etc."""

        if pd.isna(product_name) or str(product_name).strip() == "":
            return ""

        product_name = str(product_name).strip()

        # Remove bracketed prefixes using regex
        # This will match patterns like [TIPS], [SALARY], [ANYTHING] at the beginning
        import re

        cleaned_name = re.sub(r"^\[[^\]]+\]\s*", "", product_name)

        return cleaned_name.strip()

    def _transform_recipes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform recipes sheet"""

        self.log_info(f"Starting recipes transformation. DataFrame shape: {df.shape}")
        self.log_info(f"Original columns: {list(df.columns)}")

        # Rename columns
        df = self._map_columns(df, "recipes")
        self.log_info(f"After column mapping: {list(df.columns)}")

        required_columns = [
            "dish_name",
            "ingredient",
            "quantity",
            "main_ingredient",
            "unit_of_recipe",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.log_warning(f"Missing required columns for recipes: {missing_columns}")
            self.log_warning(f"Available columns: {list(df.columns)}")
            return pd.DataFrame()

        transformed_df = df.copy()

        # Clean and validate data
        for idx, row in transformed_df.iterrows():
            try:
                # Clean dish name
                dish_name = str(row["dish_name"]).strip()

                if dish_name == "":
                    self.log_error(f"Empty dish name at row {idx + 1}", idx + 1)
                    continue

                transformed_df.at[idx, "dish_name"] = dish_name

                # Clean unit of recipe
                unit_of_recipe = str(row["unit_of_recipe"]).strip()

                if unit_of_recipe == "":
                    self.log_error(f"Empty unit of recipe at row {idx + 1}", idx + 1)
                    continue

                transformed_df.at[idx, "unit_of_recipe"] = unit_of_recipe

                # Clean ingredient
                ingredient = str(row["ingredient"]).strip()

                if ingredient == "":
                    self.log_error(f"Empty ingredient at row {idx + 1}", idx + 1)
                    continue

                transformed_df.at[idx, "ingredient"] = ingredient

                # Clean quantity
                quantity = self._clean_decimal(row["quantity"])

                if quantity is None:
                    self.log_error(f"Invalid quantity at row {idx + 1}", idx + 1)
                    continue

                transformed_df.at[idx, "quantity"] = quantity

                # Clean main ingredient
                main_ingredient = self._clean_boolean(row["main_ingredient"])
                transformed_df.at[idx, "main_ingredient"] = main_ingredient

            except Exception as e:
                self.log_error(
                    f"Error processing recipe row {idx + 1}: {str(e)}", idx + 1
                )

        # Final DataFrame with only required columns
        transformed_df = transformed_df[required_columns]

        return transformed_df

    def _clean_boolean(self, value):
        """Clean and convert value to boolean"""

        if pd.isna(value):
            return False

        if isinstance(value, bool):
            return value

        # Convert string values
        str_value = str(value).lower().strip()

        if str_value in ["true", "1", "yes", "oui", "y", "t"]:
            return True
        elif str_value in [
            "false",
            "0",
            "no",
            "non",
            "n",
            "f",
            "nan",
            "none",
            "null",
            "",
        ]:
            return False
        else:
            return False  # Default to False for unknown values
