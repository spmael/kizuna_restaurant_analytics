from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Product,
    Purchase,
    PurchasesCategory,
    Recipe,
    RecipeIngredient,
    Sales,
    SalesCategory,
    UnitOfMeasure,
)


@admin.register(PurchasesCategory)
class PurchasesCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "sort_order", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "name_fr", "name_en")
    ordering = ("sort_order", "name")

    fieldsets = (
        (None, {"fields": ("name", "sort_order", "description")}),
        ("Translations", {"fields": ("name_fr", "name_en"), "classes": ("collapse",)}),
        (_("Status"), {"fields": ("is_active",)}),
    )


@admin.register(SalesCategory)
class SalesCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "sort_order", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "name_fr", "name_en")
    ordering = ("sort_order", "name")

    fieldsets = (
        (None, {"fields": ("name", "sort_order", "description")}),
        ("Translations", {"fields": ("name_fr", "name_en"), "classes": ("collapse",)}),
        (_("Status"), {"fields": ("is_active",)}),
    )


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ("name", "abbreviation", "name_fr", "sort_order", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "abbreviation", "name_fr", "name_en")
    ordering = ("sort_order", "name")

    fieldsets = (
        (None, {"fields": ("name", "abbreviation", "sort_order", "description")}),
        ("Translations", {"fields": ("name_fr", "name_en"), "classes": ("collapse",)}),
        (_("Status"), {"fields": ("is_active",)}),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sales_category",
        "purchase_category",
        "unit_of_measure",
        "current_selling_price",
        "current_cost_per_unit",
        "current_stock",
        "updated_at",
    )
    list_filter = (
        "sales_category",
        "purchase_category",
        "unit_of_measure",
        "is_active",
        "updated_at",
    )
    search_fields = ("name", "name_fr", "name_en")
    readonly_fields = ("stock_value",)

    fieldsets = (
        (None, {"fields": ("name", "sales_category", "purchase_category")}),
        ("Translations", {"fields": ("name_fr", "name_en"), "classes": ("collapse",)}),
        (
            "Measurmenet & Pricing",
            {
                "fields": (
                    "unit_of_measure",
                    "current_selling_price",
                    "current_cost_per_unit",
                ),
            },
        ),
        ("Inventory", {"fields": ("current_stock", "stock_value")}),
        ("Description", {"fields": ("description",)}),
        (_("Status"), {"fields": ("is_active",)}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("sales_category")
        return qs


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "purchase_date",
        "quantity_purchased",
        "total_cost",
        "cost_type_fr",
        "cost_type_en",
        "unit_of_recipe",
        "created_at",
    )
    list_filter = ("status", "created_at")
    date_hierarchy = "purchase_date"
    readonly_fields = ("total_cost",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "product",
                    "purchase_date",
                    "quantity_purchased",
                    "updated_at",
                )
            },
        ),
        (_("Financials"), {"fields": ("total_cost",)}),
        (_("Cost Type"), {"fields": ("cost_type_fr", "cost_type_en")}),
        (_("Additional Information"), {"fields": ("unit_of_recipe")}),
    )


@admin.register(Sales)
class SalesAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "sale_date",
        "quantity_sold",
        "total_revenue",
        "created_at",
    )
    list_filter = ("status", "created_at")
    date_hierarchy = "sale_date"
    readonly_fields = ("total_revenue",)

    fieldsets = (
        (None, {"fields": ("product", "sale_date", "quantity_sold", "updated_at")}),
        (_("Financials"), {"fields": ("total_revenue",)}),
        (
            _("Additional Information"),
            {"fields": ("customer", "cashier")},
        ),
    )


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "name_en")
    inlines = [RecipeIngredientInline]

    fieldsets = ((None, {"fields": ("name", "description")}),)
