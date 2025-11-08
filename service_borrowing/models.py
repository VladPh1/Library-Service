from django.db import models

from service_book.models import Book
from user.models import User


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField()
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return (f"Book: {self.book},"
                f"Borrow date: {self.borrow_date},"
                f"Expected date: {self.expected_return_date},"
                f"Actual return date: {self.actual_return_date}")
