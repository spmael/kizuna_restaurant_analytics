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
        self.affected_product_names = getattr(self, "affected_product_names", set())
        self.affected_recipe_names = getattr(self, "affected_recipe_names", set())

        try:
            self._prepare_caches(data)
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

                # Load recipe versions and cost snapshots after recipes are loaded
                if "recipes" in data:
                    results["recipe_versions"] = self._load_recipe_versions()
                    results["recipe_cost_snapshots"] = (
                        self._load_recipe_cost_snapshots()
                    )

        except Exception as e:
            self.log_error(f"Error loading data: {str(e)}")
            raise

        self.log_loader_stats()
        return results

    def _prepare_caches(self, data: Dict[str, pd.DataFrame]):
        """Prepare lookup caches and prefetch existing rows to avoid per-row queries"""
        # Product cache
        self._product_by_name = {
            p.name.lower(): p
            for p in Product.objects.all().only(
                "id",
                "name",
                "unit_of_measure",
                "current_selling_price",
                "current_cost_per_unit",
                "current_stock",
            )
        }
        # Categories and units
        self._purchases_cat_cache = {c.name: c for c in PurchasesCategory.objects.all()}
        self._sales_cat_cache = {c.name: c for c in SalesCategory.objects.all()}
        self._uom_cache = {u.name: u for u in UnitOfMeasure.objects.all()}

        # Helper to normalize names list
        def _names(df: pd.DataFrame, col: str) -> list:
            try:
                return [
                    str(n).strip().lower()
                    for n in df[col].dropna().astype(str).unique().tolist()
                ]
            except Exception:
                return []

        # Prefetch existing purchases
        self._existing_purchases = {}
        if (
            "purchases" in data
            and data["purchases"] is not None
            and not data["purchases"].empty
        ):
            dates = data["purchases"]["purchase_date"].unique().tolist()
            names = _names(data["purchases"], "product")
            prod_ids = [
                self._product_by_name[n].id for n in names if n in self._product_by_name
            ]
            for obj in Purchase.objects.filter(
                purchase_date__in=dates, product_id__in=prod_ids
            ).only(
                "id", "purchase_date", "product_id", "total_cost", "quantity_purchased"
            ):
                self._existing_purchases[(obj.purchase_date, obj.product_id)] = obj

        # Prefetch existing sales
        self._existing_sales = {}
        if "sales" in data and data["sales"] is not None and not data["sales"].empty:
            dates = data["sales"]["sale_date"].unique().tolist()
            names = _names(data["sales"], "product")
            prod_ids = [
                self._product_by_name[n].id for n in names if n in self._product_by_name
            ]
            for obj in Sales.objects.filter(
                sale_date__in=dates, product_id__in=prod_ids
            ).only(
                "id",
                "sale_date",
                "product_id",
                "order_number",
                "total_sale_price",
                "quantity_sold",
                "unit_sale_price",
                "customer",
            ):
                key = (obj.sale_date, obj.product_id, str(obj.order_number))
                self._existing_sales[key] = obj

    def _load_products(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Load products into database"""

        created = 0
        updated = 0
        errors = 0

        for idx, row in df.iterrows():
            try:
                # Get or create purchases and sales categories
                def _normalize_name(value, default_value):
                    try:
                        if value is None:
                            return default_value
                        name = str(value).strip()
                        if not name or name.lower() == "nan":
                            return default_value
                        return name
                    except Exception:
                        return default_value

                purchases_category_name = _normalize_name(
                    row.get("purchase_category"), "Unknown"
                )
                sales_category_name = _normalize_name(
                    row.get("sales_category"), "Unknown"
                )

                purchases_category = self._purchases_cat_cache.get(
                    purchases_category_name
                )
                if not purchases_category:
                    purchases_category = PurchasesCategory.objects.create(
                        name=purchases_category_name,
                        name_fr=purchases_category_name,
                    )
                    self._purchases_cat_cache[purchases_category_name] = (
                        purchases_category
                    )

                sales_category = self._sales_cat_cache.get(sales_category_name)
                if not sales_category:
                    sales_category = SalesCategory.objects.create(
                        name=sales_category_name,
                        name_fr=sales_category_name,
                    )
                    self._sales_cat_cache[sales_category_name] = sales_category

                # Get or create unit of measure
                unit_of_measure_name = _normalize_name(
                    row.get("unit_of_measure"), "unit"
                )
                unit_of_measure = self._uom_cache.get(unit_of_measure_name)
                if not unit_of_measure:
                    unit_of_measure = UnitOfMeasure.objects.create(
                        name=unit_of_measure_name,
                        abbreviation=unit_of_measure_name,
                        name_fr=unit_of_measure_name,
                    )
                    self._uom_cache[unit_of_measure_name] = unit_of_measure

                # Get or create product - use cache (case-insensitive)
                product_name = row["name"]
                key_name = str(product_name).lower()
                product = self._product_by_name.get(key_name)

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
                    self._product_by_name[key_name] = product
                    self.log_info(f"Created new product: {product_name}")
                else:
                    # Update existing product only if changed
                    changed = False
                    if product.current_cost_per_unit != row["current_cost_per_unit"]:
                        product.current_cost_per_unit = row["current_cost_per_unit"]
                        changed = True
                    if (
                        "current_selling_price" in row
                        and row["current_selling_price"] is not None
                        and product.current_selling_price
                        != row["current_selling_price"]
                    ):
                        product.current_selling_price = row["current_selling_price"]
                        changed = True
                    if (
                        "current_stock" in row
                        and row["current_stock"] is not None
                        and product.current_stock != row["current_stock"]
                    ):
                        product.current_stock = row["current_stock"]
                        changed = True
                    if changed:
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
                # Find product from cache
                product = self._product_by_name.get(str(row["product"]).lower())

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

                # Get order number from order_number column (mapped from "Commander" in transformer)
                order_number = str(row.get("order_number", f"order_{idx}"))

                # Check for existing sale with same order number, date, and product
                key = (row["sale_date"], product.id, order_number)
                existing_sale = self._existing_sales.get(key)

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
                            existing_sale.customer = row.get(
                                "customer", ""
                            )  # Add missing customer field
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
                        existing_sale.customer = row.get(
                            "customer", ""
                        )  # Add missing customer field
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
                        customer=row.get("customer", ""),  # Add missing customer field
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

                # Only process purchases from affected dates
                purchases = Purchase.objects.select_related("product").filter(
                    purchase_date__in=self.affected_dates
                )
                logger.info(
                    f"Processing {purchases.count()} purchases from affected dates"
                )
            else:
                # If we don't have specific affected dates, clear all and regenerate
                # This is a fallback for backward compatibility
                ConsolidatedPurchases.objects.all().delete()
                logger.info("Cleared all consolidated purchases (fallback mode)")

                # Process all purchases
                purchases = Purchase.objects.select_related("product").all()
                logger.info(
                    f"Processing all {purchases.count()} purchases (fallback mode)"
                )

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
                f"Created {created_count} consolidated purchase records (incremental update)"
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

                # Only process sales from affected dates
                sales = Sales.objects.select_related("product").filter(
                    sale_date__in=self.affected_dates
                )
                logger.info(f"Processing {sales.count()} sales from affected dates")
            else:
                # If we don't have specific affected dates, clear all and regenerate
                # This is a fallback for backward compatibility
                ConsolidatedSales.objects.all().delete()
                logger.info("Cleared all consolidated sales (fallback mode)")

                # Process all sales
                sales = Sales.objects.select_related("product").all()
                logger.info(f"Processing all {sales.count()} sales (fallback mode)")

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
                f"Created {created_count} consolidated sales records (incremental update)"
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

        # Scope by affected names if provided
        affected_names = getattr(self, "affected_product_names", None)
        if affected_names:
            scoped_products = []
            for name in affected_names:
                p = self._product_by_name.get(name)
                if p:
                    scoped_products.append(p)
            all_products = scoped_products
        else:
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
                logger.debug(
                    f"Legacy rules already loaded (consolidation: {consolidation_count}, conversions: {conversion_count}). Skipping."
                )
                return

            logger.debug(
                "Loading legacy consolidation rules and unit conversions after products..."
            )

            # Load consolidation rules if they don't exist
            if consolidation_count == 0:
                logger.info("Loading legacy consolidation rules (first-time only)...")
                product_consolidation_service.load_legacy_consolidation_rules()
                new_consolidation_count = ProductConsolidation.objects.count()
                logger.info(
                    f"Total consolidation rules present: {new_consolidation_count}"
                )
            else:
                logger.debug(
                    f"Consolidation rules already exist ({consolidation_count} rules)"
                )

            # Load unit conversions and standards if they don't exist
            if conversion_count == 0:
                logger.info(
                    "Loading legacy unit conversions and standards (first-time only)..."
                )
                result = (
                    unit_conversion_service.load_legacy_unit_conversions_and_standards()
                )
                logger.info(
                    f"Loaded {result['conversions_created']} conversions and {result['standards_created']} standards"
                )
            else:
                logger.debug(
                    f"Unit conversions already exist ({conversion_count} conversions)"
                )

            logger.debug("Legacy rules loading completed successfully")

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
                            logger.debug(
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
                            logger.debug(
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
        # Only process purchases from affected dates if we have them
        if hasattr(self, "affected_dates") and self.affected_dates:
            # Clear cost history for affected dates only
            ProductCostHistory.objects.filter(
                purchase_date__in=self.affected_dates
            ).delete()
            logger.info(
                f"Cleared cost history for affected dates: {self.affected_dates}"
            )

            # Only process consolidated purchases from affected dates
            consolidated_purchases = ConsolidatedPurchases.objects.filter(
                purchase_date__in=self.affected_dates
            )
            logger.info(
                f"Processing {consolidated_purchases.count()} consolidated purchases from affected dates"
            )
        else:
            # If we don't have specific affected dates, clear all and regenerate
            # This is a fallback for backward compatibility
            ProductCostHistory.objects.all().delete()
            logger.info("Cleared all cost history (fallback mode)")

            # Process all consolidated purchases
            consolidated_purchases = ConsolidatedPurchases.objects.all()
            logger.info(
                f"Processing all {consolidated_purchases.count()} consolidated purchases (fallback mode)"
            )

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

    def _load_recipe_versions(self) -> Dict[str, Any]:
        """Track recipe changes and create version history"""
        try:
            from datetime import date

            from django.db import IntegrityError, transaction

            from apps.recipes.models import Recipe, RecipeVersion

            logger.info("Starting recipe version tracking...")

            created_versions = 0
            updated_versions = 0
            errors = 0

            # Get recipes processed in this upload (scoped if provided)
            affected_recipes = getattr(self, "affected_recipe_names", None)
            if affected_recipes:
                recipes = Recipe.objects.filter(
                    dish_name__in=list({r for r in affected_recipes})
                )
            else:
                recipes = Recipe.objects.all()

            for recipe in recipes:
                try:
                    with transaction.atomic():
                        # Get current recipe ingredients as a hash for comparison
                        current_ingredients = self._get_recipe_ingredients_hash(recipe)

                        # Latest version (any date)
                        latest_version = (
                            RecipeVersion.objects.filter(recipe=recipe)
                            .order_by("-effective_date")
                            .first()
                        )

                        today = date.today()
                        # Existing version for today (avoid UNIQUE constraint)
                        existing_today = RecipeVersion.objects.filter(
                            recipe=recipe, effective_date=today
                        ).first()

                        if latest_version:
                            previous_ingredients = latest_version.change_notes

                            if current_ingredients != previous_ingredients:
                                if existing_today:
                                    # Update today's version instead of creating a duplicate
                                    existing_today.change_notes = current_ingredients
                                    existing_today.is_active = True
                                    # Keep version number or bump to next minor
                                    existing_today.version_number = (
                                        existing_today.version_number
                                        or self._get_next_version_number(recipe)
                                    )
                                    existing_today.save()
                                    updated_versions += 1
                                    logger.info(
                                        f"Updated today's version for recipe: {recipe.dish_name}"
                                    )
                                else:
                                    # End the previous active version
                                    latest_version.end_date = today
                                    latest_version.is_active = False
                                    latest_version.save()

                                    # Create new active version for today
                                    new_version_number = self._get_next_version_number(
                                        recipe
                                    )
                                    RecipeVersion.objects.create(
                                        recipe=recipe,
                                        version_number=new_version_number,
                                        effective_date=today,
                                        change_notes=current_ingredients,
                                        is_active=True,
                                    )
                                    created_versions += 1
                                    logger.info(
                                        f"Created new version {new_version_number} for recipe: {recipe.dish_name}"
                                    )
                            else:
                                logger.debug(
                                    f"No changes detected for recipe: {recipe.dish_name}"
                                )
                        else:
                            if existing_today:
                                # Ensure today's initial version is active and carries current state
                                existing_today.change_notes = current_ingredients
                                existing_today.is_active = True
                                existing_today.version_number = (
                                    existing_today.version_number or "1.0"
                                )
                                existing_today.save()
                                updated_versions += 1
                                logger.info(
                                    f"Updated initial version for recipe: {recipe.dish_name}"
                                )
                            else:
                                # First version for this recipe
                                RecipeVersion.objects.create(
                                    recipe=recipe,
                                    version_number="1.0",
                                    effective_date=today,
                                    change_notes=current_ingredients,
                                    is_active=True,
                                )
                                created_versions += 1
                                logger.info(
                                    f"Created initial version 1.0 for recipe: {recipe.dish_name}"
                                )

                except IntegrityError as e:
                    errors += 1
                    error_msg = f"Integrity error during recipe versioning for {recipe.dish_name}: {str(e)}"
                    self.log_error(error_msg)
                except Exception as e:
                    errors += 1
                    error_msg = f"Error creating recipe version for {recipe.dish_name}: {str(e)}"
                    self.log_error(error_msg)

            logger.info(
                f"Recipe version tracking completed: {created_versions} new versions, {updated_versions} updated, {errors} errors"
            )
            return {
                "created": created_versions,
                "updated": updated_versions,
                "errors": errors,
            }

        except Exception as e:
            error_msg = f"Error in recipe version tracking: {str(e)}"
            logger.error(error_msg)
            self.log_error(error_msg)
            return {"created": 0, "updated": 0, "errors": 1}

    def _load_recipe_cost_snapshots(self) -> Dict[str, Any]:
        """Create cost snapshots for all recipes after cost updates"""
        try:
            from decimal import Decimal

            from django.utils import timezone

            from apps.analytics.services.recipe_costing import RecipeCostingService
            from apps.recipes.models import Recipe, RecipeCostSnapshot

            logger.info("Starting recipe cost snapshot creation...")

            created_snapshots = 0
            errors = 0

            # Initialize recipe costing service
            costing_service = RecipeCostingService()

            # Get all active recipes (scoped if provided)
            affected_recipes = getattr(self, "affected_recipe_names", None)
            if affected_recipes:
                recipes = Recipe.objects.filter(
                    is_active=True, dish_name__in=list({r for r in affected_recipes})
                )
            else:
                recipes = Recipe.objects.filter(is_active=True)

            from django.db.models.functions import TruncDate

            today_date = timezone.now().date()

            for recipe in recipes:
                try:
                    # Calculate current recipe costs
                    cost_data = costing_service.calculate_recipe_cost(recipe)

                    # Calculate food cost percentage if selling price exists
                    food_cost_pct = None
                    if (
                        recipe.actual_selling_price_per_portion
                        and recipe.actual_selling_price_per_portion > 0
                    ):
                        food_cost_pct = (
                            cost_data["total_cost_per_portion"]
                            / recipe.actual_selling_price_per_portion
                        ) * 100

                    # Upsert cost snapshot per recipe per day (idempotent)
                    snapshot = (
                        RecipeCostSnapshot.objects.annotate(
                            day=TruncDate("snapshot_date")
                        )
                        .filter(recipe=recipe, day=today_date)
                        .first()
                    )

                    if snapshot:
                        snapshot.base_food_cost_per_portion = cost_data[
                            "base_cost_per_portion"
                        ]
                        snapshot.waste_cost_per_portion = cost_data.get(
                            "waste_cost_per_portion", Decimal("0")
                        )
                        snapshot.labor_cost_per_portion = cost_data.get(
                            "labor_cost_per_portion", Decimal("0")
                        )
                        snapshot.total_cost_per_portion = cost_data[
                            "total_cost_per_portion"
                        ]
                        snapshot.selling_price = recipe.actual_selling_price_per_portion
                        snapshot.food_cost_percentage = food_cost_pct
                        snapshot.calculation_method = "weighted_average"
                        snapshot.notes = "Snapshot updated during ETL processing"
                        snapshot.save()
                    else:
                        RecipeCostSnapshot.objects.create(
                            recipe=recipe,
                            snapshot_date=timezone.now(),
                            base_food_cost_per_portion=cost_data[
                                "base_cost_per_portion"
                            ],
                            waste_cost_per_portion=cost_data.get(
                                "waste_cost_per_portion", Decimal("0")
                            ),
                            labor_cost_per_portion=cost_data.get(
                                "labor_cost_per_portion", Decimal("0")
                            ),
                            total_cost_per_portion=cost_data["total_cost_per_portion"],
                            selling_price=recipe.actual_selling_price_per_portion,
                            food_cost_percentage=food_cost_pct,
                            calculation_method="weighted_average",
                            notes="Snapshot created during ETL processing",
                        )
                        created_snapshots += 1
                    logger.info(
                        f"Upserted cost snapshot for recipe: {recipe.dish_name}"
                    )

                except Exception as e:
                    errors += 1
                    error_msg = (
                        f"Error creating cost snapshot for {recipe.dish_name}: {str(e)}"
                    )
                    self.log_error(error_msg)

            logger.info(
                f"Recipe cost snapshot creation completed: {created_snapshots} snapshots, {errors} errors"
            )
            return {"created": created_snapshots, "errors": errors}

        except Exception as e:
            error_msg = f"Error in recipe cost snapshot creation: {str(e)}"
            logger.error(error_msg)
            self.log_error(error_msg)
            return {"created": 0, "errors": 1}

    def _get_recipe_ingredients_hash(self, recipe) -> str:
        """Generate a hash of recipe ingredients for change detection"""
        try:
            from apps.recipes.models import RecipeIngredient

            # Get all ingredients for this recipe
            ingredients = RecipeIngredient.objects.filter(recipe=recipe).order_by(
                "ingredient__name"
            )

            # Create a hash string from ingredient data
            ingredient_data = []
            for ingredient in ingredients:
                ingredient_data.append(
                    f"{ingredient.ingredient.name}:{ingredient.quantity}:{ingredient.unit_of_recipe.name if ingredient.unit_of_recipe else 'None'}"
                )

            # Sort to ensure consistent hash
            ingredient_data.sort()
            return "|".join(ingredient_data)

        except Exception as e:
            logger.warning(
                f"Error generating recipe hash for {recipe.dish_name}: {str(e)}"
            )
            return ""

    def _get_next_version_number(self, recipe) -> str:
        """Get the next version number for a recipe"""
        try:
            from apps.recipes.models import RecipeVersion

            # Get the latest version number
            latest_version = (
                RecipeVersion.objects.filter(recipe=recipe)
                .order_by("-version_number")
                .first()
            )

            if latest_version:
                # Parse version number (assuming format like "1.0", "1.1", etc.)
                try:
                    version_parts = latest_version.version_number.split(".")
                    major = int(version_parts[0])
                    minor = int(version_parts[1]) if len(version_parts) > 1 else 0
                    return f"{major}.{minor + 1}"
                except (ValueError, IndexError):
                    # Fallback: increment the last version number
                    return f"{latest_version.version_number}.1"
            else:
                return "1.0"

        except Exception as e:
            logger.warning(
                f"Error getting next version number for {recipe.dish_name}: {str(e)}"
            )
            return "1.0"

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
