from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import Recipe, RecipeCostSnapshot, RecipeIngredient


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    fields = (
        "ingredient",
        "quantity",
        "unit_of_recipe",
        "main_ingredient",
        "cost_per_unit",
        "total_cost",
        "is_optional",
    )
    readonly_fields = ("cost_per_unit", "total_cost")

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("ingredient", "unit_of_recipe")
        )


class RecipeCostSnapshotInline(admin.TabularInline):
    model = RecipeCostSnapshot
    extra = 0
    readonly_fields = (
        "snapshot_date",
        "base_food_cost_per_portion",
        "waste_cost_per_portion",
        "labor_cost_per_portion",
        "total_cost_per_portion",
        "selling_price",
        "food_cost_percentage",
    )
    fields = (
        "snapshot_date",
        "base_food_cost_per_portion",
        "waste_cost_per_portion",
        "labor_cost_per_portion",
        "total_cost_per_portion",
        "selling_price",
        "food_cost_percentage",
        "calculation_method",
        "notes",
    )

    def has_add_permission(self, request, obj=None):
        return False  # Snapshots should be created programmatically


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "dish_name",
        "category",
        "serving_size",
        "total_prep_time_display",
        "base_food_cost_per_portion",
        "suggested_selling_price_per_portion",
        "actual_food_cost_percentage_display",
        "is_active",
        "ingredients_count",
    )
    list_filter = ("category", "is_active", "is_seasonal", "last_costed_date")
    search_fields = ("dish_name", "dish_name_fr", "dish_name_en", "description")
    readonly_fields = (
        "base_food_cost_per_portion",
        "suggested_selling_price_per_portion",
        "actual_food_cost_percentage_display",
        "total_prep_time_display",
        "ingredients_summary",
        "cost_history_link",
    )
    inlines = [RecipeIngredientInline, RecipeCostSnapshotInline]

    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": (
                    "dish_name",
                    "dish_name_fr",
                    "dish_name_en",
                    "description",
                    "category",
                )
            },
        ),
        (_("Portion Information"), {"fields": ("serving_size", "portion_weight")}),
        (
            _("Timing"),
            {
                "fields": (
                    "prep_time_minutes",
                    "cook_time_minutes",
                    "total_prep_time_display",
                )
            },
        ),
        (
            _("Costing"),
            {
                "fields": (
                    "base_food_cost_per_portion",
                    "waste_factor_percentage",
                    "labour_cost_percentage",
                    "target_food_cost_percentage",
                    "suggested_selling_price_per_portion",
                    "actual_selling_price_per_portion",
                    "actual_food_cost_percentage_display",
                )
            },
        ),
        (
            _("Status & Metadata"),
            {
                "fields": (
                    "is_active",
                    "is_seasonal",
                    "last_costed_date",
                    "cost_calculation_notes",
                )
            },
        ),
        (
            _("Ingredients & History"),
            {
                "fields": ("ingredients_summary", "cost_history_link"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = [
        "recalculate_costs",
        "create_cost_snapshot",
        "activate_recipes",
        "deactivate_recipes",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("ingredients")

    def total_prep_time_display(self, obj):
        """Display total prep time in a readable format"""
        total_minutes = obj.total_prep_time
        if total_minutes < 60:
            return f"{total_minutes} min"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h {minutes}m"

    total_prep_time_display.short_description = _("Total Time")

    def actual_food_cost_percentage_display(self, obj):
        """Display actual food cost percentage with color coding"""
        if obj.actual_food_cost_per_portion:
            percentage = obj.actual_food_cost_per_portion
            if percentage <= 25:
                color = "green"
            elif percentage <= 35:
                color = "orange"
            else:
                color = "red"
            return format_html(
                '<span style="color: {};">{:.1f}%</span>', color, percentage
            )
        return "-"

    actual_food_cost_percentage_display.short_description = _("Actual Food Cost %")

    def ingredients_count(self, obj):
        """Display number of ingredients"""
        return obj.ingredients.count()

    ingredients_count.short_description = _("Ingredients")

    def ingredients_summary(self, obj):
        """Display a summary of ingredients with costs"""
        ingredients = obj.ingredients.all().select_related(
            "ingredient", "unit_of_recipe"
        )
        if not ingredients:
            return "No ingredients added yet."

        summary = []
        total_cost = 0

        for ing in ingredients:
            cost = ing.total_cost or 0
            total_cost += cost
            unit_name = ing.unit_of_recipe.name if ing.unit_of_recipe else "unit"
            summary.append(
                f"• {ing.ingredient.name}: {ing.quantity} {unit_name} " f"(${cost:.2f})"
            )

        summary.append(f"\n<b>Total Cost: ${total_cost:.2f}</b>")
        return mark_safe("<br>".join(summary))

    ingredients_summary.short_description = _("Ingredients Summary")

    def cost_history_link(self, obj):
        """Link to view cost history"""
        if obj.cost_snapshots.exists():
            count = obj.cost_snapshots.count()
            return format_html(
                '<a href="{}">View {} cost snapshots</a>',
                reverse("admin:recipes_recipecostsnapshot_changelist")
                + f"?recipe__id__exact={obj.id}",
                count,
            )
        return "No cost history available"

    cost_history_link.short_description = _("Cost History")

    def recalculate_costs(self, request, queryset):
        """Recalculate costs for selected recipes"""
        updated = 0
        for recipe in queryset:
            try:
                recipe.calculate_costs()
                updated += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error calculating costs for {recipe.dish_name}: {str(e)}",
                    level="ERROR",
                )

        self.message_user(
            request, f"Successfully recalculated costs for {updated} recipes."
        )

    recalculate_costs.short_description = _("Recalculate costs for selected recipes")

    def create_cost_snapshot(self, request, queryset):
        """Create cost snapshots for selected recipes"""
        from django.utils import timezone

        created = 0
        for recipe in queryset:
            try:
                # Calculate current costs
                costs = recipe.calculate_costs(save=False)

                # Create snapshot
                RecipeCostSnapshot.objects.create(
                    recipe=recipe,
                    snapshot_date=timezone.now(),
                    base_food_cost_per_portion=costs.get("base_cost_per_portion", 0),
                    waste_cost_per_portion=costs.get("waste_cost_per_portion", 0),
                    labor_cost_per_portion=costs.get("labor_cost_per_portion", 0),
                    total_cost_per_portion=costs.get("total_cost_per_portion", 0),
                    selling_price=recipe.actual_selling_price_per_portion,
                    food_cost_percentage=recipe.actual_food_cost_per_portion,
                    calculation_method="weighted_average",
                    notes="Snapshot created from admin action",
                )
                created += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error creating snapshot for {recipe.dish_name}: {str(e)}",
                    level="ERROR",
                )

        self.message_user(
            request, f"Successfully created cost snapshots for {created} recipes."
        )

    create_cost_snapshot.short_description = _(
        "Create cost snapshots for selected recipes"
    )

    def activate_recipes(self, request, queryset):
        """Activate selected recipes"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Successfully activated {updated} recipes.")

    activate_recipes.short_description = _("Activate selected recipes")

    def deactivate_recipes(self, request, queryset):
        """Deactivate selected recipes"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Successfully deactivated {updated} recipes.")

    deactivate_recipes.short_description = _("Deactivate selected recipes")


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = (
        "recipe",
        "ingredient",
        "quantity",
        "unit_of_recipe",
        "main_ingredient",
        "cost_per_unit",
        "total_cost",
        "is_optional",
    )
    list_filter = (
        "main_ingredient",
        "unit_of_recipe",
        "is_optional",
        "recipe__category",
    )
    search_fields = ("recipe__dish_name", "ingredient__name")
    readonly_fields = ("cost_per_unit", "total_cost", "cost_per_portion")

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("recipe", "ingredient", "quantity", "unit_of_recipe")},
        ),
        (_("Costing"), {"fields": ("cost_per_unit", "total_cost", "cost_per_portion")}),
        (
            _("Options"),
            {"fields": ("main_ingredient", "is_optional", "preparation_notes")},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("recipe", "ingredient", "unit_of_recipe")
        )


