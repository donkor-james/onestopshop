"""
Generate realistic bulk data so performance claims can be measured.

    python manage.py seed_products --products 100000 --variants 3

Uses bulk_create (Product.save() is bypassed, so slugs are set here).
"""
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Category, Product, ProductVariant

SIZES = ['XS', 'S', 'M', 'L', 'XL']
COLORS = ['Black', 'White', 'Red', 'Blue', 'Green', 'Kente Gold']
CATEGORIES = ['Dresses', 'Shirts', 'Trousers', 'Shoes', 'Bags', 'Accessories']


class Command(BaseCommand):
    help = 'Seed categories, products and variants for load testing'

    def add_arguments(self, parser):
        parser.add_argument('--products', type=int, default=10000)
        parser.add_argument('--variants', type=int, default=3,
                            help='variants per product (max 30)')
        parser.add_argument('--batch', type=int, default=2000)
        parser.add_argument('--seed', type=int, default=42)

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(opts['seed'])
        categories = [Category.objects.get_or_create(name=n)[0] for n in CATEGORIES]
        start = Product.objects.filter(name__startswith='Seed ').count()
        per_product = min(opts['variants'], len(SIZES) * len(COLORS))
        created = 0

        for offset in range(0, opts['products'], opts['batch']):
            count = min(opts['batch'], opts['products'] - offset)
            products = []
            for i in range(count):
                n = start + offset + i
                products.append(Product(
                    name=f'Seed product {n}', slug=f'seed-product-{n}',
                    description='Seeded product for load testing',
                    base_price=Decimal(random.randint(50, 900)),
                    category=random.choice(categories),
                    is_active=random.random() > 0.05))
            Product.objects.bulk_create(products)

            variants = []
            for product in products:
                combos = random.sample(
                    [(s, c) for s in SIZES for c in COLORS], per_product)
                for size, color in combos:
                    variants.append(ProductVariant(
                        product=product, size=size, color=color,
                        sku=f'SKU-{product.slug}-{size}-{color}'.upper().replace(' ', '-'),
                        stock_qty=random.randint(0, 40)))
            ProductVariant.objects.bulk_create(variants)
            created += count
            self.stdout.write(f'  {created}/{opts["products"]} products')

        self.stdout.write(self.style.SUCCESS('Done'))
