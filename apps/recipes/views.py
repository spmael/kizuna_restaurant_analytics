from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import RecipeForm
from .models import Recipe


class RecipeListView(LoginRequiredMixin, ListView):
    """View for listing recipes."""

    model = Recipe
    template_name = "recipes/recipe_list.html"
    context_object_name = "recipes"
    paginate_by = 20

    def get_queryset(self):
        queryset = Recipe.objects.filter(is_active=True)

        # Search functionality
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(dish_name__icontains=search_query)
                | Q(dish_name_fr__icontains=search_query)
                | Q(dish_name_en__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        return queryset.order_by("dish_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        return context


class RecipeDetailView(LoginRequiredMixin, DetailView):
    """View for displaying recipe details."""

    model = Recipe
    template_name = "recipes/recipe_detail.html"
    context_object_name = "recipe"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recipe = self.get_object()
        context["ingredients"] = recipe.ingredients.select_related(
            "ingredient", "unit_of_recipe"
        )
        return context


class RecipeCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new recipe."""

    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/recipe_form.html"
    success_url = reverse_lazy("recipes:recipe_list")

    def form_valid(self, form):
        messages.success(self.request, _("Recipe created successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating recipe. Please check the form."))
        return super().form_invalid(form)


class RecipeUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating a recipe."""

    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/recipe_form.html"
    success_url = reverse_lazy("recipes:recipe_list")

    def form_valid(self, form):
        messages.success(self.request, _("Recipe updated successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error updating recipe. Please check the form."))
        return super().form_invalid(form)


class RecipeDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting a recipe."""

    model = Recipe
    template_name = "recipes/recipe_confirm_delete.html"
    success_url = reverse_lazy("recipes:recipe_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Recipe deleted successfully."))
        return super().delete(request, *args, **kwargs)
