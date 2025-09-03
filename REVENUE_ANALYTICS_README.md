# Revenue Analytics System

## Overview

The Revenue Analytics System is a comprehensive solution for restaurant revenue analysis that answers key business questions and provides actionable insights. Built on Django with Chart.js visualizations, it follows restaurant industry standards and Cameroon market benchmarks.

## 🎯 Key Questions Answered

The system is designed to answer these critical revenue questions:

1. **"How much money are we making?"** → Total revenue trends and performance metrics
2. **"What's driving our sales?"** → Top categories and products analysis
3. **"When do we make the most money?"** → Peak hours/days and time-based patterns
4. **"Are we growing?"** → Growth rate comparisons and trend analysis
5. **"Where's our opportunity?"** → Underperforming areas and optimization opportunities

## 📊 Visual Priority

The system provides these key visualizations:

- 📈 **Daily Revenue Chart** - Shows trends at a glance
- 🥧 **Category Pie Chart** - What's selling best
- ⏰ **Time-based Bar Chart** - Peak hours analysis
- 💳 **Payment Method Breakdown** - Customer preferences
- 🏆 **Top Products Chart** - Individual product performance

## 🏗️ Architecture

### Core Components

1. **RevenueAnalyticsService** (`apps/analytics/services/revenue_analytics.py`)
   - Main service class for revenue analysis
   - Handles all business logic and calculations
   - Provides comprehensive analytics methods

2. **RevenueChartUtils** (`apps/analytics/utils/revenue_utils.py`)
   - Utility class for chart data preparation
   - Formats data for Chart.js visualizations
   - Handles chart configuration and styling

3. **Views** (`apps/analytics/views.py`)
   - `RevenueAnalyticsView` - Main analytics dashboard
   - `RevenueInsightsView` - Detailed insights and recommendations

4. **Templates**
   - `revenue_analytics.html` - Main analytics dashboard
   - `revenue_insights.html` - Detailed insights view

## 🚀 Features

### 1. Revenue Overview
- Total revenue, orders, and customers
- Average daily revenue and order values
- Performance grading (A-F) based on industry benchmarks
- Growth trend analysis

### 2. Category Analysis
- Top performing product categories
- Revenue percentage breakdown
- Performance grading for each category
- Insights on category concentration

### 3. Product Analysis
- Top performing individual products
- Revenue and quantity metrics
- Estimated profit margins
- Performance grading

### 4. Time-based Analysis
- Daily revenue patterns
- Best and worst performing days
- Weekly trends
- Seasonal analysis

### 5. Growth Analysis
- Period-over-period comparisons
- Growth rate calculations
- Trend identification
- Benchmark comparisons

### 6. Opportunity Analysis
- Underperforming categories and products
- Low-margin product identification
- Revenue optimization opportunities
- Actionable recommendations

### 7. Payment Method Analysis
- Payment method breakdown
- Cameroon market benchmarks
- Digital payment adoption insights
- Cash dependency analysis

## 📈 Industry Benchmarks

The system uses industry-standard benchmarks for Cameroon restaurant market:

### Revenue Targets
- **Small Restaurant**: 50,000 - 150,000 FCFA daily
- **Medium Restaurant**: 150,000 - 300,000 FCFA daily
- **Large Restaurant**: 300,000 - 500,000 FCFA daily

### Growth Targets
- **Monthly**: 5-15% growth
- **Quarterly**: 10-25% growth

### Category Performance
- **Main Dishes**: 40-60% of revenue
- **Beverages**: 15-25% of revenue
- **Appetizers**: 10-20% of revenue
- **Desserts**: 5-15% of revenue

### Payment Methods (Cameroon)
- **Cash**: 60-80%
- **Mobile Money**: 15-30%
- **Card**: 5-15%

## 🛠️ Installation & Setup

### Prerequisites
- Django 4.x
- Python 3.8+
- PostgreSQL (recommended)
- Chart.js (included via CDN)

### Setup Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Setup**
   ```bash
   python manage.py migrate
   ```

3. **Load Sample Data** (if needed)
   ```bash
   python manage.py load_sample_data
   ```

4. **Run Daily Summary Calculations**
   ```bash
   python manage.py calculate_daily_summaries
   ```

## 📖 Usage

### 1. Access the Analytics Dashboard

Navigate to: `/analytics/revenue/`

### 2. View Detailed Insights

Navigate to: `/analytics/revenue/insights/`



