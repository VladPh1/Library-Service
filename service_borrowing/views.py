# In borrowings/views.py

from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Borrowing
from .serializers import BorrowingSerializer


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer

    @action(detail=True, methods=["post"], url_path="return")
    def return_borrowing(self, request, pk=None):

        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response(
                {"error": "This borrowing has already been returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                borrowing.actual_return_date = timezone.now().date()
                borrowing.save()

                book = borrowing.book
                book.inventory += 1
                book.save()

                # if borrowing.actual_return_date > borrowing.expected_return_date:
                #    create_fine_payment(borrowing)
                #    pass

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data, status=status.HTTP_200_OK)
