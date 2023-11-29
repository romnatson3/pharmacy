import logging
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from bot.misc import DotAccessibleDict
from bot.tasks import send_message_to_new_user, send_message_before_searching, \
    send_message_not_found, send_message_search_result, send_message_districts, \
    send_message_product_of_the_day
from bot.models import PharmacyStock, User
from bot import texts


def create_new_user(from_user):
    if not User.objects.filter(id=from_user.id).exists():
        user = User.objects.create(
            id=from_user.id,
            username=from_user.username if from_user.username else None,
            first_name=from_user.first_name if from_user.first_name else None,
            last_name=from_user.last_name if from_user.last_name else None,
        )
        logging.info(f'Create new user: {user.id} {user.username} {user.first_name} {user.last_name}')


@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST' and request.headers.get('X-Telegram-Bot-Api-Secret-Token') == settings.X_TELEGRAM_BOT_API_SECRET_TOKEN:
        try:
            body = json.loads(request.body)
            body = DotAccessibleDict(body)
            logging.info(f'\n{body}\n')
        except Exception as e:
            logging.error('Error while parsing request body. Body:{request.body}')
            logging.exception(e)
            return HttpResponse(status=200)

        # return HttpResponse(status=200)

        if body.message.text:
            message = body.message
            logging.info(f'Incoming message from: {message.from_user.id} {message.from_user.username}, {message.text}')

            district = cache.get(f'{message.from_user.id}_district')

            if message.text == '/start':
                if not User.objects.filter(id=message.from_user.id).exists():
                    create_new_user(message.from_user)
                send_message_to_new_user.delay(message.from_user.id)

            elif message.text == texts.search_by_medication_button:
                send_message_districts.delay(message.from_user.id)

            elif message.text == texts.product_of_the_day:
                send_message_product_of_the_day.delay(message.from_user.id)

            elif district and len(message.text) >= 3:
                logging.info(f'User {message.from_user.id} searching: {message.text}')
                if district == 'all_districts':
                    where = Q(medication__name__icontains=message.text)
                else:
                    where = Q(
                        Q(medication__name__icontains=message.text) &
                        Q(pharmacy__district_id=district)
                    )
                stocks = PharmacyStock.objects.filter(where).values_list('id', flat=True)
                if stocks:
                    send_message_search_result.delay(message.from_user.id, list(stocks))
                else:
                    send_message_not_found.delay(message.from_user.id)

            elif district and len(message.text) < 3:
                send_message_before_searching.delay(message.from_user.id)

        if body.callback_query:
            message = body.callback_query
            logging.info(f'Incoming callback_query from: {message.from_user.id} '
                         f'{message.from_user.username}, {message.data}')
            data = body.callback_query.data
            if data:
                logging.info(f'User {message.from_user.id} selected district: {data}')
                cache.set(f'{message.from_user.id}_district', data, timeout=3600)
                send_message_before_searching.delay(message.from_user.id)

        return HttpResponse(status=200)
    return HttpResponse(status=400)
