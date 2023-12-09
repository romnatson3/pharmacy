import logging
import json
from celery.utils.log import get_task_logger
from app.celery import app
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value, F, Q
from django.core.cache import cache
from bot.misc import send_message, batched
from bot import texts
from bot.models import PharmacyStock, District, ProductOfTheDay, Medication, Pharmacy


logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)
CACHE_TIMEOUT = 3600

# from django.db import connection
# print(connection.queries.__len__())

keyboard_first = json.dumps(
    {
        'keyboard': [[
            {'text': texts.search_by_medication_button},
            {'text': texts.product_of_the_day_button}
        ]],
        'resize_keyboard': True
    }
)


@app.task()
def send_message_the_first(id, start=True):
    if start:
        text = texts.start_message
    else:
        text = texts.before_search_button
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=text, reply_markup=keyboard_first)
    logger.info(f'Send the first message to {id=} successfully')


@app.task()
def send_message_districts(id):
    districts = District.objects.annotate(
        text=F('name'),
        callback_data=Concat(
            Value('district_'),
            Cast(F('id'), output_field=CharField()),
        )
    ).values('text', 'callback_data')
    inline_keyboard = batched(districts, 2)
    inline_keyboard[-1].append({'text': texts.all_districts, 'callback_data': 'district_all'})
    reply_markup = json.dumps({'inline_keyboard': inline_keyboard})
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.district, reply_markup=reply_markup)
    logger.info(f'Send message about districts to {id=} successfully')


@app.task()
def send_message_not_found(id):
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.not_found)
    logger.info(f'Send message not found to {id=} successfully')


@app.task()
def send_message_before_searching(id):
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.search_message)
    logger.info(f'Send message before searching to {id=} successfully')


@app.task()
def send_message_medication_buttons(id, medication_ids):
    medications = Medication.objects.filter(id__in=medication_ids).all()
    keyboard = batched([dict(text=f'💊 {str(i)}⠀') for i in medications], 1) # U+2800 after str(i) is a zero width space
    reply_markup = json.dumps(
        {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
    )
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.select_medication_or_search, reply_markup=reply_markup)
    logger.info(f'Send medication buttons message to {id=} successfully')


@app.task()
def send_message_search_result(id, medication_full_name):
    district = cache.get(f'{id}_district')
    if not district:
        logger.info(f'Cache for {id=} is empty')
        return
    medications = (Medication.objects.annotate(medication_full_name=Value(medication_full_name, output_field=CharField()))
                   .filter(medication_full_name__icontains=F('name')).all())
    medication = list(filter(lambda x: str(x) == medication_full_name, medications))[0]
    if district == 'all':
        where = Q(medication=medication)
    else:
        where = Q(medication=medication) & Q(pharmacy__district_id=district)
    stocks = PharmacyStock.objects.select_related('pharmacy__chain').filter(where).distinct('pharmacy__chain__name')
    stocks = sorted(stocks, key=lambda x: x.price, reverse=True)
    stocks_ids = list(PharmacyStock.objects.filter(where).values_list('id', flat=True).all())
    cache.set(id, stocks_ids, timeout=CACHE_TIMEOUT)
    for stock in stocks:
        text = f'🏥 {stock.pharmacy.chain.name} 💊 {medication} 💵 <b>{stock.price} грн.</b>\n\n'
        inline_keyboard = json.dumps({'inline_keyboard': [[{'text': texts.in_detail_text, 'callback_data': f'chain_{stock.pharmacy.chain.id}'}]]})
        send_message('sendMessage', chat_id=id, parse_mode='HTML', text=text, reply_markup=inline_keyboard)
        logger.info(f'Send message search result to {id=} successfully')
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.after_search_message, reply_markup=keyboard_first)


@app.task()
def send_message_pharmacy_address(id, chain_id):
    stocks_ids = cache.get(id)
    district = cache.get(f'{id}_district')
    if not stocks_ids or not district:
        logger.info(f'Cache for {id=} is empty')
        return
    if district == 'all':
        where = Q(Q(id__in=stocks_ids) & Q(pharmacy__chain_id=chain_id))
    else:
        where = Q(Q(id__in=stocks_ids) & Q(pharmacy__chain_id=chain_id) & Q(pharmacy__district_id=district))
    stocks = list(PharmacyStock.objects
                  .select_related('pharmacy__chain', 'pharmacy__address', 'pharmacy__district')
                  .prefetch_related('pharmacy__phone')
                  .filter(where)
                  .all())
    text = f'<b>🏥 {stocks[0].pharmacy.chain.name}</b>\n\n'
    if district != 'all':
        text += f'{stocks[0].pharmacy.district.name}:\n'
    for stock in stocks:
        text += f'{stock.pharmacy.address.name}\n'
        phones = ''
        if stock.pharmacy.phone.exists():
            for phone in stock.pharmacy.phone.all():
                phones += f'{phone.number}\n'
        text += phones
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=text)
    logger.info(f'Send message addresses of pharmacies to {id=} successfully')


@app.task()
def send_message_product_of_the_day(id):
    products = (ProductOfTheDay.objects
                .select_related('medication', 'medication__form', 'medication__units',
                                'pharmacy__chain', 'pharmacy__address')
                .prefetch_related('pharmacy__phone')
                .order_by('-price')
                .all())
    if not products:
        send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.product_of_the_day_not_found)
        logger.info(f'Send message product of the day not found to {id=} successfully')
        return
    if products:
        text = ''
        for product in products:
            medication = f'💊 {product.medication} 💵 <b>{product.price} грн.</b>\n'
            pharmacy = f'🏥{product.pharmacy}\n'
            phones = ''
            if product.pharmacy.phone.exists():
                for phone in product.pharmacy.phone.all():
                    phones += f'{phone.number}\n'
            text += medication + pharmacy + phones + '\n'
        send_message('sendMessage', chat_id=id, parse_mode='HTML', text=text)
        logger.info(f'Send message product of the day to {id=} successfully')
