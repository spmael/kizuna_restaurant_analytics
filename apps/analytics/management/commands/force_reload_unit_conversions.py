from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from data_engineering.utils.unit_conversion import unit_conversion_service


class Command(BaseCommand):
    help = _("Force reload unit conversions with debugging")

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help=_("Clear existing unit conversions before reloading"),
        )

    def handle(self, *args, **options):
        clear_existing = options["clear_existing"]

        self.stdout.write(self.style.SUCCESS("Force reloading unit conversions..."))

        if clear_existing:
            from apps.restaurant_data.models import UnitConversion

            deleted_count = UnitConversion.objects.count()
            UnitConversion.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared {deleted_count} existing unit conversions")
            )

        try:
            # Force reload unit conversions
            result = (
                unit_conversion_service.load_legacy_unit_conversions_and_standards()
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully loaded {result['conversions_created']} conversions and {result['standards_created']} standards"
                )
            )

            # Check if Paprika conversion was created
            from apps.restaurant_data.models import (
                Product,
                UnitConversion,
                UnitOfMeasure,
            )

            paprika_products = Product.objects.filter(name__icontains="paprika")
            unit_measure = UnitOfMeasure.objects.filter(name="unit").first()
            g_measure = UnitOfMeasure.objects.filter(name="g").first()

            if paprika_products.exists() and unit_measure and g_measure:
                for paprika_product in paprika_products:
                    conversion = UnitConversion.objects.filter(
                        product=paprika_product,
                        from_unit=unit_measure,
                        to_unit=g_measure,
                    ).first()

                    if conversion:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✅ Paprika conversion found: {paprika_product.name} → {conversion.conversion_factor}g"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f"❌ No conversion found for {paprika_product.name}"
                            )
                        )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No Paprika products found or unit measures missing"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error reloading unit conversions: {str(e)}")
            )
            raise
