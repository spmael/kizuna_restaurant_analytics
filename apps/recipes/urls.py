from django.urls import path

from . import views

app_name = "recipes"

urlpatterns = [
    path("", views.RecipeListView.as_view(), name="recipe_list"),
    path("create/", views.RecipeCreateView.as_view(), name="recipe_create"),
    path("<int:pk>/", views.RecipeDetailView.as_view(), name="recipe_detail"),
    path("<int:pk>/update/", views.RecipeUpdateView.as_view(), name="recipe_update"),
    path("<int:pk>/delete/", views.RecipeDeleteView.as_view(), name="recipe_delete"),
]
