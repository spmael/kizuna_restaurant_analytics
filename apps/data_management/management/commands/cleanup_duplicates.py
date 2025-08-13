from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from data_engineering.loaders.database_loader import RestaurantDataLoader


class Command(BaseCommand):
    help = _("Clean up duplicate purchases and sales, then regenerate consolidated data")

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=_("Show what would be cleaned up without actually doing it"),
        )
        parser.add_argument(
            "--regenerate-consolidated",
            action="store_true",
            help=_("Regenerate consolidated purchases and sales after cleanup"),
        )

    def handle(self, *args, **options):
        self.stdout.write("🧹 Starting duplicate cleanup process...")

        # Create a loader instance (we need it for the cleanup method)
        loader = RestaurantDataLoader(user=None)  # We don't need user for cleanup

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
            # For dry run, we'll just count potential duplicates
            from apps.restaurant_data.models import Purchase, Sales
            from django.db.models import Count

            # Count potential purchase duplicates
            purchase_duplicates = (
                Purchase.objects.values("purchase_date", "product")
                .annotate(count=Count("id"))
                .filter(count__gt=1)
                .count()
            )

            # Count potential sale duplicates
            sale_duplicates = (
                Sales.objects.values("sale_date", "product")
                .annotate(count=Count("id"))
                .filter(count__gt=1)
                .count()
            )

            self.stdout.write(
                f"Would remove {purchase_duplicates} duplicate purchases"
            )
            self.stdout.write(f"Would remove {sale_duplicates} duplicate sales")

            if options["regenerate_consolidated"]:
                self.stdout.write(
                    "Would regenerate consolidated purchases and sales"
                )

        else:
            # Actually perform the cleanup
            try:
                # Clean up duplicates
                cleanup_results = loader.cleanup_duplicates()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Cleaned up {cleanup_results['purchase_duplicates']} duplicate purchases"
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Cleaned up {cleanup_results['sale_duplicates']} duplicate sales"
                    )
                )

                if options["regenerate_consolidated"]:
                    self.stdout.write("🔄 Regenerating consolidated data...")
                    
                    # Regenerate consolidated purchases
                    consolidated_purchases = loader._load_consolidated_purchases()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Regenerated {consolidated_purchases['created']} consolidated purchases"
                        )
                    )

                    # Regenerate consolidated sales
                    consolidated_sales = loader._load_consolidated_sales()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Regenerated {consolidated_sales['created']} consolidated sales"
                        )
                    )

                    # Regenerate recipe consolidated purchases
                    recipe_consolidated = loader._load_recipe_consolidated_purchases()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Regenerated {recipe_consolidated['created']} recipe consolidated purchases"
                        )
                    )

            except Exception as e:
                raise CommandError(f"Cleanup failed: {str(e)}")

        self.stdout.write(
            self.style.SUCCESS("🎉 Duplicate cleanup process completed!")
        )
