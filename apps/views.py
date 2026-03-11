from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.paginator import Paginator
from datetime import timedelta
from decimal import Decimal
import secrets
import json
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView, DetailView, CreateView
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode

from .cart import get_cart, save_cart, build_cart_items, get_cart_totals, get_cart_count
from .context_processors import get_cached_categories
from .forms import RegisterModelForm, ProfileForm, LoginForm, OtpForm
from .models import Category, Product, Order

User = get_user_model()

WISHLIST_CACHE_PREFIX = "wishlist"
WISHLIST_CACHE_TIMEOUT = 60 * 60 * 24 * 30
def _generate_otp_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _wishlist_cache_key(user_id):
    return f"{WISHLIST_CACHE_PREFIX}:user:{user_id}"


def _normalize_wishlist_ids(raw_ids):
    if not raw_ids:
        return []
    cleaned = []
    seen = set()
    for value in raw_ids:
        try:
            product_id = int(value)
        except (TypeError, ValueError):
            continue
        if product_id in seen:
            continue
        seen.add(product_id)
        cleaned.append(product_id)
    return cleaned


def _get_wishlist_ids_for_user(user_id):
    key = _wishlist_cache_key(user_id)
    raw_ids = cache.get(key) or []
    normalized = _normalize_wishlist_ids(raw_ids)
    if raw_ids != normalized:
        cache.set(key, normalized, timeout=WISHLIST_CACHE_TIMEOUT)
    return normalized


def _wishlist_ids(request):
    if not request.user.is_authenticated:
        return []
    return _get_wishlist_ids_for_user(request.user.id)


def _safe_next_url(request, fallback):
    next_url = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER")
    if not next_url:
        return fallback
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


class MainListView(TemplateView):
    template_name = "apps/main.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = get_cached_categories()
        ctx["products"] = Product.objects.select_related("category").prefetch_related("photos")[:12]
        three_days_ago = timezone.now() - timedelta(days=3)
        new_products_qs = (
            Product.objects.select_related("category")
            .prefetch_related("photos")
            .filter(created_at__gte=three_days_ago)
            .order_by("-created_at")
        )
        new_products = list(new_products_qs[:12])
        if not new_products:
            new_products = list(
                Product.objects.select_related("category")
                .prefetch_related("photos")
                .order_by("-id")[:12]
            )
        ctx["new_products"] = new_products
        ctx["wishlist_ids"] = _wishlist_ids(self.request)
        return ctx


class ProductListView(TemplateView):
    template_name = "apps/product-list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        category_id = self.kwargs.get("category_id")
        category = None
        products = Product.objects.select_related("category").prefetch_related("photos")
        if category_id:
            if int(category_id) != 0:
                category = get_object_or_404(Category, pk=category_id)
                products = products.filter(category=category)
        products = products.order_by("-id")
        paginator = Paginator(products, 50)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        ctx["category"] = category
        ctx["categories"] = get_cached_categories()
        ctx["products"] = page_obj.object_list
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["is_paginated"] = page_obj.has_other_pages()
        ctx["selected_category_id"] = category.id if category else 0
        ctx["wishlist_ids"] = _wishlist_ids(self.request)
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = "apps/order/product-detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.select_related("category").prefetch_related("photos")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["wishlist_ids"] = _wishlist_ids(self.request)
        cart_map = get_cart(self.request, create=False) or {}
        quantity = cart_map.get(self.object.id)
        ctx["in_cart"] = bool(quantity)
        ctx["cart_quantity"] = quantity if quantity else 1
        related_products = (
            Product.objects.filter(category_id=self.object.category_id)
            .exclude(pk=self.object.pk)
            .select_related("category")
            .prefetch_related("photos")
            .order_by("-created_at", "-id")[:8]
        )
        ctx["related_products"] = related_products
        return ctx


class OrderCreateView(View):
    def get(self, request):
        return redirect("main")

    def post(self, request):
        product_id = request.POST.get("product")
        if not product_id:
            return redirect("main")
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return redirect("main")
        product = get_object_or_404(Product, pk=product_id)

        first_name = request.POST.get("first_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        try:
            quantity = int(request.POST.get("quantity", "1") or 1)
        except (TypeError, ValueError):
            quantity = 1
        if quantity < 1:
            quantity = 1

        order = Order.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            first_name=first_name,
            phone_number=phone_number,
            quantity=quantity,
        )
        return redirect("order-success", pk=order.pk)


class OrderSuccessView(DetailView):
    model = Order
    template_name = "apps/order/order-success.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order = ctx.get("order")
        if order:
            ctx["total"] = order.quantity * order.product.price
        return ctx


