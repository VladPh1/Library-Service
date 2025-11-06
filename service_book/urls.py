from django.urls import path, include
from rest_framework import routers

from service_book.views import BookViewSet


router = routers.DefaultRouter()
router.register("books", BookViewSet)

urlpatterns = [path("", include(router.urls))]

app_name = "service_book"
