from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Column, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    Product,
    ProductConsolidation,
    Purchase,
    PurchasesCategory,
    Sales,
    SalesCategory,
    UnitOfMeasure,
)
from apps.recipes.models import Recipe, RecipeIngredient


class ProductForm(forms.ModelForm):
    """Form for Product model."""

    class Meta:
        model = Product
        fields = [
            "name",
            "name_fr",
            "name_en",
            "purchase_category",
            "sales_category",
            "unit_of_measure",
            "current_selling_price",
            "current_cost_per_unit",
            "current_stock",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "name_fr": forms.TextInput(attrs={"class": "form-control"}),
            "name_en": forms.TextInput(attrs={"class": "form-control"}),
            "purchase_category": forms.Select(attrs={"class": "form-select"}),
            "sales_category": forms.Select(attrs={"class": "form-select"}),
            "unit_of_measure": forms.Select(attrs={"class": "form-select"}),
            "current_selling_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "current_cost_per_unit": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "current_stock": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-md-6 mb-3"),
                Column("purchase_category", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("name_fr", css_class="form-group col-md-6 mb-3"),
                Column("sales_category", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("name_en", css_class="form-group col-md-6 mb-3"),
                Column("unit_of_measure", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("current_selling_price", css_class="form-group col-md-4 mb-3"),
                Column("current_cost_per_unit", css_class="form-group col-md-4 mb-3"),
                Column("current_stock", css_class="form-group col-md-4 mb-3"),
            ),
            "description",
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Product"), css_class="btn btn-primary"),
                    css_class="col-md-6",
                ),
                Column(
                    Button(
                        "cancel",
                        _("Cancel"),
                        css_class="btn btn-secondary",
                        onclick="history.back()",
                    ),
                    css_class="col-md-6",
                ),
            ),
        )


class PurchaseForm(forms.ModelForm):
    """Form for Purchase model."""

    class Meta:
        model = Purchase
        fields = [
            "purchase_date",
            "product",
            "quantity_purchased",
            "total_cost",
        ]
        widgets = {
            "purchase_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity_purchased": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "total_cost": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("purchase_date", css_class="form-group col-md-6 mb-3"),
                Column("product", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("quantity_purchased", css_class="form-group col-md-6 mb-3"),
                Column("total_cost", css_class="form-group col-md-6 mb-3"),
            ),
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Purchase"), css_class="btn btn-primary"),
                    css_class="col-md-6",
                ),
                Column(
                    Button(
                        "cancel",
                        _("Cancel"),
                        css_class="btn btn-secondary",
                        onclick="history.back()",
                    ),
                    css_class="col-md-6",
                ),
            ),
        )


class SalesForm(forms.ModelForm):
    """Form for Sales model."""

    class Meta:
        model = Sales
        fields = [
            "sale_date",
            "order_number",
            "product",
            "quantity_sold",
            "unit_sale_price",
            "total_sale_price",
            "customer",
            "cashier",
        ]
        widgets = {
            "sale_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "order_number": forms.TextInput(attrs={"class": "form-control"}),
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity_sold": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "unit_sale_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "total_sale_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "customer": forms.TextInput(attrs={"class": "form-control"}),
            "cashier": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("sale_date", css_class="form-group col-md-6 mb-3"),
                Column("order_number", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("product", css_class="form-group col-md-6 mb-3"),
                Column("quantity_sold", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("unit_sale_price", css_class="form-group col-md-4 mb-3"),
                Column("total_sale_price", css_class="form-group col-md-4 mb-3"),
                Column("customer", css_class="form-group col-md-4 mb-3"),
            ),
            "cashier",
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Sale"), css_class="btn btn-primary"),
                    css_class="col-md-6",
                ),
                Column(
                    Button(
                        "cancel",
                        _("Cancel"),
                        css_class="btn btn-secondary",
                        onclick="history.back()",
                    ),
                    css_class="col-md-6",
                ),
            ),
        )





