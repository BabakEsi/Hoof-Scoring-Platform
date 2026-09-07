from django.contrib import admin

from .models import User

from django.contrib import admin



    
# Register your models here.
admin.site.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "status",
        "is_active",
    )