import datetime
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.analytics.models import ProductCostHistory
from apps.restaurant_data.models import ConsolidatedPurchases
from data_engineering.utils.product_type_assignment import ProductTypeAssignmentService
from data_engineering.utils.unit_conversion import unit_conversion_service


class Command(BaseCommand):
    help = _("Regenerate ProductCostHistory from ConsolidatedPurchases data")

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=_("Show what would be changed without making changes"),
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help=_("Clear existing ProductCostHistory records before regenerating"),
        )
        parser.add_argument(
            "--product-id",
            type=str,
            help=_("Regenerate cost history for specific product by ID"),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        clear_existing = options["clear_existing"]
        product_id = options["product_id"]

        self.stdout.write(
            self.style.SUCCESS("Starting ProductCostHistory regeneration...")
        )

        # Initialize services
        unit_service = unit_conversion_service
        type_service = ProductTypeAssignmentService()

        # Clear existing records if requested
        if clear_existing and not dry_run:
            deleted_count = ProductCostHistory.objects.count()
            ProductCostHistory.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {deleted_count} existing ProductCostHistory records"
                )
            )
        elif clear_existing and dry_run:
            existing_count = ProductCostHistory.objects.count()
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would clear {existing_count} existing ProductCostHistory records"
                )
            )

        # Get consolidated purchases data
        if product_id:
            try:
                from apps.restaurant_data.models import Product

                product = Product.objects.get(id=product_id)
                consolidated_purchases = ConsolidatedPurchases.objects.filter(
                    product=product
                )
                self.stdout.write(
                    f"Processing cost history for product: {product.name}"
                )
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Product with ID {product_id} not found")
                )
                return
        else:
            consolidated_purchases = ConsolidatedPurchases.objects.all()

        total_purchases = consolidated_purchases.count()
        self.stdout.write(f"Found {total_purchases} consolidated purchases to process")

        created = 0
        updated = 0
        errors = 0

        for i, purchase in enumerate(consolidated_purchases, 1):
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
                    self.stdout.write(
                        self.style.WARNING(
                            f"No conversion factor found for {purchase.product.name} from {purchase.unit_of_purchase.name} to {recipe_unit.name}, using 1.0"
                        )
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
                    self.stdout.write(
                        self.style.WARNING(
                            f"Invalid decimal operation for {purchase.product.name}, using 0 as unit cost"
                        )
                    )

                # Convert date to timezone-aware datetime
                purchase_date = purchase.purchase_date
                if isinstance(purchase_date, datetime.date):
                    # Convert date to datetime at midnight
                    purchase_datetime = datetime.datetime.combine(
                        purchase_date, datetime.time.min
                    )
                    purchase_date = timezone.make_aware(purchase_datetime)

                # Check for existing cost history record
                existing_history = ProductCostHistory.objects.filter(
                    product=purchase.product,
                    purchase_date=purchase_date,
                    unit_of_purchase=purchase.unit_of_purchase,
                ).first()

                if existing_history:
                    # Update existing record
                    if not dry_run:
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
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Updated cost history for {purchase.product.name}"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"[DRY RUN] Would update cost history for {purchase.product.name}"
                        )
                        updated += 1
                else:
                    # Create new record
                    if not dry_run:
                        ProductCostHistory.objects.create(
                            product=purchase.product,
                            purchase_date=purchase_date,  # Use timezone-aware date
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
                            quantity_purchased=purchase.quantity_purchased,
                        )
                        created += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created cost history for {purchase.product.name}"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"[DRY RUN] Would create cost history for {purchase.product.name}"
                        )
                        created += 1

                # Progress update
                if i % 100 == 0:
                    self.stdout.write(f"Processed {i}/{total_purchases} purchases...")

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing purchase for {purchase.product.name}: {str(e)}"
                    )
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nProductCostHistory regeneration complete:"
                f"\n  Created: {created}"
                f"\n  Updated: {updated}"
                f"\n  Errors: {errors}"
                f"\n  Total processed: {total_purchases}"
            )
        )

    def _get_recipe_unit_for_product(self, product):
        """Get the unit of measure used in recipes for this product"""
        from apps.recipes.models import RecipeIngredient
        from apps.restaurant_data.models import UnitOfMeasure

        recipe_ingredients = RecipeIngredient.objects.filter(ingredient=product)
        if recipe_ingredients.exists():
            # Get the most common unit used in recipes
            unit_counts = {}
            for ingredient in recipe_ingredients:
                if (
                    ingredient.unit_of_recipe
                ):  # Use unit_of_recipe instead of unit_of_measure
                    unit_name = ingredient.unit_of_recipe.name
                    unit_counts[unit_name] = unit_counts.get(unit_name, 0) + 1

            if unit_counts:
                most_common_unit = max(unit_counts, key=unit_counts.get)
                return UnitOfMeasure.objects.get(name=most_common_unit)

        # Fallback to the product's default unit
        return product.unit_of_measure
