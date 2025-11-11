from django.urls import path, include
from rest_framework import routers

from service_borrowing.views import BorrowingViewSet


router = routers.DefaultRouter()
router.register("borrows", BorrowingViewSet)

urlpatterns = [path("", include(router.urls))]

app_name = "service_borrowing"
