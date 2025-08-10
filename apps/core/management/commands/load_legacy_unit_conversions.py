from django.core.management.base import BaseCommand
from django.db import transaction

from data_engineering.utils.unit_conversion import unit_conversion_service


class Command(BaseCommand):
    help = "Load legacy unit conversion rules into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating the conversions",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No conversions will be created")
            )

        try:
            # Preview the conversions that would be created
            legacy_conversions = [
                # Weight conversions
                ("kg", "g", "1000"),  # 1 kg = 1000 g
                ("g", "kg", "0.001"),  # 1 g = 0.001 kg
                # Volume conversions
                ("l", "ml", "1000"),  # 1 liter = 1000 ml
                ("ml", "l", "0.001"),  # 1 ml = 0.001 liter
                # Common kitchen conversions
                ("kg", "unit", "1"),  # For items sold by piece but measured in kg
                ("l", "unit", "1"),  # For liquid items
                ("g", "unit", "1"),  # For small items
                ("ml", "unit", "1"),  # For small liquid items
            ]

            self.stdout.write(f"Found {len(legacy_conversions)} unit conversions:")

            for from_unit, to_unit, factor in legacy_conversions:
                self.stdout.write(f"  {from_unit} → {to_unit} × {factor}")

            if not dry_run:
                with transaction.atomic():
                    # Use the service to load legacy unit conversions
                    result = (
                        unit_conversion_service.load_legacy_unit_conversions_and_standards()
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\nSuccessfully loaded {result['conversions_created']} conversions and {result['standards_created']} standards!"
                        )
                    )

            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\nWould create unit conversion rules (dry run mode)"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading conversions: {str(e)}"))
