from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Column, Layout, Row, Submit
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Recipe, RecipeIngredient


class RecipeForm(forms.ModelForm):
    """Form for Recipe model."""

    class Meta:
        model = Recipe
        fields = [
            "dish_name",
            "dish_name_fr",
            "dish_name_en",
            "description",
        ]
        widgets = {
            "dish_name": forms.TextInput(attrs={"class": "form-control"}),
            "dish_name_fr": forms.TextInput(attrs={"class": "form-control"}),
            "dish_name_en": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("dish_name", css_class="form-group col-md-6 mb-3"),
                Column("dish_name_fr", css_class="form-group col-md-6 mb-3"),
            ),
            Row(
                Column("dish_name_en", css_class="form-group col-md-6 mb-3"),
                Column("description", css_class="form-group col-md-6 mb-3"),
            ),
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Recipe"), css_class="btn btn-primary"),
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


class RecipeIngredientForm(forms.ModelForm):
    """Form for RecipeIngredient model."""

    class Meta:
        model = RecipeIngredient
        fields = [
            "ingredient",
            "quantity",
            "main_ingredient",
            "unit_of_recipe",
        ]
        widgets = {
            "ingredient": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "main_ingredient": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "unit_of_recipe": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column("ingredient", css_class="form-group col-md-6 mb-3"),
                Column("quantity", css_class="form-group col-md-3 mb-3"),
                Column("unit_of_recipe", css_class="form-group col-md-3 mb-3"),
            ),
            Row(
                Column("main_ingredient", css_class="form-group col-md-12 mb-3"),
            ),
            HTML("<hr>"),
            Row(
                Column(
                    Submit("submit", _("Save Ingredient"), css_class="btn btn-primary"),
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
