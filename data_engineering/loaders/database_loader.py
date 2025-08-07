import logging
from typing import Any, Dict

import pandas as pd
from django.db import transaction

from apps.restaurant_data.models import (
    Product,
    Purchase,
    PurchasesCategory,
    Sales,
    SalesCategory,
    Recipe,
    RecipeIngredient,
    UnitOfMeasure,
)

from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class RestaurantDataLoader(BaseLoader):
    """Loader for loading transformed data into the database"""

    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load data into database"""

        results = {}

        try:
            with transaction.atomic():

                # Load in order: products -> purchases -> sales
                if "products" in data:
                    results["products"] = self._load_products(data["products"])

                if "purchases" in data:
                    results["purchases"] = self._load_purchases(data["purchases"])

                if "sales" in data:
                    results["sales"] = self._load_sales(data["sales"])
        except Exception as e:
            self.log_error(f"Error loading data: {str(e)}")
            raise

        self.log_loader_stats()
        return results

    def _load_products(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Load products into database"""

        created = 0
        updated = 0
        errors = 0

        for idx, row in df.iterrows():
            try:
                # Get or create purchases and sales categories
                purchases_category_name = row.get("purchases_category", "Unknown")
                sales_category_name = row.get("sales_category", "Unknown")

                purchases_category, _ = PurchasesCategory.objects.get_or_create(
                    name=purchases_category_name,
                    defaults={"name_fr": purchases_category_name},
                )

                sales_category, _ = SalesCategory.objects.get_or_create(
                    name=sales_category_name, defaults={"name_fr": sales_category_name}
                )

                # Get or create unit of measure
                unit_of_measure_name = row.get("unit_of_measure", "unit")
                unit_of_measure, _ = UnitOfMeasure.objects.get_or_create(
                    name=unit_of_measure_name,
                    abbreviation=unit_of_measure_name,
                    defaults={"name_fr": unit_of_measure_name},
                )

                # Get or create product
                product, created = Product.objects.get_or_create(
                    name=row["product"],
                    defaults={
                        "purchase_category": purchases_category,
                        "sales_category": sales_category,
                        "unit_of_measure": unit_of_measure,
                        "current_selling_price": row["current_selling_price"],
                        "current_cost_per_unit": row["current_cost_per_unit"],
                        "current_stock": row["current_stock"],
                        "created_by": self.user,
                        "updated_by": self.user,
                    },
                )

                if created:
                    created += 1
                else:
                    # Update product
                    product.current_cost_per_unit = row["current_cost_per_unit"]
                    if (
                        "current_selling_price" in row
                        and row["current_selling_price"] is not None
                    ):
                        product.current_selling_price = row["current_selling_price"]
                    if "current_stock" in row and row["current_stock"] is not None:
                        product.current_stock = row["current_stock"]
                    product.save()
                    updated += 1

            except Exception as e:
                errors += 1
                error_msg = f"Error loading product {row['product']}: {str(e)}"
                self.log_error(error_msg)

        self.created_count = created
        self.updated_count = updated
        self.error_count = errors

        return {"created": created, "updated": updated, "errors": errors}

    def _load_purchases(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Load purchases into database"""

        created_purchases = 0
        errors = 0

        # Create individual records for each purchase
        for idx, row in df.iterrows():
            try:
                # Find product
                product = Product.objects.filter(name__iexact=row["product"]).first()

                if not product:
                    error_msg = f"Product {row['product']} not found"
                    self.log_error(error_msg)
                    continue

                # Create individual purchase record for each row
                Purchase.objects.create(
                    purchase_date=row["purchase_date"],
                    product=product,
                    total_cost=row["total_cost"],
                    quantity_purchased=row["quantity_purchased"],
                    created_by=self.user,
                    updated_by=self.user,
                )

                created_purchases += 1

            except Exception as e:
                errors += 1
                error_msg = f"Error loading purchase at row {idx + 1}: {str(e)}"
                self.log_error(error_msg)

        self.created_count = created_purchases
        self.error_count = errors

        return {"created": created_purchases, "errors": errors}

    def _load_sales(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Load sales into database"""

        created_sales = 0
        errors = 0

        for idx, row in df.iterrows():
            try:
                # Find product
                product = Product.objects.filter(name__iexact=row["product"]).first()

                if not product:
                    error_msg = f"Product {row['product']} not found"
                    self.log_error(error_msg)
                    continue
                
                # Create sale
                Sales.objects.create(
                    sale_date=row["sale_date"],
                    product=product,
                    quantity_sold=row["quantity_sold"],
                    unit_sale_price=row["unit_sale_price"],
                    total_sale_price=row["total_sale_price"],
                    created_by=self.user,
                    updated_by=self.user,
                )

                created_sales += 1

            except Exception as e:
                errors += 1
                error_msg = f"Error loading sale at row {idx + 1}: {str(e)}"
                self.log_error(error_msg)

        self.created_count = created_sales
        self.error_count = errors

        return {"created": created_sales, "errors": errors}

class RecipeDataLoader(BaseLoader):
    """Loader for loading transformed data into the database"""

    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load data into database"""

        results = {}

        try:
            with transaction.atomic():
                if "recipes" in data:
                    results["recipes"] = self._load_recipes(data["recipes"])
        
        except Exception as e:
            self.log_error(f"Error loading data: {str(e)}")
            raise
        
        self.log_loader_stats()
        return results
    
    def _load_recipes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Load recipes into database"""
        
        created_recipes = 0
        created_ingredients = 0
        errors = 0
        
        for idx, row in df.iterrows():
            try:
                # Get or create recipe
                recipe, created = Recipe.objects.get_or_create(
                    dish_name=row["dish_name"],
                    created_by=self.user,
                    updated_by=self.user,
                )
                
                if created:
                    created_recipes += 1
                else:
                    # Update recipe
                    recipe.dish_name = row["dish_name"]
                    recipe.save()
                    
                # Load ingredients
                ingredient = Product.objects.filter(name__iexact=row["ingredient"]).first()
                
                if not ingredient:
                    logger.error(f"Ingredient {row['ingredient']} not found")
                    continue
            
                # Create recipe ingredient
                RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                quantity=row["quantity"],
                main_ingredient=row["main_ingredient"],
                )

                created_ingredients += 1

            except Exception as e:
                errors += 1
                error_msg = f"Error loading recipe at row {idx + 1}: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                
        self.created_count += created_recipes + created_ingredients
        self.error_count += errors
        
        return {
            "created_recipes": created_recipes,
            "created_ingredients": created_ingredients,
            "errors": errors,
        }
