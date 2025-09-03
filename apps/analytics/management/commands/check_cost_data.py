from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
from apps.analytics.models import DailySummary
from apps.restaurant_data.models import Sales, Purchase
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Check what cost data exists in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to check (default: 7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)
        
        self.stdout.write(f"Checking data for {start_date} to {end_date}")
        
        # Check DailySummary data
        summaries = DailySummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        self.stdout.write(f"\n=== DailySummary Data ===")
        self.stdout.write(f"Found {summaries.count()} daily summaries")
        
        if summaries.exists():
            total_sales = summaries.aggregate(total=Sum('total_sales'))['total'] or 0
            total_food_cost = summaries.aggregate(total=Sum('total_food_cost'))['total'] or 0
            total_waste_cost = summaries.aggregate(total=Sum('waste_cost'))['total'] or 0
            
            self.stdout.write(f"Total sales: {total_sales}")
            self.stdout.write(f"Total food cost: {total_food_cost}")
            self.stdout.write(f"Total waste cost: {total_waste_cost}")
            
            # Show sample data
            sample = summaries.first()
            self.stdout.write(f"\nSample summary for {sample.date}:")
            self.stdout.write(f"  - Total sales: {sample.total_sales}")
            self.stdout.write(f"  - Total food cost: {sample.total_food_cost}")
            self.stdout.write(f"  - Waste cost: {sample.waste_cost}")
            self.stdout.write(f"  - Food cost %: {sample.food_cost_percentage}")
        else:
            self.stdout.write("No daily summaries found")
        
        # Check Sales data
        sales = Sales.objects.filter(
            sale_date__range=[start_date, end_date]
        )
        
        self.stdout.write(f"\n=== Sales Data ===")
        self.stdout.write(f"Found {sales.count()} sales records")
        
        if sales.exists():
            total_sales_revenue = sales.aggregate(total=Sum('total_sale_price'))['total'] or 0
            self.stdout.write(f"Total sales revenue: {total_sales_revenue}")
        
        # Check Purchase data
        purchases = Purchase.objects.filter(
            purchase_date__range=[start_date, end_date]
        )
        
        self.stdout.write(f"\n=== Purchase Data ===")
        self.stdout.write(f"Found {purchases.count()} purchase records")
        
        if purchases.exists():
            total_purchase_cost = purchases.aggregate(total=Sum('total_cost'))['total'] or 0
            self.stdout.write(f"Total purchase cost: {total_purchase_cost}")
        
        self.stdout.write("\n=== Summary ===")
        if summaries.exists() and total_food_cost > 0:
            self.stdout.write("✓ Cost data exists and should be available")
        else:
            self.stdout.write("✗ No cost data found - this is why Chapter 3 shows zeros")
            self.stdout.write("  You need to populate DailySummary records with cost data")
