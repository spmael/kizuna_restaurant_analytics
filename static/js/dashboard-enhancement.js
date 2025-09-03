// Progressive enhancement for SSR dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Only enhance if JavaScript is available
    if (typeof window !== 'undefined') {
        initializeDashboardEnhancement();
    }
});

function initializeDashboardEnhancement() {
    // Initialize all dashboard enhancements
    enhanceCharts();
    setupChapterNavigation();
    setupLoadingStates();
    
    // Note: Removed auto-update functionality since metrics API was removed
    // Dashboard data is now fully server-side rendered (SSR)
}

// Global modal instance variable
let currentModalInstance = null;

// Metric Information Display
function showMetricInfo(metricType) {
    console.log('showMetricInfo called with:', metricType);
    
    const modal = document.getElementById('metricInfoModal');
    const title = document.getElementById('metricInfoTitle');
    const body = document.getElementById('metricInfoBody');
    
    if (!modal || !title || !body) {
        console.error('Modal elements not found');
        return;
    }
    
    console.log('Modal elements found, proceeding...');
    
    let modalTitle = '';
    let modalContent = '';
    
    switch(metricType) {
        case 'revenue':
            modalTitle = 'Total Revenue & Growth';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-coins text-primary me-2"></i>Total Revenue</h6>
                    <p>Total sales revenue for the selected period in FCFA (Franc CFA). This includes all food, beverage, and service sales.</p>
                    
                    <h6><i class="fas fa-chart-line text-success me-2"></i>Period-over-Period Growth</h6>
                    <p>Percentage change in revenue compared to the previous equivalent period:</p>
                    <ul>
                        <li><strong>7 days:</strong> Current week vs previous week</li>
                        <li><strong>30 days:</strong> Current month vs previous month</li>
                        <li><strong>90 days:</strong> Current quarter vs previous quarter</li>
                    </ul>
                    
                    <h6><i class="fas fa-lightbulb text-warning me-2"></i>What This Means</h6>
                    <p><strong>Positive growth:</strong> Your business is expanding and generating more revenue</p>
                    <p><strong>Negative growth:</strong> Revenue is declining, may need attention to sales strategies</p>
                    <p><strong>Stable (0%):</strong> Revenue is consistent, good for business planning</p>
                    
                    <p class="text-muted"><small>Growth rates help identify trends and seasonal patterns in your restaurant's performance.</small></p>
                </div>
            `;
            break;
            
        case 'orders':
            modalTitle = 'Total Orders & Average Order Value';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-shopping-cart text-success me-2"></i>Total Orders</h6>
                    <p>Total number of orders placed during the selected period. Each order represents a customer transaction.</p>
                    
                    <h6><i class="fas fa-calculator text-info me-2"></i>Average Order Value</h6>
                    <p>Average revenue generated per order (Total Revenue ÷ Total Orders).</p>
                    
                    <h6><i class="fas fa-lightbulb text-warning me-2"></i>What This Means</h6>
                    <p><strong>High order count + Low average:</strong> Many small orders, consider upselling</p>
                    <p><strong>Low order count + High average:</strong> Fewer but high-value customers</p>
                    <p><strong>Balanced:</strong> Good mix of order volume and value</p>
                    
                    <p class="text-muted"><small>This metric helps optimize menu pricing and identify upselling opportunities.</small></p>
                </div>
            `;
            break;
            
        case 'customers':
            modalTitle = 'Total Customers & Average Customer Value';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-users text-info me-2"></i>Total Customers</h6>
                    <p>Total number of unique customers who made purchases during the selected period. A customer can place multiple orders but is counted once here.</p>
                    
                    <h6><i class="fas fa-arrows-rotate text-success me-2"></i>Change vs Last Period</h6>
                    <p>Shows how the number of customers changed compared to the previous equivalent period (7/30/90 days). Positive means more customers, negative means fewer.</p>
                    
                    <h6><i class="fas fa-calculator text-primary me-2"></i>Average Customer Value</h6>
                    <p>Average revenue generated per unique customer for the period.</p>
                    <ul>
                        <li><strong>Formula:</strong> Total Revenue ÷ Total Customers</li>
                        <li><strong>Example:</strong> 1,500,000 FCFA revenue and 300 customers → 5,000 FCFA per customer</li>
                    </ul>
                    
                    <h6><i class="fas fa-lightbulb text-warning me-2"></i>What This Means</h6>
                    <p><strong>High customer count + Low average:</strong> Many customers with small purchases</p>
                    <p><strong>Low customer count + High average:</strong> Fewer but high-value customers</p>
                    <p><strong>Balanced:</strong> Good mix of customer volume and value</p>
                    
                    <p class="text-muted"><small>This mirrors the customer metrics in the Revenue chapter and helps you assess growth and customer value quality over time.</small></p>
                </div>
            `;
            break;
        
        // Morning chapter specific: Customer Flow
        case 'customer_flow':
            modalTitle = 'Customer Flow';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-people-arrows text-info me-2"></i>What is Customer Flow?</h6>
                    <p>Total number of customers served during the period, regardless of whether they are registered or walk-in. This reflects traffic intensity.</p>
                    
                    <h6><i class="fas fa-arrows-rotate text-success me-2"></i>Change vs Last Period</h6>
                    <p>Compares the current period's customer count with the previous equivalent period (7/30/90 days) to reveal demand trends.</p>
                    
                    <h6><i class="fas fa-lightbulb text-warning me-2"></i>Use It For</h6>
                    <ul>
                        <li>Staffing decisions during busy/slow periods</li>
                        <li>Evaluating promotions or events impact</li>
                        <li>Tracking seasonality</li>
                    </ul>
                </div>
            `;
            break;
        
        // Morning chapter specific: Registered Customers
        case 'registered_customers':
            modalTitle = 'Registered Customers';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-user-check text-primary me-2"></i>Who Are Registered Customers?</h6>
                    <p>Customers linked to an account or identifiable profile (loyalty members, repeat customers).</p>
                    
                    <h6><i class="fas fa-chart-line text-success me-2"></i>Why It Matters</h6>
                    <ul>
                        <li>Higher retention and lifetime value</li>
                        <li>Supports targeted offers and CRM</li>
                        <li>Indicator of loyalty program effectiveness</li>
                    </ul>
                    
                    <h6><i class="fas fa-lightbulb text-warning me-2"></i>Tip</h6>
                    <p>Encourage account creation with small incentives (discounts, points) to grow this segment.</p>
                </div>
            `;
            break;
        
        // Morning chapter specific: Walk-in Customers
        case 'walk_in_customers':
            modalTitle = 'Walk-in Customers';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-user-clock text-secondary me-2"></i>Who Are Walk-in Customers?</h6>
                    <p>New or casual customers not linked to an account. They represent acquisition and spontaneous demand.</p>
                    
                    <h6><i class="fas fa-bullseye text-info me-2"></i>Why It Matters</h6>
                    <ul>
                        <li>Indicates reach and visibility</li>
                        <li>Source of potential new loyal customers</li>
                        <li>Useful for measuring street traffic and location impact</li>
                    </ul>
                    
                    <h6><i class="fas fa-lightbulb text-warning me-2"></i>Tip</h6>
                    <p>Convert walk-ins to registered customers with first-visit incentives or sign-up prompts.</p>
                </div>
            `;
            break;
            
        case 'performance':
            modalTitle = 'Performance Grade & Restaurant Classification';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-star text-warning me-2"></i>Performance Grade</h6>
                    <p>Your restaurant's performance rating based on daily revenue compared to industry benchmarks:</p>
                    <div class="grade-explanation">
                        <ul>
                            <li><span class="badge bg-danger">F</span> Below 50% of target</li>
                            <li><span class="badge bg-warning">D</span> 50-60% of target</li>
                            <li><span class="badge bg-info">C</span> 60-70% of target</li>
                            <li><span class="badge bg-primary">B</span> 70-85% of target</li>
                            <li><span class="badge bg-success">A</span> 85-100% of target</li>
                            <li><span class="badge bg-warning text-dark">A+</span> Above 100% of target</li>
                        </ul>
                    </div>
                    
                    <h6><i class="fas fa-building text-secondary me-2"></i>Restaurant Size Classification</h6>
                    <p>Based on your average daily revenue, you are classified as:</p>
                    <div class="size-classification">
                        <ul>
                            <li><span class="badge bg-info">Small Restaurant</span> Below 150,000 FCFA/day</li>
                            <li><span class="badge bg-primary">Medium Restaurant</span> 150,000 - 300,000 FCFA/day</li>
                            <li><span class="badge bg-success">Large Restaurant</span> Above 300,000 FCFA/day</li>
                        </ul>
                    </div>
                    
                    <h6><i class="fas fa-chart-line text-success me-2"></i>How It's Calculated</h6>
                    <p>The performance grade is calculated by comparing your daily revenue against industry benchmarks for your restaurant size category in Cameroon:</p>
                    <ul>
                        <li><strong>Small Restaurant:</strong> Target range: 50,000 - 150,000 FCFA/day</li>
                        <li><strong>Medium Restaurant:</strong> Target range: 150,000 - 300,000 FCFA/day</li>
                        <li><strong>Large Restaurant:</strong> Target range: 300,000 - 500,000 FCFA/day</li>
                    </ul>
                    
                    <p class="text-muted"><small>Your grade reflects how well you're performing within your category's target range. Exceeding 100% means you're outperforming industry standards!</small></p>
                </div>
            `;
            break;
        
        // Cost chapter metrics
        case 'food_cost':
            modalTitle = 'Food Cost %';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-percentage text-warning me-2"></i>Food Cost %</h6>
                    <p>The percentage of sales spent on ingredients (COGS ÷ Revenue × 100).</p>
                    <ul>
                        <li><strong>Excellent:</strong> ≤ 30%</li>
                        <li><strong>Good:</strong> 30–35%</li>
                        <li><strong>Review:</strong> > 35%</li>
                    </ul>
                    <p class="text-muted"><small>Lower food cost indicates better purchasing, portion control, and pricing discipline.</small></p>
                </div>
            `;
            break;
        case 'waste_cost':
            modalTitle = 'Waste Cost %';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-trash text-danger me-2"></i>Waste Cost %</h6>
                    <p>Estimated percentage of sales lost to waste and spoilage.</p>
                    <ul>
                        <li><strong>Excellent:</strong> ≤ 2%</li>
                        <li><strong>Good:</strong> 2–3%</li>
                        <li><strong>High:</strong> > 3% (optimize prep and forecasting)</li>
                    </ul>
                    <p class="text-muted"><small>Track prep quantities, storage, and FIFO to control waste.</small></p>
                </div>
            `;
            break;
        case 'overall_cost_performance':
            modalTitle = 'Overall Cost Performance';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-tachometer-alt text-primary me-2"></i>Overall Performance</h6>
                    <p>Composite score from food cost, waste, and consistency. Higher is better.</p>
                    <p>Grades summarize whether your costs are controlled across key drivers.</p>
                </div>
            `;
            break;
        case 'gross_profit':
            modalTitle = 'Gross Profit';
            modalContent = `
                <div class="metric-info-content">
                    <h6><i class="fas fa-coins text-success me-2"></i>Gross Profit</h6>
                    <p>Revenue minus COGS. Indicates how much is left to cover labor and overhead.</p>
                    <p><strong>Profit Margin =</strong> Gross Profit ÷ Revenue × 100.</p>
                </div>
            `;
            break;
            
        default:
            modalTitle = 'Metric Information';
            modalContent = '<p>Information about this metric is not available.</p>';
    }
    
    title.textContent = modalTitle;
    body.innerHTML = modalContent;
    
    console.log('Content set, showing modal...');
    
    // Close any existing modal first
    if (currentModalInstance) {
        currentModalInstance.hide();
        currentModalInstance = null;
    }
    
    // Ensure modal is a direct child of body to avoid pointer-events and stacking issues
    if (modal.parentElement !== document.body) {
        document.body.appendChild(modal);
    }
    
    // Use Bootstrap 5's native modal functionality
    try {
        // Create a new Bootstrap modal instance
        const bsModal = new bootstrap.Modal(modal, {
            backdrop: true,
            keyboard: true,
            focus: true
        });
        
        // Store the instance globally
        currentModalInstance = bsModal;
        
        // Safety: wire explicit click handlers for close buttons
        const headerCloseBtn = modal.querySelector('.modal-header .btn-close[data-bs-dismiss="modal"]');
        const footerCloseBtn = modal.querySelector('.modal-footer [data-bs-dismiss="modal"]');
        [headerCloseBtn, footerCloseBtn].forEach(function(btn) {
            if (btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    try { bsModal.hide(); } catch(_) {}
                }, { once: true });
            }
        });
        
        // Delegate: close on any element inside modal with data-bs-dismiss="modal"
        modal.addEventListener('click', function(ev) {
            const target = ev.target.closest('[data-bs-dismiss="modal"]');
            if (target) {
                try { bsModal.hide(); } catch(_) {}
            }
        });
        
        // Cleanup when hidden
        modal.addEventListener('hidden.bs.modal', function() {
            console.log('Modal hidden event triggered');
            currentModalInstance = null;
        });
        
        // Show the modal
        bsModal.show();
        console.log('Modal show() called successfully');
        
    } catch (error) {
        console.error('Error showing modal:', error);
        // Fallback to fallback modal
        createFallbackModal();
        const fallbackContent = document.getElementById('fallbackModalContent');
        if (fallbackContent) {
            fallbackContent.innerHTML = modalContent;
        }
    }
}

