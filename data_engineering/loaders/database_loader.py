import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

import pandas as pd
from django.db import transaction

from apps.recipes.models import Recipe, RecipeIngredient
from apps.restaurant_data.models import (
    Product,
    ProductType,
    Purchase,
    PurchasesCategory,
    Sales,
    SalesCategory,
    UnitOfMeasure,
)
from data_engineering.utils.product_consolidation import (
    ProductConsolidationService,
    product_consolidation_service,
)
from data_engineering.utils.product_type_assignment import ProductTypeAssignmentService
from data_engineering.utils.unit_conversion import unit_conversion_service

from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class RestaurantDataLoader(BaseLoader):
    """Loader for loading transformed data into the database"""

    def load(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Load data into database"""

        results = {}
        self.affected_dates = set()  # Track dates that were affected by this upload

        try:
            with transaction.atomic():

                # Load in order: products -> legacy rules -> purchases -> sales -> recipes -> consolidated_purchases
                if "products" in data:
                    results["products"] = self._load_products(data["products"])

                    # Load legacy rules after products are loaded (initial load only)
                    self._load_legacy_rules_after_products()

                if "purchases" in data:
                    results["purchases"] = self._load_purchases(data["purchases"])
                    # Track affected dates from purchases
                    if "purchases" in data:
                        purchase_dates = data["purchases"]["purchase_date"].unique()
                        self.affected_dates.update(purchase_dates)

                if "sales" in data:
                    results["sales"] = self._load_sales(data["sales"])
                    # Track affected dates from sales
                    if "sales" in data:
                        sale_dates = data["sales"]["sale_date"].unique()
                        self.affected_dates.update(sale_dates)

                # Load recipes after products are loaded
                if "recipes" in data:
                    results["recipes"] = self._load_recipes(data["recipes"])

                # Create ProductType records for all products AFTER sales data is loaded
                # This ensures the service can properly determine if products are sold or not
                results["product_types"] = self._create_product_types_for_products()

                # Load consolidated analytics after all base data is loaded
                if "purchases" in data:
                    results["consolidated_purchases"] = (
                        self._load_consolidated_purchases()
                    )

                if "sales" in data:
                    results["consolidated_sales"] = self._load_consolidated_sales()

                # Load product cost history after consolidated purchases are created
                if "purchases" in data:
                    results["product_cost_history"] = self._load_product_cost_history()

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
        updated_purchases = 0
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

                # Check for existing purchase with same date, product, and similar cost/quantity
                existing_purchase = Purchase.objects.filter(
                    purchase_date=row["purchase_date"],
                    product=product,
                ).first()

                if existing_purchase:
                    # Check if this is a duplicate (same date, product, and very similar values)
                    try:
                        cost_diff = abs(
                            float(existing_purchase.total_cost)
                            - float(row["total_cost"])
                        )
                        quantity_diff = abs(
                            float(existing_purchase.quantity_purchased)
                            - float(row["quantity_purchased"])
                        )

                        # If values are very similar (within 1% or 0.01), consider it a duplicate
                        cost_threshold = float(row["total_cost"]) * 0.01  # 1% threshold
                        quantity_threshold = (
                            float(row["quantity_purchased"]) * 0.01
                        )  # 1% threshold

                        if (
                            cost_diff <= cost_threshold
                            and quantity_diff <= quantity_threshold
                        ):
                            # This is likely a duplicate, skip it
                            logger.info(
                                f"Skipping duplicate purchase: {product.name} on {row['purchase_date']}"
                            )
                            continue
                        else:
                            # Values are different, update the existing record
                            existing_purchase.total_cost = row["total_cost"]
                            existing_purchase.quantity_purchased = row[
                                "quantity_purchased"
                            ]
                            existing_purchase.updated_by = self.user
                            existing_purchase.save()
                            updated_purchases += 1
                            logger.info(
                                f"Updated existing purchase: {product.name} on {row['purchase_date']}"
                            )
                    except (ValueError, TypeError, InvalidOperation) as e:
                        # If there's an error comparing values, treat as update
                        logger.warning(
                            f"Error comparing values for {product.name}: {str(e)}. Treating as update."
                        )
                        existing_purchase.total_cost = row["total_cost"]
                        existing_purchase.quantity_purchased = row["quantity_purchased"]
                        existing_purchase.updated_by = self.user
                        existing_purchase.save()
                        updated_purchases += 1
                        logger.info(
                            f"Updated existing purchase (error case): {product.name} on {row['purchase_date']}"
                        )
                else:
                    # Create new purchase record
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
        self.updated_count = updated_purchases
        self.error_count = errors

        return {
            "created": created_purchases,
            "updated": updated_purchases,
            "errors": errors,
        }

    def _load_sales(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Load sales into database"""

        created_sales = 0
        updated_sales = 0
        errors = 0

        for idx, row in df.iterrows():
            try:
                # Find product
                product = Product.objects.filter(name__iexact=row["product"]).first()

                if not product:
                    error_msg = f"Product {row['product']} not found"
                    self.log_error(error_msg)
                    continue

                # Get order number from commander column
                order_number = str(row.get("commander", f"order_{idx}"))

                # Check for existing sale with same order number, date, and product
                existing_sale = Sales.objects.filter(
                    sale_date=row["sale_date"],
                    product=product,
                    order_number=order_number,
                ).first()

                if existing_sale:
                    # Check if this is a true duplicate (same order, same product, same values)
                    try:
                        total_diff = abs(
                            float(existing_sale.total_sale_price)
                            - float(row["total_sale_price"])
                        )
                        quantity_diff = abs(
                            float(existing_sale.quantity_sold)
                            - float(row["quantity_sold"])
                        )

                        # If values are very similar (within 1% or 0.01), consider it a duplicate
                        total_threshold = (
                            float(row["total_sale_price"]) * 0.01
                        )  # 1% threshold
                        quantity_threshold = (
                            float(row["quantity_sold"]) * 0.01
                        )  # 1% threshold

                        if (
                            total_diff <= total_threshold
                            and quantity_diff <= quantity_threshold
                        ):
                            # This is likely a duplicate, skip it
                            logger.info(
                                f"Skipping duplicate sale: {product.name} in order {order_number} on {row['sale_date']}"
                            )
                            continue
                        else:
                            # Values are different, update the existing record
                            existing_sale.quantity_sold = row["quantity_sold"]
                            existing_sale.unit_sale_price = row["unit_sale_price"]
                            existing_sale.total_sale_price = row["total_sale_price"]
                            existing_sale.updated_by = self.user
                            existing_sale.save()
                            updated_sales += 1
                            logger.info(
                                f"Updated existing sale: {product.name} in order {order_number} on {row['sale_date']}"
                            )
                    except (ValueError, TypeError, InvalidOperation) as e:
                        # If there's an error comparing values, treat as update
                        logger.warning(
                            f"Error comparing values for {product.name}: {str(e)}. Treating as update."
                        )
                        existing_sale.quantity_sold = row["quantity_sold"]
                        existing_sale.unit_sale_price = row["unit_sale_price"]
                        existing_sale.total_sale_price = row["total_sale_price"]
                        existing_sale.updated_by = self.user
                        existing_sale.save()
                        updated_sales += 1
                        logger.info(
                            f"Updated existing sale (error case): {product.name} in order {order_number} on {row['sale_date']}"
                        )
                else:
                    # Create new sale record
                    Sales.objects.create(
                        sale_date=row["sale_date"],
                        order_number=order_number,
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
        self.updated_count = updated_sales
        self.error_count = errors

        return {"created": created_sales, "updated": updated_sales, "errors": errors}

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

            # Get the date range of purchases that were just loaded/updated
            # We'll regenerate consolidated purchases only for affected dates
            if hasattr(self, "affected_dates") and self.affected_dates:
                # Clear consolidated purchases for affected dates only
                ConsolidatedPurchases.objects.filter(
                    purchase_date__in=self.affected_dates
                ).delete()
                logger.info(
                    f"Cleared consolidated purchases for affected dates: {self.affected_dates}"
                )
            else:
                # If we don't have specific affected dates, clear all and regenerate
                # This is a fallback for backward compatibility
                ConsolidatedPurchases.objects.all().delete()
                logger.info("Cleared all consolidated purchases (fallback mode)")

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
                    # Use StandardKitchenUnit rules to determine the correct recipe unit
                    recipe_unit = self._get_recipe_unit_for_product(
                        consolidated_product
                    )

                    ConsolidatedPurchases.objects.create(
                        product=consolidated_product,
                        purchase_date=purchase.purchase_date,
                        quantity_purchased=purchase.quantity_purchased,
                        total_cost=purchase.total_cost,
                        unit_of_purchase=purchase.product.unit_of_measure,
                        unit_of_recipe=recipe_unit,
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

            # Get the date range of sales that were just loaded/updated
            # We'll regenerate consolidated sales only for affected dates
            if hasattr(self, "affected_dates") and self.affected_dates:
                # Clear consolidated sales for affected dates only
                ConsolidatedSales.objects.filter(
                    sale_date__in=self.affected_dates
                ).delete()
                logger.info(
                    f"Cleared consolidated sales for affected dates: {self.affected_dates}"
                )
            else:
                # If we don't have specific affected dates, clear all and regenerate
                # This is a fallback for backward compatibility
                ConsolidatedSales.objects.all().delete()
                logger.info("Cleared all consolidated sales (fallback mode)")

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

    def _create_product_types_for_products(self) -> Dict[str, Any]:
        """Create ProductType records for all products and ensure correct classification"""

        created = 0
        updated = 0
        errors = 0

        # Get all products (not just those without ProductType records)
        all_products = Product.objects.all()
        type_service = ProductTypeAssignmentService()

        for product in all_products:
            try:
                # Get existing ProductType
                existing_type = ProductType.objects.filter(product=product).first()

                if existing_type:
                    # Check if the existing classification is correct
                    old_product_type = existing_type.product_type
                    new_product_type = type_service._determine_product_type(product)

                    if old_product_type != new_product_type:
                        # Update existing ProductType with correct classification
                        existing_type.product_type = new_product_type
                        existing_type.save()
                        updated += 1
                        logger.info(
                            f"Updated ProductType for product: {product.name} ({old_product_type} -> {new_product_type})"
                        )
                    else:
                        # Classification is already correct
                        logger.debug(
                            f"ProductType already correct for product: {product.name} ({new_product_type})"
                        )
                else:
                    # Create new ProductType
                    type_service.get_or_create_product_type(product)
                    created += 1
                    logger.info(f"Created ProductType for product: {product.name}")

            except Exception as e:
                errors += 1
                error_msg = f"Error processing ProductType for {product.name}: {str(e)}"
                self.log_error(error_msg)

        self.created_count = created
        self.updated_count = updated
        self.error_count = errors

        return {
            "created": created,
            "updated": updated,
            "errors": errors,
        }

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
            ProductConsolidationService().load_legacy_consolidation_rules()

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

    def _load_recipes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Load recipes and ingredients into database"""

        created_recipes = 0
        created_ingredients = 0
        updated_recipes = 0
        updated_ingredients = 0
        errors = 0

        # Group by dish_name
        grouped_df = df.groupby("dish_name")

        for group_key, group_df in grouped_df:
            try:
                # Get or create recipe
                recipe, created = Recipe.objects.get_or_create(
                    dish_name=group_key,
                    defaults={
                        "created_by": self.user,
                        "updated_by": self.user,
                    },
                )

                if created:
                    created_recipes += 1
                    logger.info(f"Created new recipe: {group_key}")
                else:
                    # Update recipe
                    recipe.updated_by = self.user
                    recipe.save()
                    updated_recipes += 1
                    logger.info(f"Updated existing recipe: {group_key}")

                # Load ingredients
                for idx, row in group_df.iterrows():
                    try:
                        # Get ingredient using consolidation service to handle consolidated names
                        ingredient_name = row["ingredient"]

                        # First try to find consolidated product
                        from data_engineering.utils.product_consolidation import (
                            product_consolidation_service,
                        )

                        consolidated_product = (
                            product_consolidation_service.find_consolidated_product(
                                ingredient_name
                            )
                        )
                        if consolidated_product:
                            # Use the consolidated product (this is the primary product)
                            ingredient = consolidated_product
                            logger.info(
                                f"Found consolidated product {consolidated_product.name} for ingredient {ingredient_name}"
                            )
                        else:
                            # If no consolidation exists, try exact match with original name
                            ingredient = Product.objects.filter(
                                name__iexact=ingredient_name
                            ).first()

                            if not ingredient:
                                logger.error(
                                    f"Ingredient {ingredient_name} not found for recipe {group_key}"
                                )
                                errors += 1
                                continue

                        # Clean and validate quantity
                        try:
                            quantity = Decimal(str(row["quantity"]))
                            if quantity <= 0:
                                logger.warning(
                                    f"Invalid quantity {row['quantity']} for ingredient {row['ingredient']} in recipe {group_key}. Skipping."
                                )
                                errors += 1
                                continue
                        except (ValueError, TypeError, InvalidOperation):
                            logger.warning(
                                f"Invalid quantity value {row['quantity']} for ingredient {row['ingredient']} in recipe {group_key}. Skipping."
                            )
                            errors += 1
                            continue

                        # Get or create unit of measure
                        unit_name = str(row.get("unit_of_recipe", "")).strip()
                        if not unit_name:
                            # Use ingredient's default unit if not specified
                            unit_of_measure = ingredient.unit_of_measure
                        else:
                            unit_of_measure, _ = UnitOfMeasure.objects.get_or_create(
                                name=unit_name,
                                defaults={
                                    "abbreviation": unit_name,
                                    "description": f"Unit: {unit_name}",
                                },
                            )

                        # Get or create recipe ingredient
                        recipe_ingredient, created = (
                            RecipeIngredient.objects.get_or_create(
                                recipe=recipe,
                                ingredient=ingredient,
                                defaults={
                                    "quantity": quantity,
                                    "main_ingredient": row.get(
                                        "main_ingredient", False
                                    ),
                                    "unit_of_recipe": unit_of_measure,
                                },
                            )
                        )

                        if created:
                            created_ingredients += 1
                            logger.info(
                                f"Created ingredient {ingredient.name} for recipe {group_key}"
                            )
                        else:
                            # Update existing ingredient
                            recipe_ingredient.quantity = quantity
                            recipe_ingredient.main_ingredient = row.get(
                                "main_ingredient", False
                            )
                            recipe_ingredient.unit_of_recipe = unit_of_measure
                            recipe_ingredient.save()
                            updated_ingredients += 1
                            logger.info(
                                f"Updated ingredient {ingredient.name} for recipe {group_key}"
                            )

                    except Exception as e:
                        errors += 1
                        error_msg = f"Error loading recipe ingredient at row {idx + 1}: {str(e)}"
                        self.log_error(error_msg)

            except Exception as e:
                errors += 1
                error_msg = f"Error loading recipe {group_key}: {str(e)}"
                self.log_error(error_msg)

        self.created_count = created_recipes + created_ingredients
        self.updated_count = updated_recipes + updated_ingredients
        self.error_count = errors

        return {
            "recipes_created": created_recipes,
            "recipes_updated": updated_recipes,
            "ingredients_created": created_ingredients,
            "ingredients_updated": updated_ingredients,
            "errors": errors,
        }

    def _load_product_cost_history(self) -> Dict[str, Any]:
        """Load product cost history with unit conversions handled by UnitConversionService"""

        from apps.analytics.models import ProductCostHistory
        from apps.restaurant_data.models import ConsolidatedPurchases
        from data_engineering.utils.unit_conversion import unit_conversion_service

        created = 0
        updated = 0
        errors = 0

        # Initialize services
        unit_service = unit_conversion_service
        type_service = ProductTypeAssignmentService()

        # Get consolidated purchases data (this should already have unit conversions applied)
        consolidated_purchases = ConsolidatedPurchases.objects.all()

        for purchase in consolidated_purchases:
            try:
                # Get or create ProductType for this product
                product_type = type_service.get_or_create_product_type(purchase.product)

                # Get the actual unit used in recipes for this product
                recipe_unit = self._get_recipe_unit_for_product(purchase.product)

                # Calculate conversion factor from purchase unit to recipe unit
                conversion_factor = unit_service.get_conversion_factor(
                    from_unit=purchase.unit_of_purchase,
                    to_unit=recipe_unit,
                    product=purchase.product,
                )

                # If conversion factor is None, use 1.0 as fallback
                if conversion_factor is None:
                    conversion_factor = Decimal("1.0")
                    logger.warning(
                        f"No conversion factor found for {purchase.product.name} from {purchase.unit_of_purchase.name} to {recipe_unit.name}, using 1.0"
                    )

                # Calculate recipe quantity
                recipe_quantity = purchase.quantity_purchased * conversion_factor

                # Calculate unit cost in recipe units
                try:
                    if recipe_quantity > 0:
                        unit_cost_in_recipe_units = (
                            purchase.total_cost / recipe_quantity
                        )
                    else:
                        unit_cost_in_recipe_units = Decimal("0")
                except (InvalidOperation, ZeroDivisionError):
                    # Fallback if there's a decimal operation error
                    unit_cost_in_recipe_units = Decimal("0")
                    logger.warning(
                        f"Invalid decimal operation for {purchase.product.name}, using 0 as unit cost"
                    )

                # Check for existing cost history record
                existing_history = ProductCostHistory.objects.filter(
                    product=purchase.product,
                    purchase_date=purchase.purchase_date,
                    unit_of_purchase=purchase.unit_of_purchase,
                ).first()

                if existing_history:
                    # Update existing record
                    existing_history.quantity_ordered = purchase.quantity_purchased
                    existing_history.total_amount = purchase.total_cost
                    existing_history.unit_of_recipe = recipe_unit
                    existing_history.recipe_conversion_factor = conversion_factor
                    existing_history.recipe_quantity = recipe_quantity
                    existing_history.unit_cost_in_recipe_units = (
                        unit_cost_in_recipe_units
                    )
                    existing_history.product_category = product_type
                    existing_history.save()
                    updated += 1
                    logger.info(f"Updated cost history for {purchase.product.name}")
                else:
                    # Create new record
                    ProductCostHistory.objects.create(
                        product=purchase.product,
                        purchase_date=purchase.purchase_date,
                        quantity_ordered=purchase.quantity_purchased,
                        unit_of_purchase=purchase.unit_of_purchase,
                        total_amount=purchase.total_cost,
                        unit_of_recipe=recipe_unit,
                        recipe_conversion_factor=conversion_factor,
                        recipe_quantity=recipe_quantity,
                        unit_cost_in_recipe_units=unit_cost_in_recipe_units,
                        product_category=product_type,
                        # Legacy field for compatibility
                        cost_per_unit=unit_cost_in_recipe_units,
                        # Default fields
                        weight_factor=Decimal("1.0000"),
                        is_active=True,
                    )
                    created += 1
                    logger.info(f"Created cost history for {purchase.product.name}")

            except Exception as e:
                errors += 1
                error_msg = (
                    f"Error loading cost history for {purchase.product.name}: {str(e)}"
                )
                self.log_error(error_msg)

        self.created_count = created
        self.updated_count = updated
        self.error_count = errors

        return {
            "created": created,
            "updated": updated,
            "errors": errors,
        }

    def _get_recipe_unit_for_product(self, product: Product) -> UnitOfMeasure:
        """Get the actual recipe unit for a product by checking RecipeIngredient data"""

        # First, check if this product is used in any recipes
        from apps.recipes.models import RecipeIngredient

        recipe_ingredient = RecipeIngredient.objects.filter(ingredient=product).first()

        if recipe_ingredient and recipe_ingredient.unit_of_recipe:
            # Use the unit from the recipe ingredient
            return recipe_ingredient.unit_of_recipe

        # If no recipe ingredient found, check the StandardKitchenUnit system
        from data_engineering.utils.unit_conversion import unit_conversion_service

        standard_unit = unit_conversion_service.get_standard_kitchen_unit(
            product=product, category=product.purchase_category
        )

        if standard_unit:
            return standard_unit

        # If no standard unit found, use the product's purchase unit
        if product.unit_of_measure:
            return product.unit_of_measure
