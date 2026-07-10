from django.contrib import admin
from .models import User, Address
# Register your models here.


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name",
                    "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("is_active", "is_staff")
    ordering = ("email",)


admin.site.register(Address)
