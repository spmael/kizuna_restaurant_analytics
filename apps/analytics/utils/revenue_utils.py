import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from django.db.models import Sum

from apps.analytics.models import DailySummary
from apps.restaurant_data.models import Sales

logger = logging.getLogger(__name__)


class RevenueChartUtils:
    """
    Utility class for preparing revenue data for charts and visualizations.
    Provides formatted data for:
    - Daily Revenue Chart
    - Category Pie Chart
    - Time-based Bar Chart
    - Payment Method Breakdown
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def prepare_daily_revenue_chart_data(
        self, start_date: date, end_date: date
    ) -> Dict:
        """
        Prepare data for daily revenue trend chart.
        Returns data formatted for Chart.js line chart.
        """
        try:
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            # Prepare chart data with complete date range (including zero sales days)
            labels = []
            revenue_data = []
            orders_data = []
            customers_data = []

            current_date = start_date
            while current_date <= end_date:
                labels.append(current_date.strftime("%d/%m"))

                # Find sales data for this date
                summary = next((s for s in summaries if s.date == current_date), None)
                if summary:
                    revenue_data.append(float(summary.total_sales or 0))
                    orders_data.append(summary.total_orders or 0)
                    customers_data.append(summary.total_customers or 0)
                else:
                    revenue_data.append(0.0)
                    orders_data.append(0)
                    customers_data.append(0)

                current_date += timedelta(days=1)

            # Calculate trend indicators
            trend_analysis = self._calculate_trend_indicators(revenue_data)

            return {
                "type": "line",
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Daily Revenue (FCFA)",
                            "data": revenue_data,
                            "borderColor": "rgb(75, 192, 192)",
                            "backgroundColor": "rgba(75, 192, 192, 0.2)",
                            "tension": 0.1,
                            "yAxisID": "y",
                        },
                        {
                            "label": "Orders",
                            "data": orders_data,
                            "borderColor": "rgb(255, 99, 132)",
                            "backgroundColor": "rgba(255, 99, 132, 0.2)",
                            "tension": 0.1,
                            "yAxisID": "y1",
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "interaction": {
                        "mode": "index",
                        "intersect": False,
                    },
                    "scales": {
                        "x": {
                            "display": True,
                            "title": {"display": True, "text": "Date"},
                        },
                        "y": {
                            "type": "linear",
                            "display": True,
                            "position": "left",
                            "title": {"display": True, "text": "Revenue (FCFA)"},
                        },
                        "y1": {
                            "type": "linear",
                            "display": True,
                            "position": "right",
                            "title": {"display": True, "text": "Orders"},
                            "grid": {
                                "drawOnChartArea": False,
                            },
                        },
                    },
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"Daily Revenue Trends ({start_date} to {end_date})",
                        },
                        "legend": {"display": True},
                    },
                },
                "trend_analysis": trend_analysis,
                "summary_stats": {
                    "total_revenue": sum(revenue_data),
                    "avg_daily_revenue": (
                        sum(revenue_data) / len(revenue_data) if revenue_data else 0
                    ),
                    "best_day": max(revenue_data) if revenue_data else 0,
                    "worst_day": min(revenue_data) if revenue_data else 0,
                },
            }

        except Exception as e:
            logger.error(f"Error preparing daily revenue chart data: {e}")
            return {"error": str(e)}

    def prepare_category_pie_chart_data(
        self, start_date: date, end_date: date, limit: int = 8
    ) -> Dict:
        """
        Prepare data for category revenue pie chart.
        Returns data formatted for Chart.js pie chart.
        """
        try:
            category_sales = (
                Sales.objects.filter(sale_date__range=[start_date, end_date])
                .values("product__sales_category__name")
                .annotate(
                    total_revenue=Sum("total_sale_price"),
                    total_quantity=Sum("quantity_sold"),
                )
                .order_by("-total_revenue")
            )

            if not category_sales:
                return {"error": "No sales data found for the specified period"}

            # Prepare chart data
            labels = []
            data = []
            colors = []
            background_colors = []

            # Color palette for categories
            color_palette = [
                "#FF6384",
                "#36A2EB",
                "#FFCE56",
                "#4BC0C0",
                "#9966FF",
                "#FF9F40",
                "#FF6384",
                "#C9CBCF",
            ]

            total_revenue = sum(item["total_revenue"] for item in category_sales)
            # Convert to float for consistent calculations
            total_revenue_float = float(total_revenue)

            for i, item in enumerate(category_sales[:limit]):
                category_name = item["product__sales_category__name"] or "Uncategorized"
                revenue = float(item["total_revenue"])
                percentage = (
                    (revenue / total_revenue_float * 100)
                    if total_revenue_float > 0
                    else 0
                )

                labels.append(f"{category_name} ({percentage:.1f}%)")
                data.append(revenue)
                colors.append(color_palette[i % len(color_palette)])
                background_colors.append(color_palette[i % len(color_palette)])

            # Group remaining categories as "Others"
            if len(category_sales) > limit:
                others_revenue = sum(
                    item["total_revenue"] for item in category_sales[limit:]
                )
                if others_revenue > 0:
                    others_revenue_float = float(others_revenue)
                    others_percentage = (
                        (others_revenue_float / total_revenue_float * 100)
                        if total_revenue_float > 0
                        else 0
                    )
                    labels.append(f"Others ({others_percentage:.1f}%)")
                    data.append(float(others_revenue))
                    colors.append("#E0E0E0")
                    background_colors.append("#E0E0E0")

            return {
                "type": "pie",
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "data": data,
                            "backgroundColor": background_colors,
                            "borderColor": colors,
                            "borderWidth": 2,
                        }
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"Revenue by Category ({start_date} to {end_date})",
                        },
                        "legend": {"display": True, "position": "right"},
                        "tooltip": {
                            "callbacks": {
                                "label": "function(context) { return context.label + ': ' + context.parsed.toLocaleString() + ' FCFA'; }"
                            }
                        },
                    },
                },
                "summary": {
                    "total_revenue": total_revenue,
                    "category_count": len(category_sales),
                    "top_category": (
                        category_sales[0]["product__sales_category__name"]
                        if category_sales
                        else None
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error preparing category pie chart data: {e}")
            return {"error": str(e)}

    def prepare_time_based_bar_chart_data(
        self, start_date: date, end_date: date
    ) -> Dict:
        """
        Prepare data for time-based revenue analysis (daily patterns).
        Returns data formatted for Chart.js bar chart.
        """
        try:
            summaries = DailySummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by("date")

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Group by day of week
            daily_averages = {}
            daily_counts = {}

            for summary in summaries:
                day_name = summary.date.strftime("%A")
                if day_name not in daily_averages:
                    daily_averages[day_name] = []
                    daily_counts[day_name] = 0
                daily_averages[day_name].append(float(summary.total_sales))
                daily_counts[day_name] += 1

            # Calculate averages
            for day in daily_averages:
                daily_averages[day] = sum(daily_averages[day]) / len(
                    daily_averages[day]
                )

            # Order days properly
            day_order = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            ordered_labels = [day for day in day_order if day in daily_averages]
            ordered_data = [daily_averages[day] for day in ordered_labels]

            # Find best and worst days
            best_day = (
                max(daily_averages.items(), key=lambda x: x[1])
                if daily_averages
                else None
            )
            worst_day = (
                min(daily_averages.items(), key=lambda x: x[1])
                if daily_averages
                else None
            )

            return {
                "type": "bar",
                "data": {
                    "labels": ordered_labels,
                    "datasets": [
                        {
                            "label": "Average Daily Revenue (FCFA)",
                            "data": ordered_data,
                            "backgroundColor": [
                                (
                                    "rgba(75, 192, 192, 0.8)"
                                    if day == best_day[0]
                                    else (
                                        "rgba(255, 99, 132, 0.8)"
                                        if day == worst_day[0]
                                        else "rgba(54, 162, 235, 0.8)"
                                    )
                                )
                                for day in ordered_labels
                            ],
                            "borderColor": [
                                (
                                    "rgb(75, 192, 192)"
                                    if day == best_day[0]
                                    else (
                                        "rgb(255, 99, 132)"
                                        if day == worst_day[0]
                                        else "rgb(54, 162, 235)"
                                    )
                                )
                                for day in ordered_labels
                            ],
                            "borderWidth": 2,
                        }
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"Average Revenue by Day of Week ({start_date} to {end_date})",
                        },
                        "legend": {"display": True},
                        "tooltip": {
                            "callbacks": {
                                "label": "function(context) { return context.parsed.y.toLocaleString() + ' FCFA'; }"
                            }
                        },
                    },
                    "scales": {
                        "y": {
                            "beginAtZero": True,
                            "title": {
                                "display": True,
                                "text": "Average Revenue (FCFA)",
                            },
                        }
                    },
                },
                "insights": {
                    "best_day": best_day,
                    "worst_day": worst_day,
                    "day_variance": (
                        max(daily_averages.values()) - min(daily_averages.values())
                        if daily_averages
                        else 0
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error preparing time-based bar chart data: {e}")
            return {"error": str(e)}

    def prepare_payment_method_chart_data(
        self, start_date: date, end_date: date
    ) -> Dict:
        """
        Prepare data for payment method breakdown chart.
        Returns data formatted for Chart.js doughnut chart.
        """
        try:
            summaries = DailySummary.objects.filter(date__range=[start_date, end_date])

            if not summaries.exists():
                return {"error": "No data found for the specified period"}

            # Aggregate payment data
            payment_totals = summaries.aggregate(
                total_cash=Sum("cash_sales"),
                total_mobile_money=Sum("mobile_money_sales"),
                total_card=Sum("credit_card_sales"),
                total_other=Sum("other_payment_methods_sales"),
                total_sales=Sum("total_sales"),
            )

            total_sales = payment_totals["total_sales"] or Decimal("0")

            if total_sales <= 0:
                return {"error": "No sales data available"}

            # Prepare chart data
            labels = ["Cash", "Mobile Money", "Credit Card", "Other"]
            data = [
                float(payment_totals["total_cash"] or 0),
                float(payment_totals["total_mobile_money"] or 0),
                float(payment_totals["total_card"] or 0),
                float(payment_totals["total_other"] or 0),
            ]

            # Calculate percentages
            percentages = [
                (amount / float(total_sales) * 100) if float(total_sales) > 0 else 0
                for amount in data
            ]

            # Add percentages to labels
            labels_with_percentages = [
                f"{label} ({pct:.1f}%)" for label, pct in zip(labels, percentages)
            ]

            colors = ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0"]

            return {
                "type": "doughnut",
                "data": {
                    "labels": labels_with_percentages,
                    "datasets": [
                        {
                            "data": data,
                            "backgroundColor": colors,
                            "borderColor": colors,
                            "borderWidth": 2,
                        }
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"Payment Method Breakdown ({start_date} to {end_date})",
                        },
                        "legend": {"display": True, "position": "right"},
                        "tooltip": {
                            "callbacks": {
                                "label": "function(context) { return context.label + ': ' + context.parsed.toLocaleString() + ' FCFA'; }"
                            }
                        },
                    },
                },
                "summary": {
                    "total_sales": float(total_sales),
                    "payment_breakdown": {
                        "cash": {"amount": data[0], "percentage": percentages[0]},
                        "mobile_money": {
                            "amount": data[1],
                            "percentage": percentages[1],
                        },
                        "card": {"amount": data[2], "percentage": percentages[2]},
                        "other": {"amount": data[3], "percentage": percentages[3]},
                    },
                },
            }

        except Exception as e:
            logger.error(f"Error preparing payment method chart data: {e}")
            return {"error": str(e)}

    def prepare_product_performance_chart_data(
        self, start_date: date, end_date: date, limit: int = 10
    ) -> Dict:
        """
        Prepare data for top performing products bar chart.
        Returns data formatted for Chart.js horizontal bar chart.
        """
        try:
            product_sales = (
                Sales.objects.filter(sale_date__range=[start_date, end_date])
                .values(
                    "product__name",
                    "product__sales_category__name",
                )
                .annotate(
                    total_revenue=Sum("total_sale_price"),
                    total_quantity=Sum("quantity_sold"),
                )
                .order_by("-total_revenue")[:limit]
            )

            if not product_sales:
                return {"error": "No sales data found for the specified period"}

            # Prepare chart data
            labels = []
            revenue_data = []
            quantity_data = []
            colors = []

            for i, item in enumerate(product_sales):
                product_name = item["product__name"]
                # Truncate long product names
                if len(product_name) > 25:
                    product_name = product_name[:22] + "..."

                labels.append(product_name)
                revenue_data.append(float(item["total_revenue"]))
                quantity_data.append(float(item["total_quantity"]))
                colors.append(f"hsl({(i * 360 / limit) % 360}, 70%, 60%)")

            return {
                "type": "bar",
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Revenue (FCFA)",
                            "data": revenue_data,
                            "backgroundColor": colors,
                            "borderColor": colors,
                            "borderWidth": 1,
                        }
                    ],
                },
                "options": {
                    "indexAxis": "y",
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"Top {limit} Performing Products ({start_date} to {end_date})",
                        },
                        "legend": {"display": True},
                        "tooltip": {
                            "callbacks": {
                                "label": "function(context) { return 'Revenue: ' + context.parsed.x.toLocaleString() + ' FCFA'; }"
                            }
                        },
                    },
                    "scales": {
                        "x": {
                            "beginAtZero": True,
                            "title": {"display": True, "text": "Revenue (FCFA)"},
                        }
                    },
                },
                "summary": {
                    "total_revenue": sum(revenue_data),
                    "avg_revenue_per_product": (
                        sum(revenue_data) / len(revenue_data) if revenue_data else 0
                    ),
                    "top_product": (
                        product_sales[0]["product__name"] if product_sales else None
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Error preparing product performance chart data: {e}")
            return {"error": str(e)}

    def prepare_growth_comparison_chart_data(
        self, comparison_periods: List[Tuple[date, date]]
    ) -> Dict:
        """
        Prepare data for growth comparison chart.
        Returns data formatted for Chart.js grouped bar chart.
        """
        try:
            if len(comparison_periods) < 2:
                return {"error": "Need at least 2 periods for comparison"}

            period_data = []
            labels = []

            for i, (start_date, end_date) in enumerate(comparison_periods):
                summaries = DailySummary.objects.filter(
                    date__range=[start_date, end_date]
                )

                if summaries.exists():
                    total_revenue = summaries.aggregate(total=Sum("total_sales"))[
                        "total"
                    ] or Decimal("0")
                    total_orders = (
                        summaries.aggregate(total=Sum("total_orders"))["total"] or 0
                    )
                    total_customers = (
                        summaries.aggregate(total=Sum("total_customers"))["total"] or 0
                    )
                    days_count = summaries.count()

                    avg_daily_revenue = (
                        total_revenue / days_count if days_count > 0 else Decimal("0")
                    )
                    avg_order_value = (
                        total_revenue / total_orders
                        if total_orders > 0
                        else Decimal("0")
                    )

                    period_data.append(
                        {
                            "revenue": float(total_revenue),
                            "orders": total_orders,
                            "customers": total_customers,
                            "avg_daily_revenue": float(avg_daily_revenue),
                            "avg_order_value": float(avg_order_value),
                        }
                    )

                    labels.append(f"Period {i+1}\n({start_date} to {end_date})")
                else:
                    period_data.append(
                        {
                            "revenue": 0,
                            "orders": 0,
                            "customers": 0,
                            "avg_daily_revenue": 0,
                            "avg_order_value": 0,
                        }
                    )
                    labels.append(f"Period {i+1}\n(No data)")

            # Calculate growth rates
            growth_rates = []
            if len(period_data) >= 2:
                for i in range(1, len(period_data)):
                    current = period_data[i]
                    previous = period_data[i - 1]

                    revenue_growth = (
                        (
                            (current["revenue"] - previous["revenue"])
                            / previous["revenue"]
                            * 100
                        )
                        if previous["revenue"] > 0
                        else 0
                    )
                    orders_growth = (
                        (
                            (current["orders"] - previous["orders"])
                            / previous["orders"]
                            * 100
                        )
                        if previous["orders"] > 0
                        else 0
                    )

                    growth_rates.append(
                        {
                            "period": f"{i} vs {i-1}",
                            "revenue_growth": revenue_growth,
                            "orders_growth": orders_growth,
                        }
                    )

            return {
                "type": "bar",
                "data": {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Total Revenue (FCFA)",
                            "data": [p["revenue"] for p in period_data],
                            "backgroundColor": "rgba(75, 192, 192, 0.8)",
                            "borderColor": "rgb(75, 192, 192)",
                            "borderWidth": 1,
                        },
                        {
                            "label": "Total Orders",
                            "data": [p["orders"] for p in period_data],
                            "backgroundColor": "rgba(255, 99, 132, 0.8)",
                            "borderColor": "rgb(255, 99, 132)",
                            "borderWidth": 1,
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {"display": True, "text": "Period Comparison"},
                        "legend": {"display": True},
                    },
                    "scales": {
                        "y": {
                            "beginAtZero": True,
                            "title": {"display": True, "text": "Value"},
                        }
                    },
                },
                "growth_rates": growth_rates,
                "period_data": period_data,
            }

        except Exception as e:
            logger.error(f"Error preparing growth comparison chart data: {e}")
            return {"error": str(e)}

    # === PRIVATE HELPER METHODS ===

    def _calculate_trend_indicators(self, revenue_data: List[float]) -> Dict:
        """Calculate trend indicators for revenue data"""
        if len(revenue_data) < 2:
            return {"trend": "insufficient_data", "change_percentage": 0}

        # Calculate simple trend
        first_half = revenue_data[: len(revenue_data) // 2]
        second_half = revenue_data[len(revenue_data) // 2 :]

        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0

        if first_avg > 0:
            change_percentage = ((second_avg - first_avg) / first_avg) * 100
        else:
            change_percentage = 0

        if change_percentage > 5:
            trend = "increasing"
        elif change_percentage < -5:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change_percentage": change_percentage,
            "first_half_avg": first_avg,
            "second_half_avg": second_avg,
        }

    def format_currency(self, amount: Decimal, currency: str = "FCFA") -> str:
        """Format currency amount for display"""
        try:
            return f"{float(amount):,.0f} {currency}"
        except:
            return f"{amount} {currency}"

    def format_percentage(self, value: float, decimal_places: int = 1) -> str:
        """Format percentage for display"""
        try:
            return f"{value:.{decimal_places}f}%"
        except:
            return f"{value}%"

    def get_chart_colors(self, count: int) -> List[str]:
        """Get a list of colors for charts"""
        base_colors = [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
            "#9966FF",
            "#FF9F40",
            "#FF6384",
            "#C9CBCF",
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
        ]

        if count <= len(base_colors):
            return base_colors[:count]

        # Generate additional colors if needed
        colors = base_colors.copy()
        for i in range(len(base_colors), count):
            hue = (i * 360 / count) % 360
            colors.append(f"hsl({hue}, 70%, 60%)")

        return colors[:count]
