import logging
from typing import Any, Dict

import pandas as pd
from django.db import transaction

from apps.restaurant_data.models import (
    Product,
    Purchase,
    PurchasesCategory,
    Recipe,
    RecipeIngredient,
    Sales,
    SalesCategory,
    UnitOfMeasure,
)

from ..utils.product_consolidation import product_consolidation_service
from ..utils.unit_conversion import unit_conversion_service
from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class RestaurantDataLoader(BaseLoader):
    """Loader for loading transformed data into the database"""

    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load data into database"""

        results = {}

        try:
            with transaction.atomic():

                # Load in order: products -> legacy rules -> purchases -> sales -> consolidated_purchases
                if "products" in data:
                    results["products"] = self._load_products(data["products"])

                    # Load legacy rules after products are loaded (initial load only)
                    self._load_legacy_rules_after_products()

                if "purchases" in data:
                    results["purchases"] = self._load_purchases(data["purchases"])

                if "sales" in data:
                    results["sales"] = self._load_sales(data["sales"])

                # Load consolidated analytics after all base data is loaded
                if "purchases" in data:
                    results["consolidated_purchases"] = (
                        self._load_consolidated_purchases()
                    )

                if "sales" in data:
                    results["consolidated_sales"] = self._load_consolidated_sales()
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
                purchases_category_name = row.get("purchase_category", "Unknown")
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

                # Get or create product - use case-insensitive lookup
                product_name = row["name"]
                product = Product.objects.filter(name__iexact=product_name).first()

                if product is None:
                    # Create new product
                    product = Product.objects.create(
                        name=product_name,
                        purchase_category=purchases_category,
                        sales_category=sales_category,
                        unit_of_measure=unit_of_measure,
                        current_selling_price=row["current_selling_price"],
                        current_cost_per_unit=row["current_cost_per_unit"],
                        current_stock=row["current_stock"],
                        created_by=self.user,
                        updated_by=self.user,
                    )
                    created += 1
                    self.log_info(f"Created new product: {product_name}")
                else:
                    # Update existing product
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
                    self.log_info(f"Updated existing product: {product_name}")

            except Exception as e:
                errors += 1
                error_msg = f"Error loading product {row['name']}: {str(e)}"
                self.log_error(error_msg)

        self.created_count = created
        self.updated_count = updated
        self.error_count = errors

        # Note: Legacy rules loading moved to after recipes are loaded

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

    def _load_consolidated_purchases(self) -> Dict[str, Any]:
        """Generate consolidated purchases data by applying consolidation rules to purchases"""
        try:
            from apps.restaurant_data.models import (
                ConsolidatedPurchases,
                Product,
                ProductConsolidation,
                Purchase,
            )

            logger.info("Starting consolidated purchases generation...")

            # Clear existing consolidated purchases for this upload
            # Note: Since we simplified the models, we can't filter by data_upload anymore
            # We'll clear all consolidated purchases and regenerate them
            ConsolidatedPurchases.objects.all().delete()

            purchases = Purchase.objects.select_related("product").all()
            if not purchases.exists():
                logger.warning("No purchases found to consolidate")
                return {"created": 0, "errors": 0}

            # Get consolidation rules
            consolidation_rules = {}
            for rule in ProductConsolidation.objects.select_related(
                "primary_product"
            ).all():
                primary_name = rule.primary_product.name
                for product_id in rule.consolidated_products:
                    try:
                        product = Product.objects.get(id=product_id)
                        consolidation_rules[product.name] = {
                            "primary_name": primary_name,
                            "primary_product": rule.primary_product,
                            "rule": rule,
                        }
                    except Product.DoesNotExist:
                        continue

            # Create one consolidated purchase record for each original purchase
            created_count = 0
            errors = 0

            for purchase in purchases:
                try:
                    product_name = purchase.product.name

                    # Check if this product has consolidation rules
                    if product_name in consolidation_rules:
                        # Use consolidated product
                        consolidated_product = consolidation_rules[product_name][
                            "primary_product"
                        ]
                        consolidation_applied = True
                        consolidated_product_names = [product_name]
                    else:
                        # Use original product
                        consolidated_product = purchase.product
                        consolidation_applied = False
                        consolidated_product_names = []

                    # Create consolidated purchase record (1:1 copy with product name change)
                    ConsolidatedPurchases.objects.create(
                        product=consolidated_product,
                        purchase_date=purchase.purchase_date,
                        quantity_purchased=purchase.quantity_purchased,
                        total_cost=purchase.total_cost,
                        unit_of_purchase=purchase.product.unit_of_measure,
                        unit_of_recipe=purchase.product.unit_of_measure,
                        consolidation_applied=consolidation_applied,
                        consolidated_product_names=consolidated_product_names,
                        created_by=self.user,
                        updated_by=self.user,
                    )
                    created_count += 1

                except Exception as e:
                    errors += 1
                    error_msg = f"Error creating consolidated purchase for {purchase.product.name}: {str(e)}"
                    self.log_error(error_msg)

            logger.info(
                f"Created {created_count} consolidated purchase records (1:1 copy from {len(purchases)} original purchases)"
            )
            return {"created": created_count, "errors": errors}

        except Exception as e:
            error_msg = f"Error generating consolidated purchases: {str(e)}"
            logger.error(error_msg)
            self.log_error(error_msg)
            return {"created": 0, "errors": 1}

    def _load_consolidated_sales(self) -> Dict[str, Any]:
        """Generate consolidated sales data by applying consolidation rules to sales"""
        try:
            from apps.restaurant_data.models import (
                ConsolidatedSales,
                Product,
                ProductConsolidation,
                Sales,
            )

            logger.info("Starting consolidated sales generation...")

            # Clear existing consolidated sales for this upload
            # Note: Since we simplified the models, we can't filter by data_upload anymore
            # We'll clear all consolidated sales and regenerate them
            ConsolidatedSales.objects.all().delete()

            sales = Sales.objects.select_related("product").all()
            if not sales.exists():
                logger.warning("No sales found to consolidate")
                return {"created": 0, "errors": 0}

            # Get consolidation rules
            consolidation_rules = {}
            for rule in ProductConsolidation.objects.select_related(
                "primary_product"
            ).all():
                primary_name = rule.primary_product.name
                for product_id in rule.consolidated_products:
                    try:
                        product = Product.objects.get(id=product_id)
                        consolidation_rules[product.name] = {
                            "primary_name": primary_name,
                            "primary_product": rule.primary_product,
                            "rule": rule,
                        }
                    except Product.DoesNotExist:
                        continue

            # Create one consolidated sales record for each original sale
            created_count = 0
            errors = 0

            for sale in sales:
                try:
                    product_name = sale.product.name

                    # Check if this product has consolidation rules
                    if product_name in consolidation_rules:
                        # Use consolidated product
                        consolidated_product = consolidation_rules[product_name][
                            "primary_product"
                        ]
                        consolidation_applied = True
                        consolidated_product_names = [product_name]
                    else:
                        # Use original product
                        consolidated_product = sale.product
                        consolidation_applied = False
                        consolidated_product_names = []

                    # Create consolidated sales record (1:1 copy with product name change)
                    ConsolidatedSales.objects.create(
                        product=consolidated_product,
                        sale_date=sale.sale_date,
                        order_number=sale.order_number,
                        quantity_sold=sale.quantity_sold,
                        unit_sale_price=sale.unit_sale_price,
                        total_sale_price=sale.total_sale_price,
                        customer=sale.customer,
                        cashier=sale.cashier,
                        unit_of_sale=sale.product.unit_of_measure,
                        unit_of_recipe=sale.product.unit_of_measure,
                        consolidation_applied=consolidation_applied,
                        consolidated_product_names=consolidated_product_names,
                        created_by=self.user,
                        updated_by=self.user,
                    )
                    created_count += 1

                except Exception as e:
                    errors += 1
                    error_msg = f"Error creating consolidated sale for {sale.product.name}: {str(e)}"
                    self.log_error(error_msg)

            logger.info(
                f"Created {created_count} consolidated sales records (1:1 copy from {len(sales)} original sales)"
            )
            return {"created": created_count, "errors": errors}

        except Exception as e:
            error_msg = f"Error generating consolidated sales: {str(e)}"
            logger.error(error_msg)
            self.log_error(error_msg)
            return {"created": 0, "errors": 1}

    def _load_legacy_consolidation_rules(self):
        """Load legacy consolidation rules automatically after products are loaded (initial load only)"""
        try:
            # Import here to avoid circular imports
            from apps.restaurant_data.models import ProductConsolidation

            # Check if consolidation rules are already loaded
            existing_rules_count = ProductConsolidation.objects.count()
            if existing_rules_count > 0:
                logger.info(
                    f"Legacy consolidation rules already loaded ({existing_rules_count} rules found). Skipping auto-load."
                )
                return

            # Only load consolidation rules if this appears to be an initial data load
            if not self._is_initial_data_load():
                logger.info(
                    "This appears to be an ongoing upload, not initial load. Skipping legacy consolidation rules loading."
                )
                return

            logger.info(
                "Detected initial data load. Auto-loading legacy consolidation rules..."
            )

            # Load the legacy consolidation rules using the service
            product_consolidation_service.load_legacy_consolidation_rules()

            # Log the result
            new_rules_count = ProductConsolidation.objects.count()
            logger.info(
                f"Successfully auto-loaded {new_rules_count} legacy consolidation rules during initial setup"
            )

        except Exception as e:
            error_msg = f"Error auto-loading legacy consolidation rules: {str(e)}"
            logger.error(error_msg)
            self.log_error(error_msg)

    def _load_legacy_rules_after_products(self):
        """Load legacy consolidation rules and unit conversions after products are loaded"""
        try:
            from apps.restaurant_data.models import ProductConsolidation, UnitConversion

            # Check if legacy rules are already loaded
            consolidation_count = ProductConsolidation.objects.count()
            conversion_count = UnitConversion.objects.count()

            if consolidation_count > 0 and conversion_count > 0:
                logger.info(
                    f"Legacy rules already loaded (consolidation: {consolidation_count}, conversions: {conversion_count}). Skipping."
                )
                return

            logger.info(
                "Loading legacy consolidation rules and unit conversions after products..."
            )

            # Load consolidation rules if they don't exist
            if consolidation_count == 0:
                logger.info("Loading legacy consolidation rules...")
                product_consolidation_service.load_legacy_consolidation_rules()
                new_consolidation_count = ProductConsolidation.objects.count()
                logger.info(f"Loaded {new_consolidation_count} consolidation rules")
            else:
                logger.info(
                    f"Consolidation rules already exist ({consolidation_count} rules)"
                )

            # Load unit conversions and standards if they don't exist
            if conversion_count == 0:
                logger.info("Loading legacy unit conversions and standards...")
                result = (
                    unit_conversion_service.load_legacy_unit_conversions_and_standards()
                )
                logger.info(
                    f"Loaded {result['conversions_created']} conversions and {result['standards_created']} standards"
                )
            else:
                logger.info(
                    f"Unit conversions already exist ({conversion_count} conversions)"
                )

            logger.info("Legacy rules loading completed successfully")

        except Exception as e:
            error_msg = f"Error loading legacy rules after products: {str(e)}"
            logger.error(error_msg)
            self.log_error(error_msg)

    def _is_initial_data_load(self):
        """Determine if this is an initial data load or an ongoing upload"""
        try:
            # Import here to avoid circular imports
            from apps.data_management.models import DataUpload
            from apps.restaurant_data.models import ProductConsolidation

            # Method 1: Check if any consolidation rules already exist
            # If rules exist, this is definitely not an initial load
            if ProductConsolidation.objects.exists():
                logger.info(
                    "ProductConsolidation rules already exist - not an initial load"
                )
                return False

            # Method 2: Check total number of successful uploads in the system
            # Initial loads should be among the very first uploads
            successful_uploads = DataUpload.objects.filter(status="completed").count()

            # Method 3: Check if this upload has a specific marker for initial load
            # Look for specific filename patterns that indicate initial load
            current_upload_filename = getattr(self, "upload_filename", "")
            is_initial_filename = any(
                keyword in current_upload_filename.lower()
                for keyword in [
                    "initial",
                    "setup",
                    "first",
                    "baseline",
                    "import",
                    "migration",
                ]
            )

            # Conservative approach: Only consider it initial if:
            # 1. Very few (≤ 2) successful uploads AND
            # 2. Either filename suggests initial load OR it's the very first upload
            is_initial = successful_uploads <= 2 and (
                successful_uploads == 0 or is_initial_filename
            )

            logger.info(
                f"Initial load detection: successful_uploads={successful_uploads}, "
                f"filename_suggests_initial={is_initial_filename}, "
                f"upload_filename='{current_upload_filename}' "
                f"→ is_initial={is_initial}"
            )

            return is_initial

        except Exception as e:
            logger.warning(
                f"Error detecting initial load status: {str(e)}. Defaulting to False."
            )
            return False


class RecipeDataLoader(BaseLoader):
    """Loader for loading transformed data into the database"""

    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load data into database"""

        results = {}

        try:
            with transaction.atomic():
                if "recipes" in data:
                    results["recipes"] = self._load_recipes(data["recipes"])

                    # Note: Legacy rules are now loaded after products in RestaurantDataLoader

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

        # Group by dish_name
        grouped_df = df.groupby("dish_name")

        for group_key, group_df in grouped_df:
            try:
                # Get or create recipe
                recipe, created = Recipe.objects.get_or_create(
                    dish_name=group_key,
                    created_by=self.user,
                    updated_by=self.user,
                )

                if created:
                    created_recipes += 1
                else:
                    # Update recipe
                    recipe.dish_name = group_key
                    recipe.save()

                # Load ingredients
                for idx, row in group_df.iterrows():
                    try:
                        # Get ingredient
                        ingredient = Product.objects.filter(
                            name__iexact=row["ingredient"]
                        ).first()

                        if not ingredient:
                            logger.error(f"Ingredient {row['ingredient']} not found")
                            continue

                        # Get or create unit of measure
                        unit_name = str(row["unit_of_recipe"]).strip()
                        unit_of_measure, _ = UnitOfMeasure.objects.get_or_create(
                            name=unit_name,
                            defaults={
                                "description": f"Unit: {unit_name}",
                            },
                        )

                        RecipeIngredient.objects.get_or_create(
                            recipe=recipe,
                            ingredient=ingredient,
                            quantity=row["quantity"],
                            main_ingredient=row["main_ingredient"],
                            unit_of_recipe=unit_of_measure,
                        )

                        created_ingredients += 1

                    except Exception as e:
                        errors += 1
                        error_msg = f"Error loading recipe ingredient at row {idx + 1}: {str(e)}"
                        self.errors.append(error_msg)
                        logger.error(error_msg)

            except Exception as e:
                errors += 1
                error_msg = f"Error loading recipe at row {idx + 1}: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)

        self.created_count += created_recipes + created_ingredients
        self.error_count += errors

        return {
            "created": created_recipes + created_ingredients,
            "updated": 0,  # Recipes don't have updates, only creates
            "errors": errors,
        }

    def _is_initial_data_load(self):
        """Determine if this is an initial data load or an ongoing upload"""
        try:
            from apps.data_management.models import DataUpload
            from apps.restaurant_data.models import ProductConsolidation

            # If there are already consolidation rules, it's not initial
            if ProductConsolidation.objects.exists():
                logger.info(
                    "ProductConsolidation rules already exist - not an initial load"
                )
                return False

            # Check upload history and filename patterns
            successful_uploads = DataUpload.objects.filter(status="completed").count()
            current_upload_filename = getattr(self, "upload_filename", "")
            is_initial_filename = any(
                keyword in current_upload_filename.lower()
                for keyword in [
                    "initial",
                    "setup",
                    "first",
                    "baseline",
                    "import",
                    "migration",
                    "recipes",
                ]
            )

            is_initial = successful_uploads <= 3 and (  # Allow more uploads for recipes
                successful_uploads == 0 or is_initial_filename
            )
            logger.info(
                f"Initial load detection: successful_uploads={successful_uploads}, filename_suggests_initial={is_initial_filename}, upload_filename='{current_upload_filename}' → is_initial={is_initial}"
            )
            return is_initial

        except Exception as e:
            logger.warning(
                f"Error detecting initial load status: {str(e)}. Defaulting to False."
            )
            return False
