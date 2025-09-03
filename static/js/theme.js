/**
 * African-Inspired Restaurant Analytics Theme Management
 * Centralized JavaScript theme configuration and utilities
 */

const theme = {
  // === COLOR PALETTE ===
  colors: {
    primary: getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#E07A5F',
    secondary: getComputedStyle(document.documentElement).getPropertyValue('--color-secondary').trim() || '#81B29A',
    accent: getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim() || '#F2CC8F',
    success: getComputedStyle(document.documentElement).getPropertyValue('--color-success').trim() || '#3D405B',
    warning: getComputedStyle(document.documentElement).getPropertyValue('--color-warning').trim() || '#E07A5F',
    error: getComputedStyle(document.documentElement).getPropertyValue('--color-error').trim() || '#E07A5F',
    info: getComputedStyle(document.documentElement).getPropertyValue('--color-info').trim() || '#81B29A',
    
    // Background colors
    bgPrimary: getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim() || '#FFFFFF',
    bgSecondary: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim() || '#F8F9FA',
    bgTertiary: getComputedStyle(document.documentElement).getPropertyValue('--bg-tertiary').trim() || '#E9ECEF',
    
    // Text colors
    textPrimary: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333333',
    textSecondary: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#666666',
    textLight: getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim() || '#999999',
    textMuted: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#CCCCCC',
    textHeading: getComputedStyle(document.documentElement).getPropertyValue('--text-heading').trim() || '#333333',
  },

  // === CHART CONFIGURATIONS ===
  chartDefaults: {
    responsive: true,
    maintainAspectRatio: false,
    fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim() || 'Arial, sans-serif',
    
    plugins: {
      legend: {
        labels: {
          fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim() || 'Arial, sans-serif',
          color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#666666',
          usePointStyle: true,
          padding: 20,
          font: {
            size: 12,
            weight: '500'
          }
        }
      },
      tooltip: {
        backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim() || '#FFFFFF',
        titleColor: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333333',
        bodyColor: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#666666',
        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#E07A5F',
        borderWidth: 1,
        cornerRadius: 8,
        titleFont: {
          size: 14,
          weight: '600'
        },
        bodyFont: {
          size: 12
        },
        padding: 12
      }
    },
    
    scales: {
      x: {
        grid: {
          color: (getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#E07A5F') + '20'
        },
        ticks: {
          color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#666666',
          fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim() || 'Arial, sans-serif',
          font: {
            size: 11
          }
        }
      },
      y: {
        grid: {
          color: (getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#E07A5F') + '20'
        },
        ticks: {
          color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#666666',
          fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim() || 'Arial, sans-serif',
          font: {
            size: 11
          }
        }
      }
    }
  },

  // === CHART TYPE CONFIGURATIONS ===
  chartTypes: {
    line: {
      borderWidth: 3,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
      fill: false
    },
    bar: {
      borderWidth: 1,
      borderRadius: 4
    },
    doughnut: {
      borderWidth: 2,
      cutout: '60%'
    },
    pie: {
      borderWidth: 2
    },
    area: {
      borderWidth: 2,
      fill: true
    }
  },

  // === COLOR PALETTES ===
  colorPalettes: {
    primary: [
      '#E07A5F', '#81B29A', '#F2CC8F', '#3D405B', '#A8D5BA',
      '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8BBD9', '#FFCC80'
    ],
    secondary: [
      '#81B29A', '#F2CC8F', '#3D405B', '#E07A5F', '#A8D5BA',
      '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8BBD9', '#FFCC80'
    ],
    success: [
      '#3D405B', '#81B29A', '#A8D5BA', '#F2CC8F', '#E07A5F',
      '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8BBD9', '#FFCC80'
    ]
  }
};

// Fallback colors for when CSS variables are not available
const themeFallbackColors = {
  primary: '#E07A5F',
  secondary: '#81B29A',
  success: '#3D405B',
  warning: '#F2CC8F',
  info: '#85C1E9'
};

/**
 * Utility function to get CSS color with fallback
 */
function getThemeColor(cssVariable, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(cssVariable).trim();
  return value || fallback;
}

/**
 * Chart.js Configuration Factory
 */
class ChartConfigFactory {
  constructor() {
    this.theme = theme;
  }

  /**
   * Create base chart configuration
   */
  createBaseConfig(type = 'line') {
    const baseConfig = { ...this.theme.chartDefaults };
    const typeConfig = this.theme.chartTypes[type] || {};
    
    return {
      ...baseConfig,
      type: type,
      data: {
        datasets: [{
          ...typeConfig
        }]
      }
    };
  }

  /**
   * Create revenue trend line chart
   */
  createRevenueChart(data) {
    return {
      ...this.createBaseConfig('line'),
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Revenue (FCFA)',
          data: data.values,
          borderColor: this.theme.colors.primary,
          backgroundColor: this.theme.colors.primary + '20',
          ...this.theme.chartTypes.line
        }]
      },
      options: {
        ...this.theme.chartDefaults,
        plugins: {
          ...this.theme.chartDefaults.plugins,
          title: {
            display: true,
            text: 'Revenue Trend',
            color: this.theme.colors.textHeading,
            font: {
              size: 16,
              weight: '600'
            }
          }
        },
        scales: {
          ...this.theme.chartDefaults.scales,
          y: {
            ...this.theme.chartDefaults.scales.y,
            ticks: {
              ...this.theme.chartDefaults.scales.y.ticks,
              callback: function(value) {
                return value.toLocaleString() + ' FCFA';
              }
            }
          }
        }
      }
    };
  }

  /**
   * Create sales by category pie chart
   */
  createCategoryChart(data) {
    return {
      ...this.createBaseConfig('doughnut'),
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Sales by Category',
          data: data.values,
          backgroundColor: this.theme.colorPalettes.primary,
          ...this.theme.chartTypes.doughnut
        }]
      },
      options: {
        ...this.theme.chartDefaults,
        plugins: {
          ...this.theme.chartDefaults.plugins,
          title: {
            display: true,
            text: 'Sales by Category',
            color: this.theme.colors.textHeading,
            font: {
              size: 16,
              weight: '600'
            }
          }
        }
      }
    };
  }

  /**
   * Create peak hours bar chart
   */
  createPeakHoursChart(data) {
    return {
      ...this.createBaseConfig('bar'),
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Peak Hours',
          data: data.values,
          backgroundColor: this.theme.colors.info,
          borderColor: this.theme.colors.info,
          ...this.theme.chartTypes.bar
        }]
      },
      options: {
        ...this.theme.chartDefaults,
        plugins: {
          ...this.theme.chartDefaults.plugins,
          title: {
            display: true,
            text: 'Peak Hours Analysis',
            color: this.theme.colors.textHeading,
            font: {
              size: 16,
              weight: '600'
            }
          }
        }
      }
    };
  }

  /**
   * Create customer flow area chart
   */
  createCustomerFlowChart(data) {
    return {
      ...this.createBaseConfig('area'),
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Customer Flow',
          data: data.values,
          borderColor: this.theme.colors.success,
          backgroundColor: this.theme.colors.success + '40',
          ...this.theme.chartTypes.area
        }]
      },
      options: {
        ...this.theme.chartDefaults,
        plugins: {
          ...this.theme.chartDefaults.plugins,
          title: {
            display: true,
            text: 'Customer Flow Analysis',
            color: this.theme.colors.textHeading,
            font: {
              size: 16,
              weight: '600'
            }
          }
        }
      }
    };
  }
}

