from decimal import Decimal

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
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    current_cost_per_unit = models.DecimalField(
        _("Current Cost Per Unit"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    # Stock
    current_stock = models.DecimalField(_("Stock"), max_digits=10, decimal_places=2)

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
        _("Quantity Purchased"), max_digits=10, decimal_places=2
    )
    total_cost = models.DecimalField(_("Total Cost"), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("Purchase")
        verbose_name_plural = _("Purchases")
        ordering = ["purchase_date", "product"]

    def __str__(self):
        return f"{self.product.name} - {self.purchase_date}"


class PurchaseCostType(AuditModel):
    """Model representing a unit of measure for a recipe."""

    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name="purchase_recipe_units"
    )

    COST_TYPE_CHOICES = [
        ("operational_fixed_salaries", _("Coûts Fixes Opérationnels (Salaires)")),
        ("operational_fixed_electricity", _("Coûts Fixes Opérationnels (Électricité)")),
        ("raw_material_costs", _("Coûts Matière")),
        ("operational_fixed", _("Coûts Fixes Opérationnels")),
        ("fixed_assets_improvements", _("Immobilisations (Aménagements)")),
        ("fixed_assets_equipment", _("Immobilisations (Équipements)")),
        ("variable_costs", _("Coûts Variables")),
        ("variable_costs_supplies", _("Coûts Variables (Fournitures)")),
        ("variable_costs_packaging", _("Coûts Variables (Emballages)")),
        ("fixed_assets", _("Immobilisations")),
        ("fixed_assets_marketing", _("Immobilisations (Marketing)")),
    ]

    cost_type = models.CharField(
        _("Cost Type"),
        max_length=255,
        choices=COST_TYPE_CHOICES,
        default="raw_material_costs",
    )
    cost_type_fr = models.CharField(_("Cost Type French"), max_length=255, blank=True)
    cost_type_en = models.CharField(_("Cost Type English"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("Purchase Cost Type")
        verbose_name_plural = _("Purchase Cost Types")
        ordering = ["cost_type"]

    def __str__(self):
        return self.cost_type_fr


class PurchaseRecipeUnit(AuditModel):
    """Model representing a unit of measure for a recipe."""

    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name="purchase_recipe_units"
    )
    unit_of_purchase = models.CharField(
        _("Unit of Purchase"), max_length=20, blank=True
    )
    unit_of_recipe = models.ForeignKey(
        UnitOfMeasure, on_delete=models.CASCADE, related_name="purchase_recipe_units"
    )

    def get_unit_of_purchase(self):
        """Get the unit of measure from the product related to this purchase"""
        return self.purchase.product.unit_of_measure

    class Meta:
        verbose_name = _("Purchase Recipe Unit")
        verbose_name_plural = _("Purchase Recipe Units")
        ordering = ["unit_of_recipe"]

    def __str__(self):
        return self.unit_of_recipe.name

    def save(self, *args, **kwargs):
        """Set the unit of purchase to the unit of measure from the product related to this purchase"""
        self.unit_of_purchase = self.get_unit_of_purchase()
        super().save(*args, **kwargs)


class Sales(AuditModel):
    """Model representing a sale."""

    sale_date = models.DateField(_("Sale Date"))
    order_number = models.CharField(_("Order Number"), max_length=255)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sales")
    quantity_sold = models.DecimalField(
        _("Quantity Sold"), max_digits=10, decimal_places=2
    )
    unit_sale_price = models.DecimalField(
        _("Unit Price"), max_digits=10, decimal_places=2
    )
    total_sale_price = models.DecimalField(
        _("Total Sale Price"), max_digits=10, decimal_places=2
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


class Recipe(AuditModel):
    """Model representing a recipe."""

    dish_name = models.CharField(_("Dish Name"), max_length=255)
    dish_name_fr = models.CharField(_("French Dish Name"), max_length=255, blank=True)
    dish_name_en = models.CharField(_("English Dish Name"), max_length=255, blank=True)
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Recipe")
        verbose_name_plural = _("Recipes")
        ordering = ["dish_name"]

    def __str__(self):
        return self.dish_name


class RecipeIngredient(AuditModel):
    """Model representing an ingredient in a recipe."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    ingredient = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="recipes"
    )
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2)
    main_ingredient = models.BooleanField(_("Main Ingredient"), default=False)

    class Meta:
        verbose_name = _("Recipe Ingredient")
        verbose_name_plural = _("Recipe Ingredients")
        ordering = ["recipe", "ingredient"]

    def __str__(self):
        return f"{self.recipe.name} - {self.ingredient.name}"
