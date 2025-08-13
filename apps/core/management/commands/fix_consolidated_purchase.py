from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from apps.restaurant_data.models import ConsolidatedPurchases, Product, UnitOfMeasure
from data_engineering.utils.product_consolidation import product_consolidation_service


class Command(BaseCommand):
    """
    Fix ConsolidatedPurchases record for April 4, 2025 to handle unit conversion properly.
    """

    help = _("Fix ConsolidatedPurchases record for April 4, 2025")

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default="2025-04-04",
            help="Date to fix (YYYY-MM-DD format)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without saving changes to the database.",
        )

    def handle(self, *args, **options):
        target_date = options.get("date")
        dry_run = options.get("dry-run", False)

        try:
            # Parse the date
            year, month, day = map(int, target_date.split("-"))
            target_date_obj = date(year, month, day)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Fixing ConsolidatedPurchases for {target_date}"
                )
            )

            # Find the problematic record
            problematic_purchases = ConsolidatedPurchases.objects.filter(
                purchase_date=target_date_obj,
                product__name__icontains="Huile"
            )

            if not problematic_purchases.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"No Huile purchases found for {target_date}"
                    )
                )
                return

            self.stdout.write(
                f"Found {problematic_purchases.count()} Huile purchases for {target_date}"
            )

            for purchase in problematic_purchases:
                self.stdout.write(
                    f"  {purchase.product.name}: {purchase.quantity_purchased} {purchase.unit_of_purchase.name} - {purchase.total_cost} FCFA"
                )

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        "Dry run mode - no changes will be made"
                    )
                )
                return

            # Delete the problematic records
            deleted_count = problematic_purchases.count()
            problematic_purchases.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_count} problematic ConsolidatedPurchases records"
                )
            )

            # Now we need to recreate them with proper consolidation
            # This would require re-running the data processing pipeline for that date
            # For now, let's create a manual fix for the specific case

            # Find Huile de tournesol product
            tournesol_product = Product.objects.filter(
                name__icontains="tournesol"
            ).first()

            if tournesol_product:
                # Find the target Huile de Palme product
                palme_product = Product.objects.filter(
                    name__icontains="Huile de Palme"
                ).first()

                if palme_product:
                    # Get the liter unit
                    l_unit = UnitOfMeasure.objects.filter(name="l").first()

                    if l_unit:
                        # Create the corrected record
                        # Original: 12.00 ml for 18,000.00 FCFA
                        # Convert to: 0.012 l for 18,000.00 FCFA
                        corrected_purchase = ConsolidatedPurchases.objects.create(
                            product=palme_product,  # Consolidated into Huile de Palme
                            purchase_date=target_date_obj,
                            quantity_purchased=Decimal("0.012"),  # 12 ml = 0.012 l
                            unit_of_purchase=l_unit,  # Now in liters
                            total_cost=Decimal("18000.00"),
                            unit_of_recipe=l_unit,  # Recipe unit is also liters
                            consolidation_applied=True,
                            consolidated_product_names=["Huile de tournesol"]
                        )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created corrected record: {corrected_purchase.quantity_purchased} {corrected_purchase.unit_of_purchase.name} for {corrected_purchase.total_cost} FCFA"
                            )
                        )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully fixed ConsolidatedPurchases for {target_date}"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error fixing ConsolidatedPurchases: {str(e)}")
            )
            raise
