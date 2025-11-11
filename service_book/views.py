from django.views.generic import ListView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from service_book.models import Book
from service_book.permissions import IsAdminOrIfAuthenticatedReadOnly
from service_book.serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrIfAuthenticatedReadOnly]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                description="Filter by title (ex. ?title=dune)",
            ),
            OpenApiParameter(
                name="author",
                type=OpenApiTypes.STR,
                description="Filter by author (ex. ?author=herbert)",
            ),
            OpenApiParameter(
                name="cover",
                type=OpenApiTypes.STR,
                enum=Book.CoverChoices.values,
                description="Filter by cover",
            ),
            OpenApiParameter(
                name="inventory_min",
                type=OpenApiTypes.INT,
                description="Filter by inventory (ex. ?inventory_min=1)",
            ),
            OpenApiParameter(
                name="daily_fee_max",
                type=OpenApiTypes.DECIMAL,
                description="Filter by daily max (ex. ?daily_fee_max=15.50)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
