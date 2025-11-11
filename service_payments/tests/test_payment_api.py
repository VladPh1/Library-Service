import datetime
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from service_book.models import Book
from service_borrowing.models import Borrowing
from service_payments.models import Payment

User = get_user_model()

PAYMENTS_URL = reverse("service_payments:payment-list")
PAYMENT_SUCCESS_URL = reverse("service_payments:payment-success")
PAYMENT_CANCEL_URL = reverse("service_payments:payment-cancel")


def detail_url(payment_id):
    return reverse("service_payments:payment-detail", args=[payment_id])


def create_sample_book(**params):
    defaults = {
        "title": "Sample Book",
        "author": "Sample Author",
        "inventory": 10,
        "daily_fee": 2.00,
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


def create_sample_borrowing(user, book, **params):
    defaults = {
        "expected_return_date": timezone.now().date() + datetime.timedelta(days=5),
        "borrow_date": timezone.now().date(),
    }

    defaults.update(params)

    borrow_date = defaults.pop("borrow_date")

    borrowing = Borrowing.objects.create(user=user, book=book, **defaults)

    borrowing.borrow_date = borrow_date
    borrowing.save(update_fields=["borrow_date"])
    return borrowing


def create_sample_payment(borrowing, **params):
    defaults = {
        "status": Payment.StatusChoices.PENDING,
        "type": Payment.TypeChoices.PAYMENT,
        "session_url": "http://example.com/session",
        "session_id": "sess_123456789",
        "money_to_pay": 10.00,
    }
    defaults.update(params)
    return Payment.objects.create(borrowing=borrowing, **defaults)


class PaymentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com", password="testpassword123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@test.com", password="adminpassword123"
        )

        book = create_sample_book()
        self.borrowing_user = create_sample_borrowing(user=self.user, book=book)
        self.borrowing_admin = create_sample_borrowing(user=self.admin_user, book=book)

        self.payment_user = create_sample_payment(
            self.borrowing_user, session_id="sess_user_payment", money_to_pay=20.00
        )
        self.payment_admin = create_sample_payment(
            self.borrowing_admin,
            session_id="sess_admin_payment",
            money_to_pay=30.00,
            type=Payment.TypeChoices.FINE,
        )

    def test_anonymous_cannot_access_payments(self):
        res_list = self.client.get(PAYMENTS_URL)
        res_detail = self.client.get(detail_url(self.payment_user.id))
        res_success = self.client.get(PAYMENT_SUCCESS_URL)
        res_cancel = self.client.get(PAYMENT_CANCEL_URL)

        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res_detail.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res_success.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res_cancel.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_sees_only_own_payments_list(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(PAYMENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.payment_user.id)
        self.assertEqual(res.data[0]["money_to_pay"], "20.00")

    def test_admin_user_sees_all_payments_list(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(PAYMENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_regular_user_can_retrieve_own_payment(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(detail_url(self.payment_user.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.payment_user.id)

    def test_regular_user_cannot_retrieve_other_payment(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(detail_url(self.payment_admin.id))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_retrieve_any_payment(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(detail_url(self.payment_user.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.payment_user.id)

    @patch("service_payments.views.stripe.checkout.Session.retrieve")
    def test_payment_success_action_updates_status(self, mock_stripe_retrieve):

        mock_stripe_retrieve.return_value = MagicMock(payment_status="paid")

        self.client.force_authenticate(user=self.user)

        self.assertEqual(self.payment_user.status, Payment.StatusChoices.PENDING)

        url = f"{PAYMENT_SUCCESS_URL}?session_id={self.payment_user.session_id}"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("successful", res.data["message"])

        mock_stripe_retrieve.assert_called_with(self.payment_user.session_id)

        self.payment_user.refresh_from_db()
        self.assertEqual(self.payment_user.status, Payment.StatusChoices.PAID)

    @patch("service_payments.views.stripe.checkout.Session.retrieve")
    def test_payment_success_action_not_paid(self, mock_stripe_retrieve):
        mock_stripe_retrieve.return_value = MagicMock(payment_status="pending")
        self.client.force_authenticate(user=self.user)

        url = f"{PAYMENT_SUCCESS_URL}?session_id={self.payment_user.session_id}"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        self.payment_user.refresh_from_db()
        self.assertEqual(self.payment_user.status, Payment.StatusChoices.PENDING)

    @patch("service_payments.views.stripe.checkout.Session.retrieve")
    def test_payment_success_action_payment_not_found(self, mock_stripe_retrieve):
        mock_stripe_retrieve.return_value = MagicMock(payment_status="paid")
        self.client.force_authenticate(user=self.user)

        url = f"{PAYMENT_SUCCESS_URL}?session_id=fake_session_id_123"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Payment not found", res.data["error"])

    def test_payment_cancel_action(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(PAYMENT_CANCEL_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["message"], "Payment cancel.")

    def test_user_can_delete_own_payment(self):

        self.client.force_authenticate(user=self.user)
        payment_count = Payment.objects.count()

        res = self.client.delete(detail_url(self.payment_user.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Payment.objects.count(), payment_count - 1)

    def test_user_cannot_delete_other_payment(self):
        self.client.force_authenticate(user=self.user)
        payment_count = Payment.objects.count()

        res = self.client.delete(detail_url(self.payment_admin.id))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Payment.objects.count(), payment_count)
