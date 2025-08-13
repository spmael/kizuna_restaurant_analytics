from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from apps.restaurant_data.models import ConsolidatedPurchases, Product, UnitOfMeasure


class Command(BaseCommand):
    """
    Recreate the missing Huile de Palme ConsolidatedPurchases record for April 4, 2025.
    """

    help = _("Recreate missing Huile de Palme ConsolidatedPurchases record")

    def handle(self, *args, **options):
        try:
            target_date = date(2025, 4, 4)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Recreating Huile de Palme ConsolidatedPurchases for {target_date}"
                )
            )

            # Find the products and units
            palme_product = Product.objects.filter(name__icontains="Huile de Palme").first()
            l_unit = UnitOfMeasure.objects.filter(name="l").first()

            if not palme_product:
                self.stdout.write(
                    self.style.ERROR("Huile de Palme product not found!")
                )
                return

            if not l_unit:
                self.stdout.write(
                    self.style.ERROR("Liter unit not found!")
                )
                return

            # Check if record already exists
            existing_record = ConsolidatedPurchases.objects.filter(
                product=palme_product,
                purchase_date=target_date
            ).first()

            if existing_record:
                self.stdout.write(
                    self.style.WARNING(
                        f"Record already exists: {existing_record.quantity_purchased} {existing_record.unit_of_purchase.name} for {existing_record.total_cost} FCFA"
                    )
                )
                return

            # Create the corrected record
            # Original: 12.00 ml for 18,000.00 FCFA
            # Convert to: 0.012 l for 18,000.00 FCFA
            corrected_purchase = ConsolidatedPurchases.objects.create(
                product=palme_product,
                purchase_date=target_date,
                quantity_purchased=Decimal("0.012"),  # 12 ml = 0.012 l
                unit_of_purchase=l_unit,  # Now in liters
                total_cost=Decimal("18000.00"),
                unit_of_recipe=l_unit,  # Recipe unit is also liters
                consolidation_applied=True,
                consolidated_product_names=["Huile de tournesol"]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created record: {corrected_purchase.quantity_purchased} {corrected_purchase.unit_of_purchase.name} for {corrected_purchase.total_cost} FCFA"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error recreating record: {str(e)}")
            )
            raise
