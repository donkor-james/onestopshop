import factory
from django.utils import timezone
from datetime import timedelta
from apps.discounts.models import DiscountCode


class DiscountCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DiscountCode

    code = factory.Sequence(lambda n: f'SAVE{n}')
    discount_type = 'percentage'
    value = 10
    min_order_amount = 0
    usage_limit = 100
    used_count = 0
    valid_from = factory.LazyFunction(timezone.now)
    valid_until = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=30)
    )
    is_active = True
