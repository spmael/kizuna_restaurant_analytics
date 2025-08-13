from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel, SoftDeleteModel


class PurchasesCategory(SoftDeleteModel):
    """Model representing a category of purchases."""

    name = models.CharField(_("Name"), max_length=255)
    name_fr = models.CharField(_("French Name"), max_length=255, blank=True)
    name_en = models.CharField(_("English Name"), max_length=255, blank=True)
    description = models.TextField(_("Description"), blank=True)
    sort_order = models.PositiveIntegerField(_("Sort Order"), default=0)

    class Meta:
        verbose_name = _("Purchases Category")
        verbose_name_plural = _("Purchases Categories")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class SalesCategory(SoftDeleteModel):
    """Model representing a category of sales."""

    name = models.CharField(_("Name"), max_length=255)
    name_fr = models.CharField(_("French Name"), max_length=255, blank=True)
    name_en = models.CharField(_("English Name"), max_length=255, blank=True)
    description = models.TextField(_("Description"), blank=True)
    sort_order = models.PositiveIntegerField(_("Sort Order"), default=0)

    class Meta:
        verbose_name = _("Sales Category")
        verbose_name_plural = _("Sales Categories")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Supplier(AuditModel):
    """Model representing a supplier."""


# TODO: Add supplier model


class UnitOfMeasure(SoftDeleteModel):
    """Model representing a unit of measure."""

    name = models.CharField(_("Name"), max_length=255)
    abbreviation = models.CharField(_("Abbreviation"), max_length=255, blank=True)
    name_fr = models.CharField(_("French Name"), max_length=255, blank=True)
    name_en = models.CharField(_("English Name"), max_length=255, blank=True)
    description = models.TextField(_("Description"), blank=True)
    sort_order = models.PositiveIntegerField(_("Sort Order"), default=0)

    class Meta:
        verbose_name = _("Unit of Measure")
        verbose_name_plural = _("Units of Measure")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Product(AuditModel):
    """Model representing a product."""

    name = models.CharField(_("Product Name"), max_length=255)
    name_fr = models.CharField(_("French Name"), max_length=255, blank=True)
    name_en = models.CharField(_("English Name"), max_length=255, blank=True)

    # Purchase Category
    purchase_category = models.ForeignKey(
        PurchasesCategory, on_delete=models.CASCADE, related_name="products"
    )

    # Sales Category
    sales_category = models.ForeignKey(
        SalesCategory, on_delete=models.CASCADE, related_name="products"
    )

    # Unit of Measure
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure, on_delete=models.CASCADE, related_name="products"
    )

    # Price
    current_selling_price = models.DecimalField(
        _("Current Selling Price"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    current_cost_per_unit = models.DecimalField(
        _("Current Cost Per Unit"),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    # Stock
    current_stock = models.DecimalField(_("Stock"), max_digits=15, decimal_places=2)

    # Description
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["name", "sales_category", "purchase_category"]

    def __str__(self):
        return self.name

    @property
    def stock_value(self):
        return self.current_stock * self.current_cost_per_unit


class Purchase(AuditModel):
    """Model representing a purchase."""

    purchase_date = models.DateField(_("Purchase Date"))
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="purchases"
    )
    quantity_purchased = models.DecimalField(
        _("Quantity Purchased"), max_digits=15, decimal_places=2
    )
    total_cost = models.DecimalField(_("Total Cost"), max_digits=15, decimal_places=2)

    class Meta:
        verbose_name = _("Purchase")
        verbose_name_plural = _("Purchases")
        ordering = ["purchase_date", "product"]

    def __str__(self):
        return f"{self.product.name} - {self.purchase_date}"


class ProductType(AuditModel):
    """Model representing a unit of measure for a recipe."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="product_cost_types"
    )

    COST_TYPE_CHOICES = [
        # --- Cost of Goods Sold (COGS) ---
        ("raw_material_costs", _("Raw Materials (Food, Beverages, Ingredients)")),
        # --- Labor / Staff Costs ---
        ("labor_salaries_kitchen", _("Salaries (Kitchen)")),
        ("labor_salaries_service", _("Salaries (Service)")),
        ("labor_salaries_admin", _("Salaries (Administration)")),
        ("labor_social_charges", _("Social Charges")),
        ("labor_contractors", _("Contractors / Freelance")),
        # --- Variable Operating Costs ---
        ("variable_utilities_water", _("Variable Costs (Water)")),
        ("variable_utilities_gas", _("Variable Costs (Gas)")),
        ("variable_utilities_electricity", _("Variable Costs (Electricity)")),
        ("variable_supplies", _("Supplies (Kitchen Supplies / Bar Supplies)")),
        ("variable_cleaning", _("Cleaning Supplies")),
        ("variable_packaging", _("Packaging")),
        ("variable_commissions", _("Commissions (Delivery / Payment)")),
        # --- Fixed Operating Costs ---
        ("fixed_rent", _("Rent")),
        ("fixed_insurance", _("Insurance")),
        ("fixed_subscriptions", _("Subscriptions (Odoo, Streamlit, etc.)")),
        ("fixed_erp", _("ERP & POS Services")),
        ("fixed_communications", _("Communications & Internet")),
        ("fixed_accounting", _("Accounting & Legal Services")),
        # --- Marketing & Sales ---
        ("marketing_social_media", _("Marketing (Social Media)")),
        ("marketing_flyers", _("Marketing (Flyers, Banners)")),
        ("marketing_event", _("Marketing (Events)")),
        # --- Maintenance & Repairs ---
        ("maintenance_equipment", _("Maintenance Equipment")),
        ("maintenance_local", _("Maintenance (Local)")),
        # --- Fixed Assets / Capital Expenditure (CapEx) ---
        ("fixed_assets_equipment", _("Fixed Assets (Kitchen Equipment, POS)")),
        ("fixed_assets_improvements", _("Fixed Assets (Repairs, Painting, Flooring)")),
        ("fixed_assets_furniture", _("Fixed Assets (Furniture)")),
        ("fixed_assets_vehicles", _("Fixed Assets (Vehicles)")),
        ("fixed_assets_it", _("Fixed Assets (IT)")),
        # --- Taxes & Licenses ---
        ("taxes_local", _("Local Taxes")),
        ("taxes_licensing", _("Licenses & Permits")),
        ("taxes_vat", _("VAT / Taxes")),
        # --- Other / Miscellaneous ---
        ("misc_bank_fees", _("Bank Fees")),
        ("misc_training", _("Training")),
        ("misc_other", _("Other Miscellaneous")),
    ]

    PRODUCT_TYPE_CHOICES = [
        ("dish", _("Prepared Dish")),
        ("resale", _("Direct Buy/Resale Product")),
        ("not_sold", _("Other (Not Sold)")),
    ]

    cost_type = models.CharField(
        _("Cost Type"),
        max_length=255,
        choices=COST_TYPE_CHOICES,
        default="raw_material_costs",
    )
    cost_type_fr = models.CharField(_("Cost Type French"), max_length=255, blank=True)
    cost_type_en = models.CharField(_("Cost Type English"), max_length=255, blank=True)

    product_type = models.CharField(
        _("Product Type"),
        max_length=255,
        choices=PRODUCT_TYPE_CHOICES,
        default="resale",
    )

    class Meta:
        verbose_name = _("Purchase Cost Type")
        verbose_name_plural = _("Purchase Cost Types")
        ordering = ["cost_type"]

    def __str__(self):
        return self.cost_type_fr


class ProductConsolidation(AuditModel):
    """Model for consolidating groups of similar products with different names"""

    # The main/canonical product that others are consolidated into
    primary_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="primary_consolidations"
    )
    # List of product IDs that are consolidated into the primary product
    consolidated_products = models.JSONField(
        default=list,
        help_text=_(
            "List of product IDs that are consolidated into the primary product"
        ),
    )
    # Dictionary mapping product_id to similarity score
    similarity_scores = models.JSONField(
        default=dict, help_text=_("Dictionary mapping product_id to similarity score")
    )
    # Reason for consolidation (e.g., 'fuzzy_name_match', 'category_similarity')
    consolidation_reason = models.CharField(
        _("Consolidation Reason"),
        max_length=100,
        help_text=_(
            "Reason for consolidation (e.g., 'fuzzy_name_match', 'category_similarity')"
        ),
    )
    # Overall confidence in this consolidation (0-1)
    confidence_score = models.DecimalField(
        _("Confidence Score"),
        max_digits=5,
        decimal_places=3,
        help_text=_("Overall confidence in this consolidation (0-1)"),
    )
    is_verified = models.BooleanField(
        _("Verified"),
        default=False,
        help_text=_("Whether this consolidation has been manually verified"),
    )
    notes = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Notes about why these products are considered similar"),
    )

    class Meta:
        verbose_name = _("Product Consolidation")
        verbose_name_plural = _("Product Consolidations")
        ordering = ["-confidence_score"]

    def __str__(self):
        return f"{self.primary_product.name} (consolidates {len(self.consolidated_products)} products)"

    @property
    def consolidated_product_names(self):
        """Get list of consolidated product names"""
        if not self.consolidated_products:
            return []

        # Get products by IDs and return their names
        products = Product.objects.filter(id__in=self.consolidated_products)
        return [product.name for product in products]

    @property
    def consolidated_products_display(self):
        """Get consolidated products as a formatted string for display"""
        names = self.consolidated_product_names
        if not names:
            return "None"
        return ", ".join(names)

    def save(self, *args, **kwargs):
        """Validate consolidation data"""
        # Ensure primary product is not in consolidated_products list
        if self.primary_product.id in self.consolidated_products:
            raise ValidationError(
                _("Primary product cannot be in consolidated products list")
            )

        # Ensure all consolidated products have similarity scores
        for product_id in self.consolidated_products:
            if str(product_id) not in self.similarity_scores:
                raise ValidationError(
                    _(f"Missing similarity score for product {product_id}")
                )

        super().save(*args, **kwargs)


class Sales(AuditModel):
    """Model representing a sale."""

    sale_date = models.DateField(_("Sale Date"))
    order_number = models.CharField(_("Order Number"), max_length=255)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales")
    quantity_sold = models.DecimalField(
        _("Quantity Sold"), max_digits=15, decimal_places=2
    )
    unit_sale_price = models.DecimalField(
        _("Unit Price"), max_digits=15, decimal_places=2
    )
    total_sale_price = models.DecimalField(
        _("Total Sale Price"), max_digits=15, decimal_places=2
    )
    customer = models.CharField(
        _("Customer Name"), max_length=255, blank=True, null=True
    )
    cashier = models.CharField(_("Cashier Name"), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")
        ordering = ["sale_date", "product"]

    def __str__(self):
        return f"{self.product.name} - {self.sale_date}"


class ConsolidatedPurchases(AuditModel):
    """Model for storing consolidated purchase data aggregated by product name"""

    # Same fields as Purchase model
    purchase_date = models.DateField(_("Purchase Date"))
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="consolidated_purchases"
    )
    quantity_purchased = models.DecimalField(
        _("Quantity Purchased"), max_digits=15, decimal_places=2
    )
    total_cost = models.DecimalField(_("Total Cost"), max_digits=15, decimal_places=2)

    # Additional consolidation fields
    unit_of_purchase = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="consolidated_purchases_as_purchase_unit",
        help_text=_("Unit of measure for the quantity purchased"),
    )

    unit_of_recipe = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="consolidated_purchases_as_recipe_unit",
        help_text=_("Unit of measure for the quantity used in recipes"),
    )

    consolidation_applied = models.BooleanField(
        _("Consolidation Applied"),
        default=False,
        help_text=_("Whether consolidation rules were applied to this product"),
    )

    consolidated_product_names = models.JSONField(
        _("Consolidated Product Names"),
        default=list,
        help_text=_("List of all consolidated product names"),
    )

    class Meta:
        verbose_name = _("Consolidated Purchase")
        verbose_name_plural = _("Consolidated Purchases")
        ordering = ["purchase_date", "product"]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["purchase_date"]),
            models.Index(fields=["consolidation_applied"]),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.purchase_date}"


class UnitConversion(AuditModel):
    """Model for storing unit conversion rules and factors"""

    from_unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="conversions_from",
        verbose_name=_("From Unit"),
        help_text=_("Unit to convert from"),
    )

    to_unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="conversions_to",
        verbose_name=_("To Unit"),
        help_text=_("Unit to convert to"),
    )

    conversion_factor = models.DecimalField(
        _("Conversion Factor"),
        max_digits=15,
        decimal_places=6,
        help_text=_(
            "Factor to multiply 'from_unit' to get 'to_unit' (e.g., 1 kg = 1000 g, so factor = 1000)"
        ),
    )

    # Optional product-specific conversion
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="unit_conversions",
        null=True,
        blank=True,
        help_text=_("Specific product this conversion applies to (optional)"),
    )

    # Category-specific conversion
    category = models.ForeignKey(
        PurchasesCategory,
        on_delete=models.CASCADE,
        related_name="unit_conversions",
        null=True,
        blank=True,
        help_text=_("Product category this conversion applies to (optional)"),
    )

    is_active = models.BooleanField(
        _("Active"), default=True, help_text=_("Whether this conversion rule is active")
    )

    priority = models.PositiveIntegerField(
        _("Priority"),
        default=100,
        help_text=_(
            "Priority for applying conversions (lower number = higher priority)"
        ),
    )

    notes = models.TextField(
        _("Notes"), blank=True, help_text=_("Additional notes about this conversion")
    )

    class Meta:
        verbose_name = _("Unit Conversion")
        verbose_name_plural = _("Unit Conversions")
        ordering = ["priority", "from_unit", "to_unit"]
        unique_together = [
            ("from_unit", "to_unit", "product"),
            ("from_unit", "to_unit", "category"),
        ]
        indexes = [
            models.Index(fields=["from_unit", "to_unit"]),
            models.Index(fields=["product"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        context = ""
        if self.product:
            context = f" (Product: {self.product.name})"
        elif self.category:
            context = f" (Category: {self.category.name})"

        return f"{self.from_unit.name} → {self.to_unit.name} × {self.conversion_factor}{context}"

    def clean(self):
        """Validate conversion rule"""
        if self.from_unit == self.to_unit:
            raise ValidationError(_("From unit and to unit cannot be the same"))

        if self.product and self.category:
            raise ValidationError(
                _("Cannot specify both product and category for the same conversion")
            )


class MarketPriceReference(AuditModel):
    """Market prices for missing ingredient costs"""
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='market_prices',
        verbose_name=_("Product")
    )
    price_per_unit = models.DecimalField(
        _("Market Price"), 
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    unit_of_measure = models.ForeignKey(
        UnitOfMeasure, 
        on_delete=models.CASCADE,
        verbose_name=_("Unit of Measure")
    )
    effective_date = models.DateField(_("Effective Date"))
    source = models.CharField(_("Source"), max_length=200, help_text=_("e.g., Supplier, Market, Industry Standard"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    class Meta:
        verbose_name = _("Market Price Reference")
        verbose_name_plural = _("Market Price References")
        ordering = ['-effective_date', 'product']
        indexes = [
            models.Index(fields=['product', 'effective_date']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.price_per_unit} per {self.unit_of_measure.name} ({self.source})"

    def clean(self):
        """Validate market price reference"""
        if self.price_per_unit <= 0:
            raise ValidationError(_("Market price must be greater than zero"))


class StandardKitchenUnit(AuditModel):
    """Model for defining standard kitchen units by product category or specific products"""

    # Either category OR product should be specified, not both
    category = models.ForeignKey(
        PurchasesCategory,
        on_delete=models.CASCADE,
        related_name="standard_kitchen_units",
        null=True,
        blank=True,
        help_text=_("Product category this standard applies to"),
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="standard_kitchen_units",
        null=True,
        blank=True,
        help_text=_("Specific product this standard applies to"),
    )

    standard_unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="standard_for_categories",
        help_text=_(
            "Standard unit to use in kitchen/recipes for this category or product"
        ),
    )

    is_active = models.BooleanField(
        _("Active"), default=True, help_text=_("Whether this standard is active")
    )

    priority = models.PositiveIntegerField(
        _("Priority"),
        default=100,
        help_text=_("Priority for applying standards (lower number = higher priority)"),
    )

    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Description of why this standard unit is used"),
    )

    class Meta:
        verbose_name = _("Standard Kitchen Unit")
        verbose_name_plural = _("Standard Kitchen Units")
        ordering = ["priority", "category", "product"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["product"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        if self.product:
            return f"{self.product.name} → {self.standard_unit.name}"
        elif self.category:
            return f"{self.category.name} → {self.standard_unit.name}"
        return f"Standard: {self.standard_unit.name}"

    def clean(self):
        """Validate standard unit rule"""
        if not self.product and not self.category:
            raise ValidationError(_("Must specify either product or category"))

        if self.product and self.category:
            raise ValidationError(_("Cannot specify both product and category"))


class ConsolidatedSales(AuditModel):
    """Model for storing consolidated sales data aggregated by product name"""

    # Same fields as Sales model
    sale_date = models.DateField(_("Sale Date"))
    order_number = models.CharField(_("Order Number"), max_length=255)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="consolidated_sales"
    )
    quantity_sold = models.DecimalField(
        _("Quantity Sold"), max_digits=15, decimal_places=2
    )
    unit_sale_price = models.DecimalField(
        _("Unit Price"), max_digits=15, decimal_places=2
    )
    total_sale_price = models.DecimalField(
        _("Total Sale Price"), max_digits=15, decimal_places=2
    )
    customer = models.CharField(
        _("Customer Name"), max_length=255, blank=True, null=True
    )
    cashier = models.CharField(_("Cashier Name"), max_length=255, blank=True, null=True)

    # Additional consolidation fields
    unit_of_sale = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="consolidated_sales_as_sale_unit",
        help_text=_("Unit of measure for the quantity sold"),
    )

    unit_of_recipe = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="consolidated_sales_as_recipe_unit",
        help_text=_("Unit of measure for the quantity used in recipes"),
    )

    consolidation_applied = models.BooleanField(
        _("Consolidation Applied"),
        default=False,
        help_text=_("Whether consolidation rules were applied to this product"),
    )

    consolidated_product_names = models.JSONField(
        _("Consolidated Product Names"),
        default=list,
        help_text=_("List of all consolidated product names"),
    )

    class Meta:
        verbose_name = _("Consolidated Sale")
        verbose_name_plural = _("Consolidated Sales")
        ordering = ["sale_date", "product"]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["sale_date"]),
            models.Index(fields=["consolidation_applied"]),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.sale_date}"
