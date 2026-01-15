from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }
