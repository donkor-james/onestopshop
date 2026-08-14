from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("verify-otp/", views.VerifyOtpView.as_view(), name="verify-otp"),
    path("change-password/", views.ChangePasswordView.as_view(),
         name="change-password"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/update/", views.UpdateProfileView.as_view(), name="update-profile"),
    path("addresses/", views.AddressListCreateView.as_view(), name="address-list"),
    path("addresses/<uuid:pk>/",
         views.AddressDetailView.as_view(), name="address-detail"),
    path("addresses/<uuid:pk>/set-default/",
         views.SetDefaultAddressView.as_view(), name="set-default-address"),
]
