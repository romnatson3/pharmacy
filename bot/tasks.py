import logging
import json
from celery.utils.log import get_task_logger
from app.celery import app
from django.db.models import F
from bot.misc import send_message, batched
from bot import texts
from bot.models import PharmacyStock, District, ProductOfTheDay


logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)


@app.task()
def send_message_to_new_user(id):
    reply_markup = json.dumps(
        {
            'keyboard': [[
                {'text': texts.search_by_medication_button},
                {'text': texts.product_of_the_day}
            ]],
            'resize_keyboard': True
        }
    )
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.start_message, reply_markup=reply_markup)
    logger.info(f'Send start message to {id=} successfully')


@app.task()
def send_message_districts(id):
    districts = District.objects.annotate(text=F('name'), callback_data=F('id')).values('text', 'callback_data')
    inline_keyboard = batched(districts, 2)
    inline_keyboard[-1].append({'text': texts.all_districts, 'callback_data': 'all_districts'})
    reply_markup = json.dumps({'inline_keyboard': inline_keyboard})
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.district, reply_markup=reply_markup)
    logger.info(f'Send message about districts to {id=} successfully')


@app.task()
def send_message_not_found(id):
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=f'<i>{texts.not_found}</i>')
    logger.info(f'Send message not found to {id=} successfully')


@app.task()
def send_message_before_searching(id):
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.search_message)
    logger.info(f'Send message before searching to {id=} successfully')


@app.task()
def send_message_search_result(id, stock_ids):
    stocks = (PharmacyStock.objects
              .select_related('medication', 'medication__form', 'medication__units',
                              'pharmacy__chain', 'pharmacy__address')
              .prefetch_related('pharmacy__phone')
              .filter(id__in=stock_ids)
              .order_by('price')
              .all()[:15])
    stocks = list(reversed(stocks))
    if stocks:
        text = ''
        for stock in stocks:
            pharmacy = f'{stock.pharmacy}\n'
            medication = f'💊 <b>{stock.medication} - {stock.price} грн.</b>\n'
            phones = ''
            if stock.pharmacy.phone.exists():
                for phone in stock.pharmacy.phone.all():
                    phones += f'{phone.number}\n'
            text += medication + pharmacy + phones + '\n'
        send_message('sendMessage', chat_id=id, parse_mode='HTML', text=text)
        logger.info(f'Send message search result to {id=} successfully')


@app.task()
def send_message_product_of_the_day(id):
    products = (ProductOfTheDay.objects
                .select_related('medication', 'medication__form', 'medication__units',
                                'pharmacy__chain', 'pharmacy__address')
                .prefetch_related('pharmacy__phone')
                .order_by('-price')
                .all())
    if not products:
        send_message('sendMessage', chat_id=id, parse_mode='HTML', text=f'<i>{texts.product_of_the_day_not_found}</i>')
        logger.info(f'Send message product of the day not found to {id=} successfully')
        return
    if products:
        text = ''
        for product in products:
            pharmacy = f'{product.pharmacy}\n'
            medication = f'💊 <b>{product.medication} - {product.price} грн.</b>\n'
            phones = ''
            if product.pharmacy.phone.exists():
                for phone in product.pharmacy.phone.all():
                    phones += f'{phone.number}\n'
            text += medication + pharmacy + phones + '\n'
        send_message('sendMessage', chat_id=id, parse_mode='HTML', text=text)
        logger.info(f'Send message product of the day to {id=} successfully')
