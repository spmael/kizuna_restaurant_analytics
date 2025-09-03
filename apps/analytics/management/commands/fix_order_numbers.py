import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext as _

from apps.restaurant_data.models import Sales

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = _("Fix order numbers for all existing sales data")

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=_("Show what would be changed without making changes"),
        )
        parser.add_argument(
            "--file",
            type=str,
            help=_("Path to the original Excel file to extract correct order numbers"),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        file_path = options["file"]

        if not file_path:
            raise CommandError(_("Please provide the original Excel file using --file"))

        self.stdout.write(
            self.style.WARNING("Starting order number fix for all sales data...")
        )

        try:
            # Import the data processing components
            from data_engineering.extractors.odoo_extractor import OdooExtractor
            from data_engineering.transformers.odoo_data_cleaner import (
                OdooDataTransformer,
            )

            # Extract and transform the original data to get correct order numbers
            self.stdout.write("Extracting original data...")
            extractor = OdooExtractor(file_path)
            extracted_data = extractor.extract()

            if not extracted_data or "sales" not in extracted_data:
                raise CommandError(_("No sales data found in the file"))

            # Transform the data
            self.stdout.write("Transforming data...")
            transformer = OdooDataTransformer()
            transformed_data = transformer.transform(extracted_data)

            if not transformed_data or "sales" not in transformed_data:
                raise CommandError(_("Failed to transform sales data"))

            sales_df = transformed_data["sales"]

            # Create a mapping of sale_date + product + quantity + total to order_number
            order_mapping = {}
            for idx, row in sales_df.iterrows():
                key = (
                    str(row.get("sale_date", "")),
                    str(row.get("product", "")),
                    str(row.get("quantity_sold", "")),
                    str(row.get("total_sale_price", "")),
                )
                order_mapping[key] = str(row.get("order_number", ""))

            self.stdout.write(f"Created mapping for {len(order_mapping)} sales records")

            # Get all existing sales
            existing_sales = Sales.objects.all()
            total_sales = existing_sales.count()

            self.stdout.write(f"Found {total_sales} existing sales records to update")

            updated_count = 0
            not_found_count = 0

            with transaction.atomic():
                for sale in existing_sales:
                    # Create the same key used in mapping
                    key = (
                        str(sale.sale_date),
                        str(sale.product.name),
                        str(sale.quantity_sold),
                        str(sale.total_sale_price),
                    )

                    if key in order_mapping:
                        correct_order_number = order_mapping[key]

                        if sale.order_number != correct_order_number:
                            if not dry_run:
                                sale.order_number = correct_order_number
                                sale.save(update_fields=["order_number"])

                            self.stdout.write(
                                f"Updated: {sale.product.name} on {sale.sale_date} "
                                f"from '{sale.order_number}' to '{correct_order_number}'"
                            )
                            updated_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Not found in mapping: {sale.product.name} on {sale.sale_date} "
                                f"(qty: {sale.quantity_sold}, total: {sale.total_sale_price})"
                            )
                        )
                        not_found_count += 1

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"DRY RUN: Would update {updated_count} sales records"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully updated {updated_count} sales records"
                    )
                )

            if not_found_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not find mapping for {not_found_count} sales records"
                    )
                )

        except Exception as e:
            raise CommandError(f"Failed to fix order numbers: {str(e)}")
