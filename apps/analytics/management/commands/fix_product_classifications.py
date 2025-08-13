from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from apps.restaurant_data.models import Product, ProductType
from data_engineering.utils.product_type_assignment import ProductTypeAssignmentService


class Command(BaseCommand):
    help = _("Fix product classifications for existing data")

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=_("Show what would be changed without making changes"),
        )
        parser.add_argument(
            "--product-id",
            type=str,
            help=_("Fix specific product by ID"),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=_("Force reclassification even if ProductType already exists"),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        product_id = options["product_id"]
        force = options["force"]

        self.stdout.write(self.style.SUCCESS("Starting product classification fix..."))

        # Initialize the service
        service = ProductTypeAssignmentService()

        if product_id:
            # Fix specific product
            try:
                product = Product.objects.get(id=product_id)
                self._fix_product_classification(product, service, dry_run, force)
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Product with ID {product_id} not found")
                )
                return
        else:
            # Fix all products
            products = Product.objects.all()
            total_products = products.count()

            self.stdout.write(f"Found {total_products} products to process")

            fixed_count = 0
            error_count = 0

            for i, product in enumerate(products, 1):
                try:
                    if self._fix_product_classification(
                        product, service, dry_run, force
                    ):
                        fixed_count += 1

                    if i % 100 == 0:
                        self.stdout.write(f"Processed {i}/{total_products} products...")

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing product {product.name}: {str(e)}"
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Classification fix complete. "
                    f"Fixed: {fixed_count}, "
                    f"Errors: {error_count}, "
                    f"Total: {total_products}"
                )
            )

    def _fix_product_classification(self, product, service, dry_run, force):
        """Fix classification for a single product"""

        # Get existing ProductType
        existing_type = ProductType.objects.filter(product=product).first()

        if existing_type:
            # Check if the existing classification is correct
            old_product_type = existing_type.product_type
            new_product_type = service._determine_product_type(product)

            if old_product_type != new_product_type:
                self.stdout.write(
                    f"Product: {product.name} - "
                    f"Old: {old_product_type} -> New: {new_product_type}"
                )

                if not dry_run:
                    existing_type.product_type = new_product_type
                    existing_type.save()
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Fixed product type for {product.name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [DRY RUN] Would fix product type for {product.name}"
                        )
                    )
                return True
            else:
                return False
        else:
            # Create new ProductType
            new_product_type = service._determine_product_type(product)

            self.stdout.write(f"Product: {product.name} - New: {new_product_type}")

            if not dry_run:
                service.get_or_create_product_type(product)
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Created product type for {product.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [DRY RUN] Would create product type for {product.name}"
                    )
                )
            return True
