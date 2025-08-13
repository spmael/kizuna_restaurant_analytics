from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from apps.analytics.services.services import DailyAnalyticsService


class Command(BaseCommand):
    help = _("Update recipe costs using recipe costing service")

    def add_arguments(self, parser):
        parser.add_argument(
            "--save-snapshots",
            action="store_true",
            help=_("Save cost snapshots for historical tracking"),
        )
        parser.add_argument(
            "--date",
            type=str,
            help=_("Specific date to calculate costs for (YYYY-MM-DD format)"),
        )
        parser.add_argument(
            "--update-ingredients",
            action="store_true",
            help=_("Also update ingredient cost history"),
        )

    def handle(self, *args, **options):
        service = DailyAnalyticsService()

        # Determine target date
        if options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError(_("Invalid date format. Use YYYY-MM-DD"))
        else:
            target_date = date.today()

        self.stdout.write(
            self.style.SUCCESS(f"Updating recipe costs for {target_date}")
        )

        try:
            # Update recipe costs
            result = service.update_recipe_costs(
                save_snapshots=options["save_snapshots"]
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Recipe costs updated: {result["updated"]} recipes updated, {result["errors"]} errors'
                )
            )

            # Update ingredient cost history if requested
            if options["update_ingredients"]:
                self.stdout.write("Updating ingredient cost history...")
                ingredient_result = (
                    service.ingredient_costing_service.bulk_update_ingredient_cost_history()
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Ingredient cost history updated: {ingredient_result["created"]} created, {ingredient_result["updated"]} updated'
                    )
                )

            # Show some cost analysis
            self.stdout.write("\nCost Analysis Summary:")
            cost_analysis = service.get_recipe_cost_analysis(target_date)

            self.stdout.write(
                f'Total recipes analyzed: {cost_analysis["total_recipes"]}'
            )
            self.stdout.write(
                f'Total recipe cost: {cost_analysis["total_recipe_cost"]:,.0f} FCFA'
            )

            # Show top 5 most expensive recipes
            if cost_analysis["recipe_costs"]:
                self.stdout.write("\nTop 5 Most Expensive Recipes:")
                sorted_recipes = sorted(
                    cost_analysis["recipe_costs"],
                    key=lambda x: x["cost_data"]["total_cost_per_portion"],
                    reverse=True,
                )[:5]

                for i, recipe_data in enumerate(sorted_recipes, 1):
                    recipe = recipe_data["recipe"]
                    cost_data = recipe_data["cost_data"]
                    self.stdout.write(
                        f'{i}. {recipe.dish_name}: {cost_data["total_cost_per_portion"]:,.0f} FCFA per portion'
                    )

        except Exception as e:
            raise CommandError(f"Recipe cost update failed: {str(e)}")
