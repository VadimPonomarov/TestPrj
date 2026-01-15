from django.db import models

from core.models import TimeStampedModel


class TestRecord(TimeStampedModel):
    title = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.title
