from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import DailySummary, ProductCostHistory


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "total_sales",
        "total_orders",
        "total_customers",
        "food_cost_percentage",
        "gross_profit_margin",
    )
    list_filter = (
        "date",
        "weather_conditions",
        "is_holiday",
    )
    search_fields = ("date", "special_events", "manager_notes")
    readonly_fields = (
        "average_order_value",
        "average_ticket_size",
        "food_cost_percentage",
        "gross_profit",
        "gross_profit_margin",
        "average_items_per_order",
        "sales_per_staff",
    )
    date_hierarchy = "date"
    ordering = ("-date",)

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("date", "weather_conditions", "is_holiday", "special_events")},
        ),
        (
            _("Sales Metrics"),
            {
                "fields": (
                    "total_sales",
                    "total_orders",
                    "total_customers",
                    "average_order_value",
                    "average_ticket_size",
                    "total_items_sold",
                    "average_items_per_order",
                )
            },
        ),
        (
            _("Payment Methods"),
            {
                "fields": (
                    "cash_sales",
                    "mobile_money_sales",
                    "credit_card_sales",
                    "other_payment_methods_sales",
                )
            },
        ),
        (
            _("Cost Metrics"),
            {
                "fields": (
                    "total_food_cost",
                    "resale_cost",
                    "food_cost_percentage",
                    "waste_cost",
                    "comps_and_discounts",
                )
            },
        ),
        (
            _("Profitability"),
            {
                "fields": (
                    "gross_profit",
                    "gross_profit_margin",
                )
            },
        ),
        (
            _("Operational Metrics"),
            {
                "fields": (
                    "dine_in_orders",
                    "take_out_orders",
                    "delivery_orders",
                    "staff_count",
                    "sales_per_staff",
                )
            },
        ),
        (
            _("Time-based Breakdown"),
            {
                "fields": (
                    "lunch_sales",
                    "dinner_sales",
                    "peak_hour_sales",
                    "peak_hour_time",
                )
            },
        ),
        (
            _("Notes"),
            {"fields": ("manager_notes",)},
        ),
    )


@admin.register(ProductCostHistory)
class ProductCostHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "purchase_date",
        "unit_cost_in_recipe_units",
        "recipe_quantity",
        "unit_of_recipe",
        "is_active",
    )
    list_filter = (
        "purchase_date",
        "is_active",
        "product_category",
        "unit_of_recipe",
    )
    search_fields = (
        "product__name",
        "product__name_fr",
        "product__name_en",
    )
    readonly_fields = (
        "unit_cost_in_recipe_units",
        "recipe_quantity",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "purchase_date"
    ordering = ("-purchase_date", "product")

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("product", "purchase_date", "is_active")},
        ),
        (
            _("Original Purchase Data"),
            {
                "fields": (
                    "quantity_ordered",
                    "unit_of_purchase",
                    "total_amount",
                )
            },
        ),
        (
            _("Recipe Conversion Data"),
            {
                "fields": (
                    "unit_of_recipe",
                    "recipe_conversion_factor",
                    "recipe_quantity",
                    "unit_cost_in_recipe_units",
                )
            },
        ),
        (
            _("Analysis"),
            {
                "fields": (
                    "product_category",
                    "weight_factor",
                )
            },
        ),
        (
            _("Legacy Fields"),
            {
                "fields": (
                    "cost_per_unit",
                    "quantity_purchased",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
