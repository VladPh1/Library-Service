from celery import shared_task
from .telegram_bot import send_telegram_message
from django.utils import timezone
from service_borrowing.models import Borrowing


@shared_task
def send_notification_task(message):

    send_telegram_message(message)


@shared_task
def check_overdue_borrowings():

    today = timezone.now().date()
    overdue_list = Borrowing.objects.filter(
        actual_return_date__isnull=True, expected_return_date__lt=today
    )

    if not overdue_list.exists():
        message = "🎉 There are no overdue borrow today.!"
        send_telegram_message(message)
        return "No overdue borrowings."

    message_lines = ["🔔 ATTENTION! Overdue borrow:\n"]
    for borrowing in overdue_list:
        message_lines.append(
            f"• ID: {borrowing.id}, Book: {borrowing.book.title}, "
            f"User: {borrowing.user.email}"
        )

    send_telegram_message("\n".join(message_lines))
    return f"Sent notifications for {len(message_lines) - 1} overdue borrowings."
