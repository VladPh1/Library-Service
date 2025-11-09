from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import stripe

from service_payments.models import Payment
from service_payments.serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

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
