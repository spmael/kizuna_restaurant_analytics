#!/usr/bin/env python
import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.restaurant_data.models import Product, ProductConsolidation
from data_engineering.utils.product_consolidation import product_consolidation_service

def create_correct_consolidation():
    """Create the correct consolidation rule for Ailes de Poulet"""
    
    print("=== CREATING CORRECT CONSOLIDATION RULE ===\n")
    
    # Get the products
    ailes_cru = Product.objects.filter(name="Ailes de Poulet Cru (Kg)").first()
    ailes_paprika = Product.objects.filter(name="Ailes de Poulet au paprika").first()
    
    if not ailes_cru:
        print(f"❌ Product 'Ailes de Poulet Cru (Kg)' not found")
        return
    
    if not ailes_paprika:
        print(f"❌ Product 'Ailes de Poulet au paprika' not found")
        return
    
    print(f"✅ Found products:")
    print(f"  Ailes Cru: {ailes_cru.name} (ID: {ailes_cru.id})")
    print(f"  Ailes Paprika: {ailes_paprika.name} (ID: {ailes_paprika.id})")
    
    # Check if rule already exists
    existing_rule = ProductConsolidation.objects.filter(
        primary_product=ailes_cru
    ).first()
    
    if existing_rule:
        print(f"\n⚠️  Rule already exists:")
        print(f"  Primary: {existing_rule.primary_product.name}")
        print(f"  Consolidated: {existing_rule.consolidated_product_names}")
        return
    
    # Create the correct rule
    print(f"\nCreating consolidation rule...")
    new_rule = ProductConsolidation.objects.create(
        primary_product=ailes_cru,
        consolidated_products=[ailes_paprika.id],
        similarity_scores={str(ailes_paprika.id): 1.0},
        consolidation_reason="recipe_ingredient_fix",
        confidence_score=1.0,
        is_verified=True,
        notes="Fixed consolidation rule - Ailes de Poulet Cru (Kg) should be primary"
    )
    
    print(f"✅ Created new rule:")
    print(f"  Primary: {new_rule.primary_product.name}")
    print(f"  Consolidated: {new_rule.consolidated_product_names}")
    
    # Test the fix
    print(f"\nTesting the consolidation:")
    test_result = product_consolidation_service.find_consolidated_product("Ailes de Poulet Cru (Kg)")
    print(f"  'Ailes de Poulet Cru (Kg)' → {test_result.name if test_result else 'None'}")
    
    test_result2 = product_consolidation_service.find_consolidated_product("Ailes de Poulet au paprika")
    print(f"  'Ailes de Poulet au paprika' → {test_result2.name if test_result2 else 'None'}")
    
    if test_result and test_result.name == "Ailes de Poulet Cru (Kg)":
        print(f"\n🎉 Consolidation rule created successfully!")
        print(f"   Now 'Ailes de Poulet Cru (Kg)' will be used as the primary product.")
    else:
        print(f"\n❌ Consolidation not working as expected")

if __name__ == "__main__":
    create_correct_consolidation()

