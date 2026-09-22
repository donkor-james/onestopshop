import factory
from apps.orders.models import Order, OrderItem
from .user_factory import UserFactory
from .product_factory import VariantFactory


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    status = Order.Status.PENDING
    total_amount = factory.Faker(
        'pydecimal', left_digits=3, right_digits=2, positive=True
    )
    shipping_address = {
        'street': '12 Test Street',
        'city': 'Accra',
        'region': 'Greater Accra',
        'country': 'Ghana'
    }


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(VariantFactory)
    quantity = 1
    unit_price = factory.Faker(
        'pydecimal', left_digits=3, right_digits=2, positive=True
    )
