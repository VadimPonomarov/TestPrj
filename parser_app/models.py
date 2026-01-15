from django.db import models

from core.models import TimeStampedModel


class Product(TimeStampedModel):
    name = models.CharField(max_length=500)
    product_code = models.CharField(max_length=100, unique=True)
    source_url = models.URLField(max_length=1000, unique=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    manufacturer = models.CharField(max_length=200, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    storage = models.CharField(max_length=100, null=True, blank=True)

    review_count = models.PositiveIntegerField(default=0)
    screen_diagonal = models.CharField(max_length=100, null=True, blank=True)
    display_resolution = models.CharField(max_length=100, null=True, blank=True)

    images = models.JSONField(default=list, blank=True)
    characteristics = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(TimeStampedModel.Meta):
        db_table = "products"
        ordering = ["-created_at"]

