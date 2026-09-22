from apps.products.models import Category, Product, ProductVariant, ProductImage
from django.contrib import admin
from apps.products.models import product, image, variant, category

# Register your models here.


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'is_primary', 'order']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['size', 'color', 'sku', 'stock_qty', 'price_override']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'color',
                    'sku', 'stock_qty', 'price_override']
    list_filter = ['size', 'color']
    search_fields = ['sku', 'product__name']
    inlines = [ProductImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['size', 'color', 'sku', 'stock_qty', 'price_override']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category',
                    'base_price', 'is_active', 'created_at']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['variant', 'is_primary', 'order']
    list_filter = ['is_primary']
