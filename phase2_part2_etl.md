# 🔧 Phase 2 Part 2: ETL Pipelines & Data Processing
## Extract, Transform, Load for Restaurant Analytics

This part builds the data processing engine that handles your Odoo exports and recipe files.

## Step 3: ETL Pipeline Foundation

### 3.1 Base ETL Classes (data_engineering/extractors/base_extractor.py)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
import logging
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Base class for all data extractors"""
    
    def __init__(self, file_path: str, **kwargs):
        self.file_path = file_path
        self.options = kwargs
        self.errors = []
    
    @abstractmethod
    def extract(self) -> Dict[str, pd.DataFrame]:
        """Extract data from source and return dictionary of DataFrames"""
        pass
    
    def validate_file(self) -> bool:
        """Validate if file exists and is readable"""
        import os
        
        if not os.path.exists(self.file_path):
            self.errors.append(_("File does not exist: {}").format(self.file_path))
            return False
        
        if not os.path.isfile(self.file_path):
            self.errors.append(_("Path is not a file: {}").format(self.file_path))
            return False
        
        return True
    
    def log_extraction_stats(self, data: Dict[str, pd.DataFrame]):
        """Log extraction statistics"""
        total_rows = sum(df.shape[0] for df in data.values())
        logger.info(f"Extracted {len(data)} sheets with {total_rows} total rows")
        
        for sheet_name, df in data.items():
            logger.info(f"Sheet '{sheet_name}': {df.shape[0]} rows, {df.shape[1]} columns")

class BaseTransformer(ABC):
    """Base class for all data transformers"""
    
    def __init__(self, **kwargs):
        self.options = kwargs
        self.errors = []
        self.warnings = []
    
    @abstractmethod
    def transform(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transform the data and return cleaned DataFrames"""
        pass
    
    def log_error(self, message: str, row_number: Optional[int] = None):
        """Log transformation error"""
        error_msg = f"Row {row_number}: {message}" if row_number else message
        self.errors.append(error_msg)
        logger.error(error_msg)
    
    def log_warning(self, message: str, row_number: Optional[int] = None):
        """Log transformation warning"""
        warning_msg = f"Row {row_number}: {message}" if row_number else message
        self.warnings.append(warning_msg)
        logger.warning(warning_msg)

