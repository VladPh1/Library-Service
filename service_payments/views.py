from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

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
