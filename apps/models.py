# Create your models here.
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, UserManager
from django.db.models import Model, ForeignKey, PROTECT, ImageField, TextChoices, CASCADE, SET_NULL, Index
from django.db.models.fields import BigAutoField, CharField, TextField, DecimalField, \
    SmallIntegerField, BooleanField, PositiveIntegerField, DateTimeField


class CustomUserManager(UserManager):
    def _create_user_object(self, phone_number, password, **extra_fields):
        if not phone_number:
            raise ValueError("The given phone_number must be set")
        extra_fields.pop("email", None)
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.

        user = self.model(phone_number=phone_number, **extra_fields)
        user.password = make_password(password)
        return user

    def _create_user(self, phone_number,  password, **extra_fields):
        """
        Create and save a user with the given phone_number and password.
        """

        user = self._create_user_object(phone_number, password, **extra_fields)
        user.save(using=self._db)
        return user


    def create_user(self, phone_number, email=None, password=None, **extra_fields):
        extra_fields.pop("email", None)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number,  password, **extra_fields)

    create_user.alters_data = True



    def create_superuser(self, phone_number,  password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone_number, password, **extra_fields)

    create_superuser.alters_data = True

class User(AbstractUser):
    email = None
    objects = CustomUserManager()
    phone_number=CharField(max_length=20, unique=True)
    balance=DecimalField(max_digits=12, decimal_places=0, default=0 )
    username = CharField(max_length=150, unique=True, null=True, blank=True)

    EMAIL_FIELD = ""
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []
class Category(Model):
    title = CharField(max_length=255)
    photo = ImageField(upload_to="categories/" , )

    class Meta:
        verbose_name_plural  = "categories"

    def __str__(self):
        return self.title

    @property
    def photo_url(self):
        if self.photo and getattr(self.photo, "name", ""):
            return self.photo
        return None


class Product(Model):
    title = CharField(max_length=255)
    price = DecimalField(max_digits=14, decimal_places=0)
    description = TextField()
    category = ForeignKey(
        'apps.Category',
        on_delete=PROTECT,

    )
    quantity = SmallIntegerField()
    created_at = DateTimeField(auto_now_add=True, null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            Index(fields=["category", "price"], name="product_cat_price_idx"),
            Index(fields=["price"], name="product_price_idx"),
            Index(fields=["quantity"], name="product_qty_idx"),
        ]

    @property
    def thumbnail_photo(self):
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        photos = prefetched.get("photos")
        if photos is not None:
            for photo in photos:
                if getattr(photo, "is_thumbnail", False):
                    return photo
            return photos[0] if photos else None
        thumb = self.photos.filter(is_thumbnail=True).first()
        return thumb or self.photos.first()

    @property
    def seller_price(self):
        return self.price

    @property
    def benefit(self):
        return 0

    def __str__(self):
        return self.title


class ProductPhoto(Model):
    id = BigAutoField(primary_key=True)
    photo = ImageField(upload_to="products/")
    product = ForeignKey(
        Product,
        on_delete=CASCADE,
        related_name="photos",
        db_column="product_id",
    )
    is_thumbnail = BooleanField(default=False)

    class Meta:
        db_table = "product_photos"


class Order(Model):
    product = ForeignKey("apps.Product", on_delete=CASCADE, related_name="orders")
    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )
    first_name = CharField(max_length=200)
    phone_number = CharField(max_length=20)
    quantity = PositiveIntegerField(default=1)
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.pk}"

    @property
    def total_price(self):
        return self.quantity * self.product.price
class Payment(Model):
    class PayStatus(TextChoices):
        REVIEW = "review","ko'rib chiqish"
        COMPLETED = "complete", 'Yakunlandi'
        CANCELED = "canceled" ,"rad etildi"
    class PayType(TextChoices):
        COIN = "coin" , 'tanga'
        MONEY = "money", 'pul'
    card_number = CharField(max_length=16)
    amount=DecimalField(max_digits=12, decimal_places=0)
    status=CharField(choices=PayStatus.choices, default=PayStatus.REVIEW)
    check_photo=ImageField(upload_to="pays/" ,null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    pay_datetime = DateTimeField(auto_now_add=True)
    type=CharField(choices=PayType.choices, default=PayType.MONEY)
    user=ForeignKey('apps.User', on_delete=SET_NULL, related_name="payments", null=True, blank=True)