/**
 * Dashboard Manager Class
 * Handles dashboard initialization, chart management, and AJAX updates
 */
class DashboardManager {
  constructor() {
    this.charts = new Map();
    this.chartFactory = new ChartConfigFactory();
    this.isLoading = false;
    this.currentDateRange = 7; // Default to 7 days
    
    this.init();
  }

  init() {
    console.log('DashboardManager initialized');
    // Delay initialization to allow template charts to initialize first
    setTimeout(() => {
      this.initializeCharts();
    }, 100);
    this.bindEvents();
  }

  initializeCharts() {
    // Initialize only charts that are not already managed by the template
    // Check if the template's chart initialization has already run
    if (window.revenueChart || window.categoryChart) {
      console.log('Charts already initialized by template, skipping DashboardManager initialization');
      return;
    }
    
    // Initialize all chart canvases - only select canvas elements
    const chartCanvases = document.querySelectorAll('canvas[data-chart-type]');
    chartCanvases.forEach(canvas => {
      const chartType = canvas.dataset.chartType;
      const chartData = this.getChartData(canvas.dataset.chartId);
      
      if (chartData) {
        // Map chart types to available factory methods
        let factoryMethod;
        switch (chartType.toLowerCase()) {
          case 'revenue':
          case 'line':
            factoryMethod = 'createRevenueChart';
            break;
          case 'category':
          case 'doughnut':
          case 'pie':
            factoryMethod = 'createCategoryChart';
            break;
          case 'bar':
            factoryMethod = 'createPeakHoursChart';
            break;
          case 'area':
            factoryMethod = 'createCustomerFlowChart';
            break;
          default:
            factoryMethod = 'createRevenueChart';
        }
        
        if (this.chartFactory[factoryMethod]) {
          const config = this.chartFactory[factoryMethod](chartData);
          const chart = new Chart(canvas.getContext('2d'), config);
          this.charts.set(canvas.dataset.chartId, chart);
        } else {
          console.warn(`Factory method ${factoryMethod} not found for chart type ${chartType}`);
        }
      }
    });
  }

