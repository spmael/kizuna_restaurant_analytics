from typing import Any, Dict

from apps.analytics.models import DailySummary


def get_enhanced_food_cost_widget_data(target_date) -> Dict[str, Any]:
    """
    Enhanced version showing confidence levels and range-based cost display
    """

    try:
        daily_summary = DailySummary.objects.get(date=target_date)
    except DailySummary.DoesNotExist:
        return {
            "display_text": "No data",
            "display_mode": "no_data",
            "confidence_level": "UNKNOWN",
            "data_completeness": 0,
            "missing_count": 0,
            "status": "unknown",
            "industry_target": {"min": 25, "max": 35},
        }

    # Calculate food cost percentages
    conservative_pct = 0
    estimated_pct = 0

    if daily_summary.total_sales > 0:
        conservative_pct = (
            daily_summary.total_food_cost_conservative / daily_summary.total_sales
        ) * 100
        estimated_pct = (
            daily_summary.total_food_cost / daily_summary.total_sales
        ) * 100

    # Show range if significantly different
    cost_difference = abs(estimated_pct - conservative_pct)
    if cost_difference < 1:
        display_text = f"{estimated_pct:.1f}%"
        display_mode = "single"
    else:
        display_text = f"{conservative_pct:.1f}% - {estimated_pct:.1f}%"
        display_mode = "range"

    return {
        "display_text": display_text,
        "display_mode": display_mode,
        "confidence_level": daily_summary.cogs_confidence_level,
        "data_completeness": daily_summary.data_completeness_percentage,
        "missing_count": daily_summary.missing_ingredients_count,
        "estimated_count": daily_summary.estimated_ingredients_count,
        "status": daily_summary.food_cost_status,
        "industry_target": {"min": 25, "max": 35},
        "conservative_percentage": conservative_pct,
        "estimated_percentage": estimated_pct,
        "cost_difference": cost_difference,
    }


def get_confidence_indicator_class(confidence_level: str) -> str:
    """Get CSS class for confidence level indicator"""

    confidence_classes = {
        "HIGH": "text-success",
        "MEDIUM": "text-warning",
        "LOW": "text-danger",
        "VERY_LOW": "text-danger font-weight-bold",
    }

    return confidence_classes.get(confidence_level, "text-muted")


def get_confidence_icon(confidence_level: str) -> str:
    """Get icon for confidence level"""

    confidence_icons = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❌", "VERY_LOW": "🚨"}

    return confidence_icons.get(confidence_level, "❓")


def get_cost_range_display_class(cost_difference: float) -> str:
    """Get CSS class for cost range display"""

    if cost_difference < 1:
        return "text-success"  # Green - good agreement
    elif cost_difference < 3:
        return "text-warning"  # Yellow - moderate difference
    else:
        return "text-danger"  # Red - significant difference


def format_confidence_tooltip(daily_summary: DailySummary) -> str:
    """Format tooltip text for confidence indicator"""

    tooltip = f"Confidence: {daily_summary.cogs_confidence_level}\n"
    tooltip += f"Data Completeness: {daily_summary.data_completeness_percentage:.1f}%\n"
    tooltip += f"Missing Ingredients: {daily_summary.missing_ingredients_count}\n"
    tooltip += f"Estimated Ingredients: {daily_summary.estimated_ingredients_count}"

    if daily_summary.cogs_calculation_notes:
        tooltip += f"\n\nNotes: {daily_summary.cogs_calculation_notes}"

    return tooltip


def get_food_cost_analysis_summary(target_date) -> Dict[str, Any]:
    """Get comprehensive food cost analysis summary"""

    try:
        daily_summary = DailySummary.objects.get(date=target_date)
    except DailySummary.DoesNotExist:
        return {"has_data": False, "message": "No data available for this date"}

    # Calculate percentages
    conservative_pct = 0
    estimated_pct = 0

    if daily_summary.total_sales > 0:
        conservative_pct = (
            daily_summary.total_food_cost_conservative / daily_summary.total_sales
        ) * 100
        estimated_pct = (
            daily_summary.total_food_cost / daily_summary.total_sales
        ) * 100

    # Determine analysis status
    if daily_summary.cogs_confidence_level == "HIGH":
        analysis_status = "reliable"
        status_message = "High confidence in cost calculations"
    elif daily_summary.cogs_confidence_level == "MEDIUM":
        analysis_status = "moderate"
        status_message = "Moderate confidence - some estimates used"
    elif daily_summary.cogs_confidence_level == "LOW":
        analysis_status = "low"
        status_message = "Low confidence - significant estimates used"
    else:
        analysis_status = "very_low"
        status_message = "Very low confidence - mostly estimates"

    # Cost range analysis
    cost_difference = abs(estimated_pct - conservative_pct)
    if cost_difference < 1:
        range_status = "excellent"
        range_message = "Conservative and estimated costs are very close"
    elif cost_difference < 3:
        range_status = "good"
        range_message = "Conservative and estimated costs are reasonably close"
    elif cost_difference < 5:
        range_status = "moderate"
        range_message = (
            "Significant difference between conservative and estimated costs"
        )
    else:
        range_status = "poor"
        range_message = "Large difference between conservative and estimated costs"

    return {
        "has_data": True,
        "date": target_date,
        "conservative_percentage": conservative_pct,
        "estimated_percentage": estimated_pct,
        "cost_difference": cost_difference,
        "confidence_level": daily_summary.cogs_confidence_level,
        "data_completeness": daily_summary.data_completeness_percentage,
        "missing_ingredients": daily_summary.missing_ingredients_count,
        "estimated_ingredients": daily_summary.estimated_ingredients_count,
        "analysis_status": analysis_status,
        "status_message": status_message,
        "range_status": range_status,
        "range_message": range_message,
        "industry_target_min": 25,
        "industry_target_max": 35,
        "notes": daily_summary.cogs_calculation_notes,
    }
