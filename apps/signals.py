from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache_keys import CATEGORIES_CACHE_KEY
from .models import Category


@receiver([post_save, post_delete], sender=Category)
def clear_categories_cache(**kwargs):
    cache.delete(CATEGORIES_CACHE_KEY)
