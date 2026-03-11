from decimal import Decimal

from django.core.cache import cache

from .models import Product

CART_CACHE_PREFIX = "cart"
CART_CACHE_TIMEOUT = 60 * 60 * 24 * 7


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _cart_key_for_user(user_id):
    return f"{CART_CACHE_PREFIX}:user:{user_id}"


def _cart_key_for_session(session_key):
    return f"{CART_CACHE_PREFIX}:session:{session_key}"


def _get_cart_key(request, create=False):
    if request.user.is_authenticated:
        return _cart_key_for_user(request.user.id)

    session_key = request.session.session_key
    if not session_key and create:
        session_key = _ensure_session_key(request)
    if not session_key:
        return None
    return _cart_key_for_session(session_key)


def _load_cart_by_key(key, create=False):
    if not key:
        return None
    cart_map = cache.get(key)
    if cart_map is None:
        if not create:
            return None
        cart_map = {}
        cache.set(key, cart_map, timeout=CART_CACHE_TIMEOUT)
    normalized = {}
    for product_id, quantity in cart_map.items():
        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if quantity < 1:
            continue
        normalized[product_id] = quantity
    if cart_map and normalized != cart_map:
        cache.set(key, normalized, timeout=CART_CACHE_TIMEOUT)
    return normalized


def _merge_cart_maps(target, source):
    for product_id, quantity in source.items():
        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            continue
        if quantity < 1:
            continue
        target[product_id] = target.get(product_id, 0) + quantity


def get_cart(request, create=False):
    if request.user.is_authenticated:
        user_key = _cart_key_for_user(request.user.id)
        cart_map = _load_cart_by_key(user_key, create=create)
        if cart_map is None and create:
            cart_map = {}

        if create:
            session_key = request.session.session_key
            if session_key:
                anon_key = _cart_key_for_session(session_key)
                anon_cart = _load_cart_by_key(anon_key, create=False)
                if anon_cart:
                    cart_map = cart_map or {}
                    _merge_cart_maps(cart_map, anon_cart)
                    cache.delete(anon_key)
                    cache.set(user_key, cart_map, timeout=CART_CACHE_TIMEOUT)

        return cart_map

    session_key = request.session.session_key
    if not session_key:
        if not create:
            return None
        session_key = _ensure_session_key(request)

    cart_key = _cart_key_for_session(session_key)
    cart_map = _load_cart_by_key(cart_key, create=create)
    if cart_map is None and create:
        cart_map = {}
    return cart_map


def save_cart(request, cart_map):
    if not cart_map:
        key = _get_cart_key(request, create=False)
        if key:
            cache.delete(key)
        return

    key = _get_cart_key(request, create=True)
    if not key:
        return
    cache.set(key, cart_map, timeout=CART_CACHE_TIMEOUT)


def get_cart_count(request):
    cart_map = get_cart(request, create=False)
    if not cart_map:
        return 0
    total = 0
    for quantity in cart_map.values():
        try:
            total += int(quantity)
        except (TypeError, ValueError):
            continue
    return total


def build_cart_items(cart_map):
    if not cart_map:
        return []

    product_ids = []
    for product_id in cart_map.keys():
        try:
            product_ids.append(int(product_id))
        except (TypeError, ValueError):
            continue
    products = Product.objects.filter(id__in=product_ids).prefetch_related("photos")
    product_map = {product.id: product for product in products}

    items = []
    for product_id in product_ids:
        product = product_map.get(product_id)
        if not product:
            continue
        try:
            quantity = int(cart_map.get(product_id, 0))
        except (TypeError, ValueError):
            continue
        if quantity < 1:
            continue
        line_total = product.price * quantity
        items.append(
            {
                "id": product_id,
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
            }
        )
    return items


def get_cart_totals(items):
    total_items = 0
    total_price = Decimal("0")
    for item in items:
        quantity = item.get("quantity", 0)
        line_total = item.get("line_total", 0)
        try:
            total_items += int(quantity)
        except (TypeError, ValueError):
            pass
        try:
            total_price += Decimal(line_total)
        except (TypeError, ValueError, ArithmeticError):
            pass
    return total_items, total_price