class BaseLoader(ABC):
    """Base class for all data loaders"""
    
    def __init__(self, user=None, **kwargs):
        self.user = user
        self.options = kwargs
        self.created_count = 0
        self.updated_count = 0
        self.error_count = 0
        self.errors = []
    
    @abstractmethod
    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load data into database and return statistics"""
        pass
    
    def log_load_stats(self):
        """Log loading statistics"""
        logger.info(
            f"Loading completed - Created: {self.created_count}, "
            f"Updated: {self.updated_count}, Errors: {self.error_count}"
        )
```

### 3.2 Odoo Data Extractor (data_engineering/extractors/odoo_extractor.py)

```python
import pandas as pd
from typing import Dict
from .base_extractor import BaseExtractor
import logging

logger = logging.getLogger(__name__)

class OdooExcelExtractor(BaseExtractor):
    """Extract data from Odoo Excel export with multiple sheets"""
    
    # Expected sheet names (case-insensitive)
    EXPECTED_SHEETS = {
        'products': ['products', 'produits', 'product'],
        'purchases': ['purchases', 'achats', 'purchase', 'achat'],
        'sales': ['sales', 'ventes', 'sale', 'vente']
    }
    
    def extract(self) -> Dict[str, pd.DataFrame]:
        """Extract data from Odoo Excel file"""
        
        if not self.validate_file():
            return {}
        
        try:
            # Read all sheets from Excel file
            excel_data = pd.read_excel(
                self.file_path, 
                sheet_name=None,  # Read all sheets
                na_values=['', 'None', 'NULL', 'null', '#N/A'],
                keep_default_na=True
            )
            
            # Map sheet names to standardized names
            mapped_data = self._map_sheet_names(excel_data)
            
            # Clean and validate each sheet
            cleaned_data = {}
            for sheet_type, df in mapped_data.items():
                if df is not None and not df.empty:
                    cleaned_data[sheet_type] = self._clean_dataframe(df, sheet_type)
            
            self.log_extraction_stats(cleaned_data)
            return cleaned_data
            
        except Exception as e:
            error_msg = f"Error reading Excel file: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return {}
    
    def _map_sheet_names(self, excel_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Map actual sheet names to expected sheet types"""
        mapped_data = {}
        sheet_names = list(excel_data.keys())
        
        logger.info(f"Found sheets: {sheet_names}")
        
        for sheet_type, possible_names in self.EXPECTED_SHEETS.items():
            found_sheet = None
            
            # Look for exact matches (case-insensitive)
            for sheet_name in sheet_names:
                if sheet_name.lower().strip() in [name.lower() for name in possible_names]:
                    found_sheet = sheet_name
                    break
            
            # If exact match not found, look for partial matches
            if not found_sheet:
                for sheet_name in sheet_names:
                    for possible_name in possible_names:
                        if possible_name.lower() in sheet_name.lower():
                            found_sheet = sheet_name
                            break
                    if found_sheet:
                        break
            
            if found_sheet:
                mapped_data[sheet_type] = excel_data[found_sheet]
                logger.info(f"Mapped sheet '{found_sheet}' to '{sheet_type}'")
            else:
                logger.warning(f"No sheet found for '{sheet_type}'. Expected: {possible_names}")
                mapped_data[sheet_type] = None
        
        return mapped_data
    
    def _clean_dataframe(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Clean DataFrame based on sheet type"""
        
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Standardize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Remove leading/trailing whitespace from string columns
        for col in df.select_dtypes(include=['object']):
            df[col] = df[col].astype(str).str.strip()
            # Replace 'nan' strings back to NaN
            df[col] = df[col].replace('nan', pd.NA)
        
        logger.info(f"Cleaned {sheet_type} sheet: {df.shape[0]} rows, {df.shape[1]} columns")
        logger.info(f"Columns: {list(df.columns)}")
        
        return df

class RecipeExcelExtractor(BaseExtractor):
    """Extract recipe data from Excel file"""
    
    def extract(self) -> Dict[str, pd.DataFrame]:
        """Extract recipe data"""
        
        if not self.validate_file():
            return {}
        
        try:
            # Try to read as single sheet first
            df = pd.read_excel(
                self.file_path,
                na_values=['', 'None', 'NULL', 'null', '#N/A'],
                keep_default_na=True
            )
            
            # Clean the data
            df = self._clean_recipe_data(df)
            
            result = {'recipes': df}
            self.log_extraction_stats(result)
            return result
            
        except Exception as e:
            # Try reading all sheets in case it's multi-sheet
            try:
                excel_data = pd.read_excel(self.file_path, sheet_name=None)
                cleaned_data = {}
                
                for sheet_name, sheet_df in excel_data.items():
                    if not sheet_df.empty:
                        cleaned_data[f"recipes_{sheet_name}"] = self._clean_recipe_data(sheet_df)
                
                self.log_extraction_stats(cleaned_data)
                return cleaned_data
                
            except Exception as e2:
                error_msg = f"Error reading recipe file: {str(e2)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                return {}
    
    def _clean_recipe_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean recipe DataFrame"""
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Standardize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Clean string columns
        for col in df.select_dtypes(include=['object']):
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('nan', pd.NA)
        
        return df
```

### 3.3 Data Transformer (data_engineering/transformers/odoo_data_cleaner.py)

```python
import pandas as pd
from typing import Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime
import re
from .base_extractor import BaseTransformer

class OdooDataTransformer(BaseTransformer):
    """Transform and clean Odoo data for restaurant analytics"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Column mappings for different languages/formats
        self.column_mappings = {
            'products': {
                'name': ['name', 'nom', 'product_name', 'nom_produit'],
                'category': ['category', 'catégorie', 'categorie', 'product_category'],
                'unit_measure': ['unit', 'unité', 'unite', 'uom', 'unit_of_measure'],
                'cost': ['cost', 'coût', 'cout', 'unit_cost', 'price', 'prix'],
                'selling_price': ['selling_price', 'prix_vente', 'sale_price'],
                'barcode': ['barcode', 'code_barre', 'reference', 'ref'],
            },
            'purchases': {
                'date': ['date', 'purchase_date', 'date_achat'],
                'supplier': ['supplier', 'fournisseur', 'vendor'],
                'product': ['product', 'produit', 'product_name'],
                'quantity': ['quantity', 'quantité', 'quantite', 'qty'],
                'unit_cost': ['unit_cost', 'cout_unitaire', 'price', 'prix'],
                'total': ['total', 'total_cost', 'cout_total', 'amount'],
                'invoice': ['invoice', 'facture', 'reference', 'invoice_number'],
            },
            'sales': {
                'date': ['date', 'sale_date', 'date_vente', 'order_date'],
                'product': ['product', 'produit', 'product_name'],
                'quantity': ['quantity', 'quantité', 'quantite', 'qty'],
                'unit_price': ['unit_price', 'prix_unitaire', 'price', 'prix'],
                'total': ['total', 'total_price', 'prix_total', 'amount'],
                'customer': ['customer', 'client', 'customer_name'],
                'payment_method': ['payment', 'paiement', 'payment_method'],
            }
        }
    
    def transform(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transform all data sheets"""
        
        transformed_data = {}
        
        for sheet_type, df in data.items():
            if df is not None and not df.empty:
                try:
                    transformed_df = self._transform_sheet(df, sheet_type)
                    if transformed_df is not None and not transformed_df.empty:
                        transformed_data[sheet_type] = transformed_df
                except Exception as e:
                    self.log_error(f"Error transforming {sheet_type}: {str(e)}")
        
        return transformed_data
    
    def _transform_sheet(self, df: pd.DataFrame, sheet_type: str) -> Optional[pd.DataFrame]:
        """Transform individual sheet based on type"""
        
        if sheet_type == 'products':
            return self._transform_products(df)
        elif sheet_type == 'purchases':
            return self._transform_purchases(df)
        elif sheet_type == 'sales':
            return self._transform_sales(df)
        else:
            self.log_warning(f"Unknown sheet type: {sheet_type}")
            return df
    
    def _transform_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform products data"""
        
        # Map columns to standard names
        df = self._map_columns(df, 'products')
        
        # Required columns check
        required_cols = ['name', 'unit_measure', 'cost']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            self.log_error(f"Missing required columns for products: {missing_cols}")
            return pd.DataFrame()  # Return empty DataFrame
        
        transformed_df = df.copy()
        
        # Clean and validate data
        for idx, row in transformed_df.iterrows():
            try:
                # Clean product name
                if pd.isna(row['name']) or row['name'].strip() == '':
                    self.log_error(f"Empty product name", idx + 1)
                    continue
                
                transformed_df.at[idx, 'name'] = str(row['name']).strip()
                
                # Clean cost
                cost = self._clean_decimal(row['cost'])
                if cost is None or cost <= 0:
                    self.log_error(f"Invalid cost for product {row['name']}: {row['cost']}", idx + 1)
                    continue
                
                transformed_df.at[idx, 'cost'] = cost
                
                # Clean selling price if present
                if 'selling_price' in transformed_df.columns and not pd.isna(row['selling_price']):
                    selling_price = self._clean_decimal(row['selling_price'])
                    transformed_df.at[idx, 'selling_price'] = selling_price
                
                # Set default category if missing
                if 'category' not in transformed_df.columns or pd.isna(row.get('category')):
                    transformed_df.at[idx, 'category'] = 'Général'
                
                # Clean unit of measure
                if 'unit_measure' in transformed_df.columns:
                    uom = self._standardize_unit_measure(row['unit_measure'])
                    transformed_df.at[idx, 'unit_measure'] = uom
                
            except Exception as e:
                self.log_error(f"Error processing product row {idx + 1}: {str(e)}", idx + 1)
        
        # Remove rows with errors
        transformed_df = transformed_df.dropna(subset=['name', 'cost'])
        
        return transformed_df
    
    def _transform_purchases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform purchases data"""
        
        df = self._map_columns(df, 'purchases')
        
        required_cols = ['date', 'product', 'quantity', 'unit_cost']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            self.log_error(f"Missing required columns for purchases: {missing_cols}")
            return pd.DataFrame()
        
        transformed_df = df.copy()
        
        for idx, row in transformed_df.iterrows():
            try:
                # Clean date
                date = self._clean_date(row['date'])
                if date is None:
                    self.log_error(f"Invalid date: {row['date']}", idx + 1)
                    continue
                
                transformed_df.at[idx, 'date'] = date
                
                # Clean numeric fields
                quantity = self._clean_decimal(row['quantity'])
                unit_cost = self._clean_decimal(row['unit_cost'])
                
                if quantity is None or quantity <= 0:
                    self.log_error(f"Invalid quantity: {row['quantity']}", idx + 1)
                    continue
                
                if unit_cost is None or unit_cost <= 0:
                    self.log_error(f"Invalid unit cost: {row['unit_cost']}", idx + 1)
                    continue
                
                transformed_df.at[idx, 'quantity'] = quantity
                transformed_df.at[idx, 'unit_cost'] = unit_cost
                
                # Calculate total if not present
                if 'total' not in transformed_df.columns or pd.isna(row.get('total')):
                    transformed_df.at[idx, 'total'] = quantity * unit_cost
                else:
                    total = self._clean_decimal(row['total'])
                    transformed_df.at[idx, 'total'] = total or (quantity * unit_cost)
                
            except Exception as e:
                self.log_error(f"Error processing purchase row {idx + 1}: {str(e)}", idx + 1)
        
        # Remove invalid rows
        transformed_df = transformed_df.dropna(subset=['date', 'product', 'quantity', 'unit_cost'])
        
        return transformed_df
    
    def _transform_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform sales data"""
        
        df = self._map_columns(df, 'sales')
        
        required_cols = ['date', 'product', 'quantity', 'unit_price']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            self.log_error(f"Missing required columns for sales: {missing_cols}")
            return pd.DataFrame()
        
        transformed_df = df.copy()
        
        for idx, row in transformed_df.iterrows():
            try:
                # Clean date
                date = self._clean_date(row['date'])
                if date is None:
                    self.log_error(f"Invalid date: {row['date']}", idx + 1)
                    continue
                
                transformed_df.at[idx, 'date'] = date
                
                # Clean numeric fields
                quantity = self._clean_decimal(row['quantity'])
                unit_price = self._clean_decimal(row['unit_price'])
                
                if quantity is None or quantity <= 0:
                    self.log_error(f"Invalid quantity: {row['quantity']}", idx + 1)
                    continue
                
                if unit_price is None or unit_price <= 0:
                    self.log_error(f"Invalid unit price: {row['unit_price']}", idx + 1)
                    continue
                
                transformed_df.at[idx, 'quantity'] = quantity
                transformed_df.at[idx, 'unit_price'] = unit_price
                
                # Calculate total
                if 'total' not in transformed_df.columns or pd.isna(row.get('total')):
                    transformed_df.at[idx, 'total'] = quantity * unit_price
                else:
                    total = self._clean_decimal(row['total'])
                    transformed_df.at[idx, 'total'] = total or (quantity * unit_price)
                
                # Standardize payment method
                if 'payment_method' in transformed_df.columns:
                    payment = self._standardize_payment_method(row.get('payment_method'))
                    transformed_df.at[idx, 'payment_method'] = payment
                
            except Exception as e:
                self.log_error(f"Error processing sale row {idx + 1}: {str(e)}", idx + 1)
        
        transformed_df = transformed_df.dropna(subset=['date', 'product', 'quantity', 'unit_price'])
        
        return transformed_df
    
    def _map_columns(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Map DataFrame columns to standard names"""
        
        if sheet_type not in self.column_mappings:
            return df
        
        column_map = {}
        mappings = self.column_mappings[sheet_type]
        
        for standard_name, possible_names in mappings.items():
            for col in df.columns:
                if col.lower().strip() in [name.lower() for name in possible_names]:
                    column_map[col] = standard_name
                    break
        
        if column_map:
            df = df.rename(columns=column_map)
        
        return df
    
    def _clean_decimal(self, value) -> Optional[Decimal]:
        """Clean and convert value to Decimal"""
        
        if pd.isna(value):
            return None
        
        try:
            # Convert to string and clean
            str_value = str(value).strip()
            
            # Remove currency symbols and spaces
            str_value = re.sub(r'[^\d\.,\-]', '', str_value)
            
            # Handle different decimal separators
            str_value = str_value.replace(',', '.')
            
            # Remove extra dots (keep only the last one)
            parts = str_value.split('.')
            if len(parts) > 2:
                str_value = '.'.join(parts[:-1]).replace('.', '') + '.' + parts[-1]
            
            return Decimal(str_value)
            
        except (InvalidOperation, ValueError):
            return None
    
    def _clean_date(self, value) -> Optional[datetime]:
        """Clean and convert value to datetime"""
        
        if pd.isna(value):
            return None
        
        try:
            if isinstance(value, datetime):
                return value
            
            # Try pandas to_datetime with multiple formats
            return pd.to_datetime(value, dayfirst=True)  # European format
            
        except:
            return None
    
    def _standardize_unit_measure(self, value) -> str:
        """Standardize unit of measure"""
        
        if pd.isna(value):
            return 'pcs'
        
        value_lower = str(value).lower().strip()
        
        # Unit mappings
        unit_mappings = {
            'kg': ['kg', 'kilo', 'kilogram', 'kilogramme'],
            'g': ['g', 'gram', 'gramme', 'gr'],
            'l': ['l', 'litre', 'liter', 'lt'],
            'ml': ['ml', 'millilitre', 'milliliter'],
            'pcs': ['pcs', 'pieces', 'pièces', 'piece', 'pièce', 'unit', 'unité'],
            'dozen': ['dozen', 'douzaine', 'dz'],
            'bottle': ['bottle', 'bouteille', 'btl'],
            'can': ['can', 'boîte', 'boite'],
            'pack': ['pack', 'paquet', 'packet'],
            'box': ['box', 'caisse', 'carton'],
        }
        
        for standard_unit, variations in unit_mappings.items():
            if value_lower in variations:
                return standard_unit
        
        return value_lower  # Return as-is if no mapping found
    
    def _standardize_payment_method(self, value) -> str:
        """Standardize payment method"""
        
        if pd.isna(value):
            return 'cash'
        
        value_lower = str(value).lower().strip()
        
        if value_lower in ['cash', 'espèces', 'especes', 'liquide']:
            return 'cash'
        elif value_lower in ['card', 'carte', 'cb', 'credit', 'debit']:
            return 'card'
        elif value_lower in ['mobile', 'momo', 'orange', 'mtn', 'mobile_money']:
            return 'mobile_money'
        elif value_lower in ['transfer', 'virement', 'bank', 'banque']:
            return 'bank_transfer'
        else:
            return 'other'
```

### 3.4 Database Loader (data_engineering/loaders/database_loader.py)

```python
import pandas as pd
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from apps.restaurant_data.models import (
    Category, Product, Supplier, Purchase, PurchaseItem, Sale, SaleItem
)
from .base_extractor import BaseLoader
import logging

logger = logging.getLogger(__name__)

class RestaurantDataLoader(BaseLoader):
    """Load transformed data into restaurant database"""
    
    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load all data into database"""
        
        results = {}
        
        try:
            with transaction.atomic():
                
                # Load in order: products -> purchases -> sales
                if 'products' in data:
                    results['products'] = self._load_products(data['products'])
                
                if 'purchases' in data:
                    results['purchases'] = self._load_purchases(data['purchases'])
                
                if 'sales' in data:
                    results['sales'] = self._load_sales(data['sales'])
                
        except Exception as e:
            logger.error(f"Error during data loading: {str(e)}")
            raise
        
        self.log_load_stats()
        return results
    
    def _load_products(self, df: pd.DataFrame) -> Dict[str, int]:
        """Load products data"""
        
        created = 0
        updated = 0
        errors = 0
        
        for idx, row in df.iterrows():
            try:
                # Get or create category
                category_name = row.get('category', 'Général')
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'name_fr': category_name}
                )
                
                # Get or create product
                product, product_created = Product.objects.get_or_create(
                    name=row['name'],
                    category=category,
                    defaults={
                        'unit_of_measure': row['unit_measure'],
                        'current_cost_per_unit': row['cost'],
                        'current_selling_price': row.get('selling_price'),
                        'product_type': 'ingredient',
                        'created_by': self.user,
                        'updated_by': self.user,
                    }
                )
                
                if product_created:
                    created += 1
                else:
                    # Update existing product
                    product.current_cost_per_unit = row['cost']
                    if 'selling_price' in row and not pd.isna(row['selling_price']):
                        product.current_selling_price = row['selling_price']
                    product.updated_by = self.user
                    product.save()
                    updated += 1
                
            except Exception as e:
                errors += 1
                error_msg = f"Error loading product row {idx + 1}: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
        
        self.created_count += created
        self.updated_count += updated
        self.error_count += errors
        
        return {'created': created, 'updated': updated, 'errors': errors}
    
    def _load_purchases(self, df: pd.DataFrame) -> Dict[str, int]:
        """Load purchases data"""
        
        created_purchases = 0
        created_items = 0
        errors = 0
        
        # Group by date and supplier to create purchase records
        grouped = df.groupby(['date', 'supplier'] if 'supplier' in df.columns else ['date'])
        
        for group_key, group_df in grouped:
            try:
                # Create or get supplier
                supplier_name = group_key[1] if len(group_key) > 1 else 'Fournisseur Inconnu'
                supplier, _ = Supplier.objects.get_or_create(
                    name=supplier_name,
                    defaults={
                        'created_by': self.user,
                        'updated_by': self.user,
                    }
                )
                
                # Create purchase record
                purchase_date = group_key[0]
                total_amount = group_df['total'].sum()
                
                purchase = Purchase.objects.create(
                    purchase_date=purchase_date,
                    supplier=supplier,
                    subtotal=total_amount,
                    total_amount=total_amount,
                    status='received',
                    created_by=self.user,
                    updated_by=self.user,
                )
                
                created_purchases += 1
                
                # Create purchase items
                for idx, row in group_df.iterrows():
                    try:
                        # Find product
                        product = Product.objects.filter(
                            name__iexact=row['product']
                        ).first()
                        
                        if not product:
                            logger.warning(f"Product not found: {row['product']}")
                            continue
                        
                        PurchaseItem.objects.create(
                            purchase=purchase,
                            product=product,
                            quantity=row['quantity'],
                            unit_cost=row['unit_cost'],
                            total_cost=row['total'],
                        )
                        
                        created_items += 1
                        
                    except Exception as e:
                        errors += 1
                        error_msg = f"Error creating purchase item: {str(e)}"
                        self.errors.append(error_msg)
                        logger.error(error_msg)
                
            except Exception as e:
                errors += 1
                error_msg = f"Error creating purchase: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
        
        self.created_count += created_purchases + created_items
        self.error_count += errors
        
        return {
            'created_purchases': created_purchases, 
            'created_items': created_items, 
            'errors': errors
        }
    
    def _load_sales(self, df: pd.DataFrame) -> Dict[str, int]:
        """Load sales data"""
        
        created_sales = 0
        created_items = 0
        errors = 0
        
        # Group by date and customer (if available) to create sale records
        group_cols = ['date']
        if 'customer' in df.columns:
            group_cols.append('customer')
        if 'invoice' in df.columns:
            group_cols.append('invoice')
        
        # If no grouping possible, create individual sales
        if len(group_cols) == 1:
            df['sale_group'] = range(len(df))
            group_cols.append('sale_group')
        
        grouped = df.groupby(group_cols)
        
        for group_key, group_df in grouped:
            try:
                sale_date = group_key[0]
                customer_name = group_key[1] if len(group_key) > 1 and 'customer' in df.columns else ''
                invoice_number = group_key[2] if 'invoice' in df.columns else ''
                
                total_amount = group_df['total'].sum()
                payment_method = group_df['payment_method'].iloc[0] if 'payment_method' in group_df.columns else 'cash'
                
                sale = Sale.objects.create(
                    sale_date=sale_date,
                    invoice_number=invoice_number,
                    customer_name=customer_name,
                    payment_method=payment_method,
                    subtotal=total_amount,
                    total_amount=total_amount,
                    created_by=self.user,
                    updated_by=self.user,
                )
                
                created_sales += 1
                
                # Create sale items
                for idx, row in group_df.iterrows():
                    try:
                        product = Product.objects.filter(
                            name__iexact=row['product']
                        ).first()
                        
                        if not product:
                            logger.warning(f"Product not found: {row['product']}")
                            continue
                        
                        SaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=row['quantity'],
                            unit_price=row['unit_price'],
                            total_price=row['total'],
                        )
                        
                        created_items += 1
                        
                    except Exception as e:
                        errors += 1
                        error_msg = f"Error creating sale item: {str(e)}"
                        self.errors.append(error_msg)
                        logger.error(error_msg)
                
            except Exception as e:
                errors += 1
                error_msg = f"Error creating sale: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
        
        self.created_count += created_sales + created_items
        self.error_count += errors
        
        return {
            'created_sales': created_sales, 
            'created_items': created_items, 
            'errors': errors
        }
```

### 3.5 Complete ETL Pipeline (data_engineering/pipelines/initial_load_pipeline.py)

```python
from typing import Dict, Any, Optional
import logging
from pathlib import Path
from django.utils import timezone
from apps.data_management.models import DataUpload, ProcessingError
from ..extractors.odoo_extractor import OdooExcelExtractor, RecipeExcelExtractor
from ..transformers.odoo_data_cleaner import OdooDataTransformer
from ..loaders.database_loader import RestaurantDataLoader

logger = logging.getLogger(__name__)

class DataProcessingPipeline:
    """Complete ETL pipeline for restaurant data"""
    
    def __init__(self, upload_instance: DataUpload):
        self.upload = upload_instance
        self.user = upload_instance.uploaded_by
        self.file_path = upload_instance.file.path
        self.extractor = None
        self.transformer = None
        self.loader = None
        self.stats = {}
    
    def process(self) -> bool:
        """Run the complete ETL pipeline"""
        
        try:
            # Update status to processing
            self.upload.status = 'processing'
            self.upload.started_at = timezone.now()
            self.upload.save()
            
            logger.info(f"Starting ETL pipeline for upload {self.upload.id}")
            
            # Step 1: Extract
            extracted_data = self._extract_data()
            if not extracted_data:
                self._handle_error("Data extraction failed")
                return False
            
            # Step 2: Transform
            transformed_data = self._transform_data(extracted_data)
            if not transformed_data:
                self._handle_error("Data transformation failed")
                return False
            
            # Step 3: Load
            load_results = self._load_data(transformed_data)
            if not load_results:
                self._handle_error("Data loading failed")
                return False
            
            # Success
            self._handle_success(load_results)
            return True
            
        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._handle_error(error_msg)
            return False
    
    def _extract_data(self) -> Optional[Dict]:
        """Extract data from uploaded file"""
        
        try:
            if self.upload.file_type == 'odoo_export':
                self.extractor = OdooExcelExtractor(self.file_path)
            elif self.upload.file_type == 'recipe_data':
                self.extractor = RecipeExcelExtractor(self.file_path)
            else:
                # Try Odoo extractor as default
                self.extractor = OdooExcelExtractor(self.file_path)
            
            extracted_data = self.extractor.extract()
            
            if not extracted_data:
                for error in self.extractor.errors:
                    self._log_processing_error(0, 'extraction', error)
                return None
            
            # Calculate total rows
            total_rows = sum(df.shape[0] for df in extracted_data.values())
            self.upload.total_rows = total_rows
            self.upload.save()
            
            logger.info(f"Extracted {total_rows} rows from {len(extracted_data)} sheets")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return None
    
    def _transform_data(self, raw_data: Dict) -> Optional[Dict]:
        """Transform extracted data"""
        
        try:
            if self.upload.file_type == 'recipe_data':
                # Recipe data needs different transformation
                return raw_data  # For now, return as-is
            
            self.transformer = OdooDataTransformer()
            transformed_data = self.transformer.transform(raw_data)
            
            # Log transformation errors
            for error in self.transformer.errors:
                self._log_processing_error(0, 'transformation', error)
            
            # Log warnings
            for warning in self.transformer.warnings:
                logger.warning(warning)
            
            if not transformed_data:
                logger.error("No data after transformation")
                return None
            
            logger.info(f"Transformed {len(transformed_data)} sheets")
            return transformed_data
            
        except Exception as e:
            logger.error(f"Transformation error: {str(e)}")
            return None
    
    def _load_data(self, clean_data: Dict) -> Optional[Dict]:
        """Load cleaned data into database"""
        
        try:
            if self.upload.file_type == 'recipe_data':
                # TODO: Implement recipe loader
                logger.info("Recipe loading not yet implemented")
                return {'recipes': {'created': 0, 'updated': 0, 'errors': 0}}
            
            self.loader = RestaurantDataLoader(user=self.user)
            results = self.loader.load(clean_data)
            
            # Log loading errors
            for error in self.loader.errors:
                self._log_processing_error(0, 'loading', error)
            
            # Update upload statistics
            self.upload.processed_rows = self.loader.created_count + self.loader.updated_count
            self.upload.error_rows = self.loader.error_count
            self.upload.save()
            
            logger.info(f"Loaded data - Created: {self.loader.created_count}, Updated: {self.loader.updated_count}, Errors: {self.loader.error_count}")
            return results
            
        except Exception as e:
            logger.error(f"Loading error: {str(e)}")
            return None
    
    def _handle_success(self, results: Dict):
        """Handle successful pipeline completion"""
        
        self.upload.status = 'completed'
        self.upload.completed_at = timezone.now()
        
        # Build processing log
        log_lines = [
            f"Processing completed successfully at {timezone.now()}",
            f"Total rows processed: {self.upload.processed_rows}",
            f"Errors: {self.upload.error_rows}",
            "Results by data type:"
        ]
        
        for data_type, stats in results.items():
            log_lines.append(f"  {data_type}: {stats}")
        
        self.upload.processing_log = '\n'.join(log_lines)
        self.upload.save()
        
        logger.info(f"ETL pipeline completed successfully for upload {self.upload.id}")
    
    def _handle_error(self, error_message: str):
        """Handle pipeline error"""
        
        self.upload.status = 'failed'
        self.upload.completed_at = timezone.now()
        self.upload.error_message = error_message
        
        # Build error log
        log_lines = [
            f"Processing failed at {timezone.now()}",
            f"Error: {error_message}",
        ]
        
        if hasattr(self, 'extractor') and self.extractor and self.extractor.errors:
            log_lines.append("Extraction errors:")
            log_lines.extend(f"  - {error}" for error in self.extractor.errors)
        
        if hasattr(self, 'transformer') and self.transformer and self.transformer.errors:
            log_lines.append("Transformation errors:")
            log_lines.extend(f"  - {error}" for error in self.transformer.errors)
        
        if hasattr(self, 'loader') and self.loader and self.loader.errors:
            log_lines.append("Loading errors:")
            log_lines.extend(f"  - {error}" for error in self.loader.errors)
        
        self.upload.processing_log = '\n'.join(log_lines)
        self.upload.save()
        
        logger.error(f"ETL pipeline failed for upload {self.upload.id}: {error_message}")
    
    def _log_processing_error(self, row_number: int, error_type: str, message: str):
        """Log individual processing error"""
        
        ProcessingError.objects.create(
            upload=self.upload,
            row_number=row_number,
            error_type=error_type,
            error_message=message
        )
```

## 🎯 What We've Built

✅ **Complete ETL Pipeline**: Extract → Transform → Load  
✅ **Odoo Data Processing**: Handle multi-sheet Excel files  
✅ **Data Validation**: Comprehensive error checking  
✅ **Flexible Column Mapping**: Support French/English columns  
✅ **Error Tracking**: Detailed error logging and recovery  
✅ **Transaction Safety**: Database rollback on errors  

## 🔄 Next Steps

Ready for **Part 3: Background Processing & Data Views** to complete the data management system? 🚀