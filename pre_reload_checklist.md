# Pre-Reload Checklist

## ✅ Before Deleting Database

### 1. Backup Current Data (Optional)
```bash
# If you want to keep current data as reference
python manage.py dumpdata > backup_before_reload.json
```

### 2. Verify Our Fixes Are in Place
- [ ] `data_engineering/utils/unit_conversion.py` - Uses `name__iexact` and checks consolidation
- [ ] `data_engineering/utils/product_consolidation.py` - Fixed `find_consolidated_product` method
- [ ] `data_engineering/loaders/database_loader.py` - Loads product types after sales data
- [ ] `apps/analytics/management/commands/regenerate_cost_history.py` - Uses unit conversion service

### 3. Clean Up Temporary Files
```bash
# Remove any temporary scripts we created
rm cleanup_wrong_conversions.py
rm fix_paprika_conversion.py
rm fix_missing_unit_conversions.py
```

## 🔄 Reload Process

### 1. Delete Database and Migrations
```bash
# Delete database (adjust path as needed)
rm db.sqlite3

# Delete migrations (keep __init__.py files)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
```

### 2. Recreate Database
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Load Data
```bash
# Run your data loading process
python manage.py initial_data_load
# or whatever command you use to load data
```

## ✅ After Reload

### 1. Run Validation Script
```bash
python validate_reload.py
```

### 2. Check for Issues
The validation script will check:
- [ ] Basic data integrity (products, conversions, consolidations, cost history)
- [ ] Consolidation rules working correctly
- [ ] Unit conversions present and correct
- [ ] No consolidated products have wrong conversions
- [ ] Product type classification working
- [ ] ProductCostHistory records have correct conversion factors

### 3. Quick Fixes (if needed)
If validation finds issues, run these commands:

```bash
# Missing consolidation rules
python manage.py shell -c "from data_engineering.utils.product_consolidation import ProductConsolidationService; ProductConsolidationService().load_legacy_consolidation_rules()"

# Missing unit conversions
python manage.py shell -c "from data_engineering.utils.unit_conversion import unit_conversion_service; unit_conversion_service.load_legacy_unit_conversions_and_standards()"

# Wrong product types
python manage.py fix_product_classifications

# Wrong cost history
python manage.py regenerate_cost_history

# Wrong conversions for consolidated products
python cleanup_wrong_conversions.py
```

## 🎯 Expected Results

After a successful reload, you should see:

### ✅ Validation Output
```
=== System Validation After Fresh Reload ===

1. Basic Data Integrity
✅ Products: [number]
✅ Unit Conversions: [number]
✅ Consolidation Rules: [number]
✅ Cost History Records: [number]

2. Consolidation Rules
✅ Ailes de Poulet au paprika → Ailes de Poulet Cru (Kg)
✅ Mayonnaise ARMANTI → Sauce Mayo
✅ Huile de tournesol → Huile de Palme
✅ All consolidation rules working correctly

3. Unit Conversions
✅ Paprika: 150.000000g
✅ Pommes de terre: 150.000000g
✅ Oignons: 120.000000g
✅ All key unit conversions present and correct

4. Consolidated Product Conversions
✅ No consolidated products have wrong conversions

5. Product Type Classification
✅ Product types: [X] resale, [Y] dish, [Z] not_sold
✅ Product type classification looks correct

6. Product Cost History
✅ No obvious wrong conversions in cost history

7. Overall System Health
🎉 SYSTEM VALIDATION PASSED - All systems working correctly!
```

## 🚨 If Issues Occur

### Common Issues and Solutions:

1. **"No products found"** - Data not loaded properly
2. **"Consolidation issues"** - Run consolidation rule loading
3. **"Conversion issues"** - Run unit conversion loading
4. **"Wrong conversions for consolidated products"** - Run cleanup script
5. **"Classification issues"** - Run product type fix command

### Debug Commands:
```bash
# Check what's in the database
python manage.py shell -c "from apps.restaurant_data.models import Product; print(f'Products: {Product.objects.count()}')"

# Check specific product
python manage.py shell -c "from apps.restaurant_data.models import Product; p = Product.objects.filter(name__icontains='paprika').first(); print(f'Found: {p.name if p else \"None\"}')"

# Check unit conversions
python manage.py shell -c "from apps.restaurant_data.models import UnitConversion; print(f'Conversions: {UnitConversion.objects.count()}')"
```
