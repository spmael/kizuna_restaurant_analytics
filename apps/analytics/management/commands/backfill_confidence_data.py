from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.analytics.models import DailySummary
from apps.analytics.services.services import DailyAnalyticsService


class Command(BaseCommand):
    help = "Backfill confidence data for existing DailySummary records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to backfill (default: 30)",
        )
        parser.add_argument(
            "--start-date", type=str, help="Start date for backfill (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--end-date", type=str, help="End date for backfill (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        analytics_service = DailyAnalyticsService()

        # Determine date range
        if options["start_date"] and options["end_date"]:
            start_date = date.fromisoformat(options["start_date"])
            end_date = date.fromisoformat(options["end_date"])
        else:
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=options["days"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfilling confidence data from {start_date} to {end_date}"
            )
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Get summaries to update
        summaries = DailySummary.objects.filter(
            date__gte=start_date, date__lte=end_date
        ).order_by("date")

        self.stdout.write(f"Found {summaries.count()} summaries to process")

        updated_count = 0
        error_count = 0

        for summary in summaries:
            try:
                self.stdout.write(f"Processing {summary.date}...")

                # Recalculate with confidence
                enhanced_cost = (
                    analytics_service._calculate_enhanced_cost_metrics_with_confidence(
                        summary.date
                    )
                )

                if options["dry_run"]:
                    self.stdout.write("  Would update:")
                    self.stdout.write(
                        f'    Conservative cost: {enhanced_cost["total_food_cost_conservative"]}'
                    )
                    self.stdout.write(
                        f'    Confidence level: {enhanced_cost["cogs_confidence_level"]}'
                    )
                    self.stdout.write(
                        f'    Data completeness: {enhanced_cost["data_completeness_percentage"]}%'
                    )
                    self.stdout.write(
                        f'    Missing ingredients: {enhanced_cost["missing_ingredients_count"]}'
                    )
                    self.stdout.write(
                        f'    Estimated ingredients: {enhanced_cost["estimated_ingredients_count"]}'
                    )
                else:
                    # Update fields
                    summary.total_food_cost_conservative = enhanced_cost[
                        "total_food_cost_conservative"
                    ]
                    summary.cogs_confidence_level = enhanced_cost[
                        "cogs_confidence_level"
                    ]
                    summary.data_completeness_percentage = enhanced_cost[
                        "data_completeness_percentage"
                    ]
                    summary.missing_ingredients_count = enhanced_cost[
                        "missing_ingredients_count"
                    ]
                    summary.estimated_ingredients_count = enhanced_cost[
                        "estimated_ingredients_count"
                    ]

                    # Add notes about the update
                    notes = f"Confidence data backfilled on {date.today()}. "
                    notes += f"Confidence: {enhanced_cost['cogs_confidence_level']}, "
                    notes += f"Completeness: {enhanced_cost['data_completeness_percentage']}%"

                    if summary.cogs_calculation_notes:
                        summary.cogs_calculation_notes += f"\n{notes}"
                    else:
                        summary.cogs_calculation_notes = notes

                    summary.save()
                    updated_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(f"  ✅ Updated {summary.date}")
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error updating {summary.date}: {e}")
                )

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("BACKFILL SUMMARY:")
        self.stdout.write(f"  Date range: {start_date} to {end_date}")
        self.stdout.write(f"  Summaries processed: {summaries.count()}")

        if options["dry_run"]:
            self.stdout.write(f"  Would update: {updated_count}")
        else:
            self.stdout.write(f"  Successfully updated: {updated_count}")

        self.stdout.write(f"  Errors: {error_count}")

        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  {error_count} summaries had errors. Check logs for details."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("🎉 All summaries processed successfully!")
            )
