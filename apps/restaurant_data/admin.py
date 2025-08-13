from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    ConsolidatedPurchases,
    ConsolidatedSales,
    Product,
    ProductConsolidation,
    ProductType,
    Purchase,
    PurchasesCategory,
    Sales,
    SalesCategory,
    StandardKitchenUnit,
    UnitConversion,
    UnitOfMeasure,
)


class ProductTypeInline(admin.TabularInline):
    """Inline admin for ProductType within Product admin"""

    model = ProductType
    extra = 1
    fields = ("cost_type", "product_type", "cost_type_fr", "cost_type_en")
    verbose_name = _("Product Cost Type")
    verbose_name_plural = _("Product Cost Types")


@admin.register(PurchasesCategory)
class PurchasesCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "name_fr", "name_en")
    ordering = ("sort_order", "name")

    fieldsets = (
        (None, {"fields": ("name", "sort_order", "description")}),
        ("Translations", {"fields": ("name_fr", "name_en"), "classes": ("collapse",)}),
        (_("Status"), {"fields": ("is_active",)}),
    )


@admin.register(SalesCategory)
class SalesCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fr", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "name_fr", "name_en")
    ordering = ("sort_order", "name")

    fieldsets = (
        (None, {"fields": ("name", "sort_order", "description")}),
        ("Translations", {"fields": ("name_fr", "name_en"), "classes": ("collapse",)}),
        (_("Status"), {"fields": ("is_active",)}),
    )


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ("name", "abbreviation", "name_fr", "sort_order")
    list_filter = ("is_active",)
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
        "product_types_count",
    )
    list_filter = (
        "sales_category",
        "purchase_category",
        "unit_of_measure",
    )
    search_fields = ("name", "name_fr", "name_en")
    readonly_fields = ("stock_value", "product_types_count")
    inlines = [ProductTypeInline]

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
    )

    def product_types_count(self, obj):
        """Display the number of product types associated with this product"""
        return obj.product_cost_types.count()

    product_types_count.short_description = _("Cost Types")

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("sales_category")
        return qs


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    """Admin interface for Product Type management"""

    list_display = (
        "product",
        "cost_type_display",
        "product_type_display",
        "cost_type_fr",
        "cost_type_en",
    )

    list_filter = (
        "cost_type",
        "product_type",
        "product__purchase_category",
        "product__sales_category",
    )

    search_fields = (
        "product__name",
        "product__name_fr",
        "product__name_en",
        "cost_type_fr",
        "cost_type_en",
    )

    autocomplete_fields = ["product"]

    fieldsets = (
        (
            _("Product Association"),
            {
                "fields": ("product",),
                "description": _("Select the product this cost type applies to"),
            },
        ),
        (
            _("Cost Classification"),
            {
                "fields": (
                    "cost_type",
                    "cost_type_fr",
                    "cost_type_en",
                ),
                "description": _("Define the type of cost and its translations"),
            },
        ),
        (
            _("Product Classification"),
            {
                "fields": ("product_type",),
                "description": _("Classify the product type for business logic"),
            },
        ),
    )

    def cost_type_display(self, obj):
        """Display the cost type with better formatting"""
        return dict(ProductType.COST_TYPE_CHOICES).get(obj.cost_type, obj.cost_type)

    def product_type_display(self, obj):
        """Display the product type with better formatting"""
        return dict(ProductType.PRODUCT_TYPE_CHOICES).get(
            obj.product_type, obj.product_type
        )

    cost_type_display.short_description = _("Cost Type")
    product_type_display.short_description = _("Product Type")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "product", "product__purchase_category", "product__sales_category"
            )
        )


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "purchase_date",
        "quantity_purchased",
        "total_cost",
    )
    list_filter = ("purchase_date",)
    date_hierarchy = "purchase_date"
    search_fields = ("product__name", "product__name_fr", "product__name_en")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "product",
                    "purchase_date",
                    "quantity_purchased",
                    "total_cost",
                )
            },
        ),
    )


@admin.register(Sales)
class SalesAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "sale_date",
        "order_number",
        "quantity_sold",
        "unit_sale_price",
        "total_sale_price",
    )
    list_filter = ("sale_date",)
    date_hierarchy = "sale_date"

    fieldsets = (
        (None, {"fields": ("product", "sale_date", "order_number")}),
        (
            _("Financials"),
            {"fields": ("quantity_sold", "unit_sale_price", "total_sale_price")},
        ),
        (
            _("Additional Information"),
            {"fields": ("customer", "cashier")},
        ),
    )


@admin.register(ProductConsolidation)
class ProductConsolidationAdmin(admin.ModelAdmin):
    list_display = (
        "primary_product",
        "consolidated_products_count",
        "consolidated_products_names",
        "consolidation_reason",
        "confidence_score",
        "is_verified",
    )
    list_filter = (
        "consolidation_reason",
        "is_verified",
    )
    search_fields = ("primary_product__name", "notes")
    readonly_fields = ("consolidated_products_count", "consolidated_products_display")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "primary_product",
                    "consolidation_reason",
                    "confidence_score",
                    "is_verified",
                )
            },
        ),
        (
            "Consolidated Products",
            {
                "fields": (
                    "consolidated_products_display",
                    "consolidated_products",
                    "similarity_scores",
                ),
                "description": "Products that are consolidated into the primary product",
            },
        ),
        ("Additional Information", {"fields": ("notes",), "classes": ("collapse",)}),
    )

    def consolidated_products_count(self, obj):
        return len(obj.consolidated_products)

    def consolidated_products_names(self, obj):
        """Display consolidated product names in list view"""
        names = obj.consolidated_product_names
        if not names:
            return "None"
        # Limit display length for list view
        display = ", ".join(names)
        if len(display) > 100:
            return display[:97] + "..."
        return display

    consolidated_products_count.short_description = "Count"
    consolidated_products_names.short_description = "Consolidated Products"