  getChartData(chartId) {
    // This would typically fetch data from the server
    // For now, return mock data
    const mockData = {
      'revenue-chart': {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        values: [12000, 15000, 18000, 14000, 22000, 25000, 28000]
      },
      'category-chart': {
        labels: ['Main Dishes', 'Appetizers', 'Drinks', 'Desserts'],
        values: [45, 25, 20, 10]
      },
      'peak-hours-chart': {
        labels: ['6AM', '9AM', '12PM', '3PM', '6PM', '9PM'],
        values: [5, 15, 45, 20, 60, 35]
      },
      'customer-flow-chart': {
        labels: ['6AM', '9AM', '12PM', '3PM', '6PM', '9PM'],
        values: [10, 30, 90, 40, 120, 70]
      }
    };
    
    return mockData[chartId];
  }

  bindEvents() {
    // Note: Date range buttons use onclick handlers instead of data-date-range attributes
    // The buttons call updateRevenueDateRange() and updateCostDateRange() directly
    // So we don't need to bind events here
    
    // Bind filter change events
    const filterSelects = document.querySelectorAll('[data-filter]');
    filterSelects.forEach(select => {
      select.addEventListener('change', (e) => {
        this.updateFilters(e.target.dataset.filter, e.target.value);
      });
    });
  }

  updateDateRange(days) {
    // This method is kept for compatibility but the actual date range updates
    // are handled by the template's updateRevenueDateRange() and updateCostDateRange() functions
    if (this.isLoading) return;
    
    this.currentDateRange = days;
    this.updateButtonStates(days);
    this.fetchDashboardData(days);
  }

  updateButtonStates(activeDays) {
    // Update button states for all date range buttons across chapters
    const allDateRangeButtons = document.querySelectorAll('.btn-african[onclick*="DateRange"]');
    allDateRangeButtons.forEach(button => {
      const onclick = button.getAttribute('onclick');
      const days = parseInt(onclick.match(/\d+/)?.[0] || '7');
      
      if (days === activeDays) {
        button.classList.remove('btn-african-outline');
        button.classList.add('btn-african-primary');
      } else {
        button.classList.remove('btn-african-primary');
        button.classList.add('btn-african-outline');
      }
    });
  }

