from django.urls import path

from . import views

app_name = "restaurant_data"

urlpatterns = [
    # Product management
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/add/", views.ProductCreateView.as_view(), name="product_add"),
    path(
        "products/<uuid:pk>/", views.ProductDetailView.as_view(), name="product_detail"
    ),
    path(
        "products/<uuid:pk>/edit/",
        views.ProductUpdateView.as_view(),
        name="product_edit",
    ),
    path(
        "products/<uuid:pk>/delete/",
        views.ProductDeleteView.as_view(),
        name="product_delete",
    ),
    # Purchases management
    path("purchases/", views.PurchaseListView.as_view(), name="purchase_list"),
    path("purchases/add/", views.PurchaseCreateView.as_view(), name="purchase_add"),
    path(
        "purchases/<uuid:pk>/",
        views.PurchaseDetailView.as_view(),
        name="purchase_detail",
    ),
    # Sales management
    path("sales/", views.SalesListView.as_view(), name="sales_list"),
    path("sales/add/", views.SalesCreateView.as_view(), name="sales_add"),
    path("sales/<uuid:pk>/", views.SalesDetailView.as_view(), name="sales_detail"),
    # Stock management
    path("stock/", views.StockOverviewView.as_view(), name="stock_overview"),
    # Recipe management
    path("recipes/", views.RecipeListView.as_view(), name="recipe_list"),
    path("recipes/add/", views.RecipeCreateView.as_view(), name="recipe_add"),
    path("recipes/<uuid:pk>/", views.RecipeDetailView.as_view(), name="recipe_detail"),
]
