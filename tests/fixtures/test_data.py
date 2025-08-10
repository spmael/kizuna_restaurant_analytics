"""
Test fixtures and sample data for the Kizuna Restaurant Analytics project.
"""

import os
import tempfile

import pandas as pd
from django.contrib.auth import get_user_model

User = get_user_model()


class TestDataFixtures:
    """Class containing test data fixtures"""
    
    @staticmethod
    def create_sample_user():
        """Create a sample user for testing"""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @staticmethod
    def create_sample_odoo_data():
        """Create sample Odoo export data"""
        return {
            'products': pd.DataFrame({
                'name': ['Margherita Pizza', 'Caesar Salad', 'Tiramisu', 'Espresso'],
                'price': [12.99, 8.50, 6.99, 2.50],
                'category': ['Pizza', 'Salad', 'Dessert', 'Beverage'],
                'cost': [8.50, 4.25, 3.50, 1.25],
                'active': [True, True, True, True]
            }),
            'sales': pd.DataFrame({
                'date': ['2024-01-01', '2024-01-01', '2024-01-02', '2024-01-02', '2024-01-03'],
                'product': ['Margherita Pizza', 'Caesar Salad', 'Margherita Pizza', 'Tiramisu', 'Espresso'],
                'quantity': [2, 1, 3, 2, 5],
                'unit_price': [12.99, 8.50, 12.99, 6.99, 2.50],
                'total': [25.98, 8.50, 38.97, 13.98, 12.50]
            }),
            'purchases': pd.DataFrame({
                'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
                'supplier': ['Fresh Foods Inc', 'Quality Meats', 'Dairy Delights'],
                'product': ['Tomatoes', 'Chicken Breast', 'Mozzarella'],
                'quantity': [50, 20, 15],
                'unit_cost': [0.50, 3.25, 2.00],
                'total_cost': [25.00, 65.00, 30.00]
            })
        }
    
    @staticmethod
    def create_sample_recipes_data():
        """Create sample recipes data"""
        return {
            'recipes': pd.DataFrame({
                'recipe_name': ['Margherita Pizza', 'Caesar Salad', 'Tiramisu', 'Pasta Carbonara'],
                'ingredients': [
                    'Dough, Tomatoes, Mozzarella, Basil',
                    'Lettuce, Croutons, Parmesan, Caesar Dressing',
                    'Coffee, Mascarpone, Ladyfingers, Cocoa',
                    'Pasta, Eggs, Bacon, Parmesan'
                ],
                'cooking_time': [25, 10, 30, 20],
                'difficulty': ['Medium', 'Easy', 'Hard', 'Medium'],
                'servings': [4, 2, 6, 4],
                'category': ['Pizza', 'Salad', 'Dessert', 'Pasta']
            })
        }
    
    @staticmethod
    def create_sample_excel_file(data_dict, filename='test_data.xlsx'):
        """Create a sample Excel file with the given data"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for sheet_name, df in data_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return file_path, temp_dir
    
    @staticmethod
    def create_invalid_excel_file():
        """Create an invalid Excel file for testing error handling"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, 'invalid.xlsx')
        
        # Create a file that looks like Excel but has invalid content
        with open(file_path, 'w') as f:
            f.write("This is not a valid Excel file content")
        
        return file_path, temp_dir
    
    @staticmethod
    def create_empty_excel_file():
        """Create an empty Excel file for testing"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, 'empty.xlsx')
        
        empty_df = pd.DataFrame()
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            empty_df.to_excel(writer, sheet_name='empty', index=False)
        
        return file_path, temp_dir
    
    @staticmethod
    def create_large_dataset(rows=1000):
        """Create a large dataset for performance testing"""
        import numpy as np
        
        return {
            'products': pd.DataFrame({
                'name': [f'Product_{i}' for i in range(rows)],
                'price': np.random.uniform(5.0, 50.0, rows),
                'category': np.random.choice(['Food', 'Beverage', 'Dessert'], rows),
                'cost': np.random.uniform(2.0, 25.0, rows),
                'active': np.random.choice([True, False], rows)
            }),
            'sales': pd.DataFrame({
                'date': pd.date_range('2024-01-01', periods=rows, freq='H'),
                'product': [f'Product_{i % 100}' for i in range(rows)],
                'quantity': np.random.randint(1, 10, rows),
                'unit_price': np.random.uniform(5.0, 50.0, rows),
                'total': np.random.uniform(10.0, 500.0, rows)
            })
        }


class MockExtractor:
    """Mock extractor for testing"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.errors = []
    
    def extract(self):
        """Mock extract method"""
        if 'invalid' in self.file_path:
            self.errors.append("Invalid file format")
            return None
        
        if 'empty' in self.file_path:
            return {}
        
        # Return sample data
        return TestDataFixtures.create_sample_odoo_data()


class MockTransformer:
    """Mock transformer for testing"""
    
    def __init__(self, user):
        self.user = user
        self.errors = []
        self.warnings = []
    
    def transform(self, data):
        """Mock transform method"""
        if not data:
            self.errors.append("No data to transform")
            return None
        
        # Return transformed data
        return {
            'transformed_products': data.get('products', pd.DataFrame()),
            'transformed_sales': data.get('sales', pd.DataFrame()),
            'transformed_purchases': data.get('purchases', pd.DataFrame())
        }


class MockLoader:
    """Mock loader for testing"""
    
    def __init__(self, user):
        self.user = user
        self.errors = []
        self.created_count = 0
        self.updated_count = 0
        self.error_count = 0
    
    def load(self, data):
        """Mock load method"""
        if not data:
            self.errors.append("No data to load")
            return None
        
        # Simulate loading results
        total_records = sum(len(df) for df in data.values() if isinstance(df, pd.DataFrame))
        self.created_count = total_records
        self.updated_count = 0
        self.error_count = 0
        
        return {
            'restaurant_data': {
                'created': self.created_count,
                'updated': self.updated_count,
                'errors': self.error_count
            }
        }


# Pytest fixtures
def sample_user():
    """Pytest fixture for sample user"""
    return TestDataFixtures.create_sample_user()


def sample_odoo_data():
    """Pytest fixture for sample Odoo data"""
    return TestDataFixtures.create_sample_odoo_data()


def sample_recipes_data():
    """Pytest fixture for sample recipes data"""
    return TestDataFixtures.create_sample_recipes_data()


def sample_excel_file():
    """Pytest fixture for sample Excel file"""
    data = TestDataFixtures.create_sample_odoo_data()
    file_path, temp_dir = TestDataFixtures.create_sample_excel_file(data)
    yield file_path
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def invalid_excel_file():
    """Pytest fixture for invalid Excel file"""
    file_path, temp_dir = TestDataFixtures.create_invalid_excel_file()
    yield file_path
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def empty_excel_file():
    """Pytest fixture for empty Excel file"""
    file_path, temp_dir = TestDataFixtures.create_empty_excel_file()
    yield file_path
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True) 