  async fetchDashboardData(days) {
    if (this.isLoading) return;
    
    this.isLoading = true;
    this.showLoading();
    
    try {
      const response = await fetch(`/analytics/data/?days=${days}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      this.updateDashboard(data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      this.showError('Failed to load dashboard data');
    } finally {
      this.isLoading = false;
      this.hideLoading();
    }
  }

  updateDashboard(data) {
    // Update metric cards
    this.updateMetricCards(data.period_totals || {});
    
    // Update charts
    this.updateCharts(data);
    
    // Update date range display
    if (data.date_range) {
      this.updateDateRangeDisplay(data.date_range);
    }
  }

  updateMetricCards(totals) {
    const metricSelectors = {
      'revenue': '.metric-card.primary .metric-value',
      'customers': '.metric-card.success .metric-value',
      'orders': '.metric-card.info .metric-value',
      'cost': '.metric-card.warning .metric-value'
    };

    if (totals.total_sales) {
      const element = document.querySelector(metricSelectors.revenue);
      if (element) {
        element.textContent = `${parseInt(totals.total_sales).toLocaleString()} FCFA`;
      }
    }

    if (totals.total_customers) {
      const element = document.querySelector(metricSelectors.customers);
      if (element) {
        element.textContent = totals.total_customers;
      }
    }

    if (totals.total_orders) {
      const element = document.querySelector(metricSelectors.orders);
      if (element) {
        element.textContent = totals.total_orders;
      }
    }

    if (totals.avg_food_cost_pct) {
      const element = document.querySelector(metricSelectors.cost);
      if (element) {
        element.textContent = `${parseFloat(totals.avg_food_cost_pct).toFixed(1)}%`;
      }
    }
  }

  updateCharts(data) {
    // Update revenue chart
    if (data.revenue_data && window.revenueChart) {
      window.revenueChart.data.labels = data.revenue_data.labels || [];
      window.revenueChart.data.datasets[0].data = data.revenue_data.revenue || [];
      window.revenueChart.update();
    }

    // Update category chart
    if (data.category_data && window.categoryChart) {
      window.categoryChart.data.labels = data.category_data.labels || [];
      window.categoryChart.data.datasets[0].data = data.category_data.revenue || [];
      window.categoryChart.update();
    }

    // Update other charts as needed
    this.updateRevenueSectionCharts(data);
  }

  updateRevenueSectionCharts(data) {
    // Update daily revenue chart
    if (data.daily_revenue_chart && window.dailyRevenueChart) {
      window.dailyRevenueChart.data.labels = data.daily_revenue_chart.labels || [];
      window.dailyRevenueChart.data.datasets[0].data = data.daily_revenue_chart.revenue || [];
      window.dailyRevenueChart.update();
    }

    // Update revenue category chart
    if (data.revenue_category_chart && window.revenueCategoryChart) {
      window.revenueCategoryChart.data.labels = data.revenue_category_chart.labels || [];
      window.revenueCategoryChart.data.datasets[0].data = data.revenue_category_chart.revenue || [];
      window.revenueCategoryChart.update();
    }

    // Update time based chart
    if (data.time_based_chart && window.timeBasedChart) {
      window.timeBasedChart.data.labels = data.time_based_chart.labels || [];
      window.timeBasedChart.data.datasets[0].data = data.time_based_chart.revenue || [];
      window.timeBasedChart.update();
    }

    // Update payment chart
    if (data.payment_chart && window.paymentChart) {
      window.paymentChart.data.labels = data.payment_chart.labels || [];
      window.paymentChart.data.datasets[0].data = data.payment_chart.amounts || [];
      window.paymentChart.update();
    }
  }

  updateDateRangeDisplay(dateRange) {
    const subtitles = document.querySelectorAll('.chapter-subtitle');
    if (subtitles.length > 0 && dateRange.start && dateRange.end) {
      const startDate = new Date(dateRange.start);
      const endDate = new Date(dateRange.end);
      
      const startFormatted = startDate.toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
      const endFormatted = endDate.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'});
      
      subtitles.forEach((subtitle, index) => {
        const parentChapter = subtitle.closest('.story-chapter-content');
        if (parentChapter && parentChapter.id === 'morning-insights') {
          subtitle.textContent = `Performance snapshot for ${startFormatted} to ${endFormatted}`;
        } else if (parentChapter && parentChapter.id === 'cost-chronicles') {
          subtitle.textContent = `Cost analysis for ${startFormatted} to ${endFormatted}`;
        } else {
          subtitle.textContent = `Analysis for ${startFormatted} to ${endFormatted}`;
        }
      });
    }
  }

  showLoading() {
    const loadingElement = document.querySelector('.dashboard-loading');
    if (loadingElement) {
      loadingElement.style.display = 'flex';
    }
  }

  hideLoading() {
    const loadingElement = document.querySelector('.dashboard-loading');
    if (loadingElement) {
      loadingElement.style.display = 'none';
    }
  }

  showError(message) {
    const errorElement = document.querySelector('.dashboard-error');
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.style.display = 'block';
      setTimeout(() => {
        errorElement.style.display = 'none';
      }, 5000);
    }
  }

  updateFilters(filterType, filterValue) {
    // Handle filter updates
    console.log(`Filter updated: ${filterType} = ${filterValue}`);
    // Implement filter logic as needed
  }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Check if Chart.js is available
  if (typeof Chart !== 'undefined') {
    console.log('Chart.js loaded successfully');
    new DashboardManager();
  } else {
    console.error('Chart.js not loaded');
  }
});

// Export for global access
window.DashboardManager = DashboardManager;
window.theme = theme;
