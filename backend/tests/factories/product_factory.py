import factory
from apps.products.models import Category, Product, ProductVariant


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f'Product {n}')
    base_price = factory.Faker(
        'pydecimal', left_digits=3, right_digits=2, positive=True
    )
    category = factory.SubFactory(CategoryFactory)
    is_active = True
    description = factory.Faker('sentence')


class VariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    size = 'M'
    color = 'Red'
    sku = factory.Sequence(lambda n: f'SKU-{n}')
    stock_qty = 10
    price_override = factory.Faker(
        'pydecimal', left_digits=3, right_digits=2, positive=True
    )
