from django.core.management.base import BaseCommand
from django.db import transaction

from data_engineering.utils.product_consolidation import product_consolidation_service
from data_engineering.utils.unit_conversion import unit_conversion_service


class Command(BaseCommand):
    help = "Load all legacy rules (consolidation + unit conversions) manually"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force loading even if rules already exist",
        )

    def handle(self, *args, **options):
        force = options["force"]

        try:
            from apps.restaurant_data.models import ProductConsolidation, UnitConversion

            # Check existing rules
            consolidation_count = ProductConsolidation.objects.count()
            conversion_count = UnitConversion.objects.count()

            self.stdout.write("Current state:")
            self.stdout.write(f"  Consolidation rules: {consolidation_count}")
            self.stdout.write(f"  Unit conversions: {conversion_count}")

            if not force and (consolidation_count > 0 or conversion_count > 0):
                self.stdout.write(
                    self.style.WARNING(
                        "Rules already exist. Use --force to reload them."
                    )
                )
                return

            if force:
                self.stdout.write(
                    self.style.WARNING("FORCE MODE: Clearing existing rules...")
                )
                ProductConsolidation.objects.all().delete()
                UnitConversion.objects.all().delete()

            with transaction.atomic():
                # Load consolidation rules
                self.stdout.write("Loading consolidation rules...")
                product_consolidation_service.load_legacy_consolidation_rules()
                new_consolidation_count = ProductConsolidation.objects.count()

                # Load unit conversions
                self.stdout.write("Loading unit conversions and standards...")
                result = (
                    unit_conversion_service.load_legacy_unit_conversions_and_standards()
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSuccessfully loaded:"
                        f"\n  {new_consolidation_count} consolidation rules"
                        f"\n  {result['conversions_created']} unit conversions"
                        f"\n  {result['standards_created']} kitchen standards"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading rules: {str(e)}"))
            raise
