import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from django.utils import timezone

from apps.analytics.services.ingredient_costing import ProductCostingService
from apps.recipes.models import Recipe, RecipeCostSnapshot, RecipeIngredient

logger = logging.getLogger(__name__)


class RecipeCostingService:
    """Service for calculating recipe costs based on ingredient costs"""

    def __init__(self):
        self.ingredient_service = ProductCostingService()

    def calculate_recipe_cost(self, recipe: Recipe, as_of_date=None) -> Dict:
        """Calculate recipe cost breakdown"""

        if as_of_date is None:
            as_of_date = timezone.now()
        elif hasattr(as_of_date, "date") and not hasattr(as_of_date, "hour"):
            # If it's a date object, convert to datetime
            as_of_date = datetime.combine(as_of_date, datetime.min.time())

        # Calculate ingredient costs
        ingredient_costs = self._calculate_ingredient_costs(recipe, as_of_date)

        # Calculate waste cost
        base_cost = ingredient_costs["total_ingredient_cost"]
        waste_cost = base_cost * (recipe.waste_factor_percentage / 100)

        # Add labor cost (apply percentage to batch/base cost only)
        labor_cost = base_cost * (recipe.labour_cost_percentage / 100)

        # Total costs
        total_recipe_cost = base_cost + waste_cost + labor_cost
        if recipe.serving_size > 0:
            cost_per_portion = total_recipe_cost / recipe.serving_size
        else:
            cost_per_portion = Decimal("0")

        # Calculate suggested selling price
        if recipe.target_food_cost_percentage > 0:
            suggested_selling_price = cost_per_portion / (
                recipe.target_food_cost_percentage / 100
            )
        else:
            suggested_selling_price = cost_per_portion * Decimal(
                "3.33"
            )  # 30% food cost

        return {
            "ingredient": ingredient_costs["ingredients"],
            "total_ingredient_cost": ingredient_costs["total_ingredient_cost"],
            "waste_cost": waste_cost,
            "labor_cost": labor_cost,
            "total_recipe_cost": total_recipe_cost,
            "base_cost_per_portion": (
                base_cost / recipe.serving_size
                if recipe.serving_size > 0
                else Decimal("0")
            ),
            "total_cost_per_portion": cost_per_portion,
            "suggested_selling_price": suggested_selling_price,
            "calculation_date": as_of_date,
        }

    def calculate_recipe_cost_with_missing_ingredients(
        self, recipe: Recipe, as_of_date=None, fallback_strategy="current_cost"
    ) -> Dict:
        """
        Calculate recipe cost with handling for missing ingredient data
        fallback_strategy: 'current_cost' (use current cost), 'skip' (exclude missing), 'zero' (use zero)
        """

        if as_of_date is None:
            as_of_date = timezone.now()
        elif hasattr(as_of_date, "date") and not hasattr(as_of_date, "hour"):
            # If it's a date object, convert to datetime
            as_of_date = datetime.combine(as_of_date, datetime.min.time())

        ingredients_data = []
        total_cost = Decimal("0")
        missing_ingredients = []
        warnings = []

        for recipe_ingredient in recipe.ingredients.all():
            try:
                # Get current ingredient cost
                current_cost = self.ingredient_service.get_current_product_cost(
                    recipe_ingredient.ingredient, as_of_date
                )

                if current_cost is None or current_cost == 0:
                    if fallback_strategy == "skip":
                        missing_ingredients.append(recipe_ingredient.ingredient.name)
                        continue
                    elif fallback_strategy == "zero":
                        current_cost = Decimal("0")
                        warnings.append(
                            f"No cost data for {recipe_ingredient.ingredient.name}, using zero"
                        )
                    else:  # current_cost fallback
                        # Try to get the most recent cost
                        current_cost = self.ingredient_service.get_current_product_cost(
                            recipe_ingredient.ingredient, None
                        )
                        if current_cost is None or current_cost == 0:
                            current_cost = Decimal("0")
                            warnings.append(
                                f"No cost data for {recipe_ingredient.ingredient.name}, using zero"
                            )
                        else:
                            warnings.append(
                                f"Using current cost for {recipe_ingredient.ingredient.name} (no historical data)"
                            )

                # Calculate cost for this ingredient
                ingredient_total_cost = current_cost * recipe_ingredient.quantity
                ingredient_cost_per_portion = (
                    ingredient_total_cost / recipe.serving_size
                    if recipe.serving_size > 0
                    else Decimal("0")
                )

                ingredient_data = {
                    "ingredient": recipe_ingredient.ingredient,
                    "quantity": recipe_ingredient.quantity,
                    "unit": recipe_ingredient.unit_of_recipe,
                    "cost_per_unit": current_cost,
                    "total_cost": ingredient_total_cost,
                    "cost_per_portion": ingredient_cost_per_portion,
                    "preparation_notes": recipe_ingredient.preparation_notes,
                    "fallback_used": len(warnings) > 0
                    and recipe_ingredient.ingredient.name in warnings[-1],
                }

                ingredients_data.append(ingredient_data)
                total_cost += ingredient_total_cost

            except Exception as e:
                logger.warning(
                    f"Error calculating cost for ingredient {recipe_ingredient.ingredient.name}: {str(e)}"
                )
                missing_ingredients.append(recipe_ingredient.ingredient.name)
                if fallback_strategy != "skip":
                    warnings.append(
                        f"Error with {recipe_ingredient.ingredient.name}: {str(e)}"
                    )

        # Calculate waste cost
        base_cost = total_cost
        waste_cost = base_cost * (recipe.waste_factor_percentage / 100)

        # Add labor cost (apply percentage to batch/base cost only)
        labor_cost = base_cost * (recipe.labour_cost_percentage / 100)

        # Total costs
        total_recipe_cost = base_cost + waste_cost + labor_cost
        if recipe.serving_size > 0:
            cost_per_portion = total_recipe_cost / recipe.serving_size
        else:
            cost_per_portion = Decimal("0")

        return {
            "ingredients": ingredients_data,
            "total_ingredient_cost": total_cost,
            "waste_cost": waste_cost,
            "labor_cost": labor_cost,
            "total_recipe_cost": total_recipe_cost,
            "base_cost_per_portion": (
                base_cost / recipe.serving_size
                if recipe.serving_size > 0
                else Decimal("0")
            ),
            "total_cost_per_portion": cost_per_portion,
            "missing_ingredients": missing_ingredients,
            "warnings": warnings,
            "calculation_date": as_of_date,
        }

    def _calculate_ingredient_costs(self, recipe: Recipe, as_of_date) -> Dict:
        """Calculate costs for all ingredients in recipe"""

        # Ensure as_of_date is a datetime object
        if hasattr(as_of_date, "date") and not hasattr(as_of_date, "hour"):
            # It's a date object, convert to datetime
            as_of_date = datetime.combine(as_of_date, datetime.min.time())

        ingredients_data = []
        total_cost = Decimal("0")

        for recipe_ingredient in recipe.ingredients.all():
            # Get current ingredient cost
            current_cost = self.ingredient_service.get_current_product_cost(
                recipe_ingredient.ingredient, as_of_date
            )

            # Calculate cost for this ingredient
            ingredient_total_cost = current_cost * recipe_ingredient.quantity
            ingredient_cost_per_portion = (
                ingredient_total_cost / recipe.serving_size
                if recipe.serving_size > 0
                else Decimal("0")
            )

            ingredient_data = {
                "ingredient": recipe_ingredient.ingredient,
                "quantity": recipe_ingredient.quantity,
                "unit": recipe_ingredient.unit_of_recipe,
                "cost_per_unit": current_cost,
                "total_cost": ingredient_total_cost,
                "cost_per_portion": ingredient_cost_per_portion,
                "preparation_notes": recipe_ingredient.preparation_notes,
            }

            ingredients_data.append(ingredient_data)
            total_cost += ingredient_total_cost

        return {"ingredients": ingredients_data, "total_ingredient_cost": total_cost}

    def update_recipe_costs(self, recipe: Recipe, save_snapshot: bool = True):
        """Update recipe costs and optionally save snapshot"""

        # Calculate new costs
        cost_data = self.calculate_recipe_cost(recipe)

        # Update recipe fields
        recipe.base_food_cost_per_portion = cost_data["base_cost_per_portion"]
        recipe.total_cost_per_portion = cost_data["total_cost_per_portion"]
        recipe.suggested_selling_price_per_portion = cost_data[
            "suggested_selling_price"
        ]
        recipe.last_costed_date = timezone.now()

        # update individual ingredient costs
        for ingredient_data in cost_data["ingredients"]:
            try:
                recipe_ingredient = RecipeIngredient.objects.get(
                    recipe=recipe, ingredient=ingredient_data["ingredient"]
                )
                recipe_ingredient.cost_per_unit = ingredient_data["cost_per_unit"]
                recipe_ingredient.total_cost = ingredient_data["total_cost"]
                recipe_ingredient.cost_per_portion = ingredient_data["cost_per_portion"]
                recipe_ingredient.save()
            except RecipeIngredient.DoesNotExist:
                logger.warning(
                    f"Recipe ingredient not found for {ingredient_data['ingredient']} in recipe {recipe.dish_name}"
                )

        # Save recipe
        recipe.save()

        # Save snapshot if requested
        if save_snapshot:
            self._save_snapshot(recipe, cost_data)

    def _save_snapshot(self, recipe: Recipe, cost_data: Dict):
        """Save historical cost snapshot"""

        food_cost_pct = None
        if (
            recipe.actual_selling_price_per_portion
            and recipe.actual_selling_price_per_portion > 0
        ):
            food_cost_pct = (
                cost_data["total_cost_per_portion"]
                / recipe.actual_selling_price_per_portion
            ) * 100

        # Create snapshot
        snapshot = RecipeCostSnapshot(
            recipe=recipe,
            snapshot_date=timezone.now(),
            base_food_cost_per_portion=cost_data["base_cost_per_portion"],
            waste_cost_per_portion=(
                cost_data["waste_cost"] / recipe.serving_size
                if recipe.serving_size > 0
                else Decimal("0")
            ),
            labor_cost_per_portion=(
                cost_data["labor_cost"] / recipe.serving_size
                if recipe.serving_size > 0
                else Decimal("0")
            ),
            total_cost_per_portion=cost_data["total_cost_per_portion"],
            suggested_selling_price=cost_data["suggested_selling_price"],
            food_cost_percentage=food_cost_pct,
            calculation_method="weighted_average",
        )

        snapshot.save()

        return snapshot

    def bulk_update_recipe_costs(
        self, recipes: List[Recipe], save_snapshot: bool = True
    ):
        """Bulk update recipe costs and optionally save snapshots"""

        active_recipes = Recipe.objects.filter(is_active=True)

        updated_count = 0
        error_count = 0

        for recipe in active_recipes:
            try:
                self.update_recipe_costs(recipe, save_snapshot)
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating recipe costs for {recipe.dish_name}: {e}")
                error_count += 1

        logger.info(
            f"Bulk update complete: {updated_count} recipes updated, {error_count} errors"
        )

        return {"updated": updated_count, "errors": error_count}

    def get_recipes_by_cost_efficiency(self, limit: int = 10) -> List[Recipe]:
        """Get recipes sorted by cost efficiency (profit margin)"""

        efficient_recipes = []

        for recipe in Recipe.objects.filter(
            is_active=True,
            actual_selling_price_per_portion__gt=0,
            total_cost_per_portion__gt=0,
        ):
            profit_margin = (
                (
                    recipe.actual_selling_price_per_portion
                    - recipe.total_cost_per_portion
                )
                / recipe.actual_selling_price_per_portion
            ) * 100

            efficient_recipes.append(
                {
                    "recipe": recipe,
                    "profit_margin": profit_margin,
                    "profit_per_portion": recipe.actual_selling_price_per_portion
                    - recipe.total_cost_per_portion,
                }
            )

        return sorted(
            efficient_recipes, key=lambda x: x["profit_margin"], reverse=True
        )[:limit]

    def calculate_dual_recipe_cost(self, recipe: Recipe, target_date=None) -> Dict:
        """
        Enhanced version of calculate_recipe_cost
        Returns both conservative and estimated costs with confidence metrics
        """

        if target_date is None:
            target_date = timezone.now()
        elif hasattr(target_date, "date") and not hasattr(target_date, "hour"):
            # If it's a date object, convert to datetime
            target_date = datetime.combine(target_date, datetime.min.time())

        # Use existing method for estimated cost (with fallbacks)
        estimated_result = self.calculate_recipe_cost_with_missing_ingredients(
            recipe, target_date, fallback_strategy="current_cost"
        )

        # New: Calculate conservative cost (actual data only)
        conservative_result = self.calculate_recipe_cost_with_missing_ingredients(
            recipe, target_date, fallback_strategy="skip"
        )

        # Calculate confidence metrics
        total_ingredients = recipe.ingredients.count()
        missing_count = len(estimated_result.get("missing_ingredients", []))
        estimated_count = len(
            [
                ing
                for ing in estimated_result.get("ingredients", [])
                if ing.get("fallback_used", False)
            ]
        )
        actual_count = total_ingredients - missing_count

        # Confidence calculation
        if total_ingredients > 0:
            completeness_pct = (actual_count / total_ingredients) * 100
            if completeness_pct >= 90:
                confidence = "HIGH"
            elif completeness_pct >= 70:
                confidence = "MEDIUM"
            elif completeness_pct >= 50:
                confidence = "LOW"
            else:
                confidence = "VERY_LOW"
        else:
            confidence = "VERY_LOW"
            completeness_pct = 0

        return {
            "conservative": {
                "total_cost_per_portion": conservative_result["total_cost_per_portion"],
                "total_ingredient_cost": conservative_result["total_ingredient_cost"],
                "ingredients": conservative_result.get("ingredients", []),
            },
            "estimated": {
                "total_cost_per_portion": estimated_result["total_cost_per_portion"],
                "total_ingredient_cost": estimated_result["total_ingredient_cost"],
                "ingredients": estimated_result.get("ingredients", []),
            },
            "confidence_data": {
                "confidence_level": confidence,
                "data_completeness_percentage": completeness_pct,
                "missing_ingredients_count": missing_count,
                "estimated_ingredients_count": estimated_count,
                "warnings": estimated_result.get("warnings", []),
            },
        }
