from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    Category,
    Order,
    Payment,
    Product,
    ProductPhoto,
    User,
)

admin.site.site_header = "Alijahon Admin"
admin.site.site_title = "Alijahon Admin"
admin.site.index_title = "Boshqaruv paneli"


class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 1
    fields = ("photo", "is_thumbnail", "preview")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.photo and getattr(obj.photo, "url", ""):
            return format_html(
                '<img src="{}" style="height:48px;border-radius:6px;object-fit:cover;" />',
                obj.photo.url,
            )
        return "-"

    preview.short_description = "Preview"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "photo_preview")
    search_fields = ("title",)
    ordering = ("id",)

    def photo_preview(self, obj):
        if obj.photo and getattr(obj.photo, "url", ""):
            return format_html(
                '<img src="{}" style="height:44px;border-radius:8px;object-fit:cover;" />',
                obj.photo.url,
            )
        return "-"

    photo_preview.short_description = "Photo"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "price", "quantity", "created_at", "thumbnail")
    list_filter = ("category", "created_at")
    search_fields = ("title", "description")
    ordering = ("-id",)
    autocomplete_fields = ("category",)
    list_editable = ("price", "quantity")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    inlines = [ProductPhotoInline]

    def thumbnail(self, obj):
        thumb = obj.thumbnail_photo
        if thumb and getattr(thumb.photo, "url", ""):
            return format_html(
                '<img src="{}" style="height:44px;border-radius:8px;object-fit:cover;" />',
                thumb.photo.url,
            )
        return "-"

    thumbnail.short_description = "Rasm"


@admin.register(ProductPhoto)
class ProductPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "is_thumbnail", "preview")
    list_filter = ("is_thumbnail",)
    search_fields = ("product__title",)
    autocomplete_fields = ("product",)

    def preview(self, obj):
        if obj.photo and getattr(obj.photo, "url", ""):
            return format_html(
                '<img src="{}" style="height:44px;border-radius:8px;object-fit:cover;" />',
                obj.photo.url,
            )
        return "-"

    preview.short_description = "Rasm"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "user",
        "first_name",
        "phone_number",
        "quantity",
        "total_price_display",
        "created_at",
    )
    list_filter = ("created_at", "product__category")
    search_fields = ("first_name", "phone_number", "product__title", "user__phone_number")
    ordering = ("-created_at",)
    autocomplete_fields = ("product", "user")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"

    def total_price_display(self, obj):
        return obj.total_price

    total_price_display.short_description = "Jami"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "status", "type", "created_at")
    list_filter = ("status", "type", "created_at")
    search_fields = ("user__phone_number", "card_number")
    autocomplete_fields = ("user",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "pay_datetime")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("id", "phone_number", "first_name", "last_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("phone_number", "first_name", "last_name")
    ordering = ("-id",)
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        (
            "Shaxsiy ma'lumot",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "balance",
                )
            },
        ),
        ("Ruxsatlar", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Sana", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

