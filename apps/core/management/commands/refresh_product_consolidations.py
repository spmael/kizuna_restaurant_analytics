from __future__ import annotations

import logging
import re
import sys
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand

from apps.restaurant_data.models import Product
from data_engineering.extractors.odoo_extractor import OdooExtractor
from data_engineering.transformers.odoo_data_cleaner import OdooDataTransformer
from data_engineering.utils.product_consolidation import ProductConsolidationService


def normalize_name(name: str) -> str:
    """Normalize a product name to a base key for grouping.
    - lowercase
    - strip
    - remove content in parentheses
    - collapse multiple spaces
    """
    if not name:
        return ""
    n = name.lower().strip()
    # remove parentheses content
    n = re.sub(r"\([^)]*\)", "", n)
    # collapse spaces and punctuation variants
    n = re.sub(r"\s+", " ", n)
    return n.strip()


def group_names(names: List[str]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = defaultdict(list)
    for n in names:
        key = normalize_name(n)
        if key:
            groups[key].append(n)
    return groups


class Command(BaseCommand):
    help = "Propose or apply Product consolidation rules based on a provided Excel export (dry-run by default)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            help="Path to Odoo Excel export. If omitted, uses only DB product names to find duplicates.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply consolidation rules to the database. Default is dry-run (report only).",
        )
        parser.add_argument(
            "--min-group-size",
            type=int,
            default=2,
            help="Minimum group size to consider for consolidation.",
        )

    def handle(self, *args, **options):
        # Improve Windows console behavior for unicode
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        try:
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

        # Suppress verbose INFO logs from data_engineering to avoid encoding issues in console
        previous_levels: Dict[str, int] = {}
        for logger_name in [
            "data_engineering",
            "data_engineering.extractors.odoo_extractor",
            "data_engineering.transformers.odoo_data_cleaner",
        ]:
            lg = logging.getLogger(logger_name)
            previous_levels[logger_name] = lg.level
            lg.setLevel(logging.WARNING)

        file_path: str | None = options.get("file")
        apply_changes: bool = options.get("apply", False)
        min_group: int = options.get("min_group_size", 2)

        self.stdout.write(
            self.style.MIGRATE_HEADING("Analyzing products for consolidation")
        )

        # Step 1: Collect candidate names
        excel_names: List[str] = []
        if file_path:
            try:
                extractor = OdooExtractor(file_path)
                extracted = extractor.extract()
                transformer = OdooDataTransformer()
                transformed = transformer.transform(extracted)
                products_df = transformed.get("products")
                if (
                    products_df is not None
                    and not products_df.empty
                    and "name" in products_df.columns
                ):
                    excel_names = [
                        str(n).strip() for n in products_df["name"].dropna().tolist()
                    ]
                    self.stdout.write(
                        f"Found {len(excel_names)} product names in Excel after transform"
                    )
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Could not parse Excel: {exc}"))

        # Try to read DB names, but proceed if DB is not ready
        db_names: List[str] = []
        try:
            db_names = list(Product.objects.values_list("name", flat=True))
            self.stdout.write(f"Found {len(db_names)} products in DB")
        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping DB names (database not ready or table missing): {exc}"
                )
            )

        # Step 2: Build groups by normalized name
        candidate_names = set(db_names) | set(excel_names)
        groups = group_names(list(candidate_names))

        # Filter groups with size >= min_group and where there is more than one distinct original name
        target_groups: List[Tuple[str, List[str]]] = []
        for key, originals in groups.items():
            unique_originals = sorted(set(originals))
            if len(unique_originals) >= min_group:
                target_groups.append((key, unique_originals))

        if not target_groups:
            self.stdout.write(self.style.SUCCESS("No consolidation candidates found."))
            # Restore logger levels
            for name, lvl in previous_levels.items():
                logging.getLogger(name).setLevel(lvl)
            return

        self.stdout.write(
            self.style.HTTP_INFO(f"Found {len(target_groups)} candidate groups.")
        )

        # Step 3: Report plan and optionally apply
        service = ProductConsolidationService()
        applied = 0
        for key, originals in target_groups:
            # pick primary: prefer exact DB name that matches an Excel cleaned name if any; otherwise the shortest
            primary = originals[0]
            if excel_names:
                preferred = [n for n in originals if n in excel_names]
                if preferred:
                    primary = sorted(preferred, key=len)[0]
            else:
                primary = sorted(originals, key=len)[0]
            consolidate = [n for n in originals if n != primary]

            self.stdout.write(
                f"- Group '{key}': primary='{primary}' consolidates {len(consolidate)} -> {consolidate[:5]}{'...' if len(consolidate) > 5 else ''}"
            )

            if apply_changes and consolidate:
                service.create_consolidation_rule(
                    primary_product_name=primary,
                    consolidated_product_names=consolidate,
                    consolidation_reason=(
                        "auto_from_excel" if file_path else "auto_from_db"
                    ),
                    confidence_score=Decimal("0.9"),
                    notes=f"Auto-generated group key: {key}",
                )
                applied += 1

        # Restore logger levels
        for name, lvl in previous_levels.items():
            logging.getLogger(name).setLevel(lvl)

        if apply_changes:
            self.stdout.write(
                self.style.SUCCESS(f"Applied {applied} consolidation rules.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run only. Re-run with --apply to persist rules."
                )
            )
