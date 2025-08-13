/**
 * African-Inspired Restaurant Analytics Theme Management
 * Centralized JavaScript theme configuration and utilities
 */

const theme = {
  // === COLOR PALETTE ===
  colors: {
    primary: getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim(),
    secondary: getComputedStyle(document.documentElement).getPropertyValue('--color-secondary').trim(),
    accent: getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim(),
    success: getComputedStyle(document.documentElement).getPropertyValue('--color-success').trim(),
    warning: getComputedStyle(document.documentElement).getPropertyValue('--color-warning').trim(),
    error: getComputedStyle(document.documentElement).getPropertyValue('--color-error').trim(),
    info: getComputedStyle(document.documentElement).getPropertyValue('--color-info').trim(),
    
    // Background colors
    bgPrimary: getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim(),
    bgSecondary: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim(),
    bgTertiary: getComputedStyle(document.documentElement).getPropertyValue('--bg-tertiary').trim(),
    
    // Text colors
    textPrimary: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim(),
    textSecondary: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
    textLight: getComputedStyle(document.documentElement).getPropertyValue('--text-light').trim(),
    textMuted: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim(),
    textHeading: getComputedStyle(document.documentElement).getPropertyValue('--text-heading').trim(),
  },

  // === CHART CONFIGURATIONS ===
  chartDefaults: {
    responsive: true,
    maintainAspectRatio: false,
    fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim(),
    
    plugins: {
      legend: {
        labels: {
          fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim(),
          color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
          usePointStyle: true,
          padding: 20,
          font: {
            size: 12,
            weight: '500'
          }
        }
      },
      tooltip: {
        backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim(),
        titleColor: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim(),
        bodyColor: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim(),
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
          color: getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() + '20'
        },
        ticks: {
          color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
          fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim(),
          font: {
            size: 11
          }
        }
      },
      y: {
        grid: {
          color: getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() + '20'
        },
        ticks: {
          color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
          fontFamily: getComputedStyle(document.documentElement).getPropertyValue('--font-family-primary').trim(),
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
      borderWidth: 0,
      borderRadius: 4,
      borderSkipped: false
    },
    
    pie: {
      borderWidth: 2,
      borderColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim()
    },
    
    doughnut: {
      borderWidth: 2,
      borderColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary').trim(),
      cutout: '60%'
    },
    
    area: {
      borderWidth: 2,
      tension: 0.4,
      fill: true
    }
  },

  // === COLOR PALETTES FOR CHARTS ===
  colorPalettes: {
    primary: [
      '#E07A5F', // Warm Terracotta
      '#F2B670', // Golden Sunset
      '#6B8E3D', // Savanna Green
      '#81654F', // Clay Brown
      '#F18F01', // Sunset Orange
      '#C73E1D', // Desert Rose
    ],
    
    pastel: [
      '#F4A261', // Light Terracotta
      '#F7D794', // Light Golden
      '#A8D5BA', // Light Green
      '#B8A9A9', // Light Brown
      '#F4B942', // Light Orange
      '#E8A87C', // Light Rose
    ],
    
    gradient: [
      'linear-gradient(135deg, #E07A5F 0%, #F2B670 100%)',
      'linear-gradient(135deg, #6B8E3D 0%, #A8D5BA 100%)',
      'linear-gradient(135deg, #81654F 0%, #B8A9A9 100%)',
      'linear-gradient(135deg, #F18F01 0%, #F4B942 100%)',
      'linear-gradient(135deg, #C73E1D 0%, #E8A87C 100%)',
    ]
  }
};

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
          label: 'Orders',
          data: data.values,
          backgroundColor: this.theme.colors.secondary,
          borderColor: this.theme.colors.secondary,
          ...this.theme.chartTypes.bar
        }]
      },
      options: {
        ...this.theme.chartDefaults,
        plugins: {
          ...this.theme.chartDefaults.plugins,
          title: {
            display: true,
            text: 'Peak Hours',
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
      ...this.createBaseConfig('line'),
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Customers',
          data: data.values,
          borderColor: this.theme.colors.success,
          backgroundColor: this.theme.colors.success + '30',
          fill: true,
          ...this.theme.chartTypes.area
        }]
      },
      options: {
        ...this.theme.chartDefaults,
        plugins: {
          ...this.theme.chartDefaults.plugins,
          title: {
            display: true,
            text: 'Customer Flow',
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
 * Utility Functions
 */
const themeUtils = {
  /**
   * Format currency
   */
  formatCurrency: (amount, currency = 'FCFA') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  },

  /**
   * Format percentage
   */
  formatPercentage: (value, decimals = 1) => {
    return value.toFixed(decimals) + '%';
  },

  /**
   * Calculate percentage change
   */
  calculateChange: (current, previous) => {
    if (previous === 0) return 0;
    return ((current - previous) / previous) * 100;
  },

  /**
   * Get change indicator class
   */
  getChangeClass: (change) => {
    if (change > 0) return 'positive';
    if (change < 0) return 'negative';
    return 'neutral';
  },

  /**
   * Get status badge class
   */
  getStatusClass: (value, thresholds) => {
    if (value >= thresholds.excellent) return 'success';
    if (value >= thresholds.good) return 'info';
    if (value >= thresholds.warning) return 'warning';
    return 'error';
  },

  /**
   * Debounce function
   */
  debounce: (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  /**
   * Throttle function
   */
  throttle: (func, limit) => {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
};

/**
 * Dashboard Component Manager
 */
class DashboardManager {
  constructor() {
    this.chartFactory = new ChartConfigFactory();
    this.charts = new Map();
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.initializeCharts();
    this.setupResponsiveHandling();
  }

  setupEventListeners() {
    // Date range picker
    const dateRangePicker = document.getElementById('dateRangePicker');
    if (dateRangePicker) {
      dateRangePicker.addEventListener('change', this.handleDateRangeChange.bind(this));
    }

    // Filter controls
    const filterControls = document.querySelectorAll('.filter-select');
    filterControls.forEach(control => {
      control.addEventListener('change', this.handleFilterChange.bind(this));
    });

    // Chart type toggles
    const chartToggles = document.querySelectorAll('.chart-toggle');
    chartToggles.forEach(toggle => {
      toggle.addEventListener('click', this.handleChartToggle.bind(this));
    });
  }

  initializeCharts() {
    // Initialize all chart canvases
    const chartCanvases = document.querySelectorAll('[data-chart-type]');
    chartCanvases.forEach(canvas => {
      const chartType = canvas.dataset.chartType;
      const chartData = this.getChartData(canvas.dataset.chartId);
      
      if (chartData) {
        const config = this.chartFactory[`create${chartType}Chart`](chartData);
        const chart = new Chart(canvas.getContext('2d'), config);
        this.charts.set(canvas.dataset.chartId, chart);
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

  handleDateRangeChange(event) {
    const dateRange = event.target.value;
    this.updateDashboardData(dateRange);
  }

  handleFilterChange(event) {
    const filterType = event.target.dataset.filterType;
    const filterValue = event.target.value;
    this.updateDashboardData(null, { [filterType]: filterValue });
  }

  handleChartToggle(event) {
    const chartId = event.target.dataset.chartId;
    const chartType = event.target.dataset.chartType;
    this.updateChartType(chartId, chartType);
  }

  updateDashboardData(dateRange, filters = {}) {
    // Show loading state
    this.showLoading();
    
    // Simulate API call
    setTimeout(() => {
      this.refreshCharts();
      this.hideLoading();
    }, 1000);
  }

  updateChartType(chartId, chartType) {
    const chart = this.charts.get(chartId);
    if (chart) {
      chart.destroy();
    }
    
    const canvas = document.querySelector(`[data-chart-id="${chartId}"]`);
    const chartData = this.getChartData(chartId);
    
    if (chartData) {
      const config = this.chartFactory[`create${chartType}Chart`](chartData);
      const newChart = new Chart(canvas.getContext('2d'), config);
      this.charts.set(chartId, newChart);
    }
  }

  refreshCharts() {
    this.charts.forEach((chart, chartId) => {
      const chartData = this.getChartData(chartId);
      if (chartData) {
        chart.data.labels = chartData.labels;
        chart.data.datasets[0].data = chartData.values;
        chart.update();
      }
    });
  }

  showLoading() {
    const loadingOverlays = document.querySelectorAll('.loading-overlay');
    loadingOverlays.forEach(overlay => {
      overlay.style.display = 'flex';
    });
  }

  hideLoading() {
    const loadingOverlays = document.querySelectorAll('.loading-overlay');
    loadingOverlays.forEach(overlay => {
      overlay.style.display = 'none';
    });
  }

  setupResponsiveHandling() {
    const resizeHandler = themeUtils.debounce(() => {
      this.charts.forEach(chart => {
        chart.resize();
      });
    }, 250);
    
    window.addEventListener('resize', resizeHandler);
  }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  if (typeof Chart !== 'undefined') {
    window.dashboardManager = new DashboardManager();
  }
});

// Export for use in other modules
window.theme = theme;
window.themeUtils = themeUtils;
window.ChartConfigFactory = ChartConfigFactory;
