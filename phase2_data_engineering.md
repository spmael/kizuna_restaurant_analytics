# 🔧 Phase 2: Data Engineering - ETL Pipelines & Data Management
## Lightweight Data Processing for Restaurant Analytics

This phase focuses on building robust data processing capabilities optimized for Cameroon's restaurant environment.

## 📋 Phase 2 Overview

We'll implement:
1. **Data Management App** - File upload, validation, processing
2. **Restaurant Data App** - Core business data models 
3. **ETL Pipelines** - Extract, Transform, Load processes
4. **Data Quality System** - Validation and quality checks
5. **Background Processing** - Celery tasks for data processing

## Step 1: Restaurant Data Models

Let's start with the core business data models that represent your restaurant's operations.

### 1.1 Restaurant Data Models (apps/restaurant_data/models.py)

```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from apps.core.models import AuditModel, SoftDeleteModel

class Category(SoftDeleteModel):
    """Product categories (Entrées, Plats principaux, Desserts, Boissons)"""
    name = models.CharField(_('Category Name'), max_length=100)
    name_fr = models.CharField(_('French Name'), max_length=100, blank=True)
    name_en = models.CharField(_('English Name'), max_length=100, blank=True)
    description = models.TextField(_('Description'), blank=True)
    sort_order = models.PositiveIntegerField(_('Sort Order'), default=0)
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name

class Supplier(AuditModel):
    """Suppliers of ingredients and products"""
    name = models.CharField(_('Supplier Name'), max_length=200)
    contact_person = models.CharField(_('Contact Person'), max_length=100, blank=True)
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    address = models.TextField(_('Address'), blank=True)
    city = models.CharField(_('City'), max_length=100, default='Douala')
    country = models.CharField(_('Country'), max_length=100, default='Cameroun')
    
    # Business details
    payment_terms = models.CharField(_('Payment Terms'), max_length=100, blank=True)
    delivery_days = models.CharField(_('Delivery Days'), max_length=100, blank=True)
    minimum_order = models.DecimalField(
        _('Minimum Order (FCFA)'), 
        max_digits=10, 
        decimal_places=0, 
        null=True, 
        blank=True
    )
    
    class Meta:
        verbose_name = _('Supplier')
        verbose_name_plural = _('Suppliers')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(AuditModel):
    """Products/ingredients used in the restaurant"""
    
    UNIT_CHOICES = [
        # Weight
        ('kg', _('Kilogram')),
        ('g', _('Gram')),
        ('lb', _('Pound')),
        
        # Volume
        ('l', _('Liter')),
        ('ml', _('Milliliter')),
        ('cl', _('Centiliter')),
        
        # Count
        ('pcs', _('Pieces')),
        ('dozen', _('Dozen')),
        ('pack', _('Pack')),
        ('bottle', _('Bottle')),
        ('can', _('Can')),
        
        # Other
        ('box', _('Box')),
        ('bag', _('Bag')),
    ]
    
    PRODUCT_TYPE_CHOICES = [
        ('ingredient', _('Ingredient')),
        ('beverage', _('Beverage')),
        ('prepared_food', _('Prepared Food')),
        ('packaging', _('Packaging')),
        ('cleaning', _('Cleaning Supply')),
        ('other', _('Other')),
    ]
    
    name = models.CharField(_('Product Name'), max_length=200)
    name_fr = models.CharField(_('French Name'), max_length=200, blank=True)
    name_en = models.CharField(_('English Name'), max_length=200, blank=True)
    
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        verbose_name=_('Category'),
        related_name='products'
    )
    
    product_type = models.CharField(
        _('Product Type'), 
        max_length=20, 
        choices=PRODUCT_TYPE_CHOICES,
        default='ingredient'
    )
    
    # Unit and measurement
    unit_of_measure = models.CharField(
        _('Unit of Measure'), 
        max_length=10, 
        choices=UNIT_CHOICES
    )
    
    # Current pricing
    current_cost_per_unit = models.DecimalField(
        _('Current Cost per Unit (FCFA)'), 
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    current_selling_price = models.DecimalField(
        _('Current Selling Price (FCFA)'), 
        max_digits=10, 
        decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Inventory management
    minimum_stock_level = models.DecimalField(
        _('Minimum Stock Level'), 
        max_digits=10, 
        decimal_places=3,
        default=0
    )
    
    current_stock = models.DecimalField(
        _('Current Stock'), 
        max_digits=10, 
        decimal_places=3,
        default=0
    )
    
    # Additional info
    description = models.TextField(_('Description'), blank=True)
    barcode = models.CharField(_('Barcode'), max_length=50, blank=True)
    
    # Nutritional info (optional)
    calories_per_100g = models.PositiveIntegerField(
        _('Calories per 100g'), 
        null=True, 
        blank=True
    )
    
    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['category', 'name']
        unique_together = ['name', 'category']
    
    def __str__(self):
        return f"{self.name} ({self.get_unit_of_measure_display()})"
    
    @property
    def is_low_stock(self):
        """Check if product is below minimum stock level"""
        return self.current_stock <= self.minimum_stock_level
    
    @property
    def stock_value(self):
        """Calculate total value of current stock"""
        return self.current_stock * self.current_cost_per_unit

class Purchase(AuditModel):
    """Record of purchases from suppliers"""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('ordered', _('Ordered')),
        ('received', _('Received')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Purchase details
    purchase_date = models.DateTimeField(_('Purchase Date'))
    invoice_number = models.CharField(_('Invoice Number'), max_length=50, blank=True)
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.CASCADE,
        verbose_name=_('Supplier'),
        related_name='purchases'
    )
    
    status = models.CharField(
        _('Status'), 
        max_length=20, 
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Financial details
    subtotal = models.DecimalField(
        _('Subtotal (FCFA)'), 
        max_digits=12, 
        decimal_places=2
    )
    tax_amount = models.DecimalField(
        _('Tax Amount (FCFA)'), 
        max_digits=10, 
        decimal_places=2,
        default=0
    )
    total_amount = models.DecimalField(
        _('Total Amount (FCFA)'), 
        max_digits=12, 
        decimal_places=2
    )
    
    # Additional info
    notes = models.TextField(_('Notes'), blank=True)
    received_date = models.DateTimeField(_('Received Date'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Purchase')
        verbose_name_plural = _('Purchases')
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"Purchase {self.invoice_number or self.id} from {self.supplier}"
    
    def save(self, *args, **kwargs):
        # Calculate total if not provided
        if not self.total_amount:
            self.total_amount = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)

class PurchaseItem(models.Model):
    """Individual items in a purchase"""
    purchase = models.ForeignKey(
        Purchase, 
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        verbose_name=_('Product')
    )
    
    quantity = models.DecimalField(
        _('Quantity'), 
        max_digits=10, 
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    unit_cost = models.DecimalField(
        _('Unit Cost (FCFA)'), 
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    total_cost = models.DecimalField(
        _('Total Cost (FCFA)'), 
        max_digits=12, 
        decimal_places=2
    )
    
    # Quality info
    expiry_date = models.DateField(_('Expiry Date'), null=True, blank=True)
    batch_number = models.CharField(_('Batch Number'), max_length=50, blank=True)
    
    class Meta:
        verbose_name = _('Purchase Item')
        verbose_name_plural = _('Purchase Items')
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} {self.product.unit_of_measure}"
    
    def save(self, *args, **kwargs):
        # Calculate total cost
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
        
        # Update product cost if this is the latest purchase
        self.product.current_cost_per_unit = self.unit_cost
        self.product.save(update_fields=['current_cost_per_unit'])

class Sale(AuditModel):
    """Daily sales records"""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('card', _('Credit/Debit Card')),
        ('mobile_money', _('Mobile Money')),
        ('bank_transfer', _('Bank Transfer')),
        ('other', _('Other')),
    ]
    
    sale_date = models.DateTimeField(_('Sale Date'))
    invoice_number = models.CharField(_('Invoice Number'), max_length=50, blank=True)
    
    # Customer info (optional)
    customer_name = models.CharField(_('Customer Name'), max_length=100, blank=True)
    customer_phone = models.CharField(_('Customer Phone'), max_length=20, blank=True)
    
    # Payment details
    payment_method = models.CharField(
        _('Payment Method'), 
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    
    subtotal = models.DecimalField(
        _('Subtotal (FCFA)'), 
        max_digits=10, 
        decimal_places=2
    )
    tax_amount = models.DecimalField(
        _('Tax Amount (FCFA)'), 
        max_digits=10, 
        decimal_places=2,
        default=0
    )
    discount_amount = models.DecimalField(
        _('Discount Amount (FCFA)'), 
        max_digits=10, 
        decimal_places=2,
        default=0
    )
    total_amount = models.DecimalField(
        _('Total Amount (FCFA)'), 
        max_digits=10, 
        decimal_places=2
    )
    
    # Service details
    table_number = models.CharField(_('Table Number'), max_length=10, blank=True)
    number_of_guests = models.PositiveIntegerField(_('Number of Guests'), default=1)
    
    notes = models.TextField(_('Notes'), blank=True)
    
    class Meta:
        verbose_name = _('Sale')
        verbose_name_plural = _('Sales')
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"Sale {self.invoice_number or self.id} - {self.total_amount} FCFA"
    
    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        super().save(*args, **kwargs)

class SaleItem(models.Model):
    """Individual items in a sale"""
    sale = models.ForeignKey(
        Sale, 
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        verbose_name=_('Product')
    )
    
    quantity = models.DecimalField(
        _('Quantity'), 
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit_price = models.DecimalField(
        _('Unit Price (FCFA)'), 
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    total_price = models.DecimalField(
        _('Total Price (FCFA)'), 
        max_digits=10, 
        decimal_places=2
    )
    
    # Special instructions
    special_instructions = models.CharField(
        _('Special Instructions'), 
        max_length=200, 
        blank=True
    )
    
    class Meta:
        verbose_name = _('Sale Item')
        verbose_name_plural = _('Sale Items')
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class DailySummary(models.Model):
    """Daily sales and cost summary"""
    date = models.DateField(_('Date'), unique=True)
    
    # Sales metrics
    total_sales = models.DecimalField(
        _('Total Sales (FCFA)'), 
        max_digits=12, 
        decimal_places=2,
        default=0
    )
    total_orders = models.PositiveIntegerField(_('Total Orders'), default=0)
    average_order_value = models.DecimalField(
        _('Average Order Value (FCFA)'), 
        max_digits=10, 
        decimal_places=2,
        default=0
    )
    
    # Cost metrics
    total_food_cost = models.DecimalField(
        _('Total Food Cost (FCFA)'), 
        max_digits=12, 
        decimal_places=2,
        default=0
    )
    food_cost_percentage = models.DecimalField(
        _('Food Cost %'), 
        max_digits=5, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Customer metrics
    total_customers = models.PositiveIntegerField(_('Total Customers'), default=0)
    
    # Calculated fields
    gross_profit = models.DecimalField(
        _('Gross Profit (FCFA)'), 
        max_digits=12, 
        decimal_places=2,
        default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Daily Summary')
        verbose_name_plural = _('Daily Summaries')
        ordering = ['-date']
    
    def __str__(self):
        return f"Summary for {self.date}"
    
    def save(self, *args, **kwargs):
        # Calculate derived metrics
        if self.total_sales > 0:
            self.food_cost_percentage = (self.total_food_cost / self.total_sales) * 100
            self.gross_profit = self.total_sales - self.total_food_cost
            
            if self.total_orders > 0:
                self.average_order_value = self.total_sales / self.total_orders
        
        super().save(*args, **kwargs)
```

