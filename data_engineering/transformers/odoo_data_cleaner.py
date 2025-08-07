import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict

import pandas as pd

from .base_transformer import BaseTransformer


class OdooDataTransformer(BaseTransformer):
    """Transfrom and clean Odoo data for restauran analytics"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Column mappings for different language and format
        self.column_mappings = {
            "products": {
                "name": ["nom"],
                "purchase_category": ["catégorie_de_produits"],
                "sales_category": ["catégorie_du_point_de_vente"],
                "unit_of_measure": ["unité"],
                "current_selling_price": ["prix_de_vente"],
                "current_cost_per_unit": ["coût"],
                "current_stock": ["quantité_en_stock"],
            },
            "purchases": {
                "purchase_date": ["purchase_date"],
                "product": ["product"],
                "quantity_purchased": ["quantité_commandée"],
                "total_cost": ["total"],
            },
            "sales": {
                "sale_date": ["date_de_la_commande"],
                "order_number": ["commander"],
                "product": ["variante_de_produit"],
                "quantity_sold": ["qté_commandée"],
                "unit_sale_price": ["prix_unitaire"],
                "total_sale_price": ["total"],
                "customer": ["client"],
                "cashier": ["vendeur"],
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
        else:
            self.log_warning(f"Unknown sheet type: {sheet_type}")
            return df

    def _transform_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform products sheet"""

        # Rename columns
        df = self._map_columns(df, "products")

        # Combine name (formerly nom) with valeurs_de_la_variante to create a formatted product name
        if "name" in df.columns and "valeurs_de_la_variante" in df.columns:
            df["name"] = df.apply(
                lambda row: self._combine_nom_with_variant(
                    row["name"], row["valeurs_de_la_variante"]
                ),
                axis=1,
            )

        # Required columns check
        required_columns = [
            "name",
            "purchase_category",
            "sales_category",
            "unit_of_measure",
            "current_selling_price",
            "current_cost_per_unit",
            "current_stock",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            self.log_warning(
                f"Missing required columns for products: {missing_columns}"
            )
            return pd.DataFrame()

        transformed_df = df.copy()

        # Clean and validate data
        for idx, row in transformed_df.iterrows():
            try:
                # Clean product name
                if pd.isna(row["name"]) or row["name"].strip() == "":
                    self.log_error("Empty product name at row ", idx + 1)
                    continue

                transformed_df.at[idx, "name"] = str(row["name"]).strip()

                # Clean cost per unit
                cost_per_unit = self._clean_decimal(row["current_cost_per_unit"])
                if cost_per_unit <= 0:
                    self.log_error(
                        f"Invalid cost for product {row['name']}: {row['current_cost_per_unit']}",
                        idx + 1,
                    )
                    continue

                if cost_per_unit is None:
                    cost_per_unit = 0

                transformed_df.at[idx, "current_cost_per_unit"] = cost_per_unit

                # Clean selling price
                selling_price = self._clean_decimal(row["current_selling_price"])
                if selling_price <= 0:
                    self.log_error(
                        f"Invalid selling price for product {row['name']}: {row['current_selling_price']}",
                        idx + 1,
                    )
                    continue

                if selling_price is None:
                    selling_price = 0

                transformed_df.at[idx, "current_selling_price"] = selling_price

                # Set default purchase category if missing
                if (
                    pd.isna(row["purchase_category"])
                    or row["purchase_category"].strip() == ""
                ):
                    transformed_df.at[idx, "purchase_category"] = "Unknown"

                # Set default sales category if missing
                if (
                    pd.isna(row["sales_category"])
                    or row["sales_category"].strip() == ""
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

                transformed_df.at[idx, "current_stock"] = current_stock

            except Exception as e:
                self.log_error(
                    f"Error processing product row {idx + 1}: {str(e)}", idx + 1
                )

        # Final DataFrame with only required columns
        transformed_df = transformed_df[required_columns]

        return transformed_df

    def _transform_purchases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform purchases sheet from pivot table format to tabular format"""

        # Check if this is a pivot table format (first column contains product names and dates)
        if len(df.columns) == 3 and "unnamed:_0" in df.columns:
            return self._convert_pivot_to_tabular(df)

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
                if quantity is None or quantity <= 0:
                    self.log_error(
                        f"Invalid quantity: {row['quantity_purchased']}", idx + 1
                    )
                    continue

                transformed_df.at[idx, "quantity_purchased"] = quantity

                # Clean total
                total = self._clean_decimal(row["total_cost"])
                if total is None or total <= 0:
                    self.log_error(f"Invalid total: {row['total_cost']}", idx + 1)
                    continue

                transformed_df.at[idx, "total_cost"] = total
            except Exception as e:
                self.log_error(
                    f"Error processing purchase row {idx + 1}: {str(e)}", idx + 1
                )

        # Final DataFrame with only required columns
        transformed_df = transformed_df[required_columns]
        return transformed_df

    def _convert_pivot_to_tabular(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert pivot table format to tabular format"""

        # French month abbreviations mapping
        french_months = {
            "janv.": "01",
            "févr.": "02",
            "mars": "03",
            "avr.": "04",
            "mai": "05",
            "juin": "06",
            "juil.": "07",
            "août": "08",
            "sept.": "09",
            "oct.": "10",
            "nov.": "11",
            "déc.": "12",
        }

        result_rows = []
        current_product = None

        for idx, row in df.iterrows():
            unnamed_col = row["unnamed:_0"]
            qte = row["qté_commandée"]
            total = row["total"]

            # Check if this row contains a product name (not a date)
            # Product names typically don't contain date patterns
            if not self._is_date_string(unnamed_col, french_months):
                # This is a product name
                current_product = self._clean_product_name(str(unnamed_col).strip())
            else:
                # This is a date row, create a purchase record
                if current_product is not None:
                    # Parse the French date
                    purchase_date = self._parse_french_date(unnamed_col, french_months)

                    if purchase_date is not None:
                        result_rows.append(
                            {
                                "purchase_date": purchase_date,
                                "product": current_product,
                                "qté_commandée": qte,
                                "total": total,
                            }
                        )

        # Create the result DataFrame
        if result_rows:
            result_df = pd.DataFrame(result_rows)
            return self._clean_purchases_data(result_df)
        else:
            return pd.DataFrame()

    def _is_date_string(self, text: str, french_months: dict) -> bool:
        """Check if a string represents a French date"""
        if pd.isna(text):
            return False

        text = str(text).strip()

        # Check for French date pattern: "30 avr. 2025"
        for month_abbr in french_months.keys():
            if month_abbr in text and any(char.isdigit() for char in text):
                return True

        return False

    def _parse_french_date(self, date_str: str, french_months: dict) -> str:
        """Parse French date string to ISO format"""
        try:
            date_str = str(date_str).strip()

            # Extract day, month, and year
            parts = date_str.split()
            if len(parts) != 3:
                return None

            day = parts[0]
            month_abbr = parts[1]
            year = parts[2]

            # Get month number
            month_num = french_months.get(month_abbr)
            if month_num is None:
                return None

            # Format as ISO date
            return f"{year}-{month_num}-{day.zfill(2)}"

        except Exception as e:
            self.log_error(f"Error parsing date '{date_str}': {str(e)}")
            return None

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
                if quantity_sold is None or quantity_sold <= 0:
                    self.log_error(
                        f"Invalid quantity sold: {row['quantity_sold']}", idx + 1
                    )
                    continue

                transformed_df.at[idx, "quantity_sold"] = quantity_sold

                unit_sale_price = self._clean_decimal(row["unit_sale_price"])
                if unit_sale_price is None or unit_sale_price <= 0:
                    self.log_error(
                        f"Invalid unit sale price: {row['unit_sale_price']}", idx + 1
                    )
                    continue

                transformed_df.at[idx, "unit_sale_price"] = unit_sale_price

                # Calculate total sale price
                if "total_sale_price" not in df.columns or pd.isna(
                    row["total_sale_price"]
                ):
                    transformed_df.at[idx, "total_sale_price"] = (
                        quantity_sold * unit_sale_price
                    )
                else:
                    total_sale_price = self._clean_decimal(row["total_sale_price"])
                    transformed_df.at[idx, "total_sale_price"] = (
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

        if sheet_type in self.column_mappings:
            return df

        # Get column mappings for this sheet
        mappings = self.column_mappings.get(sheet_type, {})

        # Rename columns
        if mappings:
            df = df.rename(columns=mappings)

        column_map = {}
        mappings = self.column_mappings[sheet_type]

        # Rename columns
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

            # Try to convert to datetime with multiple formats
            return pd.to_datetime(value, dayfirst=True)

        except (ValueError, TypeError):
            self.log_warning(f"Invalid date value: {value}")
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
            "pcs": ["pcs", "pieces", "pièces", "piece", "pièce", "unit", "unité"],
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


class RecipeDataTransformer(BaseTransformer):
    """Transform and clean recipe data for restaurant analytics"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Column mappings for different language and format
        self.column_mappings = {
            "recipes": {
                "dish_name": ["plat"],
                "ingredient": ["ingrédient"],
                "quantity": ["quantité"],
                "main_ingredient": ["principal"],
            },
        }
        
    def transform(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transform and clean all sheets"""
        
        transformed_data = {}
        
        for sheet_type, df in data.items():
            if df is not None and not df.empty:
                try:
                    transformed_df = self._transform_sheet(df, sheet_type)
                    if transformed_df is not None and not transformed_df.empty:
                        transformed_data[sheet_type] = transformed_df
                except Exception as e:
                    self.log_error(f"Error transforming {sheet_type} sheet: {str(e)}")
                    
        return transformed_data
    
    def _transform_sheet(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Transform individual sheet"""
        
        if sheet_type == "recipes":
            return self._transform_recipes(df)
        else:
            self.log_warning(f"Unknown sheet type: {sheet_type}")
            return df
        
    def _transform_recipes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform recipes sheet"""
        
        # Rename columns
        df = self._map_columns(df, "recipes")
        
        required_columns = [
            "dish_name",
            "ingredient",
            "quantity",
            "main_ingredient",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.log_warning(f"Missing required columns for recipes: {missing_columns}")
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
                
                # Clean ingredient
                ingredient = str(row["ingredient"]).strip()
                
                if ingredient == "":
                    self.log_error(f"Empty ingredient at row {idx + 1}", idx + 1)
                    continue
                
                transformed_df.at[idx, "ingredient"] = ingredient
                
                # Clean quantity
                quantity = self._clean_decimal(row["quantity"])
                
                if quantity is None or quantity <= 0:
                    self.log_error(f"Invalid quantity at row {idx + 1}", idx + 1)
                    continue
                
                transformed_df.at[idx, "quantity"] = quantity
                
                # Clean main ingredient
                main_ingredient = self._clean_boolean(row["main_ingredient"])
                
                if main_ingredient == "":
                    self.log_error(f"Empty main ingredient at row {idx + 1}", idx + 1)
                    continue
                
                transformed_df.at[idx, "main_ingredient"] = main_ingredient
                
            except Exception as e:
                self.log_error(f"Error processing recipe row {idx + 1}: {str(e)}", idx + 1)
                
        # Final DataFrame with only required columns
        transformed_df = transformed_df[required_columns]
        
        return transformed_df
    
    def _map_columns(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Map DataFrames to standard column names"""
        
        if sheet_type in self.column_mappings:
            return df
        
        # Get column mappings for this sheet
        column_map = {}
        mappings = self.column_mappings[sheet_type]
        
        # Rename columns
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
        
    def _clean_boolean(self, value):
        """Clean and convert value to boolean"""
        
        if pd.isna(value):
            return None
        
        if isinstance(value, bool):
            return value
        
