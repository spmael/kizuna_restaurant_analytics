# 🏆 Cost Analytics Service - Restaurant Industry Standards

## 📋 Overview

The Cost Analytics Service provides comprehensive cost analysis for restaurant operations, focusing on food cost tracking, waste management, and cost optimization opportunities. This service answers key business questions about cost control and profitability.

## 🎯 Key Features

### 📊 Core Cost Metrics (Priority 1)
- **Food Cost Percentage Tracking** - Current vs target (25-35%)
- **Daily/Weekly Food Cost Trends** - Trend analysis and forecasting
- **Food Cost Variance** - Actual vs budget comparisons
- **Benchmark Comparison** - Industry standard indicators

### 💰 Cost Breakdown Analysis
- **Cost by Ingredient Category** - Meat, vegetables, spices analysis
- **Cost by Dish/Recipe** - Individual recipe profitability
- **Cost per Customer Served** - Customer-level cost analysis
- **Cost per Order** - Order-level cost breakdown

### 🚨 Cost Control Alerts
- **Food Cost Exceeds Targets** - Real-time alerts
- **Ingredient Price Variance** - Price fluctuation monitoring
- **High Waste Cost Warnings** - Waste threshold alerts
- **Recipe Profitability Issues** - Low-margin recipe identification

## 🏗️ Architecture

### Service Structure
```
apps/analytics/
├── services/
│   └── cost_analytics.py          # Main cost analytics service
└── utils/
    └── cost_utils.py              # Cost calculation utilities
```

### Key Components

#### 1. CostAnalyticsService
Main service class providing comprehensive cost analysis:

```python
from apps.analytics.services.cost_analytics import CostAnalyticsService

# Initialize service
cost_service = CostAnalyticsService()

# Get cost overview
overview = cost_service.get_cost_overview(start_date, end_date)
```

#### 2. CostUtils
Utility functions for cost calculations and formatting:

```python
from apps.analytics.utils.cost_utils import CostUtils

# Calculate food cost percentage
food_cost_pct = CostUtils.calculate_food_cost_percentage(food_cost, revenue)

# Format currency
formatted = CostUtils.format_currency(amount, "FCFA")
```

## 📈 Core Analytics Methods

### 1. Cost Overview
```python
overview = cost_service.get_cost_overview(start_date, end_date)
```
**Answers:** "How much are we spending on ingredients?"

**Returns:**
- Total food cost and revenue
- Food cost percentage
- Waste cost percentage
- Performance grades (A-F)
- Cost trends and alerts

### 2. Food Cost Analysis
```python
analysis = cost_service.get_food_cost_analysis(start_date, end_date)
```
**Answers:** "Are our costs under control?"

**Returns:**
- Daily food cost trends
- Cost variance analysis
- Efficiency metrics
- Control indicators

### 3. Cost by Category
```python
categories = cost_service.get_cost_by_category(start_date, end_date)
```
**Answers:** "Where are our costs concentrated?"

**Returns:**
- Cost breakdown by ingredient category
- Category performance grades
- Cost optimization insights

### 4. Waste Analysis
```python
waste = cost_service.get_waste_analysis(start_date, end_date)
```
**Answers:** "What's causing waste?"

**Returns:**
- Daily waste trends
- Waste efficiency analysis
- Reduction opportunities
- Waste cost alerts

### 5. Recipe Cost Analysis
```python
recipes = cost_service.get_recipe_cost_analysis(start_date, end_date)
```
**Answers:** "How efficient are our recipes?"

**Returns:**
- Recipe profitability analysis
- Cost per portion
- Profit margins by recipe
- Performance grades

### 6. Cost Optimization Opportunities
```python
opportunities = cost_service.get_cost_optimization_opportunities(start_date, end_date)
```
**Answers:** "Where can we reduce costs?"

**Returns:**
- High-cost ingredients
- Low-margin recipes
- Waste reduction opportunities
- Bulk purchasing suggestions

### 7. Cost Alerts
```python
alerts = cost_service.get_cost_alerts(start_date, end_date)
```
**Returns:**
- Critical alerts (food cost >40%)
- Warning alerts (elevated costs)
- Info alerts (optimization opportunities)

