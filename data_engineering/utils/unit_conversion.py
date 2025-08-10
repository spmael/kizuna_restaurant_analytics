import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Tuple

from django.core.cache import cache

if TYPE_CHECKING:
    from apps.restaurant_data.models import UnitOfMeasure

logger = logging.getLogger(__name__)


class UnitConversionService:
    """Service for handling unit conversions with database-driven rules"""

    def __init__(self):
        self.cache_timeout = 300  # 5 minutes cache

    def get_standard_kitchen_unit(
        self, product, category=None
    ) -> Optional["UnitOfMeasure"]:
        """Get the standard kitchen unit for a product or category"""
        from apps.restaurant_data.models import StandardKitchenUnit

        cache_key = f"standard_unit_{product.id if product else 'none'}_{category.id if category else 'none'}"
        standard_unit = cache.get(cache_key)

        if standard_unit is not None:
            return standard_unit

        # Try product-specific standard first (highest priority)
        if product:
            standard = (
                StandardKitchenUnit.objects.filter(product=product, is_active=True)
                .order_by("priority")
                .first()
            )

            if standard:
                cache.set(cache_key, standard.standard_unit, self.cache_timeout)
                return standard.standard_unit

        # Try category-specific standard
        if category:
            standard = (
                StandardKitchenUnit.objects.filter(category=category, is_active=True)
                .order_by("priority")
                .first()
            )

            if standard:
                cache.set(cache_key, standard.standard_unit, self.cache_timeout)
                return standard.standard_unit

        # No standard found
        cache.set(cache_key, None, self.cache_timeout)
        return None

    def get_conversion_factor(
        self, from_unit, to_unit, product=None, category=None
    ) -> Optional[Decimal]:
        """Get conversion factor between two units for a specific product/category"""
        from apps.restaurant_data.models import UnitConversion

        # If units are the same, no conversion needed
        if from_unit == to_unit:
            return Decimal("1.0")

        cache_key = f"conversion_{from_unit.id}_{to_unit.id}_{product.id if product else 'none'}_{category.id if category else 'none'}"
        factor = cache.get(cache_key)

        if factor is not None:
            return factor

        # Try to find conversion rule with priority:
        # 1. Product-specific conversion
        # 2. Category-specific conversion
        # 3. General conversion (no product/category specified)

        conversion = None

        # Try product-specific first
        if product:
            conversion = (
                UnitConversion.objects.filter(
                    from_unit=from_unit,
                    to_unit=to_unit,
                    product=product,
                    is_active=True,
                )
                .order_by("priority")
                .first()
            )

        # Try category-specific if no product-specific found
        if not conversion and category:
            conversion = (
                UnitConversion.objects.filter(
                    from_unit=from_unit,
                    to_unit=to_unit,
                    category=category,
                    is_active=True,
                )
                .order_by("priority")
                .first()
            )

        # Try general conversion if no specific found
        if not conversion:
            conversion = (
                UnitConversion.objects.filter(
                    from_unit=from_unit,
                    to_unit=to_unit,
                    product__isnull=True,
                    category__isnull=True,
                    is_active=True,
                )
                .order_by("priority")
                .first()
            )

        if conversion:
            factor = conversion.conversion_factor
            cache.set(cache_key, factor, self.cache_timeout)
            return factor

        # Try reverse conversion
        reverse_conversion = (
            UnitConversion.objects.filter(
                from_unit=to_unit, to_unit=from_unit, is_active=True
            )
            .order_by("priority")
            .first()
        )

        if reverse_conversion:
            # Reverse the conversion factor
            factor = Decimal("1.0") / reverse_conversion.conversion_factor
            cache.set(cache_key, factor, self.cache_timeout)
            return factor

        # No conversion found
        cache.set(cache_key, None, self.cache_timeout)
        return None

    def convert_quantity(
        self, quantity: Decimal, from_unit, to_unit, product=None, category=None
    ) -> Optional[Decimal]:
        """Convert quantity from one unit to another"""
        factor = self.get_conversion_factor(from_unit, to_unit, product, category)

        if factor is None:
            logger.warning(f"No conversion factor found from {from_unit} to {to_unit}")
            return None

        return quantity * factor

    def convert_to_standard_kitchen_unit(
        self, quantity: Decimal, current_unit, product, category=None
    ) -> Tuple[Optional[Decimal], Optional["UnitOfMeasure"]]:
        """Convert quantity to standard kitchen unit for the product/category"""

        # Get standard kitchen unit
        standard_unit = self.get_standard_kitchen_unit(product, category)
        if not standard_unit:
            logger.info(f"No standard kitchen unit defined for product {product.name}")
            return quantity, current_unit

        # Convert to standard unit
        converted_quantity = self.convert_quantity(
            quantity, current_unit, standard_unit, product, category
        )

        if converted_quantity is None:
            logger.warning(
                f"Could not convert {quantity} {current_unit} to {standard_unit} for {product.name}"
            )
            return quantity, current_unit

        return converted_quantity, standard_unit

    def is_food_product(self, product, category=None) -> bool:
        """Determine if a product is food-related (excluding beverages)"""
        if not category:
            category = product.purchase_category

        category_name = category.name.lower() if category else ""

        # Exclude beverages explicitly
        if "boissons" in category_name or "beverage" in category_name:
            return False

        # Check category for food products
        if (
            category_name.startswith("produits alimentaires")
            or "aliments" in category_name
        ):
            return True

        # Check product name for food keywords
        product_name = product.name.lower()
        food_keywords = [
            "huile",
            "sel",
            "sucre",
            "farine",
            "riz",
            "haricot",
            "tomate",
            "pomme",
            "carotte",
            "oignon",
            "ail",
            "gingembre",
            "piment",
            "poivre",
            "basilic",
            "persil",
            "menthe",
            "citron",
            "orange",
            "banane",
            "mangue",
            "avocat",
            "ananas",
            "papaye",
            "courgette",
            "aubergine",
            "concombre",
            "radis",
            "navet",
            "betterave",
            "chou",
            "salade",
            "laitue",
            "épinard",
            "brocoli",
            "choufleur",
            "viande",
            "porc",
            "bœuf",
            "agneau",
            "poulet",
            "poisson",
        ]

        return any(keyword in product_name for keyword in food_keywords)

    def clear_cache(self):
        """Clear conversion cache"""
        # This would clear all cache keys that start with our prefixes
        # Django's cache doesn't have a built-in way to clear by prefix
        # You might want to implement this differently based on your cache backend
        logger.info(
            "Conversion cache should be cleared manually or will expire after timeout"
        )

    def load_legacy_unit_conversions_and_standards(self):
        """Load comprehensive legacy unit conversion rules and kitchen standards"""
        from decimal import Decimal

        from apps.restaurant_data.models import (
            Product,
            PurchasesCategory,
            StandardKitchenUnit,
            UnitConversion,
            UnitOfMeasure,
        )

        logger.info("Loading legacy unit conversions and kitchen standards...")

        # Kitchen standard units based on French food categories
        kitchen_standards = {
            # Meat & Poultry - Use grams for precise portioning
            "Produits Alimentaires / Aliments / Aliments Frais / Viande": "g",
            "Produits Alimentaires / Aliments / Aliments Frais / Volaille": "g",
            "Produits Alimentaires / Aliments / Aliments Frais / Porc": "g",
            "Produits Alimentaires / Aliments / Aliments Frais / Bœuf": "g",
            "Produits Alimentaires / Aliments / Aliments Frais / Agneau": "g",
            # Vegetables - Use grams for most, pieces for count items
            "Produits Alimentaires / Aliments / Aliments Frais / Légumes": "g",
            "Produits Alimentaires / Aliments / Aliments Frais / Tubercules": "g",
            "Produits Alimentaires / Aliments / Aliments Frais / Légumes aromatiques": "g",
            # Herbs & Aromatics - Use grams for consistency
            "Produits Alimentaires / Aliments / Herbes Aromatiques": "g",
            # Spices - Use grams for precision
            "Produits Alimentaires / Aliments / Aliments Secs / Epices": "g",
            "Produits Alimentaires / Aliments / Assaisonnement": "g",
            # Oils & Liquids - Use milliliters
            "Produits Alimentaires / Aliments / Aliments Transformés / Huiles": "ml",
            # Dairy - Mixed based on product type
            "Produits Alimentaires / Aliments / Produits laitiers": "mixed",
            # Grains & Cereals - Use grams
            "Produits Alimentaires / Aliments / Aliments Transformés / Céréales": "g",
            "Produits Alimentaires / Aliments / Aliments Secs / Céréales": "g",
            # Seafood - Use pieces (changed from pc for better portioning)
            "Produits Alimentaires / Aliments / Aliments Frais / Poissons & Fruits de mer": "pc",
            # Sauces and condiments - Use grams/ml based on consistency
            "Produits Alimentaires / Aliments / Aliments Transformés / Sauces": "g",
            "Produits Alimentaires / Aliments / Condiments": "g",
            # Preserved foods
            "Produits Alimentaires / Aliments / Aliments Transformés / Conserves": "g",
            # Breads and pastries
            "Produits Alimentaires / Aliments / Aliments Transformés / Pain et Boulangerie": "pc",
            # Sugar - Use grams
            "Produits Alimentaires / Aliments / Aliments Transformés / Sucres & Produits Sucrants": "g",
        }

        # Product-specific unit assignments (for special cases)
        product_specific_units = {
            "œufs": "pc",  # Eggs counted in pieces
            "oeufs": "pc",  # Eggs counted in pieces
            "baton de manioc": "pc",  # Manioc baton counted
            "oranges": "pc",  # Oranges counted in pieces
            "gingembre": "g",  # Ginger in grams
            "pommes de terre": "g",  # Potatoes in grams
            "patates": "g",  # Sweet potatoes in grams
            "fromage gruyère": "pc",  # Gruyère cheese in pieces
            "tatie sucre sachet": "pc",  # Sugar sachet in pieces
        }

        # Step 1: Create basic unit conversions
        basic_conversions = [
            # Weight conversions
            ("kg", "g", Decimal("1000")),
            ("g", "kg", Decimal("0.001")),
            ("botte", "g", Decimal("30")),  # French: bunch = ~30g for herbs
            # Volume conversions
            ("l", "ml", Decimal("1000")),
            ("ml", "l", Decimal("0.001")),
            # Basic unit mappings
            ("unit", "pc", Decimal("1")),
            ("pc", "unit", Decimal("1")),
            ("pièce", "pc", Decimal("1")),
            ("pièces", "pc", Decimal("1")),
        ]

        conversions_created = 0

        # Create basic conversions
        for from_unit_name, to_unit_name, factor in basic_conversions:
            try:
                from_unit, _ = UnitOfMeasure.objects.get_or_create(
                    name=from_unit_name,
                    defaults={"description": f"Unit: {from_unit_name}"},
                )

                to_unit, _ = UnitOfMeasure.objects.get_or_create(
                    name=to_unit_name, defaults={"description": f"Unit: {to_unit_name}"}
                )

                # Check if conversion already exists
                existing = UnitConversion.objects.filter(
                    from_unit=from_unit,
                    to_unit=to_unit,
                    product__isnull=True,
                    category__isnull=True,
                ).first()

                if not existing:
                    UnitConversion.objects.create(
                        from_unit=from_unit,
                        to_unit=to_unit,
                        conversion_factor=factor,
                        is_active=True,
                        priority=100,
                        notes="Legacy unit conversion - basic kitchen units",
                    )
                    conversions_created += 1
                    logger.info(
                        f"Created conversion: {from_unit_name} → {to_unit_name} × {factor}"
                    )

            except Exception as e:
                logger.error(
                    f"Error creating conversion {from_unit_name}→{to_unit_name}: {str(e)}"
                )

        # Step 2: Create product-specific conversions
        product_conversions = {
            # Vegetables and herbs - unit to grams
            "pommes de terre": 150,  # 1 potato = 150g
            "oignons": 120,  # 1 onion = 120g
            "tomates": 100,  # 1 tomato = 100g
            "carottes": 80,  # 1 carrot = 80g
            "poivrons": 150,  # 1 pepper = 150g
            "aubergines": 250,  # 1 eggplant = 250g
            "courgettes": 200,  # 1 zucchini = 200g
            "concombres": 300,  # 1 cucumber = 300g
            "avocats": 150,  # 1 avocado = 150g
            "mangues": 200,  # 1 mango = 200g
            "ananas": 1000,  # 1 pineapple = 1kg
            "papayes": 500,  # 1 papaya = 500g
            "bananes": 120,  # 1 banana = 120g
            # Aromatics
            "ails": 50,  # 1 garlic bulb = 50g
            "gingembre": 100,  # 1 piece ginger = 100g
            "citron vert": 30,  # 1 lime = 30g
            "citrons": 60,  # 1 lemon = 60g
            "oranges": 150,  # 1 orange = 150g
            # Herbs
            "basilic": 25,  # 1 bunch = 25g
            "persil": 30,  # 1 bunch = 30g
            "menthe": 25,  # 1 bunch = 25g
            "coriandre": 25,  # 1 bunch = 25g
            # Spices (packages)
            "piment doux": 100,
            "poivre blanc": 50,
            "poivre noir": 50,
            "paprika": 40,
            "curcuma": 50,
            "curry": 50,
            "4 cotés": 50,  # Spice mix
            "rondelle": 35,
            # Meat products
            "ailes de poulet cru": 150,  # 1 chicken wing = 150g
            "ailes de poulet": 150,  # 1 chicken wing = 150g
            "poulet entier": 1632,  # 1 whole chicken = 1.632kg
            "rumsteak": 200,  # 1 steak = 200g
            "blanc de poulet": 200,  # 1 breast = 200g
            "cuisse de poulet": 250,  # 1 thigh = 250g
            # Sauces and condiments
            "sauce mayo": 500,  # 1 container = 500g
            "mayonnaise": 500,  # 1 container = 500g
            "ketchup": 500,  # 1 bottle = 500g
            "moutarde": 200,  # 1 jar = 200g
            # Rice and grains
            "riz": 1000,  # 1 bag = 1kg
            "farine": 1000,  # 1 bag = 1kg
        }

        # Liquid product conversions (unit to ml)
        liquid_conversions = {
            "huile de palme": 1000,  # 1 bottle = 1000ml
            "huile de tournesol": 1000,  # 1 bottle = 1000ml
            "huile d'olive": 1000,  # 1 bottle = 1000ml
            "huile": 1000,  # Default oil bottle
        }

        # Create unit measures
        unit_measure, _ = UnitOfMeasure.objects.get_or_create(
            name="unit", defaults={"description": "Unit: unit"}
        )
        g_measure, _ = UnitOfMeasure.objects.get_or_create(
            name="g", defaults={"description": "Unit: g"}
        )
        ml_measure, _ = UnitOfMeasure.objects.get_or_create(
            name="ml", defaults={"description": "Unit: ml"}
        )

        # Create product-specific conversions for solid products (unit → g)
        for product_name, grams in product_conversions.items():
            try:
                # Try to find the product
                product = Product.objects.filter(name__icontains=product_name).first()
                if product:
                    existing = UnitConversion.objects.filter(
                        from_unit=unit_measure, to_unit=g_measure, product=product
                    ).first()

                    if not existing:
                        UnitConversion.objects.create(
                            from_unit=unit_measure,
                            to_unit=g_measure,
                            conversion_factor=Decimal(str(grams)),
                            product=product,
                            is_active=True,
                            priority=10,  # Higher priority than general conversions
                            notes=f"Product-specific conversion: 1 {product_name} = {grams}g",
                        )
                        conversions_created += 1
                        logger.info(
                            f"Created product conversion: {product_name} unit → g × {grams}"
                        )

            except Exception as e:
                logger.error(
                    f"Error creating product conversion for {product_name}: {str(e)}"
                )

        # Create product-specific conversions for liquid products (unit → ml)
        for product_name, ml in liquid_conversions.items():
            try:
                product = Product.objects.filter(name__icontains=product_name).first()
                if product:
                    existing = UnitConversion.objects.filter(
                        from_unit=unit_measure, to_unit=ml_measure, product=product
                    ).first()

                    if not existing:
                        UnitConversion.objects.create(
                            from_unit=unit_measure,
                            to_unit=ml_measure,
                            conversion_factor=Decimal(str(ml)),
                            product=product,
                            is_active=True,
                            priority=10,
                            notes=f"Product-specific conversion: 1 {product_name} = {ml}ml",
                        )
                        conversions_created += 1
                        logger.info(
                            f"Created product conversion: {product_name} unit → ml × {ml}"
                        )

            except Exception as e:
                logger.error(
                    f"Error creating liquid conversion for {product_name}: {str(e)}"
                )

        # Step 3: Create kitchen standards by category
        standards_created = 0

        for category_name, standard_unit_name in kitchen_standards.items():
            if standard_unit_name == "mixed":
                continue  # Skip mixed categories

            try:
                category = PurchasesCategory.objects.filter(name=category_name).first()
                standard_unit, _ = UnitOfMeasure.objects.get_or_create(
                    name=standard_unit_name,
                    defaults={"description": f"Unit: {standard_unit_name}"},
                )

                if category:
                    existing = StandardKitchenUnit.objects.filter(
                        category=category, standard_unit=standard_unit
                    ).first()

                    if not existing:
                        StandardKitchenUnit.objects.create(
                            category=category,
                            standard_unit=standard_unit,
                            is_active=True,
                            priority=100,
                            description=f"Standard kitchen unit for {category_name}",
                        )
                        standards_created += 1
                        logger.info(
                            f"Created standard: {category_name} → {standard_unit_name}"
                        )

            except Exception as e:
                logger.error(f"Error creating standard for {category_name}: {str(e)}")

        # Step 4: Create product-specific standards
        pc_measure, _ = UnitOfMeasure.objects.get_or_create(
            name="pc", defaults={"description": "Unit: pc"}
        )

        for product_name, unit_name in product_specific_units.items():
            try:
                product = Product.objects.filter(name__icontains=product_name).first()
                unit_measure, _ = UnitOfMeasure.objects.get_or_create(
                    name=unit_name, defaults={"description": f"Unit: {unit_name}"}
                )

                if product:
                    existing = StandardKitchenUnit.objects.filter(
                        product=product, standard_unit=unit_measure
                    ).first()

                    if not existing:
                        StandardKitchenUnit.objects.create(
                            product=product,
                            standard_unit=unit_measure,
                            is_active=True,
                            priority=10,  # Higher priority than category standards
                            description=f"Product-specific standard: {product_name} uses {unit_name}",
                        )
                        standards_created += 1
                        logger.info(
                            f"Created product standard: {product_name} → {unit_name}"
                        )

            except Exception as e:
                logger.error(
                    f"Error creating product standard for {product_name}: {str(e)}"
                )

        logger.info(
            f"Legacy loading complete: {conversions_created} conversions, {standards_created} standards created"
        )
        return {
            "conversions_created": conversions_created,
            "standards_created": standards_created,
        }


unit_conversion_service = UnitConversionService()