@admin.register(RecipeCostSnapshot)
class RecipeCostSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "recipe",
        "snapshot_date",
        "base_food_cost_per_portion",
        "total_cost_per_portion",
        "selling_price",
        "food_cost_percentage_display",
        "calculation_method",
    )
    list_filter = ("snapshot_date", "calculation_method", "recipe__category")
    search_fields = ("recipe__dish_name", "notes")
    readonly_fields = (
        "snapshot_date",
        "base_food_cost_per_portion",
        "waste_cost_per_portion",
        "labor_cost_per_portion",
        "total_cost_per_portion",
        "selling_price",
        "food_cost_percentage",
    )
    date_hierarchy = "snapshot_date"

    fieldsets = (
        (_("Recipe Information"), {"fields": ("recipe", "snapshot_date")}),
        (
            _("Cost Breakdown"),
            {
                "fields": (
                    "base_food_cost_per_portion",
                    "waste_cost_per_portion",
                    "labor_cost_per_portion",
                    "total_cost_per_portion",
                )
            },
        ),
        (_("Pricing"), {"fields": ("selling_price", "food_cost_percentage")}),
        (_("Metadata"), {"fields": ("calculation_method", "notes")}),
    )

    def food_cost_percentage_display(self, obj):
        """Display food cost percentage with color coding"""
        if obj.food_cost_percentage:
            percentage = obj.food_cost_percentage
            if percentage <= 25:
                color = "green"
            elif percentage <= 35:
                color = "orange"
            else:
                color = "red"
            return format_html(
                '<span style="color: {};">{:.1f}%</span>', color, percentage
            )
        return "-"

    food_cost_percentage_display.short_description = _("Food Cost %")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("recipe")

    actions = ["export_cost_history"]

    def export_cost_history(self, request, queryset):
        """Export cost history to CSV"""
        import csv

        from django.http import HttpResponse
        from django.utils import timezone

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="recipe_cost_history_{timezone.now().strftime("%Y%m%d")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Recipe",
                "Snapshot Date",
                "Base Cost",
                "Waste Cost",
                "Labor Cost",
                "Total Cost",
                "Selling Price",
                "Food Cost %",
                "Method",
                "Notes",
            ]
        )

        for snapshot in queryset:
            writer.writerow(
                [
                    snapshot.recipe.dish_name,
                    snapshot.snapshot_date.strftime("%Y-%m-%d %H:%M"),
                    snapshot.base_food_cost_per_portion,
                    snapshot.waste_cost_per_portion,
                    snapshot.labor_cost_per_portion,
                    snapshot.total_cost_per_portion,
                    snapshot.selling_price or "",
                    snapshot.food_cost_percentage or "",
                    snapshot.calculation_method,
                    snapshot.notes,
                ]
            )

        return response

    export_cost_history.short_description = _("Export cost history to CSV")
