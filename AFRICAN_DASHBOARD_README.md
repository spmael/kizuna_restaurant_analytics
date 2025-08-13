# African-Inspired Restaurant Analytics Dashboard

## Overview

A lightweight, user-friendly restaurant analytics dashboard with African-inspired design elements, centralized theme management, and interactive Chart.js visualizations optimized for non-technical restaurant owners and managers.

## Features

### 🎨 Design System
- **African Color Palette**: Warm terracotta, golden sunset, savanna green, and clay brown
- **Typography**: Inter and Poppins fonts for modern, readable text
- **Responsive Design**: Mobile-first approach with touch-friendly interfaces
- **Accessibility**: WCAG 2.1 AA compliant with high contrast support

### 📊 Interactive Visualizations
- **Revenue Trend Charts**: Line and bar chart options
- **Sales by Category**: Doughnut charts with African color palette
- **Peak Hours Analysis**: Bar charts showing busy periods
- **Customer Flow**: Area charts for foot traffic patterns
- **Real-time Updates**: Dynamic data loading with loading states

### 🎯 User Experience
- **Non-Technical Friendly**: Simple navigation, clear labels, restaurant terminology
- **Quick Actions**: One-click access to detailed analytics
- **Performance Alerts**: Smart notifications for food cost and revenue issues
- **Mobile Responsive**: Optimized for tablet and mobile use

## File Structure

```
static/
├── css/
│   ├── theme.css          # Centralized theme management
│   ├── components.css     # Component-specific styles
│   └── style.css          # Base styles
├── js/
│   ├── theme.js           # Theme management and chart configurations
│   └── script.js          # General JavaScript utilities

templates/
├── analytics/
│   ├── dashboard_african.html    # African-inspired dashboard
│   ├── dashboard_nav.html        # Dashboard navigation component
│   └── dashboard.html            # Original dashboard
```

## Color Palette

### Primary Colors
- **Warm Terracotta**: `#E07A5F` - Primary accent color
- **Golden Sunset**: `#F2B670` - Secondary accent
- **Sahara Sand**: `#F4F3EE` - Light background
- **Clay Brown**: `#81654F` - Text and borders

### Supporting Colors
- **Deep Earth**: `#3D2914` - Headers and navigation
- **Savanna Green**: `#6B8E3D` - Success states
- **Sunset Orange**: `#F18F01` - Warnings and alerts
- **Desert Rose**: `#C73E1D` - Errors and critical states

## Usage

### Accessing the Dashboard

1. **Classic Dashboard**: `/analytics/`
2. **African Design Dashboard**: `/analytics/african/`

### Navigation

The dashboard includes a navigation component that allows users to switch between:
- **Classic Dashboard**: Original Bootstrap-based design
- **African Design**: New African-inspired design with enhanced UX

### Chart Interactions

- **Chart Type Toggle**: Switch between line, bar, and area charts
- **Date Range Selection**: Choose from 7, 30, or 90-day periods
- **Responsive Charts**: Automatically resize for different screen sizes
- **Interactive Tooltips**: Hover for detailed information

## Technical Implementation

### Theme Management

The dashboard uses CSS Custom Properties for centralized theme management:

```css
:root {
  --color-primary: #E07A5F;
  --color-secondary: #F2B670;
  --bg-primary: #F4F3EE;
  --text-primary: #343A40;
  /* ... more variables */
}
```

### Chart.js Integration

Charts are configured with the African theme:

```javascript
const chartConfig = {
  borderColor: '#E07A5F',
  backgroundColor: 'rgba(224, 122, 95, 0.1)',
  plugins: {
    tooltip: {
      backgroundColor: '#FFFFFF',
      borderColor: '#E07A5F'
    }
  }
};
```

### Responsive Design

The dashboard uses a mobile-first approach with breakpoints:
- **Mobile**: 320px - 768px
- **Tablet**: 768px - 1024px
- **Desktop**: 1024px+
- **Large Desktop**: 1440px+

