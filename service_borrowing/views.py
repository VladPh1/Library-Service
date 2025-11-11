import stripe
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.exceptions import ValidationError
from .models import Borrowing
from .serializers import BorrowingSerializer
from service_payments.models import Payment


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                description="Filter by user id (ex. ?user_id=1)",
            ),
            OpenApiParameter(
                name="book_id",
                type=OpenApiTypes.INT,
                description="Filter by book id (ex. ?book_id=5)",
            ),
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                description=(
                    "Filter by active (book is bot active). " "ex. ?is_active=true"
                ),
            ),
        ],
        responses={200: BorrowingSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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

                if borrowing.actual_return_date > borrowing.expected_return_date:

                    overdue_days = (
                        borrowing.actual_return_date - borrowing.expected_return_date
                    ).days

                    try:
                        fine_multiplier = settings.FINE_MULTIPLIER
                    except AttributeError:
                        fine_multiplier = 2

                    money_to_pay = (
                        overdue_days * borrowing.book.daily_fee * fine_multiplier
                    )

                    Payment.objects.create(
                        borrowing=borrowing,
                        status=Payment.StatusChoices.PENDING,
                        type=Payment.TypeChoices.FINE,
                        money_to_pay=money_to_pay,
                    )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):

        stripe.api_key = settings.STRIPE_SECRET_KEY

        borrowing = serializer.save(user=self.request.user)

        try:
            days_to_rent = (
                borrowing.expected_return_date - borrowing.borrow_date.date()
            ).days
            money_to_pay = borrowing.book.daily_fee * days_to_rent

            if money_to_pay <= 0:
                raise ValidationError("Incorrect price")

        except Exception as e:
            borrowing.delete()
            raise ValidationError(f"Error calculating price: {e}")

        success_url = (
            self.request.build_absolute_uri(reverse("payment:payment-success"))
            + "?session_id={CHECKOUT_SESSION_ID}"
        )

        cancel_url = self.request.build_absolute_uri(reverse("payment:payment-cancel"))

        try:
            session = stripe.checkout.Session.create(
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Rent book: {borrowing.book.title}",
                            },
                            "unit_amount": int(money_to_pay * 100),
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
            )

            Payment.objects.create(
                borrowing=borrowing,
                session_url=session.url,
                session_id=session.id,
                money_to_pay=money_to_pay,
                status=Payment.StatusChoices.PENDING,
                type=Payment.TypeChoices.PAYMENT,
            )

        except Exception as e:
            borrowing.delete()
            raise ValidationError(f"Stripe error: {str(e)}")