class LoginView(View):
    template_name = "apps/login.html"

    def get(self, request):
        form = LoginForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        phone_number = form.cleaned_data["phone_number"]
        password = form.cleaned_data["password"]

        user = authenticate(request, username=phone_number, password=password)
        if user is None:
            form.add_error(None, "Telefon yoki parol xato")
            return render(request, self.template_name, {"form": form})

        login(request, user)
        return redirect("main")


class RegisterView(View):
    template_name = "apps/register.html"

    def get(self, request):
        request.session.pop("pending_register", None)
        request.session.pop("pending_register_otp", None)
        form = RegisterModelForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = RegisterModelForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        otp_code = _generate_otp_code()
        request.session["pending_register"] = {
            "phone_number": form.cleaned_data.get("phone_number"),
            "password": form.cleaned_data.get("password"),
            "confirm_password": form.cleaned_data.get("confirm_password"),
        }
        request.session["pending_register_otp"] = otp_code
        return redirect("register-otp")


class RegisterOtpView(View):
    template_name = "apps/register-otp.html"

    def _pending(self, request):
        return request.session.get("pending_register") or {}

    def get(self, request):
        pending = self._pending(request)
        otp_code = request.session.get("pending_register_otp")
        if not pending.get("phone_number") or not otp_code:
            return redirect("register")
        form = OtpForm()
        phone_display = f"+998{pending.get('phone_number')}"
        return render(
            request,
            self.template_name,
            {"form": form, "phone": phone_display, "otp_code": otp_code},
        )

    def post(self, request):
        pending = self._pending(request)
        otp_code = request.session.get("pending_register_otp")
        if not pending.get("phone_number") or not otp_code:
            return redirect("register")
        form = OtpForm(request.POST)
        if not form.is_valid():
            phone_display = f"+998{pending.get('phone_number')}"
            return render(
                request,
                self.template_name,
                {"form": form, "phone": phone_display, "otp_code": otp_code},
            )

        if form.cleaned_data.get("otp_code") != otp_code:
            form.add_error("otp_code", "OTP kodi noto'g'ri.")
            phone_display = f"+998{pending.get('phone_number')}"
            return render(
                request,
                self.template_name,
                {"form": form, "phone": phone_display, "otp_code": otp_code},
            )

        register_form = RegisterModelForm(data=pending)
        if not register_form.is_valid():
            phone_display = f"+998{pending.get('phone_number')}"
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "phone": phone_display,
                    "otp_code": otp_code,
                    "register_errors": register_form.errors,
                },
            )

        user = register_form.save()
        login(request, user)
        request.session.pop("pending_register", None)
        request.session.pop("pending_register_otp", None)
        return redirect("main")


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("main")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "apps/profile.html"

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            if form.password_changed:
                update_session_auth_hash(request, user)
            return redirect("profile")
        ctx = self.get_context_data(form=form)
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = kwargs.get("form") or ProfileForm(instance=self.request.user)
        delete_otp = self.request.session.get("delete_otp")
        ctx["delete_otp"] = delete_otp
        ctx["show_delete_otp"] = bool(delete_otp) and self.request.GET.get("delete_otp") == "1"
        return ctx


class ProfileDeleteOtpRequestView(LoginRequiredMixin, View):
    def post(self, request):
        request.session["delete_otp"] = _generate_otp_code()
        return redirect(f"{reverse('profile')}?delete_otp=1")


class ProfileDeleteView(LoginRequiredMixin, View):
    def post(self, request):
        otp_code = request.session.get("delete_otp")
        if not otp_code:
            messages.error(request, "OTP yuborilmagan. Iltimos, avval tasdiqlang.")
            return redirect("profile")

        form = OtpForm(request.POST)
        if not form.is_valid() or form.cleaned_data.get("otp_code") != otp_code:
            messages.error(request, "OTP kodi noto'g'ri.")
            return redirect(f"{reverse('profile')}?delete_otp=1")

        user = request.user
        logout(request)
        user.delete()
        request.session.pop("delete_otp", None)
        return redirect("main")


class OrderHistoryView(LoginRequiredMixin, TemplateView):
    template_name = "apps/order/order-history.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["orders"] = (
            Order.objects.filter(user=self.request.user)
            .select_related("product")
            .order_by("-created_at")
        )
        return ctx


