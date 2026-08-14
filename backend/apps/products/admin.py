from django.contrib import admin
from apps.products.models import product, image, variant, category

# Register your models here.


class ProductImageInline(admin.TabularInline):
    model = image.ProductImage
    extra = 1  # Number of empty forms to display


class ProductVariantInline(admin.TabularInline):
    model = variant.ProductVariant
    extra = 1  # Number of empty forms to display
    inlines = [ProductImageInline]


@admin.register(product.Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductVariantInline]
    list_display = ('name', 'category', 'base_price',
                    'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)


@admin.register(category.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent')
    search_fields = ('name', 'slug')
    ordering = ('name',)


@admin.register(variant.ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ('product', 'size', 'color', 'sku',
                    'stock_qty', 'price_override')
    list_filter = ('product__category',)
    search_fields = ('product__name', 'sku')
    ordering = ('product', 'size', 'color')
