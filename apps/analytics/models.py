from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel
from apps.restaurant_data.models import Product, ProductType, UnitOfMeasure


class ProductCostHistory(models.Model):
    """Comprehensive product cost tracking with recipe-focused unit conversions"""

    # === BASIC INFORMATION ===
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cost_history",
        verbose_name=_("Product"),
    )
    purchase_date = models.DateTimeField(_("Purchase Date"))

    # === ORIGINAL PURCHASE DATA ===
    quantity_ordered = models.DecimalField(
        _("Quantity Ordered"),
        max_digits=15,
        decimal_places=2,
        help_text=_("Original quantity as ordered/purchased"),
    )
    unit_of_purchase = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="cost_history_as_purchase_unit",
        verbose_name=_("Unit of Purchase"),
        help_text=_("Unit of measure for the quantity ordered"),
    )
    total_amount = models.DecimalField(
        _("Total Amount"),
        max_digits=15,
        decimal_places=2,
        help_text=_("Total monetary cost of the purchase"),
    )

    # === RECIPE-SPECIFIC CONVERSION DATA ===
    unit_of_recipe = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="cost_history_as_recipe_unit",
        verbose_name=_("Unit of Recipe"),
        help_text=_("Unit of measure used in recipes for this ingredient"),
    )
    recipe_conversion_factor = models.DecimalField(
        _("Recipe Conversion Factor"),
        max_digits=15,
        decimal_places=6,
        help_text=_("Factor used to convert from purchase unit to recipe unit"),
    )
    recipe_quantity = models.DecimalField(
        _("Recipe Quantity"),
        max_digits=15,
        decimal_places=2,
        help_text=_("Quantity converted to recipe units"),
    )

    # === CALCULATED METRICS ===
    unit_cost_in_recipe_units = models.DecimalField(
        _("Unit Cost in Recipe Units"),
        max_digits=15,
        decimal_places=4,
        default=Decimal("0"),
        help_text=_("Cost per unit in recipe units"),
    )

    # === COST ANALYSIS FIELDS ===
    cost_per_unit = models.DecimalField(
        _("Cost per Unit"),
        max_digits=15,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text=_("Cost per unit (legacy field, use unit_cost_in_recipe_units)"),
    )
    quantity_purchased = models.DecimalField(
        _("Quantity Purchased"),
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text=_("Quantity purchased (legacy field, use recipe_quantity)"),
    )

    # === CATEGORY AND WEIGHTING ===
    product_category = models.ForeignKey(
        ProductType,
        on_delete=models.CASCADE,
        related_name="product_cost_history",
        verbose_name=_("Product Type"),
        help_text=_(
            "Provide both product type (resale or dish) and cost type (raw material costs, labor costs, etc.)"
        ),
    )

    weight_factor = models.DecimalField(
        _("Weight Factor"),
        max_digits=5,
        decimal_places=4,
        default=Decimal("1.0000"),
        help_text=_("Weight for average calculation (1.0 = full weight)"),
    )
    is_active = models.BooleanField(_("Is Active"), default=True)

    # === AUDIT FIELDS ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product Cost History")
        verbose_name_plural = _("Product Cost Histories")
        ordering = ["-purchase_date"]
        indexes = [
            models.Index(fields=["product", "-purchase_date"]),
            models.Index(fields=["product_category", "-purchase_date"]),
            models.Index(fields=["purchase_date"]),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.unit_cost_in_recipe_units} FCFA ({self.purchase_date.date()})"

    def save(self, *args, **kwargs):
        """Calculate derived metrics before saving"""
        self._calculate_derived_metrics()
        super().save(*args, **kwargs)

    def _calculate_derived_metrics(self):
        """Calculate metrics that derive from other fields"""

        from decimal import ROUND_HALF_UP

        # Calculate recipe quantity if conversion factor is available
        if self.recipe_conversion_factor > 0:
            self.recipe_quantity = (
                self.quantity_ordered * self.recipe_conversion_factor
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Calculate unit cost in recipe units
        if self.recipe_quantity > 0:
            self.unit_cost_in_recipe_units = (
                self.total_amount / self.recipe_quantity
            ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Set legacy fields for backward compatibility
        self.cost_per_unit = self.unit_cost_in_recipe_units
        self.quantity_purchased = self.recipe_quantity


class DailySummary(TimeStampedModel):
    """Daily restaurant performance summary with industry standard metrics"""

    # Primary Key
    date = models.DateField(_("Date"), unique=True, db_index=True)

    # === REVENUE METRICS ===
    total_sales = models.DecimalField(
        _("Total Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue for the day"),
    )
    total_orders = models.IntegerField(
        _("Total Orders"), default=0, help_text=_("Total number of orders for the day")
    )

    total_customers = models.PositiveIntegerField(
        _("Total Customers"),
        default=0,
        help_text=_("Number of customers served (covers)"),
    )

    average_order_value = models.DecimalField(
        _("Average Order Value"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total Sales ÷ Total Orders"),
    )
    average_ticket_size = models.DecimalField(
        _("Average Ticket Size"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total Sales ÷ Total Customers"),
    )

    # === PAYMENT METHODS ===
    cash_sales = models.DecimalField(
        _("Cash Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue from cash payments"),
    )
    mobile_money_sales = models.DecimalField(
        _("Mobile Money Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue from mobile money payments"),
    )
    credit_card_sales = models.DecimalField(
        _("Credit Card Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue from credit card payments"),
    )
    other_payment_methods_sales = models.DecimalField(
        _("Other Payment Methods Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue from other payment methods"),
    )

    # === COST METRICS (COGS - Cost of Goods Sold) ===
    total_food_cost = models.DecimalField(
        _("Total Food Cost"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total cost of food for the day"),
    )

    # === DUAL COGS TRACKING ===
    total_food_cost_conservative = models.DecimalField(
        _("Food Cost (Conservative)"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("COGS using only actual purchase data"),
    )

    # === CONFIDENCE METADATA ===
    cogs_confidence_level = models.CharField(
        _("COGS Confidence"),
        max_length=10,
        choices=[
            ('HIGH', 'High (90%+ actual data)'),
            ('MEDIUM', 'Medium (70-89% actual data)'),
            ('LOW', 'Low (50-69% actual data)'),
            ('VERY_LOW', 'Very Low (<50% actual data)')
        ],
        default='HIGH'
    )

    data_completeness_percentage = models.DecimalField(
        _("Data Completeness %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("100")
    )

    missing_ingredients_count = models.IntegerField(
        _("Missing Ingredients"),
        default=0
    )

    estimated_ingredients_count = models.IntegerField(
        _("Estimated Ingredients"),
        default=0
    )

    cogs_calculation_notes = models.TextField(
        _("COGS Notes"),
        blank=True
    )

    resale_cost = models.DecimalField(
        _("Resale Cost"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_(
            "Cost of products bought and resold directly (bottled drinks, packaged snacks, etc.)"
        ),
    )

    food_cost_percentage = models.DecimalField(
        _("Food Cost %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Industry standard: 25-35%"),
    )

    # === PROFITABILITY METRICS ===
    gross_profit = models.DecimalField(
        _("Gross Profit"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total Sales - Total Food Cost - Resale Cost"),
    )

    gross_profit_margin = models.DecimalField(
        _("Gross Profit Margin %"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("(Gross Profit ÷ Total Sales) × 100"),
    )

    # === OPERATIONAL METRICS ===
    total_items_sold = models.PositiveIntegerField(
        _("Total Items Sold"),
        default=0,
        help_text=_("Total quantity of all products sold"),
    )

    average_items_per_order = models.DecimalField(
        _("Average Items per Order"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total Items Sold ÷ Total Orders"),
    )
    dine_in_orders = models.PositiveIntegerField(
        _("Dine-in Orders"),
        default=0,
        help_text=_("Total number of dine-in orders for the day"),
    )
    take_out_orders = models.PositiveIntegerField(
        _("Take-out Orders"),
        default=0,
        help_text=_("Total number of take-out orders for the day"),
    )
    delivery_orders = models.PositiveIntegerField(
        _("Delivery Orders"),
        default=0,
        help_text=_("Total number of delivery orders for the day"),
    )

    # === TIME-BASED BREAKDOWN ===
    lunch_sales = models.DecimalField(
        _("Lunch Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue from lunch orders"),
    )

    dinner_sales = models.DecimalField(
        _("Dinner Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue from dinner orders"),
    )

    peak_hour_sales = models.DecimalField(
        _("Peak Hour Sales"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total sales revenue from peak hour orders"),
    )
    peak_hour_time = models.TimeField(
        _("Peak Hour Time"),
        null=True,
        blank=True,
        help_text=_("Time of day with highest sales volume"),
    )

    # === QUALITY/WASTE METRICS ===
    waste_cost = models.DecimalField(
        _("Waste Cost"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total cost of food wasted for the day"),
    )
    comps_and_discounts = models.DecimalField(
        _("Comps and Discounts"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Free items and discounts given to customers"),
    )

    # === STAFF METRICS ===
    staff_count = models.IntegerField(
        _("Staff Count"), default=0, help_text=_("Total number of staff for the day")
    )
    sales_per_staff = models.DecimalField(
        _("Sales per Staff"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total Sales ÷ Total Staff"),
    )

    # === WEATHER/EXTERNAL FACTORS ===
    WEATHER_CONDITIONS = [
        ("sunny", _("Sunny")),
        ("cloudy", _("Cloudy")),
        ("rainy", _("Rainy")),
        ("stormy", _("Stormy")),
    ]
    weather_conditions = models.CharField(
        _("Weather Conditions"),
        max_length=255,
        choices=WEATHER_CONDITIONS,
        default="sunny",
        help_text=_("Weather conditions for the day"),
    )
    is_holiday = models.BooleanField(
        _("Is Holiday"), default=False, help_text=_("Whether the day is a holiday")
    )
    special_events = models.CharField(
        _("Special Events"),
        max_length=255,
        blank=True,
        help_text=_("Any special events, promotions, or circumstances"),
    )

    # === NOTES ===
    manager_notes = models.TextField(
        _("Manager Notes"),
        blank=True,
        null=True,
        help_text=_("Notes from the manager for the day"),
    )

    class Meta:
        verbose_name = _("Daily Summary")
        verbose_name_plural = _("Daily Summaries")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["date", "total_sales"]),
        ]

    def __str__(self):
        return f"Daily Summary - {self.date} ({self.total_sales})"

    def save(self, *args, **kwargs):
        """Calculate derived metrics before saving and ensure all decimal fields are properly rounded"""
        import decimal

        # List all decimal fields to check
        decimal_fields = [
            "total_sales",
            "total_food_cost",
            "gross_profit",
            "gross_profit_margin",
            "average_order_value",
            "average_ticket_size",
            "food_cost_percentage",
            "cash_sales",
            "mobile_money_sales",
            "credit_card_sales",
            "other_payment_methods_sales",
            "lunch_sales",
            "dinner_sales",
            "peak_hour_sales",
            "resale_cost",
            "waste_cost",
            "comps_and_discounts",
            "average_items_per_order",
            "sales_per_staff",
        ]

        print(f"\n=== DEBUGGING SAVE FOR {self.date} ===")

        for field_name in decimal_fields:
            value = getattr(self, field_name, None)
            if value is not None:
                print(f"{field_name}: {value} (type: {type(value)})")

                # Check for invalid values
                if isinstance(value, decimal.Decimal):
                    if value.is_nan():
                        print(f"❌ {field_name} is NaN!")
                    elif value.is_infinite():
                        print(f"❌ {field_name} is infinite!")
                    elif abs(value) > decimal.Decimal(
                        "999999999999999"
                    ):  # max_digits=15
                        print(f"❌ {field_name} exceeds max_digits=15: {value}")

                    # Try to quantize and catch specific errors
                    try:
                        # Assuming 2 decimal places for most fields
                        quantized = value.quantize(decimal.Decimal("0.01"))
                        print(f"✅ {field_name} quantizes OK: {quantized}")
                    except decimal.InvalidOperation as e:
                        print(f"❌ {field_name} quantize failed: {e}")
                        print(f"   Original value: {repr(value)}")

        # Round all decimal fields before saving
        for field_name in decimal_fields:
            value = getattr(self, field_name, None)
            if value is not None and isinstance(value, decimal.Decimal):
                # Handle invalid decimals
                if value.is_nan() or value.is_infinite():
                    print(f"🔧 Setting {field_name} to 0 (was {value})")
                    setattr(self, field_name, decimal.Decimal("0.00"))
                else:
                    # Round to 2 decimal places and ensure it fits constraints
                    try:
                        rounded = value.quantize(decimal.Decimal("0.01"))
                        if abs(rounded) > decimal.Decimal("999999999999999"):
                            print(
                                f"🔧 Capping {field_name} to max value (was {rounded})"
                            )
                            setattr(
                                self, field_name, decimal.Decimal("999999999999999.00")
                            )
                        else:
                            setattr(self, field_name, rounded)
                    except decimal.InvalidOperation:
                        print(
                            f"🔧 Setting {field_name} to 0 (invalid decimal: {value})"
                        )
                        setattr(self, field_name, decimal.Decimal("0.00"))

        self._calculate_derived_metrics()
        super().save(*args, **kwargs)

    def _calculate_derived_metrics(self):
        """Calculate metrics that derive from other fields"""

        from decimal import ROUND_HALF_UP

        # Note: total_orders is calculated from sales data, not from dine_in + take_out + delivery
        # self.total_orders = (
        #     self.dine_in_orders + self.take_out_orders + self.delivery_orders
        # )
        # Average order value
        if self.total_orders > 0:
            self.average_order_value = (self.total_sales / self.total_orders).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        # Average ticket size
        if self.total_customers > 0:
            self.average_ticket_size = (
                self.total_sales / self.total_customers
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Food Cost Percentage
        if self.total_sales > 0:
            self.food_cost_percentage = (
                (self.total_food_cost / self.total_sales) * 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Gross Profit
        self.gross_profit = (
            self.total_sales - self.total_food_cost - self.resale_cost
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Gross Profit Margin
        if self.total_sales > 0:
            self.gross_profit_margin = (
                (self.gross_profit / self.total_sales) * 100
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Average Items per Order
        if self.total_orders > 0:
            self.average_items_per_order = (
                self.total_items_sold / self.total_orders
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Sales per Staff
        if self.staff_count > 0:
            self.sales_per_staff = (self.total_sales / self.staff_count).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

    # === ANALYSIS METHODS ===

    @property
    def is_food_cost_healthy(self):
        """Check if food cost percentage is within industry standards (25-35%)"""
        return 25 <= self.food_cost_percentage <= 35

    @property
    def food_cost_status(self):
        """Get food cost status"""
        if self.food_cost_percentage == 0:
            return "unknown"
        elif self.food_cost_percentage < 25:
            return "excellent"  # Very good
        elif 25 <= self.food_cost_percentage <= 30:
            return "good"  # Industry standard
        elif 30 < self.food_cost_percentage <= 35:
            return "acceptable"  # Still okay
        else:
            return "high"  # Needs attention

    @property
    def cash_percentage(self):
        """Percentage of sales paid in cash"""
        if self.total_sales > 0:
            return (self.cash_sales / self.total_sales) * 100
        return 0

    @property
    def digital_payment_percentage(self):
        """Percentage of sales paid digitally (card + mobile money)"""
        digital_sales = self.credit_card_sales + self.mobile_money_sales
        if self.total_sales > 0:
            return (digital_sales / self.total_sales) * 100
        return 0

    def get_performance_grade(self):
        """Get overall performance grade A-F"""
        food_score = 0

        # Food cost score (40% weight)
        if self.food_cost_percentage == 0:
            food_score = 0
        elif self.food_cost_percentage <= 30:
            food_score = 40
        elif self.food_cost_percentage <= 35:
            food_score = 30
        else:
            food_score = 10

        # Revenue score (30% weight)
        # This would need historical comparison, simplified for now
        revenue_score = 30 if self.total_sales > 0 else 0

        # Efficiency score (30% weight)
        efficiency_score = 0
        if self.average_order_value > 0:
            efficiency_score += 15
        if self.total_customers > 0:
            efficiency_score += 15

        total_score = food_score + revenue_score + efficiency_score

        if total_score >= 90:
            return "A"
        elif total_score >= 80:
            return "B"
        elif total_score >= 70:
            return "C"
        elif total_score >= 60:
            return "D"
        else:
            return "F"
