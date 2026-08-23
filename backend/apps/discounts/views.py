from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serialilzers import ApplyDiscountSerializer, DiscountCodeSerializer
from apps.cart.models import Cart


class ApplyDiscountView(generics.GenericAPIView):
    serializer_class = ApplyDiscountSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        discount = serializer.validated_data['discount']
        cart_total = serializer.validated_data['cart_total']

        # apply_to() is a model method — calculates in Python,
        # no extra DB query needed

        discounted_total = discount.apply_to(cart_total)

        return Response({
            'discount': DiscountCodeSerializer(discount).data,
            'original_total': cart_total,
            'discounted_total': discounted_total,
            'savings': cart_total - discounted_total
        })
