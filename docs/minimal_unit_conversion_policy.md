### Minimal Unit Conversion Policy

Last updated: 2025-09-02

Scope: Simplify unit conversions by relying on consistent metric units between purchases and recipes.

Principles:
- Products are purchased in standard metric units (kg, L/cl) and recipes specified in g/ml.
- Only essential metric conversions are supported by default. No heuristic fixer is used.

Supported default conversions (fallbacks when no DB rule exists):
- kg ↔ g (1000, 0.001)
- L ↔ ml (1000, 0.001)
- cl ↔ ml (10, 0.1)
- unit ↔ pc (1, 1)

What was removed/simplified:
- ConversionFixer usage during transformation has been disabled.
- Product-specific bottle→gram type rules are not required by default; add explicit DB rules only for rare exceptions.

Recommended data practices:
- Keep product units consistent (e.g., kg for solids, L/cl for liquids).
- Specify recipe units in g or ml. Use pc/unit only for truly countable items.
- If a product requires a special mapping (e.g., herb bunch), add an explicit `UnitConversion` DB rule for that specific product.

Impact:
- ETL is simpler and avoids heuristic DB updates.
- Costs computed from purchases (kg/L) to recipes (g/ml) work with minimal fallbacks.