## 🎯 Industry Benchmarks

### Food Cost Targets
- **Excellent:** 25-30%
- **Good:** 30-35%
- **Acceptable:** 35-40%
- **High:** 40-50%
- **Critical:** 50%+

### Waste Cost Targets
- **Excellent:** 0-2% of revenue
- **Good:** 2-3% of revenue
- **Acceptable:** 3-5% of revenue
- **High:** 5-10% of revenue
- **Critical:** 10%+ of revenue

## 💡 Usage Examples

### Basic Cost Analysis
```python
from datetime import date, timedelta
from apps.analytics.services.cost_analytics import CostAnalyticsService

# Initialize service
cost_service = CostAnalyticsService()

# Set date range (last 30 days)
end_date = date.today()
start_date = end_date - timedelta(days=30)

# Get comprehensive cost overview
overview = cost_service.get_cost_overview(start_date, end_date)

if "error" not in overview:
    print(f"Food Cost: {overview['percentage_metrics']['food_cost_percentage']:.1f}%")
    print(f"Waste Cost: {overview['percentage_metrics']['waste_cost_percentage']:.1f}%")
    print(f"Performance Grade: {overview['performance_analysis']['overall_performance']['grade']}")
```

### Cost Trend Analysis
```python
from apps.analytics.utils.cost_utils import CostUtils

# Calculate cost trends
trend = CostUtils.calculate_cost_trend(start_date, end_date, "food_cost_percentage")

if "error" not in trend:
    print(f"Trend: {trend['trend']}")
    print(f"Change: {trend['change_percentage']:.1f}%")
```

### Cost Alerts
```python
# Generate cost alerts
alerts = cost_service.get_cost_alerts(start_date, end_date)

if "error" not in alerts:
    summary = alerts['summary']
    print(f"Critical Alerts: {summary['critical_count']}")
    print(f"Warning Alerts: {summary['warning_count']}")
    
    # Show critical alerts
    for alert in alerts['alerts']['critical']:
        print(f"🚨 {alert['message']}")
```

### Recipe Profitability Analysis
```python
# Analyze recipe costs
recipes = cost_service.get_recipe_cost_analysis(start_date, end_date)

if "error" not in recipes:
    for recipe in recipes['recipes'][:5]:  # Top 5 recipes
        print(f"{recipe['recipe_name']}: {recipe['profit_margin']:.1f}% margin")
```

## 🔧 Utility Functions

### Cost Calculations
```python
from apps.analytics.utils.cost_utils import CostUtils

# Calculate percentages
food_cost_pct = CostUtils.calculate_food_cost_percentage(food_cost, revenue)
waste_cost_pct = CostUtils.calculate_waste_cost_percentage(waste_cost, revenue)
profit_margin = CostUtils.calculate_profit_margin(revenue, total_cost)

# Calculate efficiency score
efficiency = CostUtils.calculate_cost_efficiency_score(food_cost_pct, waste_cost_pct)
```

### Formatting
```python
# Format currency and percentages
formatted_cost = CostUtils.format_currency(amount, "FCFA")
formatted_pct = CostUtils.format_percentage(value, 1)

# Get status indicators
status = CostUtils.get_cost_status(food_cost_percentage)
grade = CostUtils.grade_performance(efficiency_score)
```

### Data Validation
```python
# Validate cost data
validation = CostUtils.validate_cost_data(food_cost, revenue, waste_cost)

if validation['is_valid']:
    print("✅ Data is valid")
else:
    print(f"❌ Errors: {validation['errors']}")
    print(f"⚠️ Warnings: {validation['warnings']}")
```

## 📊 Data Models Used

### DailySummary Model
Key fields for cost analysis:
- `total_food_cost` - Daily food cost
- `food_cost_percentage` - Calculated food cost %
- `waste_cost` - Daily waste cost
- `resale_cost` - Beverage costs
- `cogs_confidence_level` - Data quality indicator

