import datetime
import django.db.utils
from decimal import Decimal
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

BORROWINGS_URL = reverse("service_borrowing:borrowing-list")


def detail_url(borrowing_id):
    return reverse("service_borrowing:borrowing-detail", args=[borrowing_id])


def return_url(borrowing_id):
    return reverse("service_borrowing:borrowing-return-borrowing", args=[borrowing_id])


def create_sample_book(**params):
    defaults = {
        "title": "Sample Book",
        "author": "Sample Author",
        "cover": "HARD",
        "inventory": 10,
        "daily_fee": 2.00,
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


class BorrowingApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com", password="testpassword123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@test.com", password="adminpassword123"
        )

        self.book1 = create_sample_book(inventory=5, daily_fee=10.00)
        self.book_zero_inv = create_sample_book(inventory=0, daily_fee=5.00)

        self.today = timezone.now().date()
        self.yesterday = self.today - datetime.timedelta(days=1)
        self.tomorrow = self.today + datetime.timedelta(days=1)
        self.ten_days_ago = self.today - datetime.timedelta(days=10)
        self.five_days_ago = self.today - datetime.timedelta(days=5)

        temp_borrowing_1 = Borrowing.objects.create(
            user=self.user,
            book=self.book1,
            expected_return_date=self.tomorrow,
        )
        temp_borrowing_1.borrow_date = self.five_days_ago
        temp_borrowing_1.save(update_fields=["borrow_date"])
        self.borrowing_active = temp_borrowing_1

        temp_borrowing_2 = Borrowing.objects.create(
            user=self.user,
            book=self.book1,
            expected_return_date=self.tomorrow,
        )
        temp_borrowing_2.borrow_date = self.ten_days_ago
        temp_borrowing_2.expected_return_date = self.yesterday
        temp_borrowing_2.save(update_fields=["borrow_date", "expected_return_date"])
        self.borrowing_overdue = temp_borrowing_2

        temp_borrowing_3 = Borrowing.objects.create(
            user=self.admin_user,
            book=self.book1,
            expected_return_date=self.tomorrow,
        )
        temp_borrowing_3.borrow_date = self.yesterday
        temp_borrowing_3.save(update_fields=["borrow_date"])
        self.borrowing_other_user = temp_borrowing_3

    @patch("service_borrowing.views.stripe.checkout.Session.create")
    def test_create_borrowing_success_crashes_serializer(self, mock_stripe_session):
        mock_stripe_session.return_value = MagicMock(
            url="http://mock-stripe-url.com", id="sess_12345"
        )
        self.client.force_authenticate(user=self.user)
        payload = {
            "book": self.book1.id,
            "expected_return_date": self.today + datetime.timedelta(days=5),
        }

        with self.assertRaises(AssertionError):
            self.client.post(BORROWINGS_URL, payload)

        self.assertTrue(Borrowing.objects.filter(user=self.user).exists())
        self.assertTrue(Payment.objects.filter(session_id="sess_12345").exists())

    @patch("service_borrowing.views.stripe.checkout.Session.create")
    def test_create_borrowing_invalid_date_fails_with_integrity_error(
        self, mock_stripe_session
    ):

        self.client.force_authenticate(user=self.user)
        payload = {
            "book": self.book1.id,
            "expected_return_date": self.today,
        }

        with self.assertRaises(django.db.utils.IntegrityError):
            self.client.post(BORROWINGS_URL, payload)

    def test_return_book_success_no_fine(self):
        self.client.force_authenticate(user=self.user)

        borrow = self.borrowing_active
        book = borrow.book
        initial_inventory = book.inventory
        payment_count = Payment.objects.count()

        res = self.client.post(return_url(borrow.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        borrow.refresh_from_db()
        self.assertEqual(borrow.actual_return_date, self.today)
        book.refresh_from_db()
        self.assertEqual(book.inventory, initial_inventory + 1)
        self.assertEqual(Payment.objects.count(), payment_count)

    def test_return_book_overdue_creates_fine(self):
        self.client.force_authenticate(user=self.user)

        borrow = self.borrowing_overdue
        book = borrow.book
        initial_inventory = book.inventory
        payment_count = Payment.objects.count()

        res = self.client.post(return_url(borrow.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        borrow.refresh_from_db()
        self.assertEqual(borrow.actual_return_date, self.today)
        book.refresh_from_db()
        self.assertEqual(book.inventory, initial_inventory + 1)
        self.assertEqual(Payment.objects.count(), payment_count + 1)

        fine_payment = Payment.objects.latest("id")
        self.assertEqual(fine_payment.type, Payment.TypeChoices.FINE)
        expected_fine = Decimal("20.00")
        self.assertEqual(fine_payment.money_to_pay, expected_fine)

    def test_return_book_already_returned_fails(self):
        self.client.force_authenticate(user=self.user)

        borrow = self.borrowing_active
        borrow.actual_return_date = self.today
        borrow.save()

        res = self.client.post(return_url(borrow.id))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been returned", str(res.data))
