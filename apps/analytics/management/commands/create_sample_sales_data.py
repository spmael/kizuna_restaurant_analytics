from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.analytics.models import DailySummary


class Command(BaseCommand):
    help = "Create sample sales data for testing the Revenue Journey dashboard"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample sales data...")

        with transaction.atomic():
            # Create sample data for the last 7 days
            for i in range(7):
                target_date = date.today() - timedelta(days=i + 1)

                # Check if data already exists for this date
                if DailySummary.objects.filter(date=target_date).exists():
                    self.stdout.write(
                        f"Data already exists for {target_date}, skipping..."
                    )
                    continue

                # Create sample daily summary
                daily_summary = DailySummary.objects.create(
                    date=target_date,
                    total_sales=50000 + (i * 5000),  # Increasing sales each day
                    total_orders=20 + i,
                    total_customers=25 + i,
                    registered_customers=15 + i,
                    walk_in_customers=10 + i,
                    average_order_value=2500 + (i * 100),
                    average_ticket_size=2000 + (i * 80),
                    total_food_cost=30000 + (i * 3000),
                    food_cost_percentage=60.0 - (i * 0.5),  # Decreasing cost percentage
                    gross_profit=20000 + (i * 2000),
                )

                self.stdout.write(
                    f"Created sample data for {target_date}: {daily_summary.total_sales} FCFA"
                )

        self.stdout.write(self.style.SUCCESS("Sample sales data created successfully!"))
        self.stdout.write(
            "You can now view the Revenue Journey dashboard with sample data."
        )
