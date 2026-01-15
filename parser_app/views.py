from rest_framework import viewsets

from .models import TestRecord
from .serializers import TestRecordSerializer


class TestRecordViewSet(viewsets.ModelViewSet):
    queryset = TestRecord.objects.all().order_by("-created_at")
    serializer_class = TestRecordSerializer
