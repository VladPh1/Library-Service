from rest_framework import viewsets

from service_borrowing.models import Borrowing
from service_borrowing.serializers import BorrowingSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
