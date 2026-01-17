import django_filters
from django.db.models import Q

from .models import Product


class ProductFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    manufacturer = django_filters.CharFilter(field_name="manufacturer", lookup_expr='icontains')
    color = django_filters.CharFilter(field_name="color", lookup_expr='icontains')
    
    class Meta:
        model = Product
        fields = {
            'name': ['icontains', 'iexact'],
            'product_code': ['exact', 'icontains'],
            'storage': ['exact', 'icontains'],
            'screen_diagonal': ['exact', 'icontains'],
            'display_resolution': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte', 'gt', 'lt'],
            'updated_at': ['exact', 'gte', 'lte', 'gt', 'lt'],
        }
    
    def filter_search(self, queryset, name, value):
        """Search in multiple fields."""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(product_code__icontains=value) |
            Q(manufacturer__icontains=value) |
            Q(characteristics__icontains=value)
        )
