import email
import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.core import cache
from .models import User, Address
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UpdateProfileSerializer,
    ChangePasswordSerializer,
    AddressSerializer,
    VerifyOtpSerializer
)
from .tasks import send_otp_code


def generate_otp():
    return ''.join(str(secrets.randbelow(10)) for _ in range(6))


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        otp = generate_otp()

        # Store OTP in cache for 10 minutes
        cache.set(f"otp:{user.email}", otp, timeout=1000)
        send_otp_code.delay(user, otp)

        return Response(
            {"detail": "Registration successful. A verification code has been sent to your email."},
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {"detail": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"detail": "Account not verified. Please check your email for the verification code"},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UpdateProfileView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateProfileSerializer

    def get_object(self):
        return self.request.user


class VerifyOtpView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyOtpSerializer

    def post(self):
        serializer = self.get_serializer(data=self.request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")
            otp = serializer.validated_data.get("otp")

            # Retrieve the stored OTP from cache
            stored_otp = cache.get(f"otp:{email}")

            if stored_otp is None:
                return Response(
                    {"detail": "OTP has expired or is invalid."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if stored_otp != otp:
                return Response(
                    {"detail": "Invalid OTP."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.get(email=email)
            user.is_active = True
            user.save()

            cache.delete(f"otp:{email}")

            return Response(
                {"detail": "OTP verified successfully."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