### 1.2 Restaurant Data Admin (apps/restaurant_data/admin.py)

```python
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Avg
from .models import (
    Category, Supplier, Product, Purchase, PurchaseItem,
    Sale, SaleItem, DailySummary
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_fr', 'sort_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'name_fr', 'name_en']
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'sort_order', 'description')
        }),
        (_('Translations'), {
            'fields': ('name_fr', 'name_en'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
    )

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'contact_person', 'phone', 'city', 
        'minimum_order', 'is_active', 'created_at'
    ]
    list_filter = ['city', 'country', 'is_active', 'created_at']
    search_fields = ['name', 'contact_person', 'phone', 'email']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'contact_person')
        }),
        (_('Contact Information'), {
            'fields': ('phone', 'email', 'address', 'city', 'country')
        }),
        (_('Business Terms'), {
            'fields': ('payment_terms', 'delivery_days', 'minimum_order')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
    )

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ['total_cost']

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'supplier', 'purchase_date', 
        'total_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'supplier', 'purchase_date', 'created_at']
    search_fields = ['invoice_number', 'supplier__name', 'notes']
    date_hierarchy = 'purchase_date'
    readonly_fields = ['total_amount']
    inlines = [PurchaseItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('purchase_date', 'invoice_number', 'supplier', 'status')
        }),
        (_('Financial Details'), {
            'fields': ('subtotal', 'tax_amount', 'total_amount')
        }),
        (_('Additional Information'), {
            'fields': ('notes', 'received_date')
        }),
    )

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'product_type', 'unit_of_measure',
        'current_cost_per_unit', 'current_stock', 'is_low_stock',
        'is_active', 'updated_at'
    ]
    list_filter = [
        'category', 'product_type', 'unit_of_measure', 
        'is_active', 'created_at'
    ]
    search_fields = ['name', 'name_fr', 'name_en', 'barcode']
    readonly_fields = ['stock_value', 'is_low_stock']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'product_type')
        }),
        (_('Translations'), {
            'fields': ('name_fr', 'name_en'),
            'classes': ('collapse',)
        }),
        (_('Measurement & Pricing'), {
            'fields': (
                'unit_of_measure', 'current_cost_per_unit', 
                'current_selling_price'
            )
        }),
        (_('Inventory'), {
            'fields': (
                'current_stock', 'minimum_stock_level', 
                'stock_value', 'is_low_stock'
            )
        }),
        (_('Additional Info'), {
            'fields': ('description', 'barcode', 'calories_per_100g')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    readonly_fields = ['total_price']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'sale_date', 'customer_name',
        'payment_method', 'total_amount', 'number_of_guests', 'created_at'
    ]
    list_filter = ['payment_method', 'sale_date', 'created_at']
    search_fields = ['invoice_number', 'customer_name', 'customer_phone']
    date_hierarchy = 'sale_date'
    readonly_fields = ['total_amount']
    inlines = [SaleItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('sale_date', 'invoice_number', 'payment_method')
        }),
        (_('Customer Information'), {
            'fields': ('customer_name', 'customer_phone')
        }),
        (_('Service Details'), {
            'fields': ('table_number', 'number_of_guests')
        }),
        (_('Financial Details'), {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount')
        }),
        (_('Additional Information'), {
            'fields': ('notes',)
        }),
    )

@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_sales', 'total_orders', 'average_order_value',
        'food_cost_percentage', 'total_customers', 'gross_profit'
    ]
    list_filter = ['date']
    search_fields = ['date']
    readonly_fields = [
        'average_order_value', 'food_cost_percentage', 'gross_profit'
    ]
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        return False  # Daily summaries are auto-generated
```