class MarketView(TemplateView):
    template_name = "apps/market/market.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = get_cached_categories()
        category_id = int(self.kwargs.get("category_id", 0) or 0)
        query = (self.request.GET.get("q") or "").strip()
        min_price_raw = (self.request.GET.get("min_price") or "").strip()
        max_price_raw = (self.request.GET.get("max_price") or "").strip()
        sort = (self.request.GET.get("sort") or "new").strip()
        in_stock = (self.request.GET.get("in_stock") or "").strip() == "1"
        products = Product.objects.select_related("category").prefetch_related("photos")
        if category_id:
            products = products.filter(category_id=category_id)
        if query:
            products = products.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if min_price_raw:
            try:
                min_price_val = int(min_price_raw)
            except (TypeError, ValueError):
                min_price_val = None
            if min_price_val is not None and min_price_val >= 0:
                products = products.filter(price__gte=min_price_val)
        if max_price_raw:
            try:
                max_price_val = int(max_price_raw)
            except (TypeError, ValueError):
                max_price_val = None
            if max_price_val is not None and max_price_val >= 0:
                products = products.filter(price__lte=max_price_val)
        if in_stock:
            products = products.filter(quantity__gt=0)
        if sort == "price_asc":
            products = products.order_by("price", "-id")
        elif sort == "price_desc":
            products = products.order_by("-price", "-id")
        elif sort == "oldest":
            products = products.order_by("id")
        else:
            products = products.order_by("-id")
        paginator = Paginator(products, 50)
        page_obj = paginator.get_page(self.request.GET.get("page"))
        ctx["products"] = page_obj.object_list
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["is_paginated"] = page_obj.has_other_pages()
        ctx["choice_category"] = category_id
        ctx["query"] = query
        ctx["min_price"] = min_price_raw
        ctx["max_price"] = max_price_raw
        ctx["sort"] = sort
        ctx["in_stock"] = in_stock
        filter_params = {}
        if query:
            filter_params["q"] = query
        if min_price_raw:
            filter_params["min_price"] = min_price_raw
        if max_price_raw:
            filter_params["max_price"] = max_price_raw
        if in_stock:
            filter_params["in_stock"] = "1"
        if sort and sort != "new":
            filter_params["sort"] = sort
        ctx["filter_querystring"] = urlencode(filter_params)
        ctx["wishlist_ids"] = _wishlist_ids(self.request)
        return ctx


class SearchView(TemplateView):
    template_name = "apps/product-list.html"

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def _get_query(self):
        if self.request.method == "POST":
            query = self.request.POST.get("product") or self.request.POST.get("q") or ""
        else:
            query = self.request.GET.get("product") or self.request.GET.get("q") or ""
        return (query or "").strip()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = self._get_query()
        products = Product.objects.select_related("category").prefetch_related("photos")
        if query:
            products = products.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        products = products.order_by("-id")
        paginator = Paginator(products, 50)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        ctx["categories"] = get_cached_categories()
        ctx["products"] = page_obj.object_list
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["is_paginated"] = page_obj.has_other_pages()
        ctx["search_query"] = query
        ctx["wishlist_ids"] = _wishlist_ids(self.request)
        return ctx


class SurveyView(TemplateView):
    template_name = "apps/survey.html"


class WishlistToggleView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": "login_required", "redirect_url": reverse("login")},
                status=401,
            )

        product_id = request.POST.get("product_id")
        if not product_id and request.body:
            try:
                payload = json.loads(request.body.decode("utf-8"))
                product_id = payload.get("product_id")
            except (TypeError, ValueError, json.JSONDecodeError):
                product_id = None

        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return JsonResponse({"detail": "invalid_product"}, status=400)

        get_object_or_404(Product, pk=product_id)
        key = _wishlist_cache_key(request.user.id)
        wishlist_ids = _get_wishlist_ids_for_user(request.user.id)
        if product_id in wishlist_ids:
            wishlist_ids = [pid for pid in wishlist_ids if pid != product_id]
            liked = False
        else:
            wishlist_ids = [product_id] + wishlist_ids
            liked = True
        cache.set(key, wishlist_ids, timeout=WISHLIST_CACHE_TIMEOUT)

        return JsonResponse(
            {
                "liked": liked,
                "product_id": product_id,
            }
        )



class CartView(TemplateView):
    template_name = "apps/cart/cart.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cart_map = get_cart(self.request, create=False)
        items = build_cart_items(cart_map) if cart_map else []
        total_items, total_price = get_cart_totals(items)
        item_ids = [item.get("id") for item in items]
        selected_ids = self.request.session.pop("cart_selected_ids", None)
        if selected_ids:
            cleaned_selected = []
            item_id_set = set(item_ids)
            for raw_id in selected_ids:
                try:
                    product_id = int(raw_id)
                except (TypeError, ValueError):
                    continue
                if product_id not in item_id_set:
                    continue
                if product_id in cleaned_selected:
                    continue
                cleaned_selected.append(product_id)
            selected_ids = cleaned_selected
        if not selected_ids:
            selected_ids = item_ids
        ctx["cart"] = cart_map
        ctx["cart_items"] = items
        ctx["total_items"] = total_items
        ctx["total_price"] = total_price
        ctx["selected_ids"] = selected_ids
        ctx["all_selected"] = bool(item_ids) and len(selected_ids) == len(item_ids)
        return ctx


