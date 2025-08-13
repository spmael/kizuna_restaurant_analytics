from datetime import date
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from data_engineering.loaders.database_loader import RestaurantDataLoader


class Command(BaseCommand):
    help = _("Regenerate consolidated purchases from purchase data")

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help=_("Specific date to regenerate (YYYY-MM-DD format)"),
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help=_("Regenerate all consolidated purchases"),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=_("Show what would be regenerated without actually doing it"),
        )

    def handle(self, *args, **options):
        target_date = options.get("date")
        regenerate_all = options.get("all", False)
        dry_run = options.get("dry-run", False)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Create loader instance
        loader = RestaurantDataLoader(user=None)

        if target_date:
            # Regenerate for specific date
            try:
                year, month, day = map(int, target_date.split("-"))
                target_date_obj = date(year, month, day)
                
                self.stdout.write(
                    f"Regenerating consolidated purchases for {target_date}..."
                )
                
                if not dry_run:
                    # Set affected dates to only the target date
                    loader.affected_dates = {target_date_obj}
                    result = loader._load_consolidated_purchases()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Regenerated {result['created']} consolidated purchases for {target_date}"
                        )
                    )
                else:
                    self.stdout.write(f"Would regenerate consolidated purchases for {target_date}")
                    
            except ValueError:
                self.stdout.write(
                    self.style.ERROR("Invalid date format. Use YYYY-MM-DD")
                )
                return
                
        elif regenerate_all:
            # Regenerate all consolidated purchases
            self.stdout.write("Regenerating all consolidated purchases...")
            
            if not dry_run:
                # Clear all and regenerate
                loader.affected_dates = set()  # Empty set means regenerate all
                result = loader._load_consolidated_purchases()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Regenerated {result['created']} consolidated purchases"
                    )
                )
            else:
                self.stdout.write("Would regenerate all consolidated purchases")
                
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Please specify either --date YYYY-MM-DD or --all"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS("🎉 Consolidated purchases regeneration completed!")
        )
