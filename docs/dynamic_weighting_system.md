# Dynamic Weighting System for Ingredient Costing

## Overview

The dynamic weighting system automatically adjusts the weighting strategy for calculating ingredient costs based on the number of purchases available in the lookback period (90 days). This ensures optimal cost calculation regardless of purchase frequency.

## Weighting Strategies

### 1. Linear Weighting (≤ 3 purchases)
**When to use:** When you have 1-3 purchases in the 90-day period.

**How it works:**
- Uses simple linear decay weighting
- Newer purchases get proportionally higher weight
- Formula: `weight = (max_days - days_ago + 1) / (max_days + 1)`

**Example:**
- Purchase 1: 5 days ago, $2.50
- Purchase 2: 15 days ago, $2.30
- Result: More weight given to the $2.50 purchase

### 2. Adaptive Exponential Weighting (4-8 purchases)
**When to use:** When you have 4-8 purchases in the 90-day period.

**How it works:**
- Calculates average days between purchases
- Adjusts half-life based on purchase frequency:
  - Weekly purchases (≤7 days): 7-day half-life
  - Bi-weekly purchases (≤15 days): 15-day half-life  
  - Monthly purchases (≤30 days): 25-day half-life
  - Less frequent (>30 days): 35-day half-life
- Uses exponential decay: `weight = 2^(-days_ago / half_life)`

**Example:**
- If purchases are weekly, recent purchases get much higher weight
- If purchases are monthly, weighting is more balanced

### 3. Sophisticated Weighting (9+ purchases)
**When to use:** When you have 9+ purchases in the 90-day period.

**How it works:**
- Uses last 15 purchases maximum
- Combines multiple weighting factors:
  - Base weight: Exponential decay with 20-day half-life
  - Recency bonus: `1.5^(-position)` where position 0 is most recent
  - Volume factor: Higher volume purchases get up to 20% more weight
- Final weight: `base_weight × recency_bonus × volume_factor`

## Key Benefits

1. **Adaptive to Purchase Patterns:** Automatically adjusts to your actual purchase frequency
2. **Handles Sparse Data:** Works well even with few purchases
3. **Scales with Volume:** More sophisticated weighting for high-frequency ingredients
4. **Fallback Protection:** Always provides a reasonable cost estimate

## Configuration

The system uses these default parameters:
- **Lookback period:** 90 days
- **Minimum purchases for weighted average:** 2
- **Maximum recent purchases for sophisticated weighting:** 15

## Example Scenarios

### Scenario 1: New Ingredient (2 purchases)
```
Purchase 1: 5 days ago, $2.50
Purchase 2: 15 days ago, $2.30
Strategy: Linear weighting
Result: ~$2.45 (weighted toward recent purchase)
```

### Scenario 2: Regular Ingredient (6 purchases)
```
Purchase 1: 3 days ago, $2.60
Purchase 2: 8 days ago, $2.45
...
Strategy: Adaptive exponential (15-day half-life)
Result: ~$2.55 (balanced recent emphasis)
```

### Scenario 3: High-Frequency Ingredient (12 purchases)
```
Purchase 1: 1 day ago, $2.70
Purchase 2: 3 days ago, $2.65
...
Strategy: Sophisticated weighting
Result: ~$2.68 (strong recent emphasis + volume consideration)
```

## Implementation Details

The system is implemented in `apps/analytics/services/ingredient_costing.py` with these key methods:

- `_calculate_weighted_average_cost()`: Main entry point
- `_calculate_dynamic_weighted_average()`: Strategy selector
- `_apply_linear_weighting()`: For few purchases
- `_apply_adaptive_exponential_weighting()`: For moderate purchases
- `_apply_sophisticated_weighting()`: For many purchases
- `_get_fallback_cost()`: Fallback when no data available

## Testing

Run the test script to see the system in action:
```bash
python test_dynamic_weighting.py
```

This will demonstrate how different purchase scenarios result in different weighting strategies and cost calculations.
