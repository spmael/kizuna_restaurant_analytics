from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from apps.restaurant_data.models import Product, UnitConversion, UnitOfMeasure


class Command(BaseCommand):
    help = _("Test unit conversions and check for specific products")

    def add_arguments(self, parser):
        parser.add_argument(
            "--product-name",
            type=str,
            help=_("Check specific product name"),
        )

    def handle(self, *args, **options):
        product_name = options.get("product_name", "paprika")

        self.stdout.write(
            self.style.SUCCESS(f"Testing unit conversions for product: {product_name}")
        )

        # Check if product exists
        products = Product.objects.filter(name__icontains=product_name)
        self.stdout.write(
            f"Found {products.count()} products with '{product_name}' in name:"
        )

        for product in products:
            self.stdout.write(f"  - {product.name}")

        # Check existing unit conversions
        unit_measure = UnitOfMeasure.objects.filter(name="unit").first()
        g_measure = UnitOfMeasure.objects.filter(name="g").first()

        if unit_measure and g_measure:
            conversions = UnitConversion.objects.filter(
                from_unit=unit_measure, to_unit=g_measure
            )

            self.stdout.write(f"\nFound {conversions.count()} unit→g conversions:")
            for conv in conversions:
                product_name = conv.product.name if conv.product else "GENERAL"
                self.stdout.write(f"  - {product_name}: {conv.conversion_factor}")

        # Test the specific search
        paprika_products = Product.objects.filter(name__icontains="paprika")
        self.stdout.write(
            f"\nProducts with 'paprika' in name: {paprika_products.count()}"
        )
        for p in paprika_products:
            self.stdout.write(f"  - {p.name}")

        # Check all products that might be paprika
        all_products = Product.objects.all()
        paprika_like = [p for p in all_products if "paprika" in p.name.lower()]
        self.stdout.write(
            f"\nProducts with 'paprika' (case-insensitive): {len(paprika_like)}"
        )
        for p in paprika_like:
            self.stdout.write(f"  - {p.name}")
