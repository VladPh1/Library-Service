# Library-Service


A Django library management project that allows you to borrow books, 
track your loan, and conveniently pay for loan services.

## Installation

Python3 must be already installed

```shell

Install Celery

git clone https://github.com/VladPh1/Library-Service
cd library-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
set STRIPE_SECRET_KEY = <your secret key>
set TELEGRAM_BOT_TOKEN = <your telegram bot token>
set TELEGRAM_CHAT_ID = <your telegram chat id>

python manage.py runserver # starts Django server
```

## Getting access

* create user via /api/user/register
* get access token via /api/user/token

## Features

* Customer/User Authentication Feature
* Borrows
* Convenient Admin Panel for Advanced Management
* JWT authenticated
* Documentation is located at /api/v1/doc/swagger
* Managing user and borrows and payment
* Creating book with author
* Adding Performance
* Telegram Chat Bot with managing borrows and payments

Test User
```

SuperUser:
email: admin@admin.com
password: 1qazcde3

```