## Components

### Metric Cards
- **Revenue Card**: Total sales with trend indicators
- **Orders Card**: Total orders with growth metrics
- **Food Cost Card**: Cost percentage with status indicators
- **Average Order Card**: Order value with comparison data

### Chart Containers
- **Revenue Trend**: Main performance indicator
- **Sales by Category**: Menu performance breakdown
- **Peak Hours**: Operational insights
- **Customer Flow**: Traffic pattern analysis

### Data Tables
- **Top Products**: Best-selling items with revenue data
- **Status Badges**: Color-coded performance indicators
- **Sortable Columns**: Interactive data exploration

### Quick Actions
- **Sales Details**: Link to detailed sales analytics
- **Cost Analysis**: Access to cost management tools
- **Recipe Costing**: Menu engineering insights
- **Performance**: Overall restaurant performance

## Performance Features

### Loading States
- **Spinner Animations**: Visual feedback during data loading
- **Skeleton Screens**: Placeholder content while loading
- **Progressive Loading**: Load critical data first

### Data Management
- **Debounced Updates**: Prevent excessive API calls
- **Cached Results**: Store frequently accessed data
- **Error Handling**: Graceful fallbacks for failed requests

## Accessibility Features

### Visual Accessibility
- **High Contrast**: Sufficient color contrast ratios
- **Color Blind Friendly**: Patterns and icons supplement colors
- **Font Scaling**: Responsive typography

### Navigation Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: ARIA labels and semantic HTML
- **Focus Management**: Clear focus indicators

## Browser Support

- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+

## Installation

1. **Include CSS Files**:
   ```html
   <link rel="stylesheet" href="{% static 'css/theme.css' %}">
   <link rel="stylesheet" href="{% static 'css/components.css' %}">
   ```

2. **Include JavaScript Files**:
   ```html
   <script src="{% static 'js/theme.js' %}"></script>
   ```

3. **Add Google Fonts**:
   ```html
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
   ```

## Customization

### Modifying Colors
Update the CSS custom properties in `theme.css`:

```css
:root {
  --color-primary: #YOUR_COLOR;
  --color-secondary: #YOUR_COLOR;
  /* ... */
}
```

### Adding New Charts
Extend the `ChartConfigFactory` class in `theme.js`:

```javascript
createCustomChart(data) {
  return {
    ...this.createBaseConfig('line'),
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Custom Data',
        data: data.values,
        borderColor: this.theme.colors.primary
      }]
    }
  };
}
```

### Responsive Adjustments
Modify breakpoints in `components.css`:

```css
@media (max-width: 768px) {
  :root {
    --space-lg: 1rem;
    --font-size-2xl: 1.25rem;
  }
}
```

## Best Practices

### Performance
- Use lazy loading for non-critical components
- Optimize images and assets
- Minimize JavaScript bundle size
- Cache static assets

### User Experience
- Keep navigation simple (max 3 clicks to any information)
- Use clear, restaurant-specific terminology
- Provide contextual help and tooltips
- Ensure fast loading times

### Accessibility
- Test with screen readers
- Verify keyboard navigation
- Check color contrast ratios
- Validate ARIA labels

## Future Enhancements

### Planned Features
- **Real-time Updates**: WebSocket integration for live data
- **Export Functionality**: PDF and Excel report generation
- **Advanced Filtering**: Multi-dimensional data filtering
- **Custom Dashboards**: User-configurable layouts

### Technical Improvements
- **Progressive Web App**: Offline functionality
- **Service Workers**: Background data synchronization
- **Advanced Caching**: Intelligent data caching strategies
- **Performance Monitoring**: Real-time performance metrics

## Support

For technical support or feature requests, please refer to the main project documentation or create an issue in the project repository.

## License

This dashboard is part of the Kizuna Restaurant Analytics project and follows the same licensing terms.
