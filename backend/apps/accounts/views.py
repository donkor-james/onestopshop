import email
import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, inline_serializer
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


@extend_schema(
    tags=['Auth'],
    summary='Register a new user',
    description="""
        Creates a new user account and sends a 6-digit OTP
        to the provided email address for verification.
        The account remains inactive until the OTP is verified.
    """,
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(description='Registration successful, OTP sent to email'),
        400: OpenApiResponse(description='Validation errors (duplicate email, password mismatch etc)'),
    }
)
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


@extend_schema(
    tags=['Auth'],
    summary='Login',
    description="""
        Authenticates a user with email and password.
        Returns JWT access and refresh tokens along with the user profile.
        Account must be verified (OTP confirmed) before login is allowed.
    """,
    request=inline_serializer(
        name='LoginRequest',
        fields={
            'email': serializers.EmailField(),
            'password': serializers.CharField(),
        }
    ),
    responses={
        200: inline_serializer(
            name='LoginResponse',
            fields={
                'access': serializers.CharField(),
                'refresh': serializers.CharField(),
                'user': UserSerializer(),
            }
        ),
        400: OpenApiResponse(description='Email or password missing'),
        401: OpenApiResponse(description='Invalid credentials'),
        403: OpenApiResponse(description='Account not verified'),
    }
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


class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.validated_data['current_password']):
                return Response({"current_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            self.object.set_password(serializer.validated_data['new_password'])
            self.object.save()
            return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Profile'], summary='Get profile', description='Returns the authenticated user\'s profile.')
class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=['Profile'],
    summary='Update profile',
    description='Updates the authenticated user\'s profile. Supports partial updates via PATCH.'
)
class UpdateProfileView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateProfileSerializer

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=['Auth'],
    summary='Verify OTP',
    description="""
        Verifies the 6-digit OTP sent to the user's email during registration
        or password reset. On success, activates the account and returns
        JWT tokens so the user is logged in immediately.
        OTP expires after 10 minutes.
    """,
    request=VerifyOtpSerializer,
    responses={
        200: OpenApiResponse(description='OTP verified, returns access and refresh tokens'),
        400: OpenApiResponse(description='OTP expired or invalid'),
    }
)
class VerifyOtpView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyOtpSerializer

    def post(self, request):
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

            refresh = RefreshToken.for_user(user)

            cache.delete(f"otp:{email}")

            return Response(
                {
                    "detail": "OTP verified successfully.",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Auth'],
    summary='Logout',
    description="""
        Blacklists the provided refresh token, effectively logging the user out.
        The access token will expire naturally after its lifetime.
    """,
    request=inline_serializer(
        name='LogoutRequest',
        fields={
            'refresh': serializers.CharField()
        }
    ),
    responses={
        200: OpenApiResponse(description='Logged out successfully'),
    }
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user)


@extend_schema(
    tags=['Addresses'],
    summary='Set default address',
    description='Sets the specified address as the default delivery address.',
    request=None,
    responses={
        200: OpenApiResponse(description='Default address updated'),
        404: OpenApiResponse(description='Address not found'),
    }
)
class SetDefaultAddressView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.is_default = True
        address.save()
        return Response({"detail": "Default address updated."}, status=status.HTTP_200_OK)
