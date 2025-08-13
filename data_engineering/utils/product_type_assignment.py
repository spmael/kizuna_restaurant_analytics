"""
Utility service for automatically assigning ProductType to products
"""

import logging

from django.db.models import Sum

from apps.restaurant_data.models import Product, ProductType

logger = logging.getLogger(__name__)


class ProductTypeAssignmentService:
    """Service for automatically assigning cost types and product types to products"""

    def __init__(self):
        self.cache = {}

    def get_or_create_product_type(self, product: Product) -> ProductType:
        """Get or create ProductType for a product based on its characteristics"""

        cache_key = f"product_type_{product.id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Try to find existing ProductType
        existing_type = ProductType.objects.filter(product=product).first()
        if existing_type:
            self.cache[cache_key] = existing_type
            return existing_type

        # Determine cost type and product type based on product characteristics
        cost_type, product_type = self._determine_types(product)

        # Create new ProductType
        new_type = ProductType.objects.create(
            product=product,
            cost_type=cost_type,
            product_type=product_type,
            cost_type_fr=self._get_cost_type_fr(cost_type),
            cost_type_en=self._get_cost_type_en(cost_type),
        )

        self.cache[cache_key] = new_type
        logger.info(
            f"Created ProductType for {product.name}: {cost_type}/{product_type}"
        )

        return new_type

    def _determine_types(self, product: Product) -> tuple[str, str]:
        """Determine cost_type and product_type based on product characteristics"""

        # Determine product_type first
        product_type = self._determine_product_type(product)

        # Determine cost_type based on product_type
        cost_type = self._determine_cost_type(product, product_type)

        return cost_type, product_type

    def _determine_product_type(self, product: Product) -> str:
        """Determine if product is 'dish' (recipe), 'resale' (sold directly), or 'not_sold' (ingredients only)"""

        # Check if product is a recipe (sold as a dish)
        from apps.recipes.models import Recipe

        is_recipe = Recipe.objects.filter(dish_name__iexact=product.name).exists()
        if is_recipe:
            return "dish"

        # Check if product is sold directly (has sales records)
        has_sales = product.sales.exists()
        if has_sales:
            return "resale"

        # Check if this is a consolidated product that might have sales under different names
        has_consolidated_sales = self._check_consolidated_sales(product)
        if has_consolidated_sales:
            return "resale"

        # Check if product name appears in sales data (case-insensitive search)
        has_name_in_sales = self._check_product_name_in_sales(product)
        if has_name_in_sales:
            return "resale"

        # If product is not a recipe and has no sales, it's likely an ingredient only
        return "not_sold"

    def _determine_cost_type(self, product: Product, product_type: str) -> str:
        """Determine cost type based on product characteristics and purchase category"""

        # For resale products, definitely raw material costs
        if product_type == "resale":
            return "raw_material_costs"

        # For dishes, check if it has ingredients (recipe ingredients are raw materials)
        if product_type == "dish":
            from apps.recipes.models import RecipeIngredient

            # Check if this product is used as an ingredient in recipes
            is_ingredient = RecipeIngredient.objects.filter(ingredient=product).exists()
            if is_ingredient:
                return "raw_material_costs"

        # For remaining products, determine based on purchase category
        purchase_category = product.purchase_category.name

        # First, map general category patterns
        general_category_mapping = {
            # Expenses categories
            "Expenses": "operating_expenses",  # General expenses
            "Expenses / Salaires": "labor_salaries_kitchen",
            "Expenses / Electricité": "variable_utilities_electricity",
            "Expenses / Abonnements": "fixed_subscriptions",
            "Expenses / Travaux Aménagement": "fixed_assets_improvements",
            "Expenses / Equipements électriques": "fixed_assets_equipment",
            # Services
            "Services": "variable_supplies",
            # Produits Alimentaires (Food Products) - generally raw materials
            "Produits Alimentaires": "raw_material_costs",
            "Produits Alimentaires / Aliments": "raw_material_costs",
            "Produits Alimentaires / Boissons": "raw_material_costs",
            # Produits Non-Alimentaires (Non-Food Products)
            "Produits Non-Alimentaires / Produits d'entretien et d'hygiène": "variable_cleaning",
            "Produits Non-Alimentaires / Consommables et emballages": "variable_packaging",
            "Produits Non-Alimentaires / Équipements de restauration": "variable_supplies",
        }

        # Check for exact general category matches first
        for category_pattern, cost_type in general_category_mapping.items():
            if purchase_category.startswith(category_pattern):
                # Now apply specific subcategory rules
                specific_cost_type = self._apply_specific_rules(
                    purchase_category, cost_type
                )
                return specific_cost_type

        # If no general pattern matches, apply specific rules to the full category
        return self._apply_specific_rules(purchase_category, "raw_material_costs")

    def _apply_specific_rules(
        self, purchase_category: str, default_cost_type: str
    ) -> str:
        """Apply specific rules to refine the cost type based on subcategories"""

        category_lower = purchase_category.lower()

        # Specific subcategory mappings
        specific_mappings = {
            # Expenses subcategories
            "expenses / salaires": "labor_salaries_kitchen",
            "expenses / électricité": "variable_utilities_electricity",
            "expenses / abonnements": "fixed_subscriptions",
            "expenses / travaux aménagement": "fixed_assets_improvements",
            "expenses / loyer": "fixed_rent",
            "expenses / assurance": "fixed_insurance",
            "expenses / maintenance": "maintenance_equipment",
            "expenses / marketing": "marketing_social_media",
            "expenses / comptabilité": "fixed_accounting",
            "expenses / banque": "misc_bank_fees",
            "expenses / formation": "misc_training",
            # Services subcategories
            "services": "variable_supplies",
            "services / prestations": "variable_supplies",
            "services / maintenance": "maintenance_equipment",
            # Food products - specific subcategories
            "produits alimentaires / aliments / aliments secs / epices": "raw_material_costs",
            "produits alimentaires / aliments / aliments frais / volaille": "raw_material_costs",
            "produits alimentaires / aliments / aliments frais / légumes aromatiques": "raw_material_costs",
            "produits alimentaires / aliments / aliments frais / légumes": "raw_material_costs",
            "produits alimentaires / aliments / aliments frais / tubercules": "raw_material_costs",
            "produits alimentaires / aliments / aliments frais / bœuf": "raw_material_costs",
            "produits alimentaires / aliments / aliments transformés / pain et boulangerie": "raw_material_costs",
            "produits alimentaires / boissons / boissons alcoolisées / bières": "raw_material_costs",
            "produits alimentaires / boissons / boissons alcoolisées / alcool mix": "raw_material_costs",
            # Non-food products - specific subcategories
            "produits non-alimentaires / produits d'entretien et d'hygiène": "variable_cleaning",
            "produits non-alimentaires / consommables et emballages": "variable_packaging",
            "produits non-alimentaires / équipements de restauration": "variable_supplies",
            # Utility patterns
            "électricité": "variable_utilities_electricity",
            "eau": "variable_utilities_water",
            "gaz": "variable_utilities_gas",
            # Labor patterns
            "salaires": "labor_salaries_kitchen",
            "personnel": "labor_salaries_kitchen",
            "employés": "labor_salaries_kitchen",
            # Maintenance patterns
            "maintenance": "maintenance_equipment",
            "réparation": "maintenance_equipment",
            "travaux": "fixed_assets_improvements",
            "aménagement": "fixed_assets_improvements",
            # Marketing patterns
            "marketing": "marketing_social_media",
            "publicité": "marketing_social_media",
            # Cleaning patterns
            "entretien": "variable_cleaning",
            "hygiène": "variable_cleaning",
            "nettoyage": "variable_cleaning",
            # Packaging patterns
            "emballages": "variable_packaging",
            "consommables": "variable_packaging",
            "sacs": "variable_packaging",
            # Equipment patterns
            "équipements": "fixed_assets_equipment",
            "équipement": "fixed_assets_equipment",
            "machines": "fixed_assets_equipment",
            # Subscriptions patterns
            "abonnements": "fixed_subscriptions",
            "logiciels": "fixed_subscriptions",
            "software": "fixed_subscriptions",
            # Communication patterns
            "téléphone": "fixed_communications",
            "internet": "fixed_communications",
            "wifi": "fixed_communications",
            # Accounting patterns
            "comptabilité": "fixed_accounting",
            "juridique": "fixed_accounting",
            # Tax patterns
            "taxes": "taxes_vat",
            "tva": "taxes_vat",
            "licences": "taxes_licensing",
            # Bank patterns
            "banque": "misc_bank_fees",
            "frais bancaires": "misc_bank_fees",
            # Training patterns
            "formation": "misc_training",
            "éducation": "misc_training",
        }

        # Check for exact matches first
        for category_pattern, cost_type in specific_mappings.items():
            if category_pattern in category_lower:
                return cost_type

        # If no specific match found, return the default
        return default_cost_type

    def _check_consolidated_sales(self, product: Product) -> bool:
        """Check if this product is part of a consolidation that has sales"""
        try:
            from apps.restaurant_data.models import ProductConsolidation
            
            # Check if this product is a primary product in any consolidation
            primary_consolidations = ProductConsolidation.objects.filter(primary_product=product)
            for consolidation in primary_consolidations:
                # Check if any of the consolidated products have sales
                for product_id in consolidation.consolidated_products:
                    try:
                        consolidated_product = Product.objects.get(id=product_id)
                        if consolidated_product.sales.exists():
                            logger.info(f"Found sales for consolidated product {consolidated_product.name} under primary {product.name}")
                            return True
                    except Product.DoesNotExist:
                        continue
            
            # Check if this product is in the consolidated_products list of any consolidation
            all_consolidations = ProductConsolidation.objects.all()
            for consolidation in all_consolidations:
                if product.id in consolidation.consolidated_products:
                    # Check if the primary product has sales
                    if consolidation.primary_product.sales.exists():
                        logger.info(f"Found sales for primary product {consolidation.primary_product.name} that consolidates {product.name}")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking consolidated sales for {product.name}: {str(e)}")
            return False

    def _check_product_name_in_sales(self, product: Product) -> bool:
        """Check if product name appears in sales data (case-insensitive search)"""
        try:
            from apps.restaurant_data.models import Sales
            
            # Search for sales where the product name matches (case-insensitive)
            matching_sales = Sales.objects.filter(
                product__name__iexact=product.name
            ).exists()
            
            if matching_sales:
                logger.info(f"Found sales for product {product.name} via name matching")
                return True
            
            # Also check for partial name matches (in case of slight variations)
            # This handles cases where the product name might have slight differences
            partial_matches = Sales.objects.filter(
                product__name__icontains=product.name
            ).exists()
            
            if partial_matches:
                logger.info(f"Found partial sales match for product {product.name}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking product name in sales for {product.name}: {str(e)}")
            return False

    def _get_cost_type_fr(self, cost_type: str) -> str:
        """Get French translation for cost type"""
        translations = {
            "raw_material_costs": "Coûts des matières premières",
            "labor_salaries_kitchen": "Salaires (Cuisine)",
            "labor_salaries_service": "Salaires (Service)",
            "labor_salaries_admin": "Salaires (Administration)",
            "labor_social_charges": "Charges sociales",
            "labor_contractors": "Prestataires / Freelance",
            "variable_utilities_water": "Coûts variables (Eau)",
            "variable_utilities_gas": "Coûts variables (Gaz)",
            "variable_utilities_electricity": "Coûts variables (Électricité)",
            "variable_supplies": "Fournitures (Cuisine / Bar)",
            "variable_cleaning": "Produits de nettoyage",
            "variable_packaging": "Emballage",
            "variable_commissions": "Commissions (Livraison / Paiement)",
            "fixed_rent": "Loyer",
            "fixed_insurance": "Assurance",
            "fixed_subscriptions": "Abonnements (Odoo, Streamlit, etc.)",
            "fixed_erp": "Services ERP & POS",
            "fixed_communications": "Communications & Internet",
            "fixed_accounting": "Services comptables & juridiques",
            "marketing_social_media": "Marketing (Réseaux sociaux)",
            "marketing_flyers": "Marketing (Tracts, Bannières)",
            "marketing_event": "Marketing (Événements)",
            "maintenance_equipment": "Maintenance équipement",
            "maintenance_local": "Maintenance (Local)",
            "fixed_assets_equipment": "Immobilisations (Équipement cuisine, POS)",
            "fixed_assets_improvements": "Immobilisations (Réparations, Peinture, Sol)",
            "fixed_assets_furniture": "Immobilisations (Mobilier)",
            "fixed_assets_vehicles": "Immobilisations (Véhicules)",
            "fixed_assets_it": "Immobilisations (IT)",
            "taxes_local": "Taxes locales",
            "taxes_licensing": "Licences & Permis",
            "taxes_vat": "TVA / Taxes",
            "misc_bank_fees": "Frais bancaires",
            "misc_training": "Formation",
            "misc_other": "Autres divers",
        }
        return translations.get(cost_type, cost_type)

    def _get_cost_type_en(self, cost_type: str) -> str:
        """Get English translation for cost type"""
        translations = {
            "raw_material_costs": "Raw Materials (Food, Beverages, Ingredients)",
            "labor_salaries_kitchen": "Salaries (Kitchen)",
            "labor_salaries_service": "Salaries (Service)",
            "labor_salaries_admin": "Salaries (Administration)",
            "labor_social_charges": "Social Charges",
            "labor_contractors": "Contractors / Freelance",
            "variable_utilities_water": "Variable Costs (Water)",
            "variable_utilities_gas": "Variable Costs (Gas)",
            "variable_utilities_electricity": "Variable Costs (Electricity)",
            "variable_supplies": "Supplies (Kitchen Supplies / Bar Supplies)",
            "variable_cleaning": "Cleaning Supplies",
            "variable_packaging": "Packaging",
            "variable_commissions": "Commissions (Delivery / Payment)",
            "fixed_rent": "Rent",
            "fixed_insurance": "Insurance",
            "fixed_subscriptions": "Subscriptions (Odoo, Streamlit, etc.)",
            "fixed_erp": "ERP & POS Services",
            "fixed_communications": "Communications & Internet",
            "fixed_accounting": "Accounting & Legal Services",
            "marketing_social_media": "Marketing (Social Media)",
            "marketing_flyers": "Marketing (Flyers, Banners)",
            "marketing_event": "Marketing (Events)",
            "maintenance_equipment": "Maintenance Equipment",
            "maintenance_local": "Maintenance (Local)",
            "fixed_assets_equipment": "Fixed Assets (Kitchen Equipment, POS)",
            "fixed_assets_improvements": "Fixed Assets (Repairs, Painting, Flooring)",
            "fixed_assets_furniture": "Fixed Assets (Furniture)",
            "fixed_assets_vehicles": "Fixed Assets (Vehicles)",
            "fixed_assets_it": "Fixed Assets (IT)",
            "taxes_local": "Local Taxes",
            "taxes_licensing": "Licenses & Permits",
            "taxes_vat": "VAT / Taxes",
            "misc_bank_fees": "Bank Fees",
            "misc_training": "Training",
            "misc_other": "Other Miscellaneous",
        }
        return translations.get(cost_type, cost_type)

    def get_cost_category(self, cost_type: str) -> str:
        """Get the main financial category for a cost type"""

        # Map cost types to main financial categories
        cost_category_mapping = {
            # Raw Materials (COGS)
            "raw_material_costs": "cost_of_goods_sold",
            # Labor Costs
            "labor_salaries_kitchen": "operating_expenses",
            "labor_salaries_service": "operating_expenses",
            "labor_salaries_admin": "operating_expenses",
            "labor_social_charges": "operating_expenses",
            "labor_contractors": "operating_expenses",
            # Variable Operating Costs
            "variable_utilities_water": "variable_costs",
            "variable_utilities_gas": "variable_costs",
            "variable_utilities_electricity": "variable_costs",
            "variable_supplies": "variable_costs",
            "variable_cleaning": "variable_costs",
            "variable_packaging": "variable_costs",
            "variable_commissions": "variable_costs",
            # Fixed Operating Costs
            "fixed_rent": "fixed_costs",
            "fixed_insurance": "fixed_costs",
            "fixed_subscriptions": "fixed_costs",
            "fixed_erp": "fixed_costs",
            "fixed_communications": "fixed_costs",
            "fixed_accounting": "fixed_costs",
            # Marketing & Sales
            "marketing_social_media": "variable_costs",
            "marketing_flyers": "variable_costs",
            "marketing_event": "variable_costs",
            # Maintenance & Repairs
            "maintenance_equipment": "variable_costs",
            "maintenance_local": "variable_costs",
            # Fixed Assets (Capital Expenditure)
            "fixed_assets_equipment": "fixed_assets",
            "fixed_assets_improvements": "fixed_assets",
            "fixed_assets_furniture": "fixed_assets",
            "fixed_assets_vehicles": "fixed_assets",
            "fixed_assets_it": "fixed_assets",
            # Taxes & Licenses
            "taxes_local": "operating_expenses",
            "taxes_licensing": "operating_expenses",
            "taxes_vat": "operating_expenses",
            # Other / Miscellaneous
            "misc_bank_fees": "operating_expenses",
            "misc_training": "operating_expenses",
            "misc_other": "operating_expenses",
        }

        return cost_category_mapping.get(cost_type, "operating_expenses")

    def get_depreciation_category(self, cost_type: str) -> str:
        """Get depreciation category for fixed assets"""

        depreciation_mapping = {
            "fixed_assets_equipment": "equipment_depreciation",
            "fixed_assets_improvements": "improvements_depreciation",
            "fixed_assets_furniture": "furniture_depreciation",
            "fixed_assets_vehicles": "vehicle_depreciation",
            "fixed_assets_it": "it_depreciation",
        }

        return depreciation_mapping.get(cost_type, "no_depreciation")

    def analyze_cost_structure(self, products: list[Product] = None) -> dict:
        """Analyze cost structure by financial categories"""

        if products is None:
            products = Product.objects.all()

        analysis = {
            "cost_of_goods_sold": {"count": 0, "products": []},
            "variable_costs": {"count": 0, "products": []},
            "fixed_costs": {"count": 0, "products": []},
            "fixed_assets": {"count": 0, "products": []},
            "operating_expenses": {"count": 0, "products": []},
        }

        for product in products:
            try:
                product_type = self.get_or_create_product_type(product)
                cost_category = self.get_cost_category(product_type.cost_type)

                analysis[cost_category]["count"] += 1
                analysis[cost_category]["products"].append(
                    {
                        "name": product.name,
                        "cost_type": product_type.cost_type,
                        "product_type": product_type.product_type,
                        "category": product.purchase_category.name,
                    }
                )

            except Exception as e:
                logger.error(f"Error analyzing product {product.name}: {str(e)}")

        return analysis

    def get_financial_summary(self) -> dict:
        """Get financial summary by cost categories"""

        from apps.analytics.models import ProductCostHistory

        summary = {
            "cost_of_goods_sold": {"total_cost": 0, "count": 0},
            "variable_costs": {"total_cost": 0, "count": 0},
            "fixed_costs": {"total_cost": 0, "count": 0},
            "fixed_assets": {"total_cost": 0, "count": 0},
            "operating_expenses": {"total_cost": 0, "count": 0},
        }

        # Get all ProductTypes
        from apps.restaurant_data.models import ProductType

        product_types = ProductType.objects.all()

        for pt in product_types:
            cost_category = self.get_cost_category(pt.cost_type)

            # Get total cost for this product type
            total_cost = (
                ProductCostHistory.objects.filter(product_category=pt).aggregate(
                    total=Sum("total_amount")
                )["total"]
                or 0
            )

            summary[cost_category]["total_cost"] += total_cost
            summary[cost_category]["count"] += 1

        return summary

    def bulk_assign_product_types(self, products: list[Product] = None) -> dict:
        """Bulk assign ProductTypes to products"""

        if products is None:
            products = Product.objects.all()

        created = 0
        updated = 0
        errors = 0

        for product in products:
            try:
                # This will create or get existing ProductType
                product_type = self.get_or_create_product_type(product)

                if product_type.pk:  # Existing
                    updated += 1
                else:  # Newly created
                    created += 1

            except Exception as e:
                errors += 1
                logger.error(f"Error assigning ProductType to {product.name}: {str(e)}")

        return {
            "created": created,
            "updated": updated,
            "errors": errors,
            "total_processed": len(products),
        }

    def bulk_reclassify_product_types(self, products: list[Product] = None, force: bool = False) -> dict:
        """Bulk reclassify ProductTypes for products"""

        if products is None:
            products = Product.objects.all()

        reclassified = 0
        unchanged = 0
        errors = 0

        for product in products:
            try:
                # Get existing ProductType
                existing_type = ProductType.objects.filter(product=product).first()
                
                if existing_type and not force:
                    # Check if classification needs updating
                    old_product_type = existing_type.product_type
                    new_product_type = self._determine_product_type(product)
                    
                    if old_product_type != new_product_type:
                        existing_type.product_type = new_product_type
                        existing_type.save()
                        reclassified += 1
                        logger.info(f"Reclassified {product.name}: {old_product_type} -> {new_product_type}")
                    else:
                        unchanged += 1
                else:
                    # Create new ProductType or force recreation
                    if existing_type and force:
                        existing_type.delete()
                    
                    self.get_or_create_product_type(product)
                    reclassified += 1
                    logger.info(f"Created/Recreated ProductType for {product.name}")

            except Exception as e:
                errors += 1
                logger.error(f"Error reclassifying ProductType for {product.name}: {str(e)}")

        return {
            "reclassified": reclassified,
            "unchanged": unchanged,
            "errors": errors,
            "total_processed": len(products),
        }

    def clear_cache(self):
        """Clear the product type cache"""
        self.cache.clear()


# Global instance
product_type_assignment_service = ProductTypeAssignmentService()