class ProductConsolidationForm(forms.ModelForm):
    """Form for ProductConsolidation model."""

    class Meta:
        model = ProductConsolidation
        fields = [
            "primary_product",
            "consolidated_products",
            "consolidation_reason",
            "confidence_score",
            "is_verified",
            "notes",
        ]
        widgets = {
            "primary_product": forms.Select(attrs={"class": "form-select"}),
            "consolidated_products": forms.SelectMultiple(
                attrs={"class": "form-select"}
            ),
            "consolidation_reason": forms.TextInput(attrs={"class": "form-control"}),
            "confidence_score": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.001", "min": "0", "max": "1"}
            ),
            "is_verified": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("primary_product", css_class="form-group col-md-6 mb-3"),
                Column("consolidation_reason", css_class="form-group col-md-6 mb-3"),
            ),
            "consolidated_products",
            Row(
                Column("confidence_score", css_class="form-group col-md-6 mb-3"),
                Column("is_verified", css_class="form-group col-md-6 mb-3"),
            ),
            "notes",
            HTML("<hr>"),
            Row(
                Column(
                    Submit(
                        "submit", _("Save Consolidation"), css_class="btn btn-primary"
                    ),
                    css_class="col-md-6",
                ),
                Column(
                    Button(
                        "cancel",
                        _("Cancel"),
                        css_class="btn btn-secondary",
                        onclick="history.back()",
                    ),
                    css_class="col-md-6",
                ),
            ),
        )


class PurchasesCategoryForm(forms.ModelForm):
    """Form for PurchasesCategory model."""

    class Meta:
        model = PurchasesCategory
        fields = [
            "name",
            "name_fr",
            "name_en",
            "description",
            "sort_order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "name_fr": forms.TextInput(attrs={"class": "form-control"}),
            "name_en": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-md-6 mb-3"),
                Column("sort_order", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("name_fr", css_class="form-group col-md-6 mb-3"),
                Column("name_en", css_class="form-group col-md-6 mb-3"),
            ),
            "description",
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Category"), css_class="btn btn-primary"),
                    css_class="col-md-6",
                ),
                Column(
                    Button(
                        "cancel",
                        _("Cancel"),
                        css_class="btn btn-secondary",
                        onclick="history.back()",
                    ),
                    css_class="col-md-6",
                ),
            ),
        )


class SalesCategoryForm(forms.ModelForm):
    """Form for SalesCategory model."""

    class Meta:
        model = SalesCategory
        fields = [
            "name",
            "name_fr",
            "name_en",
            "description",
            "sort_order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "name_fr": forms.TextInput(attrs={"class": "form-control"}),
            "name_en": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-md-6 mb-3"),
                Column("sort_order", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("name_fr", css_class="form-group col-md-6 mb-3"),
                Column("name_en", css_class="form-group col-md-6 mb-3"),
            ),
            "description",
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Category"), css_class="btn btn-primary"),
                    css_class="col-md-6",
                ),
                Column(
                    Button(
                        "cancel",
                        _("Cancel"),
                        css_class="btn btn-secondary",
                        onclick="history.back()",
                    ),
                    css_class="col-md-6",
                ),
            ),
        )


class UnitOfMeasureForm(forms.ModelForm):
    """Form for UnitOfMeasure model."""

    class Meta:
        model = UnitOfMeasure
        fields = [
            "name",
            "abbreviation",
            "name_fr",
            "name_en",
            "description",
            "sort_order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "abbreviation": forms.TextInput(attrs={"class": "form-control"}),
            "name_fr": forms.TextInput(attrs={"class": "form-control"}),
            "name_en": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-md-6 mb-3"),
                Column("abbreviation", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("name_fr", css_class="form-group col-md-6 mb-3"),
                Column("name_en", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("sort_order", css_class="form-group col-md-6 mb-3"),
                Column(HTML(""), css_class="form-group col-md-6 mb-3"),
            ),
            "description",
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Unit"), css_class="btn btn-primary"),
                    css_class="col-md-6",
                ),
                Column(
                    Button(
                        "cancel",
                        _("Cancel"),
                        css_class="btn btn-secondary",
                        onclick="history.back()",
                    ),
                    css_class="col-md-6",
                ),
            ),
        )