### 1.3 Restaurant Data URLs (apps/restaurant_data/urls.py)

```python
from django.urls import path
from . import views

app_name = 'restaurant_data'

urlpatterns = [
    # Product management
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/add/', views.ProductCreateView.as_view(), name='product_add'),
    path('products/<uuid:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    
    # Supplier management
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/add/', views.SupplierCreateView.as_view(), name='supplier_add'),
    path('suppliers/<uuid:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    
    # Purchase management
    path('purchases/', views.PurchaseListView.as_view(), name='purchase_list'),
    path('purchases/add/', views.PurchaseCreateView.as_view(), name='purchase_add'),
    path('purchases/<uuid:pk>/', views.PurchaseDetailView.as_view(), name='purchase_detail'),
    
    # Sales overview
    path('sales/', views.SalesOverviewView.as_view(), name='sales_overview'),
    
    # Stock management
    path('stock/', views.StockOverviewView.as_view(), name='stock_overview'),
    path('stock/low/', views.LowStockView.as_view(), name='low_stock'),
]
```

## Step 2: Data Management App

Now let's build the data management system for uploading and processing files.

### 2.1 Data Management Models (apps/data_management/models.py)

```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel
import uuid

User = get_user_model()

class DataUpload(TimeStampedModel):
    """Track data file uploads"""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    FILE_TYPE_CHOICES = [
        ('odoo_export', _('Odoo Export')),
        ('sales_data', _('Sales Data')),
        ('purchase_data', _('Purchase Data')),
        ('inventory_data', _('Inventory Data')),
        ('recipe_data', _('Recipe Data')),
        ('other', _('Other')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File information
    file = models.FileField(
        _('Data File'), 
        upload_to='uploads/%Y/%m/',
        help_text=_('Upload Excel (.xlsx) or CSV files')
    )
    original_filename = models.CharField(_('Original Filename'), max_length=255)
    file_size = models.PositiveBigIntegerField(_('File Size (bytes)'))
    file_type = models.CharField(
        _('File Type'), 
        max_length=20, 
        choices=FILE_TYPE_CHOICES
    )
    
    # Processing information
    status = models.CharField(
        _('Status'), 
        max_length=20, 
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Statistics
    total_rows = models.PositiveIntegerField(_('Total Rows'), default=0)
    processed_rows = models.PositiveIntegerField(_('Processed Rows'), default=0)
    error_rows = models.PositiveIntegerField(_('Error Rows'), default=0)
    
    # User tracking
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        verbose_name=_('Uploaded By'),
        related_name='uploads'
    )
    
    # Processing details
    started_at = models.DateTimeField(_('Processing Started'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Processing Completed'), null=True, blank=True)
    error_message = models.TextField(_('Error Message'), blank=True)
    processing_log = models.TextField(_('Processing Log'), blank=True)
    
    class Meta:
        verbose_name = _('Data Upload')
        verbose_name_plural = _('Data Uploads')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_status_display()})"
    
    @property
    def progress_percentage(self):
        """Calculate processing progress percentage"""
        if self.total_rows == 0:
            return 0
        return (self.processed_rows / self.total_rows) * 100
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_rows == 0:
            return 0
        return ((self.total_rows - self.error_rows) / self.total_rows) * 100

class ProcessingError(TimeStampedModel):
    """Track individual processing errors"""
    upload = models.ForeignKey(
        DataUpload, 
        on_delete=models.CASCADE,
        related_name='errors'
    )
    
    row_number = models.PositiveIntegerField(_('Row Number'))
    column_name = models.CharField(_('Column Name'), max_length=100, blank=True)
    error_type = models.CharField(_('Error Type'), max_length=50)
    error_message = models.TextField(_('Error Message'))
    row_data = models.JSONField(_('Row Data'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Processing Error')
        verbose_name_plural = _('Processing Errors')
        ordering = ['upload', 'row_number']
    
    def __str__(self):
        return f"Error in {self.upload.original_filename} at row {self.row_number}"
```