class CartAddView(View):
    def post(self, request):
        product_id = request.POST.get("product") or request.POST.get("product_id")
        if not product_id:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"detail": "missing_product"}, status=400)
            return redirect(_safe_next_url(request, reverse("cart")))
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"detail": "invalid_product"}, status=400)
            return redirect(_safe_next_url(request, reverse("cart")))

        product = get_object_or_404(Product, pk=product_id)
        try:
            quantity = int(request.POST.get("quantity", "1") or 1)
        except (TypeError, ValueError):
            quantity = 1
        if quantity < 1:
            quantity = 1

        cart_map = get_cart(request, create=True) or {}
        cart_map[product_id] = cart_map.get(product_id, 0) + quantity
        save_cart(request, cart_map)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "detail": "ok",
                    "product_id": product_id,
                    "quantity": cart_map.get(product_id, 0),
                    "cart_count": get_cart_count(request),
                }
            )

        return redirect(_safe_next_url(request, reverse("cart")))


class CartUpdateView(View):
    def post(self, request, item_id):
        cart_map = get_cart(request, create=True) or {}
        product_id = int(item_id)
        if product_id not in cart_map:
            return redirect(_safe_next_url(request, reverse("cart")))
        try:
            quantity = int(request.POST.get("quantity", cart_map.get(product_id, 1)) or cart_map.get(product_id, 1))
        except (TypeError, ValueError):
            quantity = cart_map.get(product_id, 1)

        if quantity < 1:
            cart_map.pop(product_id, None)
        else:
            cart_map[product_id] = quantity
        save_cart(request, cart_map)

        return redirect(_safe_next_url(request, reverse("cart")))


class CartRemoveView(View):
    def post(self, request, item_id):
        cart_map = get_cart(request, create=True) or {}
        product_id = int(item_id)
        if product_id in cart_map:
            cart_map.pop(product_id, None)
            save_cart(request, cart_map)
        return redirect(_safe_next_url(request, reverse("cart")))


class CartOrderView(View):
    def post(self, request):
        cart_map = get_cart(request, create=True) or {}
        if not cart_map:
            return redirect(_safe_next_url(request, reverse("cart")))

        selected_ids = request.POST.getlist("selected_items")
        if not selected_ids:
            messages.error(request, "Iltimos, buyurtma uchun mahsulot tanlang.")
            return redirect(_safe_next_url(request, reverse("cart")))
        cleaned_ids = []
        for raw_id in selected_ids:
            try:
                product_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if product_id in cart_map:
                cleaned_ids.append(product_id)
        if not cleaned_ids:
            messages.error(request, "Tanlangan mahsulotlar topilmadi.")
            return redirect(_safe_next_url(request, reverse("cart")))

        first_name = (request.POST.get("first_name") or "").strip()
        phone_number = (request.POST.get("phone_number") or "").strip()
        if not first_name or not phone_number:
            messages.error(request, "Ism va telefon raqamni kiriting.")
            request.session["cart_selected_ids"] = cleaned_ids
            return redirect(_safe_next_url(request, reverse("cart")))

        products = Product.objects.filter(id__in=cleaned_ids)
        product_map = {product.id: product for product in products}
        items = []
        for product_id in cleaned_ids:
            product = product_map.get(product_id)
            quantity = cart_map.get(product_id)
            if not product or not quantity:
                continue
            items.append((product_id, product, quantity))
        if not items:
            messages.error(request, "Tanlangan mahsulotlar topilmadi.")
            return redirect(_safe_next_url(request, reverse("cart")))

        total_before = Decimal("0")
        for _, product, quantity in items:
            total_before += product.price * int(quantity)

        created_orders = []
        for product_id, product, quantity in items:
            order = Order.objects.create(
                product=product,
                user=request.user if request.user.is_authenticated else None,
                first_name=first_name,
                phone_number=phone_number,
                quantity=quantity,
            )
            created_orders.append(order)

        for product_id, _, _ in items:
            cart_map.pop(product_id, None)
        save_cart(request, cart_map)

        if len(created_orders) == 1:
            return redirect("order-success", pk=created_orders[0].pk)

        messages.success(request, f"{len(created_orders)} ta buyurtma yaratildi.")
        return redirect(_safe_next_url(request, reverse("cart")))


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "apps/wishlist/wishlist.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wishlist_ids = _wishlist_ids(self.request)
        if wishlist_ids:
            products = (
                Product.objects.filter(id__in=wishlist_ids)
                .prefetch_related("photos")
            )
            product_map = {product.id: product for product in products}
            items = [{"product": product_map[pid]} for pid in wishlist_ids if pid in product_map]
        else:
            items = []
        ctx["wishlist_items"] = items
        ctx["wishlist_ids"] = wishlist_ids
        return ctx


class SellerPaymentCreateView(CreateView):
    pass
