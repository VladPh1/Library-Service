from django.views.generic import ListView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from service_book.models import Book
from service_book.permissions import IsAdminOrIfAuthenticatedReadOnly
from service_book.serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrIfAuthenticatedReadOnly]
