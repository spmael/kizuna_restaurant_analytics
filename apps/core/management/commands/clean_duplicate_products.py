from django.core.management.base import BaseCommand

from apps.restaurant_data.models import Product, Purchase, Sales


class Command(BaseCommand):
    help = "Clean up duplicate products by merging them and updating related records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without actually doing it",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Find duplicates (case-insensitive)
        # First, get all product names and group by lowercase
        all_products = Product.objects.all()
        name_groups = {}

        for product in all_products:
            lowercase_name = product.name.lower()
            if lowercase_name not in name_groups:
                name_groups[lowercase_name] = []
            name_groups[lowercase_name].append(product)

        # Find groups with multiple products (case-insensitive duplicates)
        duplicates = []
        for lowercase_name, products in name_groups.items():
            if len(products) > 1:
                duplicates.append(
                    {
                        "name": lowercase_name,
                        "count": len(products),
                        "products": products,
                    }
                )

        # Sort by count (highest first)
        duplicates.sort(key=lambda x: x["count"], reverse=True)

        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicate products found!"))
            return

        self.stdout.write(f"Found {len(duplicates)} duplicate product names:")

        total_merged = 0

        for duplicate_info in duplicates:
            product_name = duplicate_info["name"]
            count = duplicate_info["count"]
            products = duplicate_info["products"]

            self.stdout.write(f'\nProcessing: "{product_name}" ({count} instances)')

            if len(products) <= 1:
                continue

            # Keep the first product (lowest ID) and merge others into it
            products.sort(key=lambda p: p.id)  # Sort by ID
            primary_product = products[0]
            duplicate_products = products[1:]

            self.stdout.write(
                f"  Keeping: {primary_product.name} (ID: {primary_product.id})"
            )

            # Count related records
            total_purchases = 0
            total_sales = 0

            for duplicate_product in duplicate_products:
                purchases_count = Purchase.objects.filter(
                    product=duplicate_product
                ).count()
                sales_count = Sales.objects.filter(product=duplicate_product).count()
                total_purchases += purchases_count
                total_sales += sales_count

                self.stdout.write(
                    f"  Merging: {duplicate_product.name} (ID: {duplicate_product.id})"
                )
                self.stdout.write(f"    - {purchases_count} purchases")
                self.stdout.write(f"    - {sales_count} sales")

                if not dry_run:
                    # Update all related records to point to the primary product
                    Purchase.objects.filter(product=duplicate_product).update(
                        product=primary_product
                    )
                    Sales.objects.filter(
                        product=duplicate_product
                    ).delete()  # Delete sales records

                    # Delete the duplicate product
                    duplicate_product.delete()

            self.stdout.write(
                f"  Total records moved: {total_purchases} purchases, {total_sales} sales"
            )
            total_merged += len(duplicate_products)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDRY RUN: Would merge {total_merged} duplicate products"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully merged {total_merged} duplicate products"
                )
            )

            # Final count
            final_count = Product.objects.count()
            self.stdout.write(f"Final product count: {final_count}")
