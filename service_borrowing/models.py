from django.conf import settings
from django.db import models

from service_book.models import Book
from user.models import User


class Borrowing(models.Model):
    borrow_date = models.DateField(
        auto_now_add=True,
    )
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(
        null=True,
        blank=True,
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowing")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowing"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(expected_return_date__gt=models.F("borrow_date")),
                name="expected_return_date_must_be_after_borrow_date",
            )
        ]

    def __str__(self):
        return (
            f"Book: {self.book.title},"
            f"Borrow: {self.user.email} - {self.borrow_date}"
        )
