import logging
import json
from celery.utils.log import get_task_logger
from app.celery import app
from django.db.models import F
from bot.misc import send_message, batched
from bot import texts
from bot.models import PharmacyStock, District, Pharmacy


logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)


@app.task()
def send_message_to_new_user(id):
    reply_markup = json.dumps(
        {
            'keyboard': [[
                {'text': texts.search_by_medication_button},
            ]],
            'resize_keyboard': True
        }
    )
    send_message('sendMessage', chat_id=id, parse_mode='HTML', text=texts.start_message, reply_markup=reply_markup)
    logger.info(f'Send start message to {id=} successfully')


@app.task()
def send_message_districts(id):
    districts = District.objects.annotate(text=F('name'), callback_data=F('id')).values('text', 'callback_data')
    inline_keyboard = batched(districts, 3)
    inline_keyboard.append([{'text': texts.all_districts, 'callback_data': 'all_districts'}])
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
    stocks = PharmacyStock.objects.select_related('medication').filter(id__in=stock_ids).order_by('price').all()[:5]
    stocks = list(reversed(stocks))
    pharmacy_ids = [stock.pharmacy_id for stock in stocks]
    pharmacies = Pharmacy.objects.select_related('chain', 'address').prefetch_related('phone').filter(id__in=pharmacy_ids).all()
    if stocks:
        text = ''
        for stock in stocks:
            pharmacy = list(filter(lambda x: x.id == stock.pharmacy_id, pharmacies))[0]
            medication = f'<b>{stock.medication} - {stock.price} грн.</b>\n'
            phones = ''
            if pharmacy.phone.exists():
                for phone in pharmacy.phone.all():
                    phones += f'{phone.number}\n'
            text += medication + f'{pharmacy}\n' + phones + '\n'
        send_message('sendMessage', chat_id=id, parse_mode='HTML', text=text)
        logger.info(f'Send message search result to {id=} successfully')
