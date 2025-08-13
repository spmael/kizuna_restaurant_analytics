from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditModel, TimeStampedModel
from apps.restaurant_data.models import Product, UnitOfMeasure


class Recipe(AuditModel):
    """Model representing a recipe."""

    RECIPE_CATEGORIES = [
        ("starter", _("Starter")),
        ("main", _("Main")),
        ("dessert", _("Dessert")),
        ("drink", _("Drink")),
        ("salad", _("Salad")),
        ("soup", _("Soup")),
        ("side", _("Side")),
        ("snack", _("Snack")),
        ("other", _("Other")),
    ]

    dish_name = models.CharField(_("Dish Name"), max_length=255)
    dish_name_fr = models.CharField(_("French Dish Name"), max_length=255, blank=True)
    dish_name_en = models.CharField(_("English Dish Name"), max_length=255, blank=True)
    description = models.TextField(_("Description"), blank=True)
    category = models.CharField(
        _("Category"), max_length=255, blank=True, choices=RECIPE_CATEGORIES
    )

    # Portion information
    serving_size = models.DecimalField(
        _("Serving Size"),
        max_digits=15,
        decimal_places=3,
        default=Decimal("1.000"),
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text=_("number of portfions this recipe makes"),
    )

    portion_weight = models.DecimalField(
        _("Portion Weight"),
        max_digits=15,
        decimal_places=3,
        blank=True,
        null=True,
        help_text=_("Weight of each portion in grams"),
    )

    # Cooking information
    prep_time_minutes = models.IntegerField(
        _("Preparation Time (minutes)"),
        default=0,
        help_text=_("Time required to prepare the recipe"),
    )

    cook_time_minutes = models.IntegerField(
        _("Cooking Time (minutes)"),
        default=0,
        help_text=_("Time required to cook the recipe"),
    )

    # Cost fields
    base_food_cost_per_portion = models.DecimalField(
        _("Base Food Cost per Portion"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Base food cost per portion calculated from the ingredients"),
    )

    waste_factor_percentage = models.DecimalField(
        _("Waste Factor Percentage"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Cooking loss, prep waste, spillage (default 0%)"),
    )

    labour_cost_percentage = models.DecimalField(
        _("Labour Cost Percentage"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Optional: labour cost allocation (default 0%)"),
    )

    # Target pricing
    target_food_cost_percentage = models.DecimalField(
        _("Target Food Cost Percentage"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("30.00"),
        help_text=_("Target food cost percentage (default 30%)"),
    )

    suggested_selling_price_per_portion = models.DecimalField(
        _("Suggested Selling Price per Portion"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Calculated from the target food cost percentage"),
    )

    actual_selling_price_per_portion = models.DecimalField(
        _("Actual Selling Price per Portion"),
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        help_text=_("Current selling price per portion"),
    )

    # Recipe Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_seasonal = models.BooleanField(_("Is Seasonal"), default=False)

    # Costing metadata
    last_costed_date = models.DateField(_("Last Costed Date"), blank=True, null=True)
    cost_calculation_notes = models.TextField(_("Cost Calculation Notes"), blank=True)

    class Meta:
        verbose_name = _("Recipe")
        verbose_name_plural = _("Recipes")
        ordering = ["dish_name"]

    def __str__(self):
        return f"{self.dish_name} - {self.serving_size} servings"

    def calculate_costs(self, save=True):
        """Calculate all recipe costs based on current ingredient prices"""
        from apps.analytics.recipe_services import RecipeCostingService

        costing_service = RecipeCostingService()
        costs = costing_service.calculate_recipe_costs(self)

        self.base_food_cost_per_portion = costs["base_cost_per_portion"]
        self.total_cost_per_portion = costs["total_cost_per_portion"]
        self.suggested_selling_price_per_portion = costs["suggested_selling_price"]

        if save:
            self.save()
        return costs

    @property
    def actual_food_cost_per_portion(self):
        """Calculate actual food cost percentage if selling price is set"""
        if (
            self.actual_selling_price_per_portion
            and self.actual_selling_price_per_portion > 0
        ):
            return (
                self.total_cost_per_portion / self.actual_selling_price_per_portion
            ) * 100
        return None

    @property
    def total_cost_per_portion(self):
        """Calculate total cost per portion including waste and labor"""
        base_cost = self.base_food_cost_per_portion or 0
        waste_cost = base_cost * (self.waste_factor_percentage / 100)
        labor_cost = base_cost * (self.labour_cost_percentage / 100)
        return base_cost + waste_cost + labor_cost

    @property
    def total_prep_time(self):
        """Total preparation time for the recipe"""
        return self.prep_time_minutes + self.cook_time_minutes


class RecipeIngredient(TimeStampedModel):
    """Model representing an ingredient in a recipe."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    ingredient = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="recipes"
    )
    quantity = models.DecimalField(
        _("Quantity"),
        max_digits=15,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text=_("Quantity needed for entire recipe"),
    )

    main_ingredient = models.BooleanField(_("Main Ingredient"), default=False)
    unit_of_recipe = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        blank=True,
        null=True,
    )

    # Cost fields
    cost_per_unit = models.DecimalField(
        _("Cost per Unit"),
        max_digits=15,
        decimal_places=4,
        default=Decimal("0"),
        help_text=_("Current weighted average cost per unit"),
    )

    total_cost = models.DecimalField(
        _("Total Cost"),
        max_digits=15,
        decimal_places=4,
        default=Decimal("0"),
        help_text=_("Quantity * cost per unit"),
    )

    cost_per_portion = models.DecimalField(
        _("Cost per Portion"),
        max_digits=15,
        decimal_places=4,
        default=Decimal("0"),
        help_text=_("Total cost / recipe serving size"),
    )

    # Optional fields
    preparation_notes = models.TextField(
        _("Preparation Notes"),
        blank=True,
        help_text=_("e.g., diced, sliced, chopped, etc."),
    )

    is_optional = models.BooleanField(_("Is Optional"), default=False)

    class Meta:
        verbose_name = _("Recipe Ingredient")
        verbose_name_plural = _("Recipe Ingredients")
        ordering = ["recipe", "ingredient"]

    def __str__(self):
        return f"{self.ingredient.name} - {self.quantity} {self.unit_of_recipe.name}"

    def _calculate_costs(self):
        """Calculate ingredient costs for this recipe line"""
        from apps.analytics.services.ingredient_costing import ProductCostingService

        try:
            costing_service = ProductCostingService()
            current_cost = costing_service.get_current_product_cost(self.ingredient)

            self.cost_per_unit = current_cost
            self.total_cost = self.quantity * current_cost

            # Calculate cost per portion
            if self.recipe.serving_size > 0:
                self.cost_per_portion = self.total_cost / self.recipe.serving_size
        except Exception:
            # Fallback to product's current cost if service fails
            self.cost_per_unit = self.ingredient.current_cost_per_unit or Decimal(
                "0.00"
            )
            self.total_cost = self.quantity * self.cost_per_unit

            if self.recipe.serving_size > 0:
                self.cost_per_portion = self.total_cost / self.recipe.serving_size


class RecipeCostSnapshot(TimeStampedModel):
    """Historical recipe cost snapshots for analysis"""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="cost_snapshots",
        verbose_name=_("Recipe"),
    )

    snapshot_date = models.DateTimeField(_("Snapshot Date"))

    # Cost breakdown
    base_food_cost_per_portion = models.DecimalField(
        _("Base Food Cost per Portion"), max_digits=15, decimal_places=4
    )

    waste_cost_per_portion = models.DecimalField(
        _("Waste Cost per Portion"), max_digits=15, decimal_places=4
    )

    labor_cost_per_portion = models.DecimalField(
        _("Labor Cost per Portion"), max_digits=15, decimal_places=2
    )

    total_cost_per_portion = models.DecimalField(
        _("Total Cost per Portion"), max_digits=15, decimal_places=4
    )

    selling_price = models.DecimalField(
        _("Selling Price"), max_digits=15, decimal_places=2, null=True, blank=True
    )

    food_cost_percentage = models.DecimalField(
        _("Food Cost %"), max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Context
    calculation_method = models.CharField(
        _("Calculation Method"), max_length=50, default="weighted_average"
    )

    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Recipe Cost Snapshot")
        verbose_name_plural = _("Recipe Cost Snapshots")
        ordering = ["-snapshot_date"]

    def __str__(self):
        return f"{self.recipe.dish_name} - {self.snapshot_date.date()} ({self.total_cost_per_portion})"


class RecipeVersion(TimeStampedModel):
    """Track recipe changes over time for accurate historical COGS"""
    
    recipe = models.ForeignKey(
        Recipe, 
        on_delete=models.CASCADE, 
        related_name='versions',
        verbose_name=_("Recipe")
    )
    version_number = models.CharField(_("Version"), max_length=10)
    effective_date = models.DateField(_("Effective Date"))
    end_date = models.DateField(_("End Date"), null=True, blank=True)
    change_notes = models.TextField(_("Changes"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    class Meta:
        unique_together = ['recipe', 'effective_date']
        verbose_name = _("Recipe Version")
        verbose_name_plural = _("Recipe Versions")
        ordering = ['recipe', '-effective_date']

    def __str__(self):
        return f"{self.recipe.dish_name} v{self.version_number} ({self.effective_date})"

    @property
    def is_current_version(self):
        """Check if this is the current active version"""
        return self.end_date is None and self.is_active

    def get_ingredients_for_date(self, target_date):
        """Get recipe ingredients that were active on a specific date"""
        # This would link to RecipeIngredient with version tracking
        # For now, return current ingredients
        return self.recipe.ingredients.all()
