from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from apps.analytics.services.services import DailyAnalyticsService


class Command(BaseCommand):
    help = _("Calculate daily statistics for restaurant analytics")

    def add_arguments(self, parser):
        parser.add_argument(
            "--date", type=str, help=_("Specific date to calculate (YYYY-MM-DD format)")
        )
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help=_("Number of days to calculate (backwards from date)"),
        )
        parser.add_argument(
            "--all-data",
            action="store_true",
            help=_("Calculate for all available data"),
        )
        parser.add_argument(
            "--overwrite", action="store_true", help=_("Overwrite existing summaries")
        )

    def handle(self, *args, **options):
        service = DailyAnalyticsService()

        # Determine date range
        if options["all_data"]:
            # Calculate for all sales data up to the latest available sale
            from apps.restaurant_data.models import Sales

            first_sale = Sales.objects.order_by("sale_date").first()
            last_sale = Sales.objects.order_by("sale_date").last()

            if not first_sale:
                raise CommandError(_("No sales data found"))

            start_date = first_sale.sale_date
            end_date = (
                last_sale.sale_date if last_sale else date.today() - timedelta(days=1)
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Calculating for all data: {start_date} to {end_date} (latest sale date)"
                )
            )

        elif options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
                days = options["days"]
                start_date = target_date - timedelta(days=days - 1)
                end_date = target_date
            except ValueError:
                raise CommandError(_("Invalid date format. Use YYYY-MM-DD"))

        else:
            # Default: yesterday
            end_date = date.today() - timedelta(days=1)
            start_date = end_date

        # Calculate summaries
        try:
            summaries = service.calculate_date_range_summaries(start_date, end_date)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully calculated {len(summaries)} daily summaries"
                )
            )

            # Show summary statistics
            for summary in summaries[-5:]:  # Last 5 days
                self.stdout.write(
                    f"{summary.date}: {summary.total_sales:,.0f} FCFA, "
                    f"{summary.total_orders} orders, "
                    f"{summary.food_cost_percentage:.1f}% food cost"
                )

            if service.errors:
                self.stdout.write(
                    self.style.WARNING(f"Errors encountered: {len(service.errors)}")
                )
                for error in service.errors:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))

        except Exception as e:
            raise CommandError(f"Calculation failed: {str(e)}")