### ProductCostHistory Model
For detailed cost tracking:
- `unit_cost_in_recipe_units` - Recipe costing
- `product_category` - Cost by category
- `weight_factor` - Cost variance tracking

## 🚀 Testing

Run the test script to verify functionality:

```bash
python test_cost_analytics.py
```

The test script demonstrates:
- All major service methods
- Utility functions
- Data formatting
- Error handling
- Performance analysis

## 📈 Dashboard Integration

### Cost Health Dashboard
- Food Cost % Gauge (Green: <30%, Yellow: 30-35%, Red: >35%)
- Waste Cost Tracker (Target: <3% of revenue)
- Cost Variance Indicator (Actual vs Budget)

### Cost Trend Charts
- Daily Food Cost % line chart
- Cost by Category pie chart
- Recipe Profitability bar chart

### Cost Alerts Section
- 🚨 Critical alerts (Food cost >35%)
- ⚠️ Warning alerts (Waste >3%, Price increases)
- 💡 Optimization opportunities

## 🎯 Business Insights

### Action-Oriented Language
- **"Food cost excellent - keep it up!"**
- **"Meat prices rising - watch portions"**
- **"Vegetables cheap this month - promote veggie dishes"**
- **"High waste yesterday - check prep amounts"**

### Success Metrics
- Food Cost % stays below 35% (ideal: 25-30%)
- Waste Cost under 3% of revenue
- Cost Variance within ±5% of budget
- Recipe Profitability >65% gross margin

## 🔄 Integration with Revenue Analytics

The Cost Analytics Service works seamlessly with the Revenue Analytics Service to provide comprehensive business insights:

```python
from apps.analytics.services.revenue_analytics import RevenueAnalyticsService
from apps.analytics.services.cost_analytics import CostAnalyticsService

# Get both revenue and cost analysis
revenue_service = RevenueAnalyticsService()
cost_service = CostAnalyticsService()

revenue_overview = revenue_service.get_revenue_overview(start_date, end_date)
cost_overview = cost_service.get_cost_overview(start_date, end_date)

# Calculate net profit
net_profit = revenue_overview['total_metrics']['total_revenue'] - cost_overview['total_metrics']['total_food_cost']
```

## 🛠️ Configuration

### Customizing Benchmarks
Modify the `COST_BENCHMARKS` in `CostAnalyticsService` or `CostUtils`:

```python
COST_BENCHMARKS = {
    "food_cost_targets": {
        "excellent": (25, 30),  # Adjust for your restaurant
        "good": (30, 35),
        # ... customize as needed
    }
}
```

### Alert Thresholds
Customize alert thresholds in the service methods:

```python
# In get_cost_alerts method
food_cost_threshold = 40.0  # Customize threshold
waste_cost_threshold = 5.0   # Customize threshold
```

## 📝 Future Enhancements

### Planned Features
1. **Seasonal Cost Analysis** - Historical cost patterns
2. **Supplier Cost Comparison** - Vendor performance analysis
3. **Menu Engineering Integration** - Cost-based menu optimization
4. **Real-time Cost Monitoring** - Live cost tracking
5. **Predictive Cost Modeling** - Cost forecasting

### Advanced Analytics
1. **Cost Variance Analysis** - Detailed variance reporting
2. **Portion Control Tracking** - Recipe consistency monitoring
3. **Labor Cost Integration** - Full cost analysis
4. **Inventory Cost Tracking** - Stock value analysis

## 🤝 Contributing

When adding new cost analytics features:

1. **Follow the existing pattern** - Use similar method signatures
2. **Add comprehensive tests** - Include edge cases
3. **Update documentation** - Document new methods
4. **Use utility functions** - Leverage existing CostUtils
5. **Handle errors gracefully** - Return error dictionaries

## 📞 Support

For questions or issues with the Cost Analytics Service:

1. Check the test script for usage examples
2. Review the utility functions for common calculations
3. Verify data model relationships
4. Test with sample data first

---

**🎉 The Cost Analytics Service provides restaurant owners with the tools they need to control costs, reduce waste, and maximize profitability through data-driven insights!**
