import logging
from decimal import Decimal
from typing import List

from apps.restaurant_data.models import Product, ProductConsolidation

logger = logging.getLogger(__name__)


class ProductConsolidationService:
    """Service class for managing product consolidation rules and legacy migration"""

    def __init__(self, **kwargs):
        self.errors = []

    def log_error(self, message: str):
        """Log error message"""
        self.errors.append(message)
        logger.error(message)

    def create_consolidation_rule(
        self,
        primary_product_name: str,
        consolidated_product_names: List[str],
        consolidation_reason: str = "manual_consolidation",
        confidence_score: Decimal = Decimal("0.9"),
        notes: str = "",
    ) -> ProductConsolidation:
        """
        Create a new consolidation rule in the database

        Args:
            primary_product_name: The main product name to consolidate into
            consolidated_product_names: List of product names to be consolidated
            consolidation_reason: Reason for consolidation
            confidence_score: Confidence score (0-1)
            notes: Additional notes

        Returns:
            ProductConsolidation instance
        """
        try:
            # Get primary product (don't create if it doesn't exist)
            primary_product = Product.objects.filter(
                name__iexact=primary_product_name
            ).first()
            if not primary_product:
                self.log_error(
                    f"Primary product '{primary_product_name}' not found in database"
                )
                return None

            # Get consolidated product IDs (only for existing products)
            consolidated_products = []
            similarity_scores = {}

            for product_name in consolidated_product_names:
                product = Product.objects.filter(name__iexact=product_name).first()
                if product:
                    consolidated_products.append(product.id)
                    similarity_scores[str(product.id)] = float(confidence_score)
                else:
                    self.log_error(
                        f"Consolidated product '{product_name}' not found in database"
                    )

            if not consolidated_products:
                self.log_error(
                    f"No valid consolidated products found for rule with primary '{primary_product_name}'"
                )
                return None

            # Create consolidation rule
            consolidation = ProductConsolidation.objects.create(
                primary_product=primary_product,
                consolidated_products=consolidated_products,
                similarity_scores=similarity_scores,
                consolidation_reason=consolidation_reason,
                confidence_score=confidence_score,
                notes=notes,
                is_verified=True,
            )

            logger.info(
                f"Created consolidation rule: {primary_product_name} consolidates {len(consolidated_products)} products"
            )
            return consolidation

        except Exception as e:
            self.log_error(f"Error creating consolidation rule: {str(e)}")
            raise

    @classmethod
    def get_legacy_rules(cls):
        """Get the legacy consolidation rules dictionary"""
        return {
            # Poulet - Consolidations
            "Poulet Cru (Kg)": "Poulet (Entier)",
            "Poulet Cru (kg)": "Poulet (Entier)",
            "Poulet (Unité) (Entier)": "Poulet (Entier)",
            "Poulet (Unité) (Quartier)": "Poulet (Entier)",
            # Ailes de poulet - Consolidations
            "Ailes de Poulet Cru (Kg)": "Ailes de Poulet au paprika",
            "Ailes de Poulet Cru (kg)": "Ailes de Poulet au paprika",
            "Ailes de poulet Cru (Kg)": "Ailes de Poulet au paprika",
            # Filet de bœuf - Consolidations
            "Filet de Bœuf": "FAUX FILET",
            # Pommes de terre - Consolidations
            "Pomme de terre Allumettes": "Pommes de terre",
            "Pommes de terre Allumettes": "Pommes de terre",
            # Mayonnaise/Sauce - Consolidations
            "Mayonnaise ARMANTI": "Sauce Mayo",
            "Mayonnaise Calve 820ml": "Sauce Mayo",
            # huile - consolidation
            "Huile de tournesol": "Huile de Palme",
        }

    def load_legacy_consolidation_rules(self):
        """
        Load the legacy consolidation rules from your old script into the database
        This is a one-time migration function
        """
        legacy_rules = self.get_legacy_rules()

        # Group by primary product
        grouped_rules = {}
        for original, primary in legacy_rules.items():
            if primary not in grouped_rules:
                grouped_rules[primary] = []
            grouped_rules[primary].append(original)

        # Create consolidation rules
        for primary_product, consolidated_products in grouped_rules.items():
            try:
                self.create_consolidation_rule(
                    primary_product_name=primary_product,
                    consolidated_product_names=consolidated_products,
                    consolidation_reason="legacy_migration",
                    confidence_score=Decimal("0.95"),
                    notes="Migrated from legacy consolidation script",
                )
            except Exception as e:
                self.log_error(
                    f"Error creating legacy rule for {primary_product}: {str(e)}"
                )

        logger.info(f"Migrated {len(grouped_rules)} legacy consolidation rules")


# Create a singleton instance for easy access
product_consolidation_service = ProductConsolidationService()
