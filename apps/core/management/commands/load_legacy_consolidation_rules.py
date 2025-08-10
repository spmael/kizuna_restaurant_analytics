from django.core.management.base import BaseCommand
from django.db import transaction

from data_engineering.utils.product_consolidation import (
    ProductConsolidationService,
    product_consolidation_service,
)


class Command(BaseCommand):
    help = (
        "Load legacy product consolidation rules from the old script into the database"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating the rules",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No rules will be created")
            )

        try:
            # Get legacy rules from the service class
            legacy_rules = ProductConsolidationService.get_legacy_rules()

            # Group by primary product for display
            grouped_rules = {}
            for original, primary in legacy_rules.items():
                if primary not in grouped_rules:
                    grouped_rules[primary] = []
                grouped_rules[primary].append(original)

            self.stdout.write(f"Found {len(grouped_rules)} consolidation groups:")

            for primary_product, consolidated_products in grouped_rules.items():
                self.stdout.write(f"\n  {primary_product}:")
                for product in consolidated_products:
                    self.stdout.write(f"    - {product}")

            if not dry_run:
                with transaction.atomic():
                    # Use the service to load legacy rules
                    product_consolidation_service.load_legacy_consolidation_rules()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\nSuccessfully migrated {len(grouped_rules)} legacy consolidation rules!"
                        )
                    )

            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nWould create {len(grouped_rules)} consolidation rules (dry run mode)"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error migrating rules: {str(e)}"))
