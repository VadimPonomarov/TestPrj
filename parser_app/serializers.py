from core.serializers import BaseModelSerializer
from .models import TestRecord


class TestRecordSerializer(BaseModelSerializer):
    class Meta:
        model = TestRecord
        fields = ["id", "title", "created_at", "updated_at"]
