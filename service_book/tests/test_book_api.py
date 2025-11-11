from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from service_book.models import Book
from service_book.serializers import BookSerializer


BOOKS_URL = reverse("service_book:book-list")


def detail_url(book_id):
    return reverse("service_book:book-detail", args=[book_id])


def create_sample_book(**params):
    defaults = {
        "title": "Sample Book",
        "author": "Sample Author",
        "cover": "HARD",
        "inventory": 10,
        "daily_fee": 1.99,
    }
    defaults.update(params)
    return Book.objects.create(**defaults)


class BookApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="testpasswod123"
        )
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@test.com", password="adminpassword123"
        )

        self.book1 = create_sample_book(title="Dune", author="Frank Herbert")
        self.book2 = create_sample_book(
            title="Catcher in the Rye", author="Salinger", cover="SOFT"
        )

        self.serializer1 = BookSerializer(self.book1)
        self.serializer2 = BookSerializer(self.book2)

    def test_anonymous_cannot_list_books(self):
        res = self.client.get(BOOKS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_create_book(self):
        payload = {
            "title": "New",
            "author": "New",
            "inventory": 1,
            "daily_fee": 1,
        }
        res = self.client.post(BOOKS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_list_books(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(BOOKS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertIn(self.serializer1.data, res.data)
        self.assertIn(self.serializer2.data, res.data)

    def test_authenticated_user_can_retrieve_book(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(detail_url(self.book1.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, self.serializer1.data)

    def test_authenticated_user_cannot_create_book(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "title": "Forbidden Book",
            "author": "User",
            "inventory": 5,
            "daily_fee": 2.50,
            "cover": "SOFT",
        }
        res = self.client.post(BOOKS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_cannot_update_book(self):
        self.client.force_authenticate(user=self.user)
        payload = {"title": "Updated Title"}
        res = self.client.patch(detail_url(self.book1.id), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_cannot_delete_book(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.delete(detail_url(self.book1.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_create_book(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "title": "Admin's Book",
            "author": "Admin",
            "inventory": 20,
            "daily_fee": 5.00,
            "cover": "HARD",
        }
        res = self.client.post(BOOKS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        book_exists = Book.objects.filter(title="Admin's Book").exists()
        self.assertTrue(book_exists)
        self.assertEqual(res.data["title"], payload["title"])

    def test_admin_user_can_update_book(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"title": "Updated by Admin", "inventory": 99}
        res = self.client.patch(detail_url(self.book1.id), payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.book1.refresh_from_db()
        self.assertEqual(self.book1.title, payload["title"])
        self.assertEqual(self.book1.inventory, payload["inventory"])

    def test_admin_user_can_delete_book(self):
        self.client.force_authenticate(user=self.admin_user)
        self.assertEqual(Book.objects.count(), 2)

        res = self.client.delete(detail_url(self.book1.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Book.objects.count(), 1)
        book_exists = Book.objects.filter(id=self.book1.id).exists()
        self.assertFalse(book_exists)