// Export for potential use in other scripts
window.DashboardEnhancement = {
    initialize: initializeDashboardEnhancement,
    formatCurrency: formatCurrency
};

// Fallback modal if Bootstrap fails
function createFallbackModal() {
    console.log('Creating fallback modal...');
    
    // Remove existing modal if any
    const existingModal = document.getElementById('fallbackModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create simple modal
    const modalHTML = `
        <div id="fallbackModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        ">
            <div style="
                background: white;
                padding: 20px;
                border-radius: 10px;
                max-width: 600px;
                max-height: 80vh;
                overflow-y: auto;
                position: relative;
            ">
                <button onclick="closeFallbackModal()" style="
                    position: absolute;
                    top: 10px;
                    right: 15px;
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #666;
                ">&times;</button>
                <div id="fallbackModalContent"></div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Add click outside to close
    document.getElementById('fallbackModal').addEventListener('click', (e) => {
        if (e.target.id === 'fallbackModal') {
            closeFallbackModal();
        }
    });
}

function closeFallbackModal() {
    const modal = document.getElementById('fallbackModal');
    if (modal) {
        modal.remove();
    }
}

// Global function for fallback modal
window.closeFallbackModal = closeFallbackModal;

// Make functions global
window.showMetricInfo = showMetricInfo;