@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    """Admin interface for unit conversions"""

    list_display = [
        "from_unit",
        "to_unit",
        "conversion_factor",
        "context_display",
        "is_active",
        "priority",
    ]

    list_filter = [
        "is_active",
        "from_unit",
        "to_unit",
        "category",
        "priority",
    ]

    search_fields = [
        "from_unit__name",
        "to_unit__name",
        "product__name",
        "category__name",
        "notes",
    ]

    fieldsets = (
        (
            _("Basic Conversion"),
            {
                "fields": (
                    "from_unit",
                    "to_unit",
                    "conversion_factor",
                    "is_active",
                    "priority",
                )
            },
        ),
        (
            _("Context (Optional)"),
            {
                "fields": ("product", "category"),
                "description": _(
                    "Specify either product or category to make this conversion context-specific"
                ),
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": ("notes",),
                "classes": ("collapse",),
            },
        ),
    )

    def context_display(self, obj):
        """Display the context (product or category) for this conversion"""
        if obj.product:
            return f"Product: {obj.product.name}"
        elif obj.category:
            return f"Category: {obj.category.name}"
        return "General"

    context_display.short_description = _("Context")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("from_unit", "to_unit", "product", "category")
        )


@admin.register(StandardKitchenUnit)
class StandardKitchenUnitAdmin(admin.ModelAdmin):
    """Admin interface for standard kitchen units"""

    list_display = [
        "context_display",
        "standard_unit",
        "is_active",
        "priority",
    ]

    list_filter = [
        "is_active",
        "standard_unit",
        "category",
        "priority",
    ]

    search_fields = [
        "product__name",
        "category__name",
        "standard_unit__name",
        "description",
    ]

    fieldsets = (
        (
            _("Standard Unit Definition"),
            {"fields": ("standard_unit", "is_active", "priority")},
        ),
        (
            _("Context (Choose One)"),
            {
                "fields": ("product", "category"),
                "description": _(
                    "Specify either product or category for this standard unit"
                ),
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": ("description",),
                "classes": ("collapse",),
            },
        ),
    )

    def context_display(self, obj):
        """Display the context (product or category) for this standard"""
        if obj.product:
            return f"Product: {obj.product.name}"
        elif obj.category:
            return f"Category: {obj.category.name}"
        return "Unknown"

    context_display.short_description = _("Applied To")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("product", "category", "standard_unit")
        )


@admin.register(ConsolidatedPurchases)
class ConsolidatedPurchasesAdmin(admin.ModelAdmin):
    """Admin interface for consolidated purchases"""

    list_display = [
        "product",
        "purchase_date",
        "quantity_purchased",
        "total_cost",
        "consolidation_applied",
    ]

    list_filter = [
        "consolidation_applied",
        "purchase_date",
        "product__purchase_category",
    ]

    search_fields = [
        "product__name",
        "consolidated_product_names",
    ]

    readonly_fields = [
        "consolidated_product_names_display",
    ]

    fieldsets = (
        (
            _("Product Information"),
            {"fields": ("product", "purchase_date")},
        ),
        (
            _("Purchase Information"),
            {
                "fields": (
                    "quantity_purchased",
                    "total_cost",
                    "unit_of_purchase",
                    "unit_of_recipe",
                )
            },
        ),
        (
            _("Consolidation Information"),
            {
                "fields": (
                    "consolidation_applied",
                    "consolidated_product_names_display",
                    "consolidated_product_names",
                )
            },
        ),
    )

    def consolidated_product_names_display(self, obj):
        """Display consolidated product names as formatted string"""
        if not obj.consolidated_product_names:
            return "None"
        return ", ".join(obj.consolidated_product_names)

    consolidated_product_names_display.short_description = _(
        "Consolidated Product Names"
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("product", "unit_of_purchase", "unit_of_recipe")
        )


@admin.register(ConsolidatedSales)
class ConsolidatedSalesAdmin(admin.ModelAdmin):
    """Admin interface for consolidated sales"""

    list_display = [
        "product",
        "sale_date",
        "order_number",
        "quantity_sold",
        "total_sale_price",
        "consolidation_applied",
    ]

    list_filter = [
        "consolidation_applied",
        "sale_date",
        "product__sales_category",
    ]

    search_fields = [
        "product__name",
        "order_number",
        "consolidated_product_names",
    ]

    readonly_fields = [
        "consolidated_product_names_display",
    ]

    fieldsets = (
        (
            _("Product Information"),
            {"fields": ("product", "sale_date", "order_number")},
        ),
        (
            _("Sale Information"),
            {
                "fields": (
                    "quantity_sold",
                    "unit_sale_price",
                    "total_sale_price",
                    "customer",
                    "cashier",
                    "unit_of_sale",
                    "unit_of_recipe",
                )
            },
        ),
        (
            _("Consolidation Information"),
            {
                "fields": (
                    "consolidation_applied",
                    "consolidated_product_names_display",
                    "consolidated_product_names",
                )
            },
        ),
    )

    def consolidated_product_names_display(self, obj):
        """Display consolidated product names as formatted string"""
        if not obj.consolidated_product_names:
            return "None"
        return ", ".join(obj.consolidated_product_names)

    consolidated_product_names_display.short_description = _(
        "Consolidated Product Names"
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("product", "unit_of_sale", "unit_of_recipe")
        )
