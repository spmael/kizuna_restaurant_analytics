import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from django.core.cache import cache
from django.db.models import Avg
from django.utils import timezone

from apps.analytics.models import ProductCostHistory
from apps.restaurant_data.models import Product

logger = logging.getLogger(__name__)


class ProductCostingService:
    """Service for calculating product costs using ProductCostHistory with multiple calculation methods"""

    def __init__(self):
        self.cost_cache = {}  # cache for performance
        self.default_lookback_days = 90  # 3 months
        self.min_purchase_count = 2  # Minimum purchases to calculate weighted average
        self.cache_timeout = 3600  # 1 hour for Django cache

    def get_current_product_cost(self, product: Product, as_of_date=None) -> Decimal:
        """Get current weighted average cost for a product (your existing method)"""

        if as_of_date is None:
            as_of_date = timezone.now()
        elif isinstance(as_of_date, date) and not isinstance(as_of_date, datetime):
            # If it's a date object, convert to timezone-aware datetime
            as_of_date = timezone.make_aware(
                datetime.combine(as_of_date, datetime.min.time())
            )
        elif isinstance(as_of_date, str):
            # If it's a string, try to parse it
            try:
                as_of_date = datetime.fromisoformat(as_of_date.replace("Z", "+00:00"))
                if timezone.is_naive(as_of_date):
                    as_of_date = timezone.make_aware(as_of_date)
            except ValueError:
                as_of_date = timezone.now()

        # Check cache first
        cache_key = self._get_product_cache_key(product, as_of_date, "current")
        if cache_key in self.cost_cache:
            return self.cost_cache[cache_key]

        # Calculate weighted average cost using your existing logic
        cost = self._calculate_weighted_average_cost(product, as_of_date)

        # Cache the result
        self.cost_cache[cache_key] = cost

        return cost

    def get_fifo_cost(self, product: Product, as_of_date=None) -> Decimal:
        """Calculate FIFO (First In, First Out) cost"""

        if as_of_date is None:
            as_of_date = timezone.now()

        # Ensure as_of_date is timezone-aware
        if timezone.is_naive(as_of_date):
            as_of_date = timezone.make_aware(as_of_date)

        cache_key = self._get_product_cache_key(product, as_of_date, "fifo")
        cached_cost = cache.get(cache_key)

        if cached_cost is not None:
            return cached_cost

        # Get the oldest cost history record before or on the given date
        cost_history = (
            ProductCostHistory.objects.filter(
                product=product, purchase_date__lte=as_of_date, is_active=True
            )
            .order_by("purchase_date")
            .first()
        )

        if cost_history:
            cost = cost_history.unit_cost_in_recipe_units
        else:
            cost = self._get_fallback_cost(product)

        # Cache the result
        cache.set(cache_key, cost, self.cache_timeout)

        return cost

    def get_lifo_cost(self, product: Product, as_of_date=None) -> Decimal:
        """Calculate LIFO (Last In, First Out) cost"""

        if as_of_date is None:
            as_of_date = timezone.now()

        # Ensure as_of_date is timezone-aware
        if timezone.is_naive(as_of_date):
            as_of_date = timezone.make_aware(as_of_date)

        cache_key = self._get_product_cache_key(product, as_of_date, "lifo")
        cached_cost = cache.get(cache_key)

        if cached_cost is not None:
            return cached_cost

        # Get the most recent cost history record before or on the given date
        cost_history = (
            ProductCostHistory.objects.filter(
                product=product, purchase_date__lte=as_of_date, is_active=True
            )
            .order_by("-purchase_date")
            .first()
        )

        if cost_history:
            cost = cost_history.unit_cost_in_recipe_units
        else:
            cost = self._get_fallback_cost(product)

        # Cache the result
        cache.set(cache_key, cost, self.cache_timeout)

        return cost

    def get_moving_average_cost(
        self, product: Product, as_of_date=None, periods=3
    ) -> Decimal:
        """Calculate moving average cost over specified number of periods"""

        if as_of_date is None:
            as_of_date = timezone.now()

        # Ensure as_of_date is timezone-aware
        if timezone.is_naive(as_of_date):
            as_of_date = timezone.make_aware(as_of_date)

        cache_key = self._get_product_cache_key(product, as_of_date, f"ma_{periods}")
        cached_cost = cache.get(cache_key)

        if cached_cost is not None:
            return cached_cost

        # Get the most recent cost history records
        cost_records = ProductCostHistory.objects.filter(
            product=product, purchase_date__lte=as_of_date, is_active=True
        ).order_by("-purchase_date")[:periods]

        if not cost_records.exists():
            return self.get_current_product_cost(product, as_of_date)

        # Calculate simple moving average
        total_cost = sum(record.unit_cost_in_recipe_units for record in cost_records)
        cost = total_cost / len(cost_records)

        # Cache the result
        cache.set(cache_key, cost, self.cache_timeout)

        return cost

    def get_standard_cost(self, product: Product, as_of_date=None) -> Decimal:
        """Get standard cost (target cost) for a product"""

        if as_of_date is None:
            as_of_date = timezone.now()

        # Ensure as_of_date is timezone-aware
        if timezone.is_naive(as_of_date):
            as_of_date = timezone.make_aware(as_of_date)

        cache_key = self._get_product_cache_key(product, as_of_date, "standard")
        cached_cost = cache.get(cache_key)

        if cached_cost is not None:
            return cached_cost

        # Calculate standard cost as average of last 6 months
        start_date = as_of_date - timedelta(days=180)

        cost_records = ProductCostHistory.objects.filter(
            product=product,
            purchase_date__gte=start_date,
            purchase_date__lte=as_of_date,
            is_active=True,
        )

        if cost_records.exists():
            avg_cost = cost_records.aggregate(
                avg_cost=Avg("unit_cost_in_recipe_units")
            )["avg_cost"]
            cost = avg_cost or Decimal("0.00")
        else:
            cost = self._get_fallback_cost(product)

        # Cache the result
        cache.set(cache_key, cost, self.cache_timeout)

        return cost

    def get_cost_with_markup(
        self, product: Product, markup_percentage=30, as_of_date=None
    ) -> Decimal:
        """Calculate cost with markup percentage"""

        base_cost = self.get_current_product_cost(product, as_of_date)
        markup = base_cost * (markup_percentage / 100)
        return base_cost + markup

    def get_cost_comparison(
        self, product: Product, as_of_date=None
    ) -> Dict[str, Decimal]:
        """Get cost comparison using different calculation methods"""

        if as_of_date is None:
            as_of_date = timezone.now()

        return {
            "current_weighted": self.get_current_product_cost(product, as_of_date),
            "fifo": self.get_fifo_cost(product, as_of_date),
            "lifo": self.get_lifo_cost(product, as_of_date),
            "moving_average_3": self.get_moving_average_cost(product, as_of_date, 3),
            "moving_average_6": self.get_moving_average_cost(product, as_of_date, 6),
            "standard": self.get_standard_cost(product, as_of_date),
            "with_30p_markup": self.get_cost_with_markup(product, 30, as_of_date),
        }

    # Your existing weighting methods (keeping them exactly as they were)
    def _calculate_weighted_average_cost(self, product: Product, as_of_date) -> Decimal:
        """Calculate weighted average cost based on recent purchases"""

        # Ensure as_of_date is a timezone-aware datetime object
        if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime):
            # It's a date object, convert to timezone-aware datetime
            as_of_date = timezone.make_aware(
                datetime.combine(as_of_date, datetime.min.time())
            )
        elif timezone.is_naive(as_of_date):
            # It's a naive datetime, make it timezone-aware
            as_of_date = timezone.make_aware(as_of_date)

        # Get recent cost history
        lookback_date = as_of_date - timedelta(days=self.default_lookback_days)

        cost_history = ProductCostHistory.objects.filter(
            product=product,
            purchase_date__gte=lookback_date,
            purchase_date__lte=as_of_date,
            is_active=True,
        ).order_by("-purchase_date")

        purchase_count = cost_history.count()

        if purchase_count == 0:
            # No recent purchases, use current product cost or last known cost
            return self._get_fallback_cost(product)

        if purchase_count == 1:
            # Only one purchase, use it directly
            return cost_history.first().unit_cost_in_recipe_units

        # Multiple purchases: use dynamic weighting strategy
        return self._calculate_dynamic_weighted_average(
            cost_history, as_of_date, purchase_count
        )

    def _calculate_dynamic_weighted_average(
        self, cost_history, as_of_date, purchase_count: int
    ) -> Decimal:
        """Calculate weighted average with dynamic weighting based on purchase count"""

        # Ensure as_of_date is a timezone-aware datetime object
        if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime):
            # It's a date object, convert to timezone-aware datetime
            as_of_date = timezone.make_aware(
                datetime.combine(as_of_date, datetime.min.time())
            )
        elif timezone.is_naive(as_of_date):
            # It's a naive datetime, make it timezone-aware
            as_of_date = timezone.make_aware(as_of_date)

        # Dynamic weighting strategy based on purchase count
        if purchase_count <= 3:
            # Few purchases: use simple recency weighting (linear decay)
            return self._apply_linear_weighting(cost_history, as_of_date)
        elif purchase_count <= 8:
            # Moderate purchases: use exponential decay with adaptive half-life
            return self._apply_adaptive_exponential_weighting(
                cost_history, as_of_date, purchase_count
            )
        else:
            # Many purchases: use sophisticated time-based weighting
            return self._apply_sophisticated_weighting(
                cost_history, as_of_date, purchase_count
            )

    def _apply_linear_weighting(self, cost_history, as_of_date) -> Decimal:
        """Simple linear decay weighting for few purchases"""
        # Ensure as_of_date is a timezone-aware datetime object
        if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime):
            # It's a date object, convert to timezone-aware datetime
            as_of_date = timezone.make_aware(
                datetime.combine(as_of_date, datetime.min.time())
            )
        elif timezone.is_naive(as_of_date):
            # It's a naive datetime, make it timezone-aware
            as_of_date = timezone.make_aware(as_of_date)

        total_weighted_cost = Decimal("0")
        total_weight = Decimal("0")

        max_days = max(
            (as_of_date - record.purchase_date).days for record in cost_history
        )

        for cost_record in cost_history:
            days_ago = (as_of_date - cost_record.purchase_date).days
            # Linear weight: newer purchases get higher weight
            weight = Decimal(max_days - days_ago + 1) / Decimal(max_days + 1)

            weighted_cost = cost_record.unit_cost_in_recipe_units * weight
            total_weighted_cost += weighted_cost
            total_weight += weight

        if total_weight > 0:
            return total_weighted_cost / total_weight
        else:
            return sum(
                record.unit_cost_in_recipe_units for record in cost_history
            ) / len(cost_history)

    def _apply_adaptive_exponential_weighting(
        self, cost_history, as_of_date, purchase_count: int
    ) -> Decimal:
        """Adaptive exponential decay weighting for moderate purchases"""
        # Ensure as_of_date is a timezone-aware datetime object
        if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime):
            # It's a date object, convert to timezone-aware datetime
            as_of_date = timezone.make_aware(
                datetime.combine(as_of_date, datetime.min.time())
            )
        elif timezone.is_naive(as_of_date):
            # It's a naive datetime, make it timezone-aware
            as_of_date = timezone.make_aware(as_of_date)

        total_weighted_cost = Decimal("0")
        total_weight = Decimal("0")

        # Calculate adaptive half-life based on purchase frequency
        date_range = (as_of_date - cost_history.last().purchase_date).days
        avg_days_between_purchases = date_range / (purchase_count - 1)

        # Half-life should be proportional to purchase frequency
        # More frequent purchases = shorter half-life (more emphasis on recency)
        # Less frequent purchases = longer half-life (more balanced weighting)
        if avg_days_between_purchases <= 7:
            half_life_days = Decimal("7")  # Weekly purchases
        elif avg_days_between_purchases <= 15:
            half_life_days = Decimal("15")  # Bi-weekly purchases
        elif avg_days_between_purchases <= 30:
            half_life_days = Decimal("25")  # Monthly purchases
        else:
            half_life_days = Decimal("35")  # Less frequent purchases

        for cost_record in cost_history[:10]:  # Limit to 10 most recent
            days_ago = (as_of_date - cost_record.purchase_date).days

            # Exponential decay formula: weight = 2^(-t/half_life)
            weight = Decimal(2) ** (Decimal(-days_ago) / half_life_days)

            weighted_cost = cost_record.unit_cost_in_recipe_units * weight
            total_weighted_cost += weighted_cost
            total_weight += weight

        if total_weight > 0:
            return total_weighted_cost / total_weight
        else:
            return sum(
                record.unit_cost_in_recipe_units for record in cost_history
            ) / len(cost_history)

    def _apply_sophisticated_weighting(
        self, cost_history, as_of_date, purchase_count: int
    ) -> Decimal:
        """Sophisticated time-based weighting for many purchases"""
        # Ensure as_of_date is a timezone-aware datetime object
        if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime):
            # It's a date object, convert to timezone-aware datetime
            as_of_date = timezone.make_aware(
                datetime.combine(as_of_date, datetime.min.time())
            )
        elif timezone.is_naive(as_of_date):
            # It's a naive datetime, make it timezone-aware
            as_of_date = timezone.make_aware(as_of_date)

        total_weighted_cost = Decimal("0")
        total_weight = Decimal("0")

        # Use more recent purchases with higher weight
        recent_purchases = cost_history[:15]  # Last 15 purchases

        # Calculate time-based weights with volume consideration
        for i, cost_record in enumerate(recent_purchases):
            days_ago = (as_of_date - cost_record.purchase_date).days

            # Base weight: exponential decay
            base_weight = Decimal(2) ** (Decimal(-days_ago) / Decimal("20"))

            # Recency bonus: more recent purchases get additional weight
            recency_bonus = Decimal(1.5) ** (Decimal(-i))  # i=0 for most recent

            # Volume consideration (if available)
            volume_factor = Decimal("1.0")
            if cost_record.recipe_quantity:
                # Higher volume purchases get slightly more weight
                volume_factor = min(
                    Decimal("1.2"),
                    Decimal("1.0") + (cost_record.recipe_quantity / Decimal("100")),
                )

            # Combined weight
            weight = base_weight * recency_bonus * volume_factor

            weighted_cost = cost_record.unit_cost_in_recipe_units * weight
            total_weighted_cost += weighted_cost
            total_weight += weight

        if total_weight > 0:
            return total_weighted_cost / total_weight
        else:
            return sum(
                record.unit_cost_in_recipe_units for record in cost_history
            ) / len(cost_history)

    def _get_fallback_cost(self, product: Product) -> Decimal:
        """Get fallback cost when no recent purchase history is available"""

        # 1. Try last known cost from history (prioritize ProductCostHistory)
        last_cost = (
            ProductCostHistory.objects.filter(product=product, is_active=True)
            .order_by("-purchase_date")
            .first()
        )

        if last_cost:
            return last_cost.unit_cost_in_recipe_units

        # 2. Only use current product cost as last resort (but log warning)
        if product.current_cost_per_unit and product.current_cost_per_unit > 0:
            logger.warning(
                f"Using Product.current_cost_per_unit for {product.name} (no ProductCostHistory available)"
            )
            return product.current_cost_per_unit

        # 3. Default to zero (log warning)
        logger.warning(f"No cost information available for product {product.name}")
        return Decimal("0")

    def get_cost_trend(self, product: Product, days: int = 30) -> List[Dict]:
        """Get cost trend data for a product over time"""

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        cost_history = ProductCostHistory.objects.filter(
            product=product,
            purchase_date__gte=start_date,
            purchase_date__lte=end_date,
            is_active=True,
        ).order_by("purchase_date")

        trend_data = []

        for record in cost_history:
            trend_data.append(
                {
                    "date": record.purchase_date.date(),
                    "cost": float(record.unit_cost_in_recipe_units),
                    "quantity": float(record.recipe_quantity),
                }
            )

        return trend_data

    def get_detailed_cost_trend(self, product: Product, days_back=90) -> Dict[str, any]:
        """Get detailed cost trend analysis for a product"""

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_back)

        cost_records = ProductCostHistory.objects.filter(
            product=product,
            purchase_date__gte=start_date,
            purchase_date__lte=end_date,
            is_active=True,
        ).order_by("purchase_date")

        if not cost_records.exists():
            return {
                "trend": "stable",
                "change_percentage": 0,
                "min_cost": 0,
                "max_cost": 0,
                "avg_cost": 0,
                "volatility": 0,
                "purchase_count": 0,
                "total_quantity": 0,
            }

        costs = [record.unit_cost_in_recipe_units for record in cost_records]
        quantities = [record.recipe_quantity for record in cost_records]

        min_cost = min(costs)
        max_cost = max(costs)
        avg_cost = sum(costs) / len(costs)
        total_quantity = sum(quantities)

        # Calculate volatility (standard deviation)
        variance = sum((cost - avg_cost) ** 2 for cost in costs) / len(costs)
        volatility = variance.sqrt()

        # Calculate trend
        if len(costs) >= 2:
            first_cost = costs[0]
            last_cost = costs[-1]
            change_percentage = (
                ((last_cost - first_cost) / first_cost * 100) if first_cost > 0 else 0
            )

            if change_percentage > 5:
                trend = "increasing"
            elif change_percentage < -5:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
            change_percentage = 0

        return {
            "trend": trend,
            "change_percentage": change_percentage,
            "min_cost": min_cost,
            "max_cost": max_cost,
            "avg_cost": avg_cost,
            "volatility": volatility,
            "purchase_count": len(cost_records),
            "total_quantity": total_quantity,
        }

    def get_cost_analysis_report(
        self, product: Product, as_of_date=None
    ) -> Dict[str, any]:
        """Generate comprehensive cost analysis report"""

        if as_of_date is None:
            as_of_date = timezone.now()

        # Get all cost methods
        cost_comparison = self.get_cost_comparison(product, as_of_date)

        # Get trend analysis
        trend_analysis = self.get_detailed_cost_trend(product, days_back=90)

        # Get recent purchases
        recent_purchases = ProductCostHistory.objects.filter(
            product=product, purchase_date__lte=as_of_date, is_active=True
        ).order_by("-purchase_date")[:10]

        recent_purchases_data = []
        for purchase in recent_purchases:
            recent_purchases_data.append(
                {
                    "date": purchase.purchase_date,
                    "quantity": purchase.recipe_quantity,
                    "unit_cost": purchase.unit_cost_in_recipe_units,
                    "total_cost": purchase.total_amount,
                    "unit_of_measure": purchase.unit_of_recipe.name,
                }
            )

        return {
            "product_name": product.name,
            "analysis_date": as_of_date,
            "cost_comparison": cost_comparison,
            "trend_analysis": trend_analysis,
            "recent_purchases": recent_purchases_data,
            "recommended_cost_method": self._get_recommended_cost_method(
                trend_analysis, cost_comparison
            ),
        }

    def _get_recommended_cost_method(
        self, trend_analysis: Dict, cost_comparison: Dict
    ) -> str:
        """Determine recommended cost calculation method based on analysis"""

        volatility = trend_analysis.get("volatility", 0)
        change_percentage = trend_analysis.get("change_percentage", 0)

        if volatility > 10:  # High volatility
            return "current_weighted"  # Your sophisticated weighting handles volatility well
        elif abs(change_percentage) > 20:  # Significant cost changes
            return "moving_average_6"
        elif volatility < 5:  # Low volatility
            return "current_weighted"
        else:
            return "current_weighted"

    def bulk_update_product_cost_history(self, start_date: datetime = None):
        """Bulk update product cost history from ConsolidatedPurchases data"""

        if start_date is None:
            start_date = timezone.now() - timedelta(days=self.default_lookback_days)

        # Import here to avoid circular imports
        from apps.restaurant_data.models import ConsolidatedPurchases

        consolidated_purchases = ConsolidatedPurchases.objects.filter(
            purchase_date__gte=start_date
        ).select_related("product", "unit_of_measure")

        created_count = 0
        updated_count = 0

        for item in consolidated_purchases:
            # Get or create ProductType for this product
            product_type = self._get_or_create_product_type(item.product)

            # Use the product's current unit of measure for recipe units
            recipe_unit = item.product.unit_of_measure

            # Calculate conversion factor if units are different
            conversion_factor = Decimal("1.0")
            if item.unit_of_measure != recipe_unit:
                # Try to get conversion factor from unit conversion system
                try:
                    from data_engineering.utils.unit_conversion import (
                        UnitConversionService,
                    )

                    conversion_service = UnitConversionService()
                    conversion_factor = conversion_service.get_conversion_factor(
                        from_unit=item.unit_of_measure, to_unit=recipe_unit
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not get conversion factor for {item.product.name}: {e}"
                    )
                    conversion_factor = Decimal("1.0")

            # Calculate recipe quantity and unit cost with conversion
            recipe_quantity = item.quantity_ordered * conversion_factor
            unit_cost_in_recipe_units = (
                item.total_amount / recipe_quantity
                if recipe_quantity > 0
                else Decimal("0")
            )

            history, created = ProductCostHistory.objects.get_or_create(
                product=item.product,
                purchase_date=item.purchase_date,
                defaults={
                    "quantity_ordered": item.quantity_ordered,
                    "unit_of_purchase": item.unit_of_measure,
                    "total_amount": item.total_amount,
                    "unit_of_recipe": recipe_unit,  # Use product's current unit
                    "recipe_conversion_factor": conversion_factor,
                    "recipe_quantity": recipe_quantity,
                    "unit_cost_in_recipe_units": unit_cost_in_recipe_units,
                    "product_category": product_type,
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
            else:
                # Update existing record
                history.quantity_ordered = item.quantity_ordered
                history.unit_of_purchase = item.unit_of_measure
                history.total_amount = item.total_amount
                history.unit_of_recipe = recipe_unit  # Use product's current unit
                history.recipe_conversion_factor = conversion_factor
                history.recipe_quantity = recipe_quantity
                history.unit_cost_in_recipe_units = unit_cost_in_recipe_units
                history.product_category = product_type
                history.save()
                updated_count += 1

        # Clear entire cache
        self.cost_cache.clear()

        logger.info(
            f"Bulk cost history update completed: "
            f"{created_count} created, {updated_count} updated"
        )

        return {"created": created_count, "updated": updated_count}

    def _get_or_create_product_type(self, product: Product):
        """Get or create ProductType for a product"""
        from apps.restaurant_data.models import ProductType

        # Try to get existing product type
        product_type = ProductType.objects.filter(product=product).first()

        if not product_type:
            # Create default product type
            product_type = ProductType.objects.create(
                product=product,
                cost_type="raw_material_costs",
                product_type=(
                    "resale"
                    if product.sales_category.name.lower() in ["beverages", "drinks"]
                    else "dish"
                ),
            )

        return product_type

    def _clear_product_cache(self, product: Product):
        """Clear the cache for a product over time"""
        keys_to_delete = []
        for key in self.cost_cache.keys():
            if key.startswith(f"{product.id}_"):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self.cost_cache[key]

    def _get_product_cache_key(self, product: Product, as_of_date, method_suffix=""):
        """Get cache key for product cost"""
        # Ensure as_of_date is a timezone-aware datetime object for consistent handling
        if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime):
            # It's a date object, convert to timezone-aware datetime
            as_of_date = timezone.make_aware(
                datetime.combine(as_of_date, datetime.min.time())
            )
        elif timezone.is_naive(as_of_date):
            # It's a naive datetime, make it timezone-aware
            as_of_date = timezone.make_aware(as_of_date)

        # Now we can safely call .date() since as_of_date is guaranteed to be a timezone-aware datetime
        return f"{product.id}_{as_of_date.date()}_{method_suffix}"

    def clear_cache(self, product: Product = None):
        """Clear cost cache for a product or all products"""
        if product:
            # Clear cache for specific product
            self._clear_product_cache(product)
            # Also clear Django cache
            pattern = f"product_cost_{product.id}_*"
            cache.delete_pattern(pattern)
        else:
            # Clear all cost-related cache
            self.cost_cache.clear()
            cache.clear()