### 2.2 Data Management Forms (apps/data_management/forms.py)

```python
from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML
from .models import DataUpload
import os

class DataUploadForm(forms.ModelForm):
    """Form for uploading data files"""
    
    class Meta:
        model = DataUpload
        fields = ['file', 'file_type']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': '.xlsx,.xls,.csv'
            }),
            'file_type': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<div class="alert alert-info">' + 
                 str(_('Upload Excel (.xlsx) or CSV files. Maximum file size: 10MB')) + 
                 '</div>'),
            Row(
                Column('file_type', css_class='form-group col-md-4 mb-3'),
                Column('file', css_class='form-group col-md-8 mb-3'),
            ),
            HTML('<div id="file-info" class="mb-3" style="display:none;"></div>'),
            Submit('submit', _('Upload File'), css_class='btn btn-primary')
        )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (10MB limit for Sub-Saharan Africa)
            if file.size > 10 * 1024 * 1024:  
                raise forms.ValidationError(
                    _('File size must be less than 10MB.')
                )
            
            # Check file extension
            ext = os.path.splitext(file.name)[1].lower()
            allowed_extensions = ['.xlsx', '.xls', '.csv']
            
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    _('Only Excel (.xlsx, .xls) and CSV files are allowed.')
                )
        
        return file
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set additional fields
        if instance.file:
            instance.original_filename = instance.file.name
            instance.file_size = instance.file.size
        
        if commit:
            instance.save()
        
        return instance

class DataFilterForm(forms.Form):
    """Form for filtering data uploads"""
    
    STATUS_CHOICES = [('', _('All Statuses'))] + DataUpload.STATUS_CHOICES
    FILE_TYPE_CHOICES = [('', _('All File Types'))] + DataUpload.FILE_TYPE_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    file_type = forms.ChoiceField(
        choices=FILE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='form-group col-md-3'),
                Column('file_type', css_class='form-group col-md-3'),
                Column('date_from', css_class='form-group col-md-3'),
                Column('date_to', css_class='form-group col-md-3'),
            ),
            Submit('submit', _('Filter'), css_class='btn btn-secondary')
        )
```

Continue in the next response with the ETL pipelines and data processing components...

## 🎯 What We've Built So Far

✅ **Restaurant Data Models**: Products, Suppliers, Purchases, Sales, Daily Summaries  
✅ **Data Upload System**: File upload tracking with progress monitoring  
✅ **Admin Interface**: Comprehensive admin for all restaurant data  
✅ **Lightweight Forms**: Optimized for Cameroon's connectivity  
✅ **Cameroon Context**: FCFA currency, French translations, local business practices  

This foundation provides the core data structure your restaurant analytics will build upon. Ready for the next part with ETL pipelines and data processing? 🚀