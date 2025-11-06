from django.views.generic import ListView
from rest_framework import viewsets

from service_book.models import Book
from service_book.serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
