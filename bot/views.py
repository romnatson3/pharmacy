import logging
import json
import re
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from bot.misc import DotAccessibleDict
from bot.tasks import send_message_the_first, send_message_before_searching, \
    send_message_not_found, send_message_search_result, send_message_districts, \
    send_message_product_of_the_day, send_message_medication_buttons, \
    send_message_pharmacy_address
from bot.models import PharmacyStock, User
from bot import texts


CACHE_TIMEOUT = 3600


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

            if message.text == '/start':
                if not User.objects.filter(id=message.from_user.id).exists():
                    create_new_user(message.from_user)
                send_message_the_first.delay(message.from_user.id)
                return HttpResponse(status=200)

            if message.text == texts.search_by_medication_button:
                cache.delete(f'{message.from_user.id}_district')
                send_message_districts.delay(message.from_user.id)
                return HttpResponse(status=200)

            if message.text == texts.product_of_the_day_button:
                send_message_product_of_the_day.delay(message.from_user.id)
                return HttpResponse(status=200)

            district = cache.get(f'{message.from_user.id}_district')
            if not district:
                send_message_the_first.delay(message.from_user.id, start=False)
                return HttpResponse(status=200)

            if '⠀' in message.text: # U+2800
                text = re.sub(r'💊|⠀', '', message.text).strip()
                logging.info(f'User {message.from_user.id} selected medication: {text}')
                send_message_search_result.delay(message.from_user.id, text)

            elif len(message.text) >= 3:
                logging.info(f'User {message.from_user.id} searching: {message.text}')
                if district == 'all':
                    where = Q(medication__name__icontains=message.text)
                else:
                    where = Q(
                        Q(medication__name__icontains=message.text) &
                        Q(pharmacy__district_id=district)
                    )
                medication_ids = PharmacyStock.objects.filter(where).values_list('medication_id', flat=True).distinct()
                if medication_ids:
                    send_message_medication_buttons.delay(message.from_user.id, list(medication_ids))
                else:
                    send_message_not_found.delay(message.from_user.id)

            else:
                send_message_before_searching.delay(message.from_user.id)

        if body.callback_query:
            message = body.callback_query
            logging.info(f'Incoming callback_query from: {message.from_user.id} '
                         f'{message.from_user.username}, {message.data}')
            data = body.callback_query.data

            if 'district' in data:
                _, district_id = data.split('_')
                logging.info(f'User {message.from_user.id} selected district: {data}')
                cache.set(f'{message.from_user.id}_district', district_id, timeout=CACHE_TIMEOUT)
                send_message_before_searching.delay(message.from_user.id)

            elif 'chain' in data:
                _, chain_id = data.split('_')
                logging.info(f'User {message.from_user.id} selected chain: {chain_id}')
                send_message_pharmacy_address.delay(message.from_user.id, chain_id)

        return HttpResponse(status=200)
    return HttpResponse(status=400)
