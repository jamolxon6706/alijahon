from django.core.cache import cache

from .cache_keys import CATEGORIES_CACHE_KEY, CATEGORIES_CACHE_TIMEOUT
from .cart import get_cart_count
from .models import Category


def get_cached_categories():
    categories = cache.get(CATEGORIES_CACHE_KEY)
    if categories is None:
        categories = list(Category.objects.all())
        cache.set(CATEGORIES_CACHE_KEY, categories, timeout=CATEGORIES_CACHE_TIMEOUT)
    return categories

def categories_processor(request):
    return {"categories": get_cached_categories()}


def cart_processor(request):
    return {"cart_count": get_cart_count(request)}
