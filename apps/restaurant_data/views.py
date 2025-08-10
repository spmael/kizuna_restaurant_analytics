from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    ProductConsolidationForm,
    ProductForm,
    PurchaseForm,
    PurchasesCategoryForm,
    RecipeForm,
    SalesCategoryForm,
    SalesForm,
    UnitOfMeasureForm,
)
from .models import (
    Product,
    ProductConsolidation,
    Purchase,
    PurchasesCategory,
    Recipe,
    Sales,
    SalesCategory,
    UnitOfMeasure,
)


# Product Views
class ProductListView(LoginRequiredMixin, ListView):
    """View for listing products."""

    model = Product
    template_name = "restaurant_data/product_list.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        queryset = Product.objects.select_related(
            "purchase_category", "sales_category", "unit_of_measure"
        ).filter(is_active=True)

        # Search functionality
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(name_fr__icontains=search_query)
                | Q(name_en__icontains=search_query)
                | Q(purchase_category__name__icontains=search_query)
                | Q(sales_category__name__icontains=search_query)
            )

        # Filter by category
        category = self.request.GET.get("category")
        if category:
            queryset = queryset.filter(purchase_category_id=category)

        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = PurchasesCategory.objects.filter(is_active=True)
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_category"] = self.request.GET.get("category", "")
        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """View for displaying product details."""

    model = Product
    template_name = "restaurant_data/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()

        # Get recent purchases and sales
        context["recent_purchases"] = product.purchases.order_by("-purchase_date")[:5]
        context["recent_sales"] = product.sales.order_by("-sale_date")[:5]

        # Calculate statistics
        context["total_purchased"] = (
            product.purchases.aggregate(total=Sum("quantity_purchased"))["total"] or 0
        )
        context["total_sold"] = (
            product.sales.aggregate(total=Sum("quantity_sold"))["total"] or 0
        )

        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new product."""

    model = Product
    form_class = ProductForm
    template_name = "restaurant_data/product_form.html"
    success_url = reverse_lazy("restaurant_data:product_list")

    def form_valid(self, form):
        messages.success(self.request, _("Product created successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, _("Error creating product. Please check the form.")
        )
        return super().form_invalid(form)


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating a product."""

    model = Product
    form_class = ProductForm
    template_name = "restaurant_data/product_form.html"
    success_url = reverse_lazy("restaurant_data:product_list")

    def form_valid(self, form):
        messages.success(self.request, _("Product updated successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, _("Error updating product. Please check the form.")
        )
        return super().form_invalid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting a product."""

    model = Product
    template_name = "restaurant_data/product_confirm_delete.html"
    success_url = reverse_lazy("restaurant_data:product_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Product deleted successfully."))
        return super().delete(request, *args, **kwargs)


# Purchase Views
class PurchaseListView(LoginRequiredMixin, ListView):
    """View for listing purchases."""

    model = Purchase
    template_name = "restaurant_data/purchase_list.html"
    context_object_name = "purchases"
    paginate_by = 20

    def get_queryset(self):
        queryset = Purchase.objects.select_related("product").filter(is_active=True)

        # Search functionality
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query)
                | Q(product__name_fr__icontains=search_query)
                | Q(product__name_en__icontains=search_query)
            )

        return queryset.order_by("-purchase_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        return context


class PurchaseDetailView(LoginRequiredMixin, DetailView):
    """View for displaying purchase details."""

    model = Purchase
    template_name = "restaurant_data/purchase_detail.html"
    context_object_name = "purchase"


class PurchaseCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new purchase."""

    model = Purchase
    form_class = PurchaseForm
    template_name = "restaurant_data/purchase_form.html"
    success_url = reverse_lazy("restaurant_data:purchase_list")

    def form_valid(self, form):
        messages.success(self.request, _("Purchase created successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, _("Error creating purchase. Please check the form.")
        )
        return super().form_invalid(form)


# Sales Views
class SalesListView(LoginRequiredMixin, ListView):
    """View for listing sales."""

    model = Sales
    template_name = "restaurant_data/sales_list.html"
    context_object_name = "sales"
    paginate_by = 20

    def get_queryset(self):
        queryset = Sales.objects.select_related("product").filter(is_active=True)

        # Search functionality
        search_query = self.request.GET.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query)
                | Q(product__name_fr__icontains=search_query)
                | Q(product__name_en__icontains=search_query)
                | Q(order_number__icontains=search_query)
                | Q(customer__icontains=search_query)
            )

        return queryset.order_by("-sale_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        return context


class SalesDetailView(LoginRequiredMixin, DetailView):
    """View for displaying sales details."""

    model = Sales
    template_name = "restaurant_data/sales_detail.html"
    context_object_name = "sale"


class SalesCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new sale."""

    model = Sales
    form_class = SalesForm
    template_name = "restaurant_data/sales_form.html"
    success_url = reverse_lazy("restaurant_data:sales_list")

    def form_valid(self, form):
        messages.success(self.request, _("Sale created successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating sale. Please check the form."))
        return super().form_invalid(form)


# Recipe Views
class RecipeListView(LoginRequiredMixin, ListView):
    """View for listing recipes."""

    model = Recipe
    template_name = "restaurant_data/recipe_list.html"
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
    template_name = "restaurant_data/recipe_detail.html"
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
    template_name = "restaurant_data/recipe_form.html"
    success_url = reverse_lazy("restaurant_data:recipe_list")

    def form_valid(self, form):
        messages.success(self.request, _("Recipe created successfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Error creating recipe. Please check the form."))
        return super().form_invalid(form)


# Stock Overview View
class StockOverviewView(LoginRequiredMixin, TemplateView):
    """View for stock overview."""

    template_name = "restaurant_data/stock_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get stock statistics
        products = Product.objects.filter(is_active=True).select_related(
            "purchase_category", "sales_category", "unit_of_measure"
        )

        context["products"] = products
        context["total_products"] = products.count()
        context["low_stock_products"] = products.filter(current_stock__lt=10)
        context["out_of_stock_products"] = products.filter(current_stock=0)

        # Calculate total stock value
        total_value = sum(product.stock_value for product in products)
        context["total_stock_value"] = total_value

        return context


# Category Views
class PurchasesCategoryListView(LoginRequiredMixin, ListView):
    """View for listing purchase categories."""

    model = PurchasesCategory
    template_name = "restaurant_data/purchases_category_list.html"
    context_object_name = "categories"
    paginate_by = 20

    def get_queryset(self):
        return PurchasesCategory.objects.filter(is_active=True).order_by(
            "sort_order", "name"
        )


class PurchasesCategoryCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new purchase category."""

    model = PurchasesCategory
    form_class = PurchasesCategoryForm
    template_name = "restaurant_data/purchases_category_form.html"
    success_url = reverse_lazy("restaurant_data:purchases_category_list")

    def form_valid(self, form):
        messages.success(self.request, _("Purchase category created successfully."))
        return super().form_valid(form)


class SalesCategoryListView(LoginRequiredMixin, ListView):
    """View for listing sales categories."""

    model = SalesCategory
    template_name = "restaurant_data/sales_category_list.html"
    context_object_name = "categories"
    paginate_by = 20

    def get_queryset(self):
        return SalesCategory.objects.filter(is_active=True).order_by(
            "sort_order", "name"
        )


class SalesCategoryCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new sales category."""

    model = SalesCategory
    form_class = SalesCategoryForm
    template_name = "restaurant_data/sales_category_form.html"
    success_url = reverse_lazy("restaurant_data:sales_category_list")

    def form_valid(self, form):
        messages.success(self.request, _("Sales category created successfully."))
        return super().form_valid(form)


# Unit of Measure Views
class UnitOfMeasureListView(LoginRequiredMixin, ListView):
    """View for listing units of measure."""

    model = UnitOfMeasure
    template_name = "restaurant_data/unit_of_measure_list.html"
    context_object_name = "units"
    paginate_by = 20

    def get_queryset(self):
        return UnitOfMeasure.objects.filter(is_active=True).order_by(
            "sort_order", "name"
        )


class UnitOfMeasureCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new unit of measure."""

    model = UnitOfMeasure
    form_class = UnitOfMeasureForm
    template_name = "restaurant_data/unit_of_measure_form.html"
    success_url = reverse_lazy("restaurant_data:unit_of_measure_list")

    def form_valid(self, form):
        messages.success(self.request, _("Unit of measure created successfully."))
        return super().form_valid(form)


# Product Consolidation Views
class ProductConsolidationListView(LoginRequiredMixin, ListView):
    """View for listing product consolidations."""

    model = ProductConsolidation
    template_name = "restaurant_data/product_consolidation_list.html"
    context_object_name = "consolidations"
    paginate_by = 20

    def get_queryset(self):
        return (
            ProductConsolidation.objects.select_related("primary_product")
            .filter(is_active=True)
            .order_by("-confidence_score")
        )


class ProductConsolidationCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new product consolidation."""

    model = ProductConsolidation
    form_class = ProductConsolidationForm
    template_name = "restaurant_data/product_consolidation_form.html"
    success_url = reverse_lazy("restaurant_data:product_consolidation_list")

    def form_valid(self, form):
        messages.success(self.request, _("Product consolidation created successfully."))
        return super().form_valid(form)


class ProductConsolidationDetailView(LoginRequiredMixin, DetailView):
    """View for displaying product consolidation details."""

    model = ProductConsolidation
    template_name = "restaurant_data/product_consolidation_detail.html"
    context_object_name = "consolidation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consolidation = self.get_object()

        # Get consolidated products
        consolidated_products = Product.objects.filter(
            id__in=consolidation.consolidated_products
        )
        context["consolidated_products"] = consolidated_products

        return context


# API Views for AJAX
def get_products_ajax(request):
    """AJAX view for getting products."""
    search_query = request.GET.get("q", "")
    products = Product.objects.filter(
        Q(name__icontains=search_query)
        | Q(name_fr__icontains=search_query)
        | Q(name_en__icontains=search_query)
    ).filter(is_active=True)[:10]

    data = [{"id": product.id, "name": product.name} for product in products]
    return JsonResponse({"results": data})


def get_product_details_ajax(request, product_id):
    """AJAX view for getting product details."""
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        data = {
            "id": product.id,
            "name": product.name,
            "current_selling_price": float(product.current_selling_price),
            "current_cost_per_unit": float(product.current_cost_per_unit),
            "current_stock": float(product.current_stock),
            "unit_of_measure": product.unit_of_measure.name,
        }
        return JsonResponse({"success": True, "data": data})
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "error": "Product not found"})