## 🧪 Testing

### Run the Test Script

```bash
python test_revenue_analytics.py
```

This will:
- Check data requirements
- Test all analytics functions
- Verify chart utilities
- Provide a comprehensive test report

### Manual Testing

1. **Check Data Availability**
   ```python
   from apps.analytics.models import DailySummary
   from apps.restaurant_data.models import Sales
   
   # Check if you have data
   summary_count = DailySummary.objects.count()
   sales_count = Sales.objects.count()
   ```

2. **Test Service Functions**
   ```python
   from apps.analytics.services.revenue_analytics import RevenueAnalyticsService
   
   service = RevenueAnalyticsService()
   overview = service.get_revenue_overview(start_date, end_date)
   ```

## 📊 Data Requirements

### Required Models

1. **DailySummary** (`apps/analytics.models.DailySummary`)
   - Daily aggregated metrics
   - Revenue, orders, customers
   - Payment method breakdown
   - Performance metrics

2. **Sales** (`apps.restaurant_data.models.Sales`)
   - Individual sales records
   - Product, quantity, revenue
   - Date and customer information

3. **Product** (`apps.restaurant_data.models.Product`)
   - Product information
   - Categories and pricing
   - Cost data

4. **SalesCategory** (`apps.restaurant_data.models.SalesCategory`)
   - Product categories
   - Category hierarchy

### Data Quality Requirements

- **Sales Data**: Must have sale_date, product, quantity_sold, total_sale_price
- **Products**: Must have sales_category relationship
- **DailySummary**: Can be generated from sales data using the analytics service

## 🔧 Configuration

### Settings

The system uses Django settings for configuration. Key settings:

```python
# settings.py

# Analytics settings
ANALYTICS_SETTINGS = {
    'DEFAULT_DATE_RANGE_DAYS': 30,
    'CHART_COLORS': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
    'PERFORMANCE_GRADES': {
        'A': (90, 100),
        'B': (80, 89),
        'C': (70, 79),
        'D': (60, 69),
        'F': (0, 59),
    }
}
```

### Customization

1. **Benchmarks**: Modify `REVENUE_BENCHMARKS` in `RevenueAnalyticsService`
2. **Charts**: Customize chart colors and options in `RevenueChartUtils`
3. **Insights**: Add custom insight generation logic
4. **Grading**: Adjust performance grading criteria

## 📈 Performance Optimization

### Database Optimization

1. **Indexes**: Ensure proper database indexes on date fields
2. **Aggregation**: Use database aggregation for large datasets
3. **Caching**: Implement caching for frequently accessed data

### Query Optimization

1. **Select Related**: Use `select_related()` for foreign key relationships
2. **Prefetch Related**: Use `prefetch_related()` for many-to-many relationships
3. **Database Views**: Consider creating database views for complex aggregations

## 🔒 Security

### Access Control

- All views require authentication (`LoginRequiredMixin`)
- API endpoints are protected
- Data access is restricted to authorized users

### Data Privacy

- No sensitive customer data is exposed
- Aggregated data only
- Audit trails for data access

## 🐛 Troubleshooting

### Common Issues

1. **No Data Found**
   - Check if DailySummary records exist
   - Verify sales data is loaded
   - Run daily summary calculations

2. **Chart Errors**
   - Check Chart.js is loaded
   - Verify chart data format
   - Check browser console for errors

3. **Performance Issues**
   - Check database indexes
   - Monitor query performance
   - Consider caching solutions

### Debug Mode

Enable debug mode for detailed error information:

```python
# settings.py
DEBUG = True
```



## 🤝 Contributing

### Development Guidelines

1. **Code Style**: Follow PEP 8 and Django conventions
2. **Testing**: Write tests for new features
3. **Documentation**: Update documentation for changes
4. **Performance**: Consider performance impact of changes

### Adding New Features

1. **Service Layer**: Add methods to `RevenueAnalyticsService`
2. **Chart Utils**: Add chart preparation methods to `RevenueChartUtils`
3. **Views**: Add new views or extend existing ones
4. **Templates**: Create or update templates
5. **Tests**: Add comprehensive tests

## 📞 Support

For support and questions:

1. Check the troubleshooting section
2. Review the API documentation
3. Run the test script to verify functionality
4. Check the Django logs for errors

## 📄 License

This revenue analytics system is part of the Kizuna Restaurant Analytics project.

---

**Built with ❤️ for restaurant success**
