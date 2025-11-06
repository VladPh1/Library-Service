from django.db import models


class Book(models.Model):
    class CoverChoices(models.TextChoices):
        HARD = "HARD"
        SOFT = "SOFT"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(
        max_length=4,
        choices=CoverChoices.choices,
        default=CoverChoices.HARD,
    )
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.title} (Author: {self.author})"
