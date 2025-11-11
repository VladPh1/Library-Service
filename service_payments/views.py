from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import stripe

from service_payments.models import Payment
from service_payments.serializers import PaymentSerializer
from notifications.tasks import send_notification_task


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                enum=Payment.StatusChoices.values,
                description="Filter by payment status",
            ),
            OpenApiParameter(
                name="type",
                type=OpenApiTypes.STR,
                enum=Payment.TypeChoices.values,
                description="Filter by payment type",
            ),
            OpenApiParameter(
                name="borrowing_id",
                type=OpenApiTypes.INT,
                description="Filter by borrowing id (ex. ?borrowing_id=3)",
            ),
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                description=(
                    "Filter by user id" "(ex. ?user_id=2). ( 'borrowing__user_id')"
                ),
            ),
        ],
        responses={200: PaymentSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            queryset = Payment.objects.all()
        else:
            queryset = Payment.objects.filter(borrowing__user=user)
        return queryset.select_related("borrowing", "borrowing__user")

    @action(detail=False, methods=["get"], url_path="success")
    def success(self, request):
        session_id = request.query_params.get("session_id")

        try:
            session = stripe.checkout.Session.retrieve(session_id)

            if session.payment_status == "paid":

                payment = Payment.objects.get(session_id=session_id)
                payment.status = Payment.StatusChoices.PAID
                payment.save()

                message = f"✅ Payment success!\nBorrow ID: {payment.borrowing.id}\nTotal: ${payment.money_to_pay}"
                send_notification_task.delay(message)

                return Response(
                    {"message": f"Payment {payment.id} successful!"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"message": "Payment not successful."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="cancel")
    def cancel(self, request):
        return Response({"message": "Payment cancel."})